"""The handover.tools Worker (D47).

Routes, MCP and the self-describing docs are all derived from the registry, so they cannot drift apart.
"""
import json, time
from urllib.parse import urlparse, parse_qs
from workers import WorkerEntrypoint, Response

import meter, guard
from page import PAGE
from registry import all_tools, get_tool
# Tools register themselves on import. Add one import line and REST / MCP / discover all pick it up.
# domain_check was retired on 2026-09-22 (D15).
from tools import handoff, channel
import client_src, docs, fonts_src, icons

# MCP dual era (spec 2026-07-28)
#   modern (2026-07-28+): no handshake. Every request carries its version in params._meta, mirrored in HTTP headers;
#                         server/discover is a mandatory RPC; no sessions, no batching.
#   legacy (<=2025-11-25): an initialize handshake sets up the session.
# We serve both: requests with the modern _meta take the new path, initialize takes the old one (the spec's "dual-era server").
MCP_MODERN = "2026-07-28"
MCP_LEGACY = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05", "2024-10-07"]
MCP_SUPPORTED = [MCP_MODERN] + MCP_LEGACY
MCP_LATEST = MCP_MODERN
PV_KEY = "io.modelcontextprotocol/protocolVersion"

SITE = "handover.tools"                                  # product site (D47)
# Site icons: path -> (file name in fonts_src.IMAGES, None = icons.FAVICON_SVG; Content-Type)
ICON_FILES = {"/favicon.ico": ("favicon.ico", "image/x-icon"),
              "/favicon.svg": (None, "image/svg+xml"),
              "/icon-192.png": ("icon-192.png", "image/png"),
              "/apple-touch-icon.png": ("apple-touch-icon.png", "image/png"),
              # Official app icons of the two clients in the homepage example (96px App Store originals, D50). They only show which client it is; no partnership or endorsement implied
              "/img/client-muse.png": ("client-muse.png", "image/png"),
              "/img/client-claude.png": ("client-claude.png", "image/png")}

# Error codes the spec reserves for the protocol layer
E_HEADER_MISMATCH = -32020      # headers disagree with the body, or a required header is missing
E_UNSUPPORTED_VERSION = -32022  # we do not support the requested protocol version

INSTRUCTIONS = ("Hand work from one agent to another. handoff_* stores one piece of text behind an "
                "8-letter link (not encrypted); channel_* pairs two agents for multi-round, end-to-end "
                "encrypted exchange through the local client at /client/channel.py. Free; "
                "every call is metered at price 0. When a result cannot be determined "
                "the value is null with a reason field — never a guess. Prefer the "
                "structuredContent field over parsing the text output.")


def unb64(v):
    """Decode the spec's =?base64?...?= sentinel encoding, used to wrap non-ASCII header values."""
    if isinstance(v, str) and v.startswith("=?base64?") and v.endswith("?="):
        import base64
        try:
            return base64.b64decode(v[9:-2]).decode("utf-8")
        except Exception:
            return v
    return v

_swept_at = 0.0


# CORS fully open. Content is protected only by the code; there are no cookies or sessions, so open CORS lowers no security,
# while closed CORS makes browser-based agents fail in ways that are hard to figure out (D21).
CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Accept, MCP-Protocol-Version",
    "Access-Control-Max-Age": "86400",
}


def jres(obj, status=200, vary=None):
    headers = {"Content-Type": "application/json; charset=utf-8", "X-Robots-Tag": "noindex", **CORS}
    if vary:
        # The same URL serves HTML or JSON depending on Accept, so caches must keep them apart, or a crawler may get the noindex JSON
        headers["Vary"] = vary
    return Response(json.dumps(obj, ensure_ascii=False), status=status, headers=headers)


def wants_html(request) -> bool:
    """Only an explicit request for HTML gets the web page. curl sends */* by default, so the agent contract is unaffected."""
    return "text/html" in (request.headers.get("accept") or "")


def wants_home_page(request) -> bool:
    """Homepage only, looser than wants_html (D50): a browser-like UA sending */* or no Accept also gets the page.
    AI assistants' fetchers often request this way; they used to get the noindex JSON signpost and
    concluded it "isn't a usable website". curl / wget / SDK user agents don't contain Mozilla and still get JSON;
    an explicit application/json request always gets JSON."""
    accept = request.headers.get("accept") or ""
    if "text/html" in accept:
        return True
    if "application/json" in accept:
        return False
    return "mozilla" in (request.headers.get("user-agent") or "").lower()


class Default(WorkerEntrypoint):

    async def fetch(self, request):
        global _swept_at
        u = urlparse(str(request.url))
        path, base = u.path, f"{u.scheme}://{u.netloc}"

        await meter.ensure_schema(self.env)
        await guard.ensure_schema(self.env)
        if time.time() - _swept_at > 600:
            _swept_at = time.time()
            for _sweep in (guard.sweep, meter.sweep, handoff.sweep_expired, channel.sweep_expired):
                try:
                    await _sweep(self.env)
                except Exception:
                    pass

        if request.method == "OPTIONS":
            return Response("", status=204, headers=CORS)

        # Without redirecting http://, Google indexes http://handover.tools/ as a separate URL (Search Console
        # reports "Alternate page with proper canonical tag"). Only GET/HEAD redirect: a 301 turns POST into GET,
        # so agents calling the API over http keep working. Check CF-Visitor rather than u.scheme: local wrangler dev rewrites the URL
        # to http://handover.tools (see wrangler.toml), so judging by scheme would 301 the whole local site; locally this header is absent
        if ('"scheme":"http"' in (request.headers.get("cf-visitor") or "").replace(" ", "")
                and request.method in ("GET", "HEAD")):
            return Response("", status=301, headers={
                "Location": f"https://{SITE}{path}" + (f"?{u.query}" if u.query else ""),
                "Cache-Control": "public, max-age=86400"})

        if path == "/":
            if wants_home_page(request):
                return Response(PAGE, headers={
                    "Content-Type": "text/html; charset=utf-8",
                    "Cache-Control": "public, max-age=300",
                    "X-Content-Type-Options": "nosniff",
                    "Referrer-Policy": "no-referrer",
                    "Vary": "Accept, User-Agent",
                })
            return jres({
                "service": "handover.tools",
                "description": ("One agent writes it, another agent reads it; the person only carries an "
                                "8-letter link. One-shot: store a piece of context, get a link like "
                                "handover.tools/kvmtrhxp, give it to an agent on the other side. "
                                "Channel: two agents on two machines for multi-round work, "
                                "end-to-end encrypted, with a person approving every message."),
                "hand_off_now": ("Asked to hand something over (or off) with handover.tools? If you can run commands: "
                                 f"curl -s -X POST {base}/api/handoff/put -H 'Content-Type: application/json' "
                                 "-d '{\"content\":\"...\",\"label\":\"...\"}' (write long content to a file and "
                                 "use --data-binary @file). Tell the person the returned say_on_the_other_device; "
                                 "keep revoke_key in this conversation and do not show it. NOT encrypted: "
                                 "no credentials or private data. With MCP, use handoff_put instead."),
                "channel_now": ("Asked to open or join a handover.tools channel? It needs the local client "
                                f"(it does the encryption): follow the Channel part of {base}/llms.txt. "
                                "Ask the person before downloading and running it if you normally would."),
                "tools": [t.name for t in all_tools()],
                "discover": f"{base}/api/discover",
                "mcp": f"{base}/mcp",
                "web": f"{base}/ (open in a browser to fetch a handoff without an agent)",
                "channel_client": f"{base}{client_src.PATH}",
                "guide": f"{base}/guide (how to use; /guide.md for agents)",
                "security": f"{base}/security.md",
                "llms_txt": f"{base}/llms.txt",
                "note": ("/api/discover is the full reference (every tool and input schema). This response and any offline "
                         "documentation may be out of date."),
            }, vary="Accept, User-Agent")

        if path in docs.REDIRECTS:
            return Response("", status=301, headers={"Location": docs.REDIRECTS[path], **CORS})
        if path in docs.PAGES:
            # handoff docs: two pages for people, three files for LLMs (src/docs.py). Every number comes from implementation constants
            body, ctype = docs.PAGES[path]
            return Response(body, headers={"Content-Type": ctype,
                                           "Cache-Control": "public, max-age=300", **CORS})

        if path == "/og.png":
            # Social preview card (assets/og.html -> assets/gen_og.sh)
            import base64
            return Response(base64.b64decode(fonts_src.IMAGES["og.png"]), headers={
                "Content-Type": "image/png", "Cache-Control": "public, max-age=86400"})
        if path in ICON_FILES:
            # Site icons (assets/gen_icons.sh). Google search results only accept crawlable URLs, not data: URIs
            import base64
            name, ctype = ICON_FILES[path]
            data = icons.FAVICON_SVG.encode() if name is None else base64.b64decode(fonts_src.IMAGES[name])
            return Response(data, headers={"Content-Type": ctype, "Cache-Control": "public, max-age=86400"})
        if path == "/sitemap.xml":
            urls = "".join(f"<url><loc>https://{SITE}{p}</loc></url>"
                           for p in ("/", "/guide", "/security", "/terms", "/privacy", "/changelog"))
            return Response('<?xml version="1.0" encoding="UTF-8"?>'
                            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
                            headers={"Content-Type": "application/xml; charset=utf-8",
                                     "Cache-Control": "public, max-age=3600"})
        if path == "/.well-known/security.txt":
            return Response(docs.security_txt(), headers={"Content-Type": "text/plain; charset=utf-8",
                                                          "X-Robots-Tag": "noindex",
                                                          "Cache-Control": "public, max-age=86400"})
        if path == "/robots.txt":
            # Cloudflare's managed robots.txt may prepend its content-signal comments; the rules and Sitemap here are authoritative
            return Response(f"User-agent: *\nAllow: /\n\nSitemap: https://{SITE}/sitemap.xml\n",
                            headers={"Content-Type": "text/plain; charset=utf-8",
                                     "Cache-Control": "public, max-age=3600"})

        if path.startswith("/fonts/"):
            # Self-hosted fonts (D30). File names carry a content hash as ?v=, so they can be cached for a long time
            hit = fonts_src.FONTS.get(path[len("/fonts/"):])
            if not hit:
                return jres({"error": "not_found"}, 404)
            import base64
            return Response(base64.b64decode(hit[0]), headers={
                "Content-Type": "font/woff2", "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=31536000, immutable"})

        if path == client_src.PATH:
            # The local encryption client for channel. The server only moves ciphertext; all crypto happens in this script (D26).
            # Downloading the client from us means trusting us once more. So we also publish its sha256
            # and say in discover: if you care, verify it against the source repository.
            return Response(client_src.SRC, headers={
                "Content-Type": "text/x-python; charset=utf-8",
                "X-Content-SHA256": client_src.SHA256, **CORS})

        if path == "/api/health":
            return jres({"ok": True, "ts": time.time()})

        if path == "/api/usage":
            return jres(await guard.usage_snapshot(self.env, meter.caller_of(request)))

        if path == "/api/discover":
            return await self._discover(request, base, u)

        if path == "/mcp":
            if request.method != "POST":
                return jres({"error": "method_not_allowed", "hint": "The MCP endpoint accepts POST only."}, 405)
            return await self._mcp(request)

        for t in all_tools():
            if path == t.path:
                return await self._rest(request, t, u)

        # Short URL handover.tools/kvmtrhxp (D38, D39): the code is itself a URL, and the prompt includes the domain,
        # so an agent with nothing configured knows where to fetch. **Opening it does not use up the code**: it only returns instructions, and the real read is a second request;
        # otherwise pasting the link into a chat app would let the preview crawler burn the read-once content (D21).
        code = handoff._normalize(path.lstrip("/"))
        if code and path.count("/") == 1:
            pretty = handoff._pretty(code)
            if wants_html(request):
                # Opened with a code: move the fetch box to the top (.home.prefill, set server-side so it doesn't flash)
                return Response(PAGE.replace('<div class="home">', '<div class="home prefill">', 1)
                                    .replace("<script>\n// Crockford",
                                             f'<script>window.PREFILL = "{code}";</script>\n<script>\n// Crockford', 1),
                                headers={"Content-Type": "text/html; charset=utf-8", "X-Robots-Tag": "noindex",
                                         "Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
            return Response(docs.code_landing(pretty, base), headers={
                "Content-Type": "text/markdown; charset=utf-8", "Cache-Control": "no-store",
                "X-Robots-Tag": "noindex", **CORS})

        return jres({"error": "not_found", "hint": "See / or /api/discover"}, 404)

    # ---------- self-describing docs ----------
    async def _discover(self, request, base, u):
        caller = meter.caller_of(request)
        doc = {
            "service": "handover.tools",
            "base": base,
            "conventions": [
                "When a result cannot be determined, the value is null and a reason is given. "
                "Nothing is ever guessed.",
                "Every call is metered (current price: 0). Free quota is per-IP per-day; "
                "a service-wide daily cap also applies.",
                "This document is generated from the tool registry, so it can never drift "
                "from the implementation.",
                "handoff_* is NOT encrypted. channel_* is end-to-end encrypted and must be used "
                "through the local client; see security for the threat model and what is "
                "not claimed.",
            ],
            "how_to_use": f"{base}/guide.md",
            "source": "https://github.com/gammaland/handover",
            "changelog": f"{base}/changelog.md",
            "privacy": f"{base}/privacy.md",
            "security": f"{base}/security.md",
            "usage": await guard.usage_snapshot(self.env, caller),
            "channel_client": {
                "url": f"{base}{client_src.PATH}",
                "sha256": client_src.SHA256,
                "run": f"curl -sO {base}{client_src.PATH} && uv run channel.py --help",
                "why": ("channel_* tools move only ciphertext. Pairing (SPAKE2) and encryption "
                        "(ChaCha20-Poly1305) happen in this local client, so the server never "
                        "sees plaintext or the key. Downloading the client from the same server "
                        "means trusting it once more; verify the sha256 against the source "
                        "if that matters to you."),
                "source": "https://github.com/gammaland/handover/blob/main/client/channel.py",
            },
            "mcp": {
                "endpoint": f"{base}/mcp",
                "transport": "streamable-http",
                "protocol": MCP_LATEST,
                "supported_versions": MCP_SUPPORTED,
                "eras": ("Dual-era. Modern clients (2026-07-28) send the protocol version in "
                         "params._meta and mirror it into the MCP-Protocol-Version header; "
                         "server/discover returns everything in one call. Legacy clients "
                         "(2025-11-25 and earlier) use the initialize handshake. Both work."),
                "not_implemented": ("SSE response streams, MRTR input requests, and "
                                    "subscriptions/listen — this server answers every request "
                                    "with a single JSON object, which the spec permits."),
            },
            "tools": [{
                "name": t.name, "title": t.title, "summary": t.summary,
                "rest": f"GET|POST {base}{t.path}",
                "input_schema": t.input_schema,
                "cost_micro_usd": t.cost_micro,
                "examples": [e.replace("$BASE", base) for e in t.examples],
            } for t in all_tools()],
        }
        if parse_qs(u.query).get("format", [""])[0] == "text":
            L = ["# handover.tools", "", f"Base: {base}", "", "## Conventions"]
            L += [f"- {c}" for c in doc["conventions"]]
            L += ["", "## Tools"]
            for t in doc["tools"]:
                L += ["", f"### {t['name']} — {t['title']}", t["summary"], "", f"`{t['rest']}`"]
                L += [f"    {e}" for e in t["examples"]]
            return Response("\n".join(L),
                            headers={"Content-Type": "text/plain; charset=utf-8", **CORS})
        return jres(doc)

    # ---------- REST ----------
    async def _rest(self, request, t, u):
        caller = meter.caller_of(request)
        verdict = await (guard.admit_keyed if t.keyed else guard.admit)(self.env, caller)
        if not verdict["ok"]:
            await meter.record(self.env, tool=t.name, caller=caller, transport="rest",
                               status="rate_limited", cost_micro=0, duration_ms=0)
            return jres(verdict["body"], verdict["status"])

        if request.method == "POST":
            try:
                args = json.loads(await request.text())
            except Exception:
                args = {}
        else:
            q = parse_qs(u.query)
            args = {k: v[0] for k, v in q.items()}
        args["_caller"] = caller

        t0 = time.time()
        try:
            out = await t.run(args, self.env)
            await meter.record(self.env, tool=t.name, caller=caller, transport="rest",
                               status="ok", cost_micro=t.cost_micro,
                               duration_ms=(time.time() - t0) * 1000)
            return jres(out)
        except Exception as e:
            await meter.record(self.env, tool=t.name, caller=caller, transport="rest",
                               status="error", cost_micro=0,
                               duration_ms=(time.time() - t0) * 1000, meta=str(e))
            return jres({"error": f"{type(e).__name__}: {e}"}, 500)

    # ---------- MCP (JSON-RPC 2.0) ----------
    async def _mcp(self, request):
        try:
            body = json.loads(await request.text())
        except Exception:
            return jres({"jsonrpc": "2.0", "id": None,
                         "error": {"code": -32700, "message": "Parse error"}}, 400)

        hdr_ver = request.headers.get("mcp-protocol-version")

        # Batching: modern explicitly allows only a single request/notification. The legacy era keeps supporting it.
        if isinstance(body, list):
            if hdr_ver == MCP_MODERN or any(self._is_modern(m) for m in body if isinstance(m, dict)):
                return jres({"jsonrpc": "2.0", "id": None, "error": {
                    "code": E_HEADER_MISMATCH,
                    "message": ("Batched requests are not part of protocol version "
                                f"{MCP_MODERN}. Send one JSON-RPC message per POST.")}}, 400)
            out = [r for (r, _) in [await self._rpc(m, request) for m in body] if r]
            return jres(out) if out else Response("", status=202)

        r, status = await self._rpc(body, request)
        if r is None:
            return Response("", status=202, headers=CORS)
        return jres(r, status)

    @staticmethod
    def _is_modern(msg) -> bool:
        """The test is "did it use the modern way of declaring a version", not "do we recognise the declared value".

        This was first written as `meta.get(PV_KEY) == MCP_MODERN`, so a request declaring an unknown version
        slid into the legacy path and was handled as a normal request: it returned 200 where it should have returned -32022.
        Legacy clients never send PV_KEY in _meta, so "is this key present" is the era test.
        """
        meta = ((msg.get("params") or {}).get("_meta") or {})
        return PV_KEY in meta

    def _modern_guard(self, request, msg, mid):
        """Header checks for the modern era. Returns (error body, http status) or None.

        Only applies to requests that **declare modern intent**: legacy clients don't send these headers,
        and the spec allows treating a request without them as an older version, so this can't be enforced across the board.
        """
        h = request.headers
        method = msg.get("method")
        params = msg.get("params") or {}
        body_ver = (params.get("_meta") or {}).get(PV_KEY)
        hdr_ver = h.get("mcp-protocol-version")

        def bad(code, message, data=None):
            e = {"code": code, "message": message}
            if data:
                e["data"] = data
            return ({"jsonrpc": "2.0", "id": mid, "error": e}, 400)

        # Headers and body must agree (intermediaries route by header, the server executes by body; a mismatch is a security hole)
        if hdr_ver and body_ver and hdr_ver != body_ver:
            return bad(E_HEADER_MISMATCH,
                       f"MCP-Protocol-Version header {hdr_ver!r} does not match "
                       f"_meta value {body_ver!r}.")
        ver = body_ver or hdr_ver
        if ver not in MCP_SUPPORTED:
            return bad(E_UNSUPPORTED_VERSION, "Unsupported protocol version",
                       {"supported": MCP_SUPPORTED, "requested": ver})

        if not h.get("mcp-method"):
            return bad(E_HEADER_MISMATCH, "Missing required Mcp-Method header.")
        if h.get("mcp-method") != method:
            return bad(E_HEADER_MISMATCH,
                       f"Mcp-Method header {h.get('mcp-method')!r} does not match "
                       f"body method {method!r}.")
        if method == "tools/call":
            name = params.get("name")
            got = unb64(h.get("mcp-name"))
            if not got:
                return bad(E_HEADER_MISMATCH, "Missing required Mcp-Name header for tools/call.")
            if got != name:
                return bad(E_HEADER_MISMATCH,
                           f"Mcp-Name header {got!r} does not match body name {name!r}.")
        return None

    async def _rpc(self, msg, request):
        """Returns (response body or None, http status). A notification returns (None, 202)."""
        mid = msg.get("id")
        method = msg.get("method")
        params = msg.get("params") or {}
        modern = self._is_modern(msg) or request.headers.get("mcp-protocol-version") == MCP_MODERN
        # In the modern era **every** result must carry resultType (always "complete" without MRTR).
        # It used to be added only to server/discover, and Claude Code rejected tools/list (found by the user on 2026-09-30)
        ok = lambda res: ({"jsonrpc": "2.0", "id": mid,
                           "result": {"resultType": "complete", **res} if modern else res}, 200)
        err = lambda c, m, st=200: ({"jsonrpc": "2.0", "id": mid,
                                     "error": {"code": c, "message": m}}, st)

        if modern:
            bad = self._modern_guard(request, msg, mid)
            if bad:
                return bad

        # server/discover: the mandatory RPC of the modern era, replacing the initialize handshake
        if method == "server/discover":
            return ok({
                "supportedVersions": MCP_SUPPORTED,
                "capabilities": {"tools": {}},
                "_meta": {"io.modelcontextprotocol/serverInfo":
                          {"name": "handover.tools", "version": "1.0.0"}},
                "instructions": INSTRUCTIONS,
                "ttlMs": 3600000,
                "cacheScope": "public",
            })

        if method == "initialize":
            # Legacy entry point. Modern clients never get here.
            want = params.get("protocolVersion")
            return ok({
                "protocolVersion": want if want in MCP_LEGACY else MCP_LEGACY[0],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "handover.tools", "version": "1.0.0"},
                "instructions": INSTRUCTIONS,
            })
        if method == "notifications/initialized":
            return (None, 202)
        if method == "ping":
            return ok({})
        if method == "tools/list":
            res = {"tools": [{"name": t.name, "title": t.title,
                              "description": t.summary, "inputSchema": t.input_schema}
                             for t in all_tools()]}
            if modern:
                # Modern list results must carry cache hints (Claude Code rejects them otherwise, D41). The tool list is the same for everyone
                res.update({"ttlMs": 3600000, "cacheScope": "public"})
            return ok(res)
        if method == "tools/call":
            t = get_tool(params.get("name"))
            if not t:
                return err(-32602, f"unknown tool: {params.get('name')}")

            caller = meter.caller_of(request)
            verdict = await (guard.admit_keyed if t.keyed else guard.admit)(self.env, caller)
            if not verdict["ok"]:
                await meter.record(self.env, tool=t.name, caller=caller, transport="mcp",
                                   status="rate_limited", cost_micro=0, duration_ms=0)
                return ok({"isError": True, "content": [
                    {"type": "text", "text": json.dumps(verdict["body"], ensure_ascii=False)}]})

            t0 = time.time()
            try:
                margs = dict(params.get("arguments") or {})
                margs["_caller"] = caller
                out = await t.run(margs, self.env)
                await meter.record(self.env, tool=t.name, caller=caller, transport="mcp",
                                   status="ok", cost_micro=t.cost_micro,
                                   duration_ms=(time.time() - t0) * 1000)
                return ok({"content": [{"type": "text",
                                        "text": json.dumps(out, ensure_ascii=False, indent=2)}],
                           "structuredContent": out})
            except Exception as e:
                await meter.record(self.env, tool=t.name, caller=caller, transport="mcp",
                                   status="error", cost_micro=0,
                                   duration_ms=(time.time() - t0) * 1000, meta=str(e))
                return ok({"isError": True, "content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}]})

        if mid is None:
            return (None, 202)
        # The modern era requires unknown methods to return HTTP 404, to tell it apart from
        # the 404 of a legacy server that simply lacks the endpoint (that one has no JSON-RPC error body)
        return err(-32601, f"Method not found: {method}", 404 if modern else 200)
