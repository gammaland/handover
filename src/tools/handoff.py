"""handoff: hand context from one device to another.

Put some content in and get an 8-letter code; enter the code on another device to take it.
Contract: docs/spec/handoff.md. Architecture: docs/system-design.md.

v1 is NOT encrypted: the server can read the content. This must appear in the tool description and /api/discover,
      not just in a code comment.
"""
import hashlib, time, unicodedata
from datetime import datetime, timezone

import guard
from registry import tool

# Crockford base32, without the easily confused I L O U
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
# Codes people type use letters only (D39): switching between letters and digits on a phone keyboard is the worst part. 22 letters, 8 of them = about 5.5e10.
# Validation still uses _ALPHABET: old codes with digits must still work, and the I/L/O/U folding stays.
_LETTERS = "ABCDEFGHJKMNPQRSTVWXYZ"
_CODE_LEN = 8
_MAX_BYTES = 256 * 1024
_MAX_LABEL = 120
_DEFAULT_TTL_MIN = 60
_MAX_TTL_MIN = 1440
_REVOKE_LEN = 26            # about 130 bits. Not meant to be typed; the writing agent keeps it

_ready = False


async def ensure_schema(env):
    global _ready
    if _ready:
        return
    await env.DB.prepare(
        "CREATE TABLE IF NOT EXISTS handoffs ("
        " code_hash TEXT PRIMARY KEY, content TEXT NOT NULL,"
        " label TEXT NOT NULL DEFAULT '', burn INTEGER NOT NULL DEFAULT 1,"
        " reads INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL,"
        " expires_at INTEGER NOT NULL, creator TEXT NOT NULL DEFAULT '',"
        " revoke_hash TEXT NOT NULL DEFAULT '')"
    ).run()
    # The table may predate revoke_hash (the first version went to production on 09-23), so add the column. If it exists this raises; swallow it.
    try:
        await env.DB.prepare(
            "ALTER TABLE handoffs ADD COLUMN revoke_hash TEXT NOT NULL DEFAULT ''").run()
    except Exception:
        pass
    await env.DB.prepare(
        "CREATE INDEX IF NOT EXISTS idx_handoffs_expires ON handoffs(expires_at)").run()
    await env.DB.prepare(
        "CREATE INDEX IF NOT EXISTS idx_handoffs_revoke ON handoffs(revoke_hash)").run()
    _ready = True


async def sweep_expired(env):
    """Lazy cleanup. Fetching deletes too; this catches the ones nobody fetches."""
    await env.DB.prepare("DELETE FROM handoffs WHERE expires_at <= ?1").bind(
        int(time.time())).run()


def _random_bytes(n: int) -> bytes:
    """CSPRNG. os.urandom usually works under Pyodide; otherwise fall back to JS crypto."""
    try:
        from secrets import token_bytes
        return token_bytes(n)
    except Exception:
        from js import crypto, Uint8Array
        buf = Uint8Array.new(n)
        crypto.getRandomValues(buf)
        return bytes(buf.to_py())


def _new_code(n: int = _CODE_LEN) -> str:
    # 256 % 32 == 0, so byte % 32 has no modulo bias
    return "".join(_ALPHABET[b % 32] for b in _random_bytes(n))


def _new_spoken(n: int = _CODE_LEN) -> str:
    """A code for people to type: letters only. 256 % 22 != 0, so drop bytes >= 242 (rejection sampling) to avoid bias."""
    out = []
    while len(out) < n:
        out += [_LETTERS[b % 22] for b in _random_bytes(n * 2) if b < 242]
    return "".join(out[:n])


def _pretty(code: str) -> str:
    # Shown lowercase, without a hyphen (D39): the other side types it into handover.tools/<code> as is, no shift key and no symbol keyboard
    return code.lower()


def _normalize(raw) -> str | None:
    """A typed code may have hyphens, lowercase, or 0/O and 1/I/L mixed up. Fold them all into one form.

    NFKC first: full-width characters from Chinese input methods (１Ｃ３Ｈ) must fold to half-width; otherwise isalnum() accepts them
    but they are not in the alphabet, and the whole code is rejected (found in production on 2026-09-29)."""
    t = unicodedata.normalize("NFKC", str(raw or "")).strip()
    # People give the agent "handover.tools/kvmtrhxp", and agents often pass the whole link through (D38)
    if "code=" in t:
        t = t.split("code=")[-1].split("&")[0]
    elif "/" in t:
        t = t.rstrip("/").split("/")[-1]
    s = "".join(ch for ch in t.upper() if ch.isalnum())
    s = s.replace("I", "1").replace("L", "1").replace("O", "0").replace("U", "V")
    if len(s) != _CODE_LEN or any(ch not in _ALPHABET for ch in s):
        return None
    return s


def _hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _iso(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), timezone.utc).isoformat()


def _truthy(v, default: bool) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "yes", "on")


# --------------------------------------------------------------------------- put
@tool(
    name="handoff_put",
    title="Hand off context to another device",
    summary=(
        "Store a piece of context and get back a short code. The person gives the link "
        "handover.tools/<code> to an agent on another device and it can fetch the content — no copy-paste "
        "of long text. The code is 8 letters, easy to type on a phone. "
        "NOT ENCRYPTED: the server can read what you store, so never put credentials, tokens, "
        "or private data in it. Content becomes unreadable after the TTL expires, and by default "
        "it can only be fetched once. The response also returns a revoke_key — keep it for the "
        "rest of this session so you can destroy the content immediately with handoff_revoke if "
        "the person changes their mind. Writes are limited to a small number per day; reads are not."
    ),
    path="/api/handoff/put",
    input_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string",
                        "description": "The text to hand off. Maximum 256 KB of UTF-8."},
            "label": {"type": "string",
                      "description": "Optional short hint shown to whoever fetches it, so they "
                                     "can confirm they got the right thing. Max 120 characters."},
            "ttl_minutes": {"type": "integer",
                            "description": "Minutes until the content can no longer be fetched. "
                                           "Default 60, maximum 1440 (24h)."},
            "burn_after_read": {"type": "boolean",
                                "description": "If true (the default) the content can be fetched "
                                               "exactly once and is deleted on that fetch."},
        },
        "required": ["content"],
    },
    examples=[
        'curl -X POST $BASE/api/handoff/put -d \'{"content":"...session summary...","label":"design notes"}\'',
    ],
)
async def handoff_put(args, env):
    await ensure_schema(env)

    # Write gate (D20): an order of magnitude tighter than the general quota. **Validate the content before charging the quota**,
    # otherwise one malformed request would eat a tenth of the daily write allowance.
    content = args.get("content")
    if not isinstance(content, str) or not content.strip():
        return {"code": None, "reason": "content is required and must be a non-empty string."}

    size = len(content.encode("utf-8"))
    if size > _MAX_BYTES:
        return {"code": None,
                "reason": f"content is {size} bytes; the limit is {_MAX_BYTES} bytes."}

    try:
        ttl = int(args.get("ttl_minutes") or _DEFAULT_TTL_MIN)
    except (TypeError, ValueError):
        return {"code": None, "reason": "ttl_minutes must be an integer."}
    ttl = max(1, min(ttl, _MAX_TTL_MIN))

    label = str(args.get("label") or "")[:_MAX_LABEL]
    burn = _truthy(args.get("burn_after_read"), True)

    caller = str(args.get("_caller") or "")
    gate = await guard.take_write(env, caller)
    if not gate["ok"]:
        return {"code": None, "reason": gate["reason"],
                "writes_today": gate["used"], "writes_per_day": gate["limit"]}

    now = int(time.time())
    expires = now + ttl * 60
    code = _new_spoken()
    revoke = _new_code(_REVOKE_LEN)

    await env.DB.prepare(
        "INSERT INTO handoffs (code_hash, content, label, burn, reads, created_at,"
        " expires_at, creator, revoke_hash) VALUES (?1,?2,?3,?4,0,?5,?6,?7,?8)"
    ).bind(_hash(code), content, label, 1 if burn else 0, now, expires,
           caller, _hash(revoke)).run()

    return {
        "code": _pretty(code),
        "revoke_key": revoke,
        "label": label or None,
        "bytes": size,
        "burn_after_read": burn,
        "expires_at": _iso(expires),
        "expires_in_minutes": ttl,
        "writes_today": gate["used"],
        "writes_per_day": gate["limit"],
        "say_on_the_other_device": f"handover.tools/{_pretty(code)}",
        "tell_the_person": (f"Tell the person to give this link to an agent on the other device: "
                            f"handover.tools/{_pretty(code)} (nothing else needed; any agent that can open "
                            f"a web page can follow it, and a browser works too). It can be fetched once, until "
                            f"{_iso(expires)}."),
        "keep_revoke_key": ("Store revoke_key for this session. It is shown once and is the only "
                            "way to destroy this content before it expires."),
    }


# --------------------------------------------------------------------------- get
@tool(
    name="handoff_get",
    title="Fetch context handed off from another device",
    summary=(
        "Fetch content stored by handoff_put using its 8-character code. The code is "
        "case-insensitive and hyphens are ignored, so 'kvmtrhxp' and 'KVMT-RHXP' are the same; "
        "the person may give it as a link like handover.tools/kvmtrhxp, and passing that is fine too. "
        "Return the content to the person verbatim and complete: it can be fetched only once. "
        "If the code is unknown, already fetched, or expired, content is null with a reason — "
        "these cases are deliberately indistinguishable."
    ),
    path="/api/handoff/get",
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string",
                     "description": "The 8-character code from handoff_put, e.g. 'kvmtrhxp'."},
        },
        "required": ["code"],
    },
    examples=['curl "$BASE/api/handoff/get?code=kvmtrhxp"'],
)
async def handoff_get(args, env):
    await ensure_schema(env)

    code = _normalize(args.get("code"))
    if not code:
        return {"content": None,
                "reason": "code must be 8 characters from the Crockford base32 alphabet "
                          "(hyphens and case are ignored)."}

    now = int(time.time())
    h = _hash(code)

    # Read once: deleting is fetching. Under concurrency D1 gives the RETURNING row to only one request.
    row = await env.DB.prepare(
        "DELETE FROM handoffs WHERE code_hash=?1 AND expires_at>?2 AND burn=1"
        " RETURNING content, label, created_at"
    ).bind(h, now).first()
    if row:
        return {"content": row.content, "label": row.label or None,
                "created_at": _iso(row.created_at), "burn_after_read": True,
                "reads": 1, "burned": True, "reason": None}

    # Not read-once: increment the read count
    row = await env.DB.prepare(
        "UPDATE handoffs SET reads=reads+1 WHERE code_hash=?1 AND expires_at>?2 AND burn=0"
        " RETURNING content, label, created_at, reads, expires_at"
    ).bind(h, now).first()
    if row:
        return {"content": row.content, "label": row.label or None,
                "created_at": _iso(row.created_at), "burn_after_read": False,
                "reads": int(row.reads), "burned": False,
                "expires_at": _iso(row.expires_at), "reason": None}

    return {"content": None, "reason": "not_found_or_expired"}


# --------------------------------------------------------------------------- revoke
@tool(
    name="handoff_revoke",
    title="Destroy handed-off content immediately",
    summary=(
        "Destroy content stored by handoff_put right now, before its TTL runs out and whether or "
        "not it has been fetched. Requires the revoke_key returned by handoff_put — the person "
        "fetching with the short code cannot revoke, only the writer can. Use this the moment "
        "someone says they sent the wrong thing, or changed their mind. Revoking an already gone "
        "item is not an error: the outcome is reported as 'already_gone'."
    ),
    path="/api/handoff/revoke",
    input_schema={
        "type": "object",
        "properties": {
            "revoke_key": {"type": "string",
                           "description": "The revoke_key returned by handoff_put. Not the short "
                                          "code — the short code cannot destroy anything."},
        },
        "required": ["revoke_key"],
    },
    examples=['curl -X POST $BASE/api/handoff/revoke -d \'{"revoke_key":"..."}\''],
)
async def handoff_revoke(args, env):
    await ensure_schema(env)

    raw = "".join(ch for ch in unicodedata.normalize("NFKC", str(args.get("revoke_key") or "")).upper()
                  if ch.isalnum())
    if len(raw) != _REVOKE_LEN or any(ch not in _ALPHABET for ch in raw):
        return {"revoked": False, "reason": (
            f"revoke_key must be the {_REVOKE_LEN}-character key returned by handoff_put. "
            "The short handoff code cannot revoke.")}

    # The delete itself is atomic: of concurrent repeated revokes only one gets the row; the others honestly report already_gone.
    row = await env.DB.prepare(
        "DELETE FROM handoffs WHERE revoke_hash=?1 RETURNING label, expires_at"
    ).bind(_hash(raw)).first()
    if not row:
        return {"revoked": False, "reason": "already_gone",
                "detail": ("Nothing matched that revoke_key: it was already revoked, already "
                           "fetched and burned, or it expired. The content is not retrievable "
                           "either way.")}
    return {"revoked": True, "label": row.label or None,
            "would_have_expired_at": _iso(row.expires_at), "reason": None}
