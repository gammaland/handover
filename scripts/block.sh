#!/bin/bash
# Operator tools for abuse reports (D44). The blocklist stops writes (handoff_put, channel_open) only;
# reads are unaffected. Everything edits D1 directly, so no redeploy is needed.
#   scripts/block.sh list
#   scripts/block.sh add 203.0.113.7 "phishing links, report 2026-10-02"   # block one IP exactly
#   scripts/block.sh add 203.0.113.  "botnet range"                          # ending in . or : = the whole range
#   scripts/block.sh remove 203.0.113.
#   scripts/block.sh who <link-or-code>     # is this one-shot still stored, and who created it (creator IP is kept 30 days)
#   scripts/block.sh show <link-or-code>    # print the content. NEVER use this for reports of child sexual abuse material
#   scripts/block.sh purge <link-or-code>   # delete this one
#   scripts/block.sh purge-ip <ip>          # delete everything still stored from this IP
# Targets production by default (needs CLOUDFLARE_API_TOKEN); LOCAL=1 targets the local dev database.
set -e
cd "$(dirname "$0")/.."
[ -d /opt/homebrew/opt/node@22/bin ] && export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
WHERE=--remote; [ -n "$LOCAL" ] && WHERE=--local
q() { npx wrangler d1 execute handover-tools $WHERE --command "$1" 2>/dev/null | python3 -c '
import json,sys,re
t=sys.stdin.read(); m=re.search(r"\[\s*\{.*\}\s*\]", t, re.S)
for r in (json.loads(m.group(0))[0].get("results", []) if m else []): print(r)'; }
esc() { printf "%s" "$1" | sed "s/'/''/g"; }
# link / code -> code_hash, matching the server's normalization (spec/handoff §2.2):
# last path segment, uppercase, alphanumerics only, I/L->1 O->0 U->V
hash_of() { printf "%s" "${1##*/}" | tr 'a-z' 'A-Z' | tr -cd 'A-Z0-9' | tr 'ILOU' '110V' | shasum -a 256 | cut -d' ' -f1; }
case "$1" in
  list)   q "SELECT prefix, reason, datetime(created_at, 'unixepoch') AS since FROM blocks ORDER BY created_at DESC" ;;
  add)    [ -n "$2" ] || { echo "usage: $0 add <ip-or-prefix> <reason>"; exit 1; }
          q "INSERT OR REPLACE INTO blocks (prefix, reason, created_at) VALUES ('$(esc "$2")', '$(esc "$3")', strftime('%s','now'))"
          echo "blocked writes from $2" ;;
  remove) q "DELETE FROM blocks WHERE prefix = '$(esc "$2")'"; echo "unblocked $2" ;;
  who)    h=$(hash_of "$2")
          q "SELECT creator, datetime(created_at, 'unixepoch') AS created, datetime(expires_at, 'unixepoch') AS expires, reads, burn, label, length(content) AS bytes FROM handoffs WHERE code_hash = '$h'"
          echo "(no output = already fetched, revoked or expired; nothing is stored)" ;;
  show)   h=$(hash_of "$2"); q "SELECT content FROM handoffs WHERE code_hash = '$h'" ;;
  purge)  h=$(hash_of "$2"); q "DELETE FROM handoffs WHERE code_hash = '$h'"; echo "deleted $2 (if it was still stored)" ;;
  purge-ip) [ -n "$2" ] || { echo "usage: $0 purge-ip <ip>"; exit 1; }
          q "SELECT count(*) AS n FROM handoffs WHERE creator = '$(esc "$2")'"
          q "DELETE FROM handoffs WHERE creator = '$(esc "$2")'"; echo "deleted everything still stored from $2" ;;
  *) sed -n 2,12p "$0"; exit 1 ;;
esac
