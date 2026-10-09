#!/bin/bash
# Platform end-to-end tests. Run scripts/dev.sh first for local; for production use BASE=https://handover.tools tests/e2e.sh
B=${BASE:-http://127.0.0.1:8787}
# Write tests use up the daily write quota (10/day, D20). Locally run them freely; against production they are skipped by default,
# set WRITES=1 explicitly to really run the write paths. This is the real cost D20 ran into on day one.
case "$B" in *127.0.0.1*|*localhost*) WRITES=${WRITES:-1} ;; *) WRITES=${WRITES:-0} ;; esac
# Local: reset counters first, otherwise a second run in a row hits the write quota and reports a pile of false failures
case "$B" in *127.0.0.1*|*localhost*)
  (cd "$(dirname "$0")/.." && PATH="/opt/homebrew/opt/node@22/bin:$PATH" npx wrangler d1 execute handover-tools --local --command "DELETE FROM counters" >/dev/null 2>&1) ;; esac
pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  ✅ $1"; pass=$((pass+1));
        else echo "  ❌ $1 — expected [$3] got [$2]"; fail=$((fail+1)); fi; }
j() { python3 -c "import json,sys;d=json.load(sys.stdin);print(json.dumps(d$1) if isinstance(d$1,(dict,list)) else d$1)" 2>/dev/null; }

echo "── platform (system-design §3) ──"
chk "health"              "$(curl -s $B/api/health | j "['ok']")" "True"
chk "health hides the runtime"   "$(curl -s $B/api/health | j "['ok']")$(curl -s $B/api/health | grep -c runtime)" "True0"
chk "GET / signpost"         "$(curl -s $B/ | j "['service']")" "handover.tools"
chk "points to discover"        "$(curl -s $B/ | j "['discover']" | grep -c discover)" "1"
chk "404 has a hint"          "$(curl -s $B/nope | j "['error']")" "not_found"

echo "── fetch page / CORS (system-design §3, spec/handoff §4) ──"
chk "browser gets HTML"       "$(curl -s -H 'Accept: text/html' $B/ | head -c 15)" "<!doctype html>"
chk "page has the fetch input"       "$(curl -s -H 'Accept: text/html' $B/ | grep -c 'id="code"')" "1"
chk "fetch script is in the page"          "$(curl -s -H 'Accept: text/html' $B/ | grep -c 'function fetchIt')" "1"
chk "homepage footer doesn't repeat For agents"  "$(curl -s -H 'Accept: text/html' $B/ | sed -n '/<footer>/,/<\/footer>/p' | grep -c 'Agents: start with')" "0"
chk "subpage footers keep the agents link"  "$(curl -s $B/guide | sed -n '/<footer>/,/<\/footer>/p' | grep -c 'Agents: start with')" "1"
chk "fonts self-hosted (woff2)"        "$(curl -s -o /dev/null -w '%{content_type}' $B/fonts/atkinson-hyperlegible-next.woff2)" "font/woff2"
chk "page links no external fonts"        "$(curl -s -H 'Accept: text/html' $B/ | grep -c 'fonts.googleapis\|fonts.gstatic')" "0"
chk "page never fetches from the URL automatically"  "$(curl -s -H 'Accept: text/html' $B/ | grep -ci 'location.search\|URLSearchParams')" "0"
chk "curl still gets JSON by default"     "$(curl -s $B/ | j "['service']")" "handover.tools"
chk "JSON points to the web page"      "$(curl -s $B/ | j "['web']" | grep -c browser)" "1"
# D50: AI assistants' fetchers often send */* + a browser UA; they used to get the noindex JSON and called it "not a usable website"
chk "browser UA with */* gets the page"    "$(curl -s -A 'Mozilla/5.0 (compatible; Google-Extended)' -H 'Accept: */*' $B/ | head -c 15)" "<!doctype html>"
chk "browser UA without Accept gets the page" "$(curl -s -A 'Mozilla/5.0' -H 'Accept:' $B/ | head -c 15)" "<!doctype html>"
chk "explicit JSON request gets JSON"        "$(curl -s -A 'Mozilla/5.0' -H 'Accept: application/json' $B/ | j "['service']")" "handover.tools"
chk "homepage says what it is first"              "$(curl -s -H 'Accept: text/html' $B/ | grep -c 'Hand work from one AI agent to another')" "1"
chk "homepage explains the difference"                "$(curl -s -H 'Accept: text/html' $B/ | grep -c 'A handoff, not a workspace')" "1"
chk "client icons on both ends of the example"      "$(curl -s -o /dev/null -w '%{http_code}' $B/img/client-muse.png)$(curl -s -o /dev/null -w '%{http_code}' $B/img/client-claude.png)$(curl -s -H 'Accept: text/html' $B/ | grep -c 'class="client"><img')" "2002002"
chk "opened with a code, fetch box comes first"         "$(curl -s -H 'Accept: text/html' $B/kvmtrhxp | grep -c 'class="home prefill"')$(curl -s -H 'Accept: text/html' $B/ | grep -c 'home prefill')" "10"
chk "code links only look at Accept; */* still gets instructions" "$(curl -s -A 'Mozilla/5.0' -H 'Accept: */*' $B/kvmtrhxp | head -c 15)" "# handover code"
chk "CORS open"             "$(curl -s -D- -o /dev/null $B/api/health | grep -ci 'access-control-allow-origin: \*')" "1"
chk "OPTIONS preflight -> 204"    "$(curl -s -o /dev/null -w '%{http_code}' -X OPTIONS $B/mcp)" "204"

echo "── public docs ──"
chk "/guide how-to"         "$(curl -s -o /dev/null -w '%{http_code}' $B/guide)" "200"
chk "guide has the comparison table"           "$(curl -s $B/guide | grep -c 'Compared with clipboards and magic-wormhole')" "1"
chk "/security"       "$(curl -s -o /dev/null -w '%{http_code}' $B/security)" "200"
chk "guide uses the short-link prompt"      "$(curl -s $B/guide | grep -c '<span class="chip">handover.tools/')" "1"
chk "revoke says only the same conversation can"      "$(curl -s $B/guide | grep -c 'Only the conversation that handed it off can')" "1"
chk "discloses the web analytics script"          "$(curl -s $B/security | grep -c 'Cloudflare Web Analytics')" "1"
chk "the LLM version discloses it too"        "$(curl -s $B/security.md | grep -c 'Cloudflare Web Analytics')" "1"
chk "security states one-shot is unencrypted"      "$(curl -s $B/security | grep -c 'One-shot is not encrypted')" "1"
chk "separate architecture diagram per mode"        "$(curl -s $B/security | grep -o 'class="flow"' | wc -l | tr -d ' ')" "2"
chk "guide explains how data is destroyed"          "$(curl -s $B/guide | grep -c 'What happens to your data')" "1"
chk "every page has the same header"        "$(for u in / /guide /security; do curl -s -H 'Accept: text/html' $B$u | grep -c 'class="brand" href="/"'; done | tr -d '\n')" "111"
chk "/guide.md for LLMs"       "$(curl -s $B/guide.md | head -1)" "# handover"
chk "/security.md"           "$(curl -s $B/security.md | head -1)" "# handover security"
chk "old path 301s"              "$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' $B/how-it-works | sed -E 's#https?://[^/]*##')" "301 /security"
chk "llms.txt"               "$(curl -s $B/llms.txt | head -1)" "# handover.tools"
chk "client downloadable"            "$(curl -s $B/client/channel.py | head -1)" "# /// script"
chk "client sha256 matches the header"   "$(curl -s $B/client/channel.py | shasum -a 256 | cut -c1-64)" "$(curl -s -D- -o /dev/null $B/client/channel.py | grep -i x-content-sha256 | awk '{print $2}' | tr -d '\r')"
chk "sha256 matches discover"  "$(curl -s $B/api/discover | j "['channel_client']['sha256']")" "$(curl -s $B/client/channel.py | shasum -a 256 | cut -c1-64)"

echo "── channel: parts that need no write quota (spec/channel §7) ──"
CH() { curl -s -X POST $B/api/channel/$1 -H 'Content-Type: application/json' -d "$2"; }
chk "join with an invalid nameplate"         "$(CH join '{"nameplate":"!!","pake_msg":"AAAA"}' | j "['key']")" "None"
# Full-width (CJK input method) must fold to half-width: an unknown code should report not_found, not "bad format"
echo "── short link handover.tools/<code> (spec/handoff §4) ──"
chk "short link gives the agent instructions"         "$(curl -s $B/KVMT-RHXP | head -1)" "# handover code kvmtrhxp"
chk "instructions include the real fetch URL"      "$(curl -s $B/kvmtrhxp | grep -c 'api/handoff/get?code=kvmtrhxp')" "1"
chk "instructions explain how to join a channel"  "$(curl -s $B/kvmtrhxp | grep -c 'channel.py join kvmtrhxp')" "1"
chk "browser: homepage + prefilled code"    "$(curl -s -H 'Accept: text/html' $B/kvmtrhxp | grep -c 'window.PREFILL = "KVMTRHXP"')" "1"
chk "prefill doesn't fetch"                  "$(curl -s -H 'Accept: text/html' $B/kvmtrhxp | grep -c 'PREFILL.*fetchIt\|fetchIt();$')" "0"
chk "security page numbers use 22 letters"    "$(curl -s $B/security | grep -c '32<sup>')$(curl -s $B/security.md | grep -c '32^')" "00"
chk "social preview image"                 "$(curl -s -o /dev/null -w '%{http_code} %{content_type}' $B/og.png)" "200 image/png"
chk "favicon.ico (search result icon)"   "$(curl -s -o /dev/null -w '%{http_code} %{content_type}' $B/favicon.ico)" "200 image/x-icon"
chk "favicon.svg"                "$(curl -s -o /dev/null -w '%{http_code} %{content_type}' $B/favicon.svg)" "200 image/svg+xml"
chk "icon-192 / apple-touch-icon" "$(curl -s -o /dev/null -w '%{http_code}' $B/icon-192.png)$(curl -s -o /dev/null -w '%{http_code}' $B/apple-touch-icon.png)" "200200"
chk "page icon is a crawlable URL"        "$(curl -s -H 'Accept: text/html' $B/ | grep -c 'rel="icon" href="/favicon.ico"')$(curl -s -H 'Accept: text/html' $B/ | grep -c 'data:image/svg')" "10"
chk "llms.txt no longer points to percall"    "$(curl -s $B/llms.txt | grep -c 'percall.tools')" "0"
chk "page has OG tags"              "$(curl -s -H 'Accept: text/html' $B/guide | grep -c 'property="og:image" \|twitter:card\|rel="canonical"')" "3"
chk "sitemap"                   "$(curl -s $B/sitemap.xml | grep -o '<loc>' | wc -l | tr -d ' ')" "6"
chk "robots points to the sitemap"         "$(curl -s $B/robots.txt | grep -c 'Sitemap: https://handover.tools/sitemap.xml')" "1"
chk "homepage cache varies by Accept"        "$(curl -sI $B/ | grep -ic '^vary: accept, user-agent')$(curl -sI -H 'Accept: text/html' $B/ | grep -ic '^vary: accept, user-agent')" "11"
chk "security.txt kept out of search"     "$(curl -sI $B/.well-known/security.txt | grep -ic 'x-robots-tag: noindex')" "1"
chk "code links kept out of search"         "$(curl -sI $B/kvmtrhxp | grep -ic 'x-robots-tag: noindex')$(curl -sI -H 'Accept: text/html' $B/kvmtrhxp | grep -ic 'x-robots-tag: noindex')" "11"
chk "docs pages are indexable"             "$(curl -sI -H 'Accept: text/html' $B/guide | grep -ic 'noindex')" "0"
chk "terms page"                 "$(curl -s -H 'Accept: text/html' $B/terms | grep -c 'mailto:abuse@handover.tools')$(curl -s $B/terms.md | head -1)" "2# Terms"
chk "security.txt"                "$(curl -s $B/.well-known/security.txt | grep -c '^Contact: mailto:security@handover.tools\|^Expires: 20')" "2"
chk "footer has terms and abuse address"         "$(curl -s -H 'Accept: text/html' $B/guide | grep -c 'href=\"/terms\">Terms</a>.*Report abuse')" "1"
chk "footer links privacy, changelog, source"   "$(curl -s -H 'Accept: text/html' $B/guide | grep -o 'href=\"/privacy\"\|href=\"/changelog\"\|href=\"https://github.com/gammaland/handover\"' | sort -u | wc -l | tr -d ' ')" "3"
chk "privacy page"                  "$(curl -s -o /dev/null -w '%{http_code}' $B/privacy)$(curl -s $B/privacy.md | head -1)" "200# Privacy"
chk "privacy states the IP retention from config" "$(curl -s $B/privacy.md | grep -c "erased after $(grep IP_RETENTION_DAYS "$(dirname "$0")/../wrangler.toml" | cut -d'"' -f2) days")" "1"
chk "privacy has a contact address"   "$(curl -s $B/privacy | grep -c 'mailto:privacy@handover.tools')" "1"
chk "changelog page lists every entry" "$(curl -s $B/changelog | grep -o 'class="cl-entry"' | wc -l | tr -d ' ')" "$(grep -c '^## ' "$(dirname "$0")/../CHANGELOG.md")"
chk "changelog.md is the repository file" "$(curl -s $B/changelog.md | shasum -a 256 | cut -c1-16)" "$(shasum -a 256 "$(dirname "$0")/../CHANGELOG.md" | cut -c1-16)"
chk "discover links the source"     "$(curl -s $B/api/discover | j "['source']")" "https://github.com/gammaland/handover"
chk "llms.txt links the source"     "$(curl -s $B/llms.txt | grep -c 'github.com/gammaland/handover')" "1"
chk "browser fetch shows a caution"             "$(curl -s -H 'Accept: text/html' $B/ | grep -c 'class=\"caution\"')" "1"
chk "homepage no longer spells codes out"            "$(curl -s $B/ | grep -c 'spelled out\|juliett')" "0"
chk "status line doesn't use window.status"      "$(curl -s $B/ | grep -c 'var status ')" "0"
chk "existing paths aren't treated as codes"          "$(curl -s -o /dev/null -w '%{http_code}' $B/guide)" "200"
chk "old /handoff 301s to /guide"    "$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' $B/handoff | sed -E 's#https?://[^/]*##')" "301 /guide"
chk "non-code paths still 404"         "$(curl -s -o /dev/null -w '%{http_code}' $B/nope)" "404"
chk "full links parse"    "$(curl -s "$B/api/handoff/get?code=handover.tools%2FZZZZ-ZZZZ" | j "['reason']")" "not_found_or_expired"
chk "full-width code normalised"            "$(curl -s "$B/api/handoff/get?code=%EF%BC%92%EF%BC%92%EF%BC%92%EF%BC%92%EF%BC%92%EF%BC%92%EF%BC%92%EF%BC%92" | j "['reason']")" "not_found_or_expired"
chk "full-width nameplate normalised"        "$(CH join '{"nameplate":"ＺＺＺ","pake_msg":"AAAA"}' | j "['reason']")" "not_found_or_expired"
chk "MCP descriptions give the client's full URL"  "$(curl -s -X POST $B/mcp -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | grep -o 'https://handover.tools/client/channel.py' | wc -l | tr -d ' ')" "4"
chk "join with an unknown nameplate"         "$(CH join '{"nameplate":"ZZZ","pake_msg":"AAAA"}' | j "['reason']")" "not_found_or_expired"
chk "join refuses non-base64"      "$(CH join '{"nameplate":"ZZZ","pake_msg":"not base64!"}' | j "['key']")" "None"
chk "fake key fetch"            "$(CH fetch '{"key":"ZZZZZZZZZZZZZZZZZZZZZZZZZZ"}' | j "['reason']")" "not_found_or_closed"
FAKE_SEND=$(python3 -c 'import os,base64,json;print(json.dumps({"key":"Z"*26,"ciphertext":base64.b64encode(os.urandom(64)).decode()}))')
chk "fake key send"             "$(CH send "$FAKE_SEND" | j "['reason']")" "not_found_or_closed"
chk "fake key close"            "$(CH close '{"key":"ZZZZZZZZZZZZZZZZZZZZZZZZZZ"}' | j "['closed']")" "False"
chk "open refuses an empty pake"        "$(CH open '{}' | j "['nameplate']")" "None"

chk "IP retention copy matches config"  "$(curl -s $B/security.md | grep -c "after $(grep IP_RETENTION_DAYS "$(dirname "$0")/../wrangler.toml" | cut -d'"' -f2) days")" "1"

echo "── self-describing docs (system-design §2) ──"
chk "discover works"        "$(curl -s $B/api/discover | j "['service']")" "handover.tools"
chk "includes the MCP endpoint"          "$(curl -s $B/api/discover | j "['mcp']['protocol']")" "2026-07-28"
chk "text format"            "$(curl -s "$B/api/discover?format=text" | head -1)" "# handover.tools"

echo "── MCP, legacy era (system-design §9) ──"
I='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}'
chk "protocol version negotiation"          "$(curl -s -X POST $B/mcp -H 'Content-Type: application/json' -d "$I" | j "['result']['protocolVersion']")" "2025-06-18"
chk "tools/list has 8 tools" "$(curl -s -X POST $B/mcp -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | j "['result']['tools']" | python3 -c 'import json,sys;print(len(json.load(sys.stdin)))')" "8"
chk "unknown tool errors"          "$(curl -s -X POST $B/mcp -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"nope"}}' | j "['error']['code']")" "-32602"
chk "ping"                 "$(curl -s -X POST $B/mcp -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":4,"method":"ping"}' | j "['result']")" "{}"

echo "── MCP 2026-07-28, modern era (system-design §9) ──"
# The payload must be built at top level and referenced by variable; written straight inside $( ), the nested quotes get re-parsed
M=2026-07-28
META="\"_meta\":{\"io.modelcontextprotocol/protocolVersion\":\"$M\"}"
HJ=(-H "Content-Type: application/json")
HM=("${HJ[@]}" -H "MCP-Protocol-Version: $M")
P_DISC="{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"server/discover\",\"params\":{$META}}"
P_PING="{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"ping\",\"params\":{$META}}"
P_CALL="{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"handoff_get\",\"arguments\":{\"code\":\"22222222\"},$META}}"
P_OLDV='{"jsonrpc":"2.0","id":5,"method":"ping","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"1900-01-01"}}}'
P_NOPE="{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"nope\",\"params\":{$META}}"
P_BATCH="[$P_PING]"
B64=$(python3 -c 'import base64;print("=?base64?"+base64.b64encode(b"handoff_get").decode()+"?=")')
st() { curl -s -o /tmp/_m -w '%{http_code}' "$@"; }

chk "server/discover exists"     "$(curl -s -X POST $B/mcp "${HM[@]}" -H 'Mcp-Method: server/discover' -d "$P_DISC" | j "['result']['resultType']")" "complete"
chk "discover prefers 2026-07-28"  "$(curl -s -X POST $B/mcp "${HM[@]}" -H 'Mcp-Method: server/discover' -d "$P_DISC" | j "['result']['supportedVersions'][0]")" "2026-07-28"
P_LIST="{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"tools/list\",\"params\":{$META}}"
chk "modern tools/list has resultType" "$(curl -s -X POST $B/mcp "${HM[@]}" -H 'Mcp-Method: tools/list' -d "$P_LIST" | j "['result']['resultType']")" "complete"
chk "modern tools/list has cache hints"   "$(curl -s -X POST $B/mcp "${HM[@]}" -H 'Mcp-Method: tools/list' -d "$P_LIST" | j "['result']['cacheScope']")" "public"
chk "modern ping has resultType"      "$(curl -s -X POST $B/mcp "${HM[@]}" -H 'Mcp-Method: ping' -d "$P_PING" | j "['result']['resultType']")" "complete"
chk "modern tools/call has resultType" "$(curl -s -X POST $B/mcp "${HM[@]}" -H 'Mcp-Method: tools/call' -H 'Mcp-Name: handoff_get' -d "$P_CALL" | j "['result']['resultType']")" "complete"
chk "legacy tools/list has no resultType" "$(curl -s -X POST $B/mcp "${HJ[@]}" -d '{"jsonrpc":"2.0","id":8,"method":"tools/list"}' | grep -c resultType)" "0"

chk "header/body mismatch -> 400"      "$(st -X POST $B/mcp "${HJ[@]}" -H 'MCP-Protocol-Version: 2025-11-25' -H 'Mcp-Method: ping' -d "$P_PING")" "400"
chk "header/body mismatch -> -32020"   "$(j "['error']['code']" < /tmp/_m)" "-32020"
chk "missing Mcp-Method -> -32020"    "$(curl -s -X POST $B/mcp "${HM[@]}" -d "$P_PING" | j "['error']['code']")" "-32020"
chk "tools/call missing Mcp-Name"    "$(curl -s -X POST $B/mcp "${HM[@]}" -H 'Mcp-Method: tools/call' -d "$P_CALL" | j "['error']['code']")" "-32020"

chk "unknown version -> 400"            "$(st -X POST $B/mcp "${HJ[@]}" -H 'MCP-Protocol-Version: 1900-01-01' -H 'Mcp-Method: ping' -d "$P_OLDV")" "400"
chk "unknown version -> -32022"         "$(j "['error']['code']" < /tmp/_m)" "-32022"
chk "-32022 reports requested"     "$(j "['error']['data']['requested']" < /tmp/_m)" "1900-01-01"

chk "unknown method -> HTTP 404"       "$(st -X POST $B/mcp "${HM[@]}" -H 'Mcp-Method: nope' -d "$P_NOPE")" "404"
chk "unknown method -> -32601"         "$(j "['error']['code']" < /tmp/_m)" "-32601"
chk "modern forbids batching -> 400"       "$(st -X POST $B/mcp "${HM[@]}" -d "$P_BATCH")" "400"
chk "Mcp-Name base64 sentinel"      "$(curl -s -X POST $B/mcp "${HM[@]}" -H 'Mcp-Method: tools/call' -H "Mcp-Name: $B64" -d "$P_CALL" | j "['result']['structuredContent']['reason']")" "not_found_or_expired"
chk "legacy initialize still works"   "$(curl -s -X POST $B/mcp "${HJ[@]}" -d '{"jsonrpc":"2.0","id":9,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}' | j "['result']['protocolVersion']")" "2025-06-18"

if [ "$WRITES" = "1" ]; then
echo "── handoff: put / get (spec/handoff §3.1, §3.2) ──"
# This section uses 6 writes of quota (handoff 5 + channel_open 1; 10 per caller per day, D20).
#    So tests/e2e.sh can run against production at most twice a day. The write gate itself is tested in tests/quota.sh.
PUT() { curl -s -X POST $B/api/handoff/put -H 'Content-Type: application/json' -d "$1"; }
GET() { curl -s "$B/api/handoff/get?code=$1"; }
REVOKE() { curl -s -X POST $B/api/handoff/revoke -H 'Content-Type: application/json' -d "{\"revoke_key\":\"$1\"}"; }

R=$(PUT '{"content":"round trip payload","label":"suite"}')          # write 1
C=$(printf '%s' "$R" | j "['code']")
chk "put tells the person what to say on the other device"  "$(printf '%s' "$R" | j "['say_on_the_other_device']" | grep -cE '^handover.tools/[a-z]{8}$')" "1"
chk "old codes with digits still parse"     "$(curl -s $B/K7M2-4QX9 | head -1)" "# handover code k7m24qx9"
chk "put returns an 8-letter lowercase code" "$(printf '%s' "$C" | grep -cE '^[a-z]{8}$')" "1"
chk "put returns revoke_key"   "$(printf '%s' "$R" | j "['revoke_key']" | wc -c | tr -d ' ')" "27"
chk "read-once by default"          "$(printf '%s' "$R" | j "['burn_after_read']")" "True"
chk "default TTL 60 minutes"      "$(printf '%s' "$R" | j "['expires_in_minutes']")" "60"
chk "reports write allowance"          "$(printf '%s' "$R" | j "['writes_per_day']")" "10"
chk "fetches the original text"             "$(GET "$C" | j "['content']")" "round trip payload"
chk "gone after the read"          "$(GET "$C" | j "['reason']")" "not_found_or_expired"

R2=$(PUT '{"content":"multi read","burn_after_read":false,"ttl_minutes":5}')   # write 2
C3=$(printf '%s' "$R2" | j "['code']")
chk "non-read-once can be read again"        "$(GET "$C3" >/dev/null; GET "$C3" | j "['content']")" "multi read"
chk "read count increments"             "$(GET "$C3" | j "['reads']")" "3"
chk "full-width also fetches"             "$(GET "$(python3 -c "import sys,urllib.parse;c=sys.argv[1];print(urllib.parse.quote(''.join(chr(ord(x)+0xFEE0) if x.isalnum() else x for x in c)))" "$C3")" | j "['content']")" "multi read"
chk "short link doesn't use up the code"          "$(curl -s $B/$C3 >/dev/null; curl -s "$B/api/handoff/get?code=$C3" | j "['content']")" "multi read"
chk "full link also fetches"          "$(curl -s "$B/api/handoff/get?code=handover.tools/$C3" | j "['content']")" "multi read"
chk "uppercase with hyphen also fetches"     "$(GET "$(printf '%s' "$C3" | tr 'a-z' 'A-Z' | sed 's/^..../&-/')" | j "['content']")" "multi read"

echo "── handoff: writer revokes (spec/handoff §3.3) ──"
R3=$(PUT '{"content":"sent by mistake","label":"oops"}')             # write 3
C4=$(printf '%s' "$R3" | j "['code']")
RK=$(printf '%s' "$R3" | j "['revoke_key']")
chk "the short code can't revoke"          "$(REVOKE "$C4" | j "['revoked']")" "False"
chk "revoke_key revokes"  "$(REVOKE "$RK" | j "['revoked']")" "True"
chk "gone after revoke"          "$(GET "$C4" | j "['reason']")" "not_found_or_expired"
chk "repeat revoke reports already_gone" "$(REVOKE "$RK" | j "['reason']")" "already_gone"

echo "── handoff: input validation, no write quota used (spec/handoff §3.1, §5) ──"
chk "empty content refused"           "$(PUT '{"content":"  "}' | j "['code']")" "None"
python3 -c "import json;print(json.dumps({'content':'x'*(256*1024+10)}))" > /tmp/_big.json
chk "oversized content refused"          "$(curl -s -X POST $B/api/handoff/put -H 'Content-Type: application/json' --data-binary @/tmp/_big.json | j "['code']")" "None"
chk "invalid code is explained"          "$(GET "zzz" | j "['content']")" "None"
chk "unknown code doesn't leak existence"     "$(GET "22222222" | j "['reason']")" "not_found_or_expired"
chk "invalid revoke_key refused"  "$(REVOKE "tooshort" | j "['revoked']")" "False"
chk "TTL capped at 1440"   "$(PUT '{"content":"x","ttl_minutes":99999}' | j "['expires_in_minutes']")" "1440"   # write 4
chk "MCP can put too"         "$(curl -s -X POST $B/mcp -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":9,"method":"tools/call","params":{"name":"handoff_put","arguments":{"content":"via mcp"}}}' | j "['result']['structuredContent']['burn_after_read']")" "True"   # write 5

echo "── channel: the server only moves bytes (spec/channel §7, §8) ──"
# Uses 1 write of quota (channel_open). The full two-sided encryption test is tests/channel.sh.
# Always build JSON with jb: hand-written "{\"a\":1,\"b\":2}" inside $( ) triggers brace expansion,
#    splitting one request into two broken curls. The first version of this section "passed by accident" on several checks that way.
jb() { python3 -c 'import json,sys
d={}
for kv in sys.argv[1:]:
    k,v=kv.split("=",1)
    d[k]={"true":True,"false":False}.get(v, int(v) if v.isdigit() else v)
print(json.dumps(d))' "$@"; }
# Fake ciphertext must look like real ciphertext: random bytes. Too short or mostly printable is refused as plaintext (D37)
CT=$(python3 -c "import os,base64;print(base64.b64encode(os.urandom(64)).decode())")
PLAIN=$(python3 -c "import base64,json;print(base64.b64encode(json.dumps({'v':1,'n':1,'kind':'note','body':'this is plaintext'}).encode()).decode())")
O=$(CH open "$(jb pake_msg=QUFBQQ==)")
NP=$(printf '%s' "$O" | j "['nameplate']"); KA=$(printf '%s' "$O" | j "['key']")
chk "open returns only a 3-letter nameplate"     "$(printf '%s' "$NP" | wc -c | tr -d ' ')" "3"
chk "open doesn't return the full code"         "$(printf '%s' "$O" | j ".get('code')")" "None"
chk "cannot send before the peer joins"         "$(CH send "$(jb key=$KA ciphertext=$CT)" | j "['reason']")" "peer_not_joined"
PX=$(printf '%s' "$O" | j "['pairing_expires_at']")
chk "fetch before join keeps the 60-minute window" "$(CH fetch "$(jb key=$KA)" | j "['expires_at']")" "$PX"
J=$(CH join "$(jb nameplate=$(printf '%s' "$NP" | tr 'A-Z' 'a-z') pake_msg=QkJCQg==)")
KB=$(printf '%s' "$J" | j "['key']")
chk "join gets A's pake"     "$(printf '%s' "$J" | j "['peer_pake_msg']")" "QUFBQQ=="
chk "fetch after join slides the expiry"  "$([ "$(CH fetch "$(jb key=$KA peek=true)" | j "['expires_at']")" \> "$PX" ] && echo yes)" "yes"
chk "a nameplate works only once"         "$(CH join "$(jb nameplate=$NP pake_msg=QkJCQg==)" | j "['reason']")" "not_found_or_expired"
chk "A fetch gets B's pake"  "$(CH fetch "$(jb key=$KA)" | j "['peer_pake_msg']")" "QkJCQg=="
chk "plaintext refused"              "$(CH send "$(jb key=$KB ciphertext=$PLAIN)" | j "['reason']")" "not_ciphertext"
chk "too short also refused"           "$(CH send "$(jb key=$KB ciphertext=QQ==)" | j "['reason']")" "not_ciphertext"
chk "B's send gets seq 1"        "$(CH send "$(jb key=$KB ciphertext=$CT)" | j "['seq']")" "1"
CH fetch "$(jb key=$KA peek=true)" >/dev/null
chk "peek doesn't mark read"           "$(CH fetch "$(jb key=$KA peek=true)" | j "['messages'][0]['ciphertext']")" "$CT"
chk "A gets the ciphertext unchanged"          "$(CH fetch "$(jb key=$KA)" | j "['messages'][0]['ciphertext']")" "$CT"
chk "nothing new after fetching"          "$(CH fetch "$(jb key=$KA)" | j "['messages']")" "[]"
chk "after=0 re-reads"          "$(CH fetch "$(jb key=$KA after=0)" | j "['messages'][0]['seq']")" "1"
chk "B sees A has read"           "$(CH fetch "$(jb key=$KB peek=true)" | j "['peer_read_seq']")" "1"
chk "B doesn't receive its own message"       "$(CH fetch "$(jb key=$KB)" | j "['messages']")" "[]"
chk "B's fetch has no pairing material"  "$(CH fetch "$(jb key=$KB)" | j ".get('peer_pake_msg')")" "None"
chk "close"                   "$(CH close "$(jb key=$KB)" | j "['closed']")" "True"
chk "other side can't fetch after close"       "$(CH fetch "$(jb key=$KA)" | j "['reason']")" "not_found_or_closed"

else
  echo "── handoff ── (skipped: write tests use 6 of the daily quota; WRITES=1 tests/e2e.sh to run them)"
fi

echo "── metering and quotas (system-design §7) ──"
chk "usage readable"           "$(curl -s $B/api/usage | j "['you']['free_per_day']")" "200"
chk "write quota visible"          "$(curl -s $B/api/usage | j "['you']['writes_per_day']")" "10"
chk "usage hides site-wide usage"   "$(curl -s $B/api/usage | grep -c 'service\|daily_cap\|upstream')" "0"
chk "usage doesn't echo the IP"        "$(curl -s $B/api/usage | grep -c 'caller')" "0"
chk "discover hides site-wide usage" "$(curl -s $B/api/discover | grep -c 'daily_cap\|upstream\|\"runtime\"')" "0"

if [ "$B" = "https://handover.tools" ]; then
  echo "── production only: http->https (system-design §3) ──"
  chk "http homepage 301s to https"        "$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' -H 'Accept: text/html' http://handover.tools/guide?x=1)" "301 https://handover.tools/guide?x=1"
  chk "http POST doesn't redirect (API keeps working)"  "$(curl -s -o /dev/null -w '%{http_code}' -X POST http://handover.tools/mcp -d '{}')" "202"
fi
echo ""
echo "passed $pass / failed $fail"
[ $fail -eq 0 ]
