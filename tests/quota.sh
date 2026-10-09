#!/bin/bash
# Quota gate tests. They change D1 state, so they are separate from tests/e2e.sh. Run scripts/dev.sh first.
# Local only: this edits the counters table directly. Never run it against production.
cd "$(dirname "$0")/.."
export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
B=${BASE:-http://127.0.0.1:8787}; DAY=$(date -u +%Y-%m-%d); pass=0; fail=0
d1() { npx wrangler d1 execute handover-tools --local --command "$1" >/dev/null 2>&1; }
chk() { [ "$2" = "$3" ] && { echo "  ✅ $1"; pass=$((pass+1)); } || { echo "  ❌ $1 — expected $3 got $2"; fail=$((fail+1)); }; }

# Read path: fetch a code that doesn't exist. 200 = let through, 429/503 = blocked by a gate
rcode() { curl -s -o /dev/null -w "%{http_code}" "$B/api/handoff/get?code=22222222"; }
# Write path: check whether the body has a code; when the write gate blocks, code is null
wput()  { curl -s -X POST "$B/api/handoff/put" -H 'Content-Type: application/json' \
            -d '{"content":"cap probe"}' \
          | python3 -c 'import sys,json;d=json.load(sys.stdin);print("ok" if d.get("code") else "blocked")'; }

echo "── entry gate (system-design §7) ──"
d1 "DELETE FROM counters WHERE window='$DAY'"
chk "normal request passes"             "$(rcode)" "200"

d1 "INSERT INTO counters (scope,window,n) VALUES ('global','$DAY',20000) ON CONFLICT(scope,window) DO UPDATE SET n=20000"
chk "service daily cap -> 503"    "$(rcode)" "503"

d1 "UPDATE counters SET n=0 WHERE scope='global' AND window='$DAY'"
d1 "INSERT INTO counters (scope,window,n) VALUES ('caller:127.0.0.1','$DAY',200) ON CONFLICT(scope,window) DO UPDATE SET n=200"
chk "per-caller daily cap -> 429"  "$(rcode)" "429"

echo "── write gate: blocks writes, not reads (system-design §7) ──"
d1 "DELETE FROM counters WHERE window='$DAY'"
chk "can write within quota"           "$(wput)" "ok"

d1 "INSERT INTO counters (scope,window,n) VALUES ('write:127.0.0.1','$DAY',10) ON CONFLICT(scope,window) DO UPDATE SET n=10"
chk "10 writes used -> write refused"     "$(wput)" "blocked"
chk "**reads still work**"      "$(rcode)" "200"

d1 "DELETE FROM counters WHERE window='$DAY'"

echo "── blocklist: writes only (system-design §7) ──"
wreason() { curl -s -X POST "$B/api/handoff/put" -H 'Content-Type: application/json' -d '{"content":"x"}' \
            | python3 -c 'import sys,json;print(json.load(sys.stdin).get("reason","")[:8])'; }
d1 "INSERT OR REPLACE INTO blocks (prefix,reason,created_at) VALUES ('127.0.0.','test',0)"
chk "range prefix block -> write refused"    "$(wreason)" "blocked:"
chk "only writes are blocked, reads still work"    "$(rcode)" "200"
d1 "DELETE FROM blocks WHERE prefix='127.0.0.'"
d1 "INSERT OR REPLACE INTO blocks (prefix,reason,created_at) VALUES ('127.0.0.12','test',0)"
chk "without a trailing . only exact match"   "$(wput)" "ok"
d1 "DELETE FROM blocks WHERE prefix='127.0.0.12'"
chk "can write after unblock"             "$(wput)" "ok"

d1 "DELETE FROM counters WHERE window='$DAY'"
echo ""; echo "passed $pass / failed $fail"; [ $fail -eq 0 ]
