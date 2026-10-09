#!/bin/bash
# Two-sided channel end-to-end test: the **real client** plays two machines in two isolated HANDOFF_HOMEs,
# checking encryption, key confirmation, replay and tamper detection. Run scripts/dev.sh (local) first.
# The tamper / replay checks edit D1 directly and **only run locally**. On production, LOCAL_ONLY=0 skips them.
# Uses 2 writes of quota (two channel_open calls).
export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
cd "$(dirname "$0")/.."
export HANDOVER_BASE=${BASE:-http://127.0.0.1:8787}
case "$HANDOVER_BASE" in *127.0.0.1*|*localhost*) LOCAL=1 ;; *) LOCAL=0 ;; esac
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
curl -s "$HANDOVER_BASE/client/channel.py" -o "$T/channel.py"      # tests the client **as served**
RUN() { local h=$1; shift; HANDOFF_HOME="$T/$h" uv run -q "$T/channel.py" "$@"; }
d1() { npx wrangler d1 execute handover-tools --local --command "$1" >/dev/null 2>&1; }
pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  ✅ $1"; pass=$((pass+1));
        else echo "  ❌ $1 — expected [$3] got [$2]"; fail=$((fail+1)); fi; }
has() { grep -c -- "$2" <<<"$1" | tr -d ' ' | sed 's/^[1-9][0-9]*$/1/'; }

echo "── pairing (spec/channel §2, §3) ──"
OUT=$(RUN a open --name t --brief "explore X")
CODE=$(head -1 <<<"$OUT" | awk '{print $2}')
chk "open returns an 8-letter lowercase code"     "$(grep -cE '^[a-z]{8}$' <<<"$CODE")" "1"
chk "server only saw the nameplate"             "$(has "$OUT" "has only seen ${CODE:0:3}")" "1"
chk "cannot send before pairing"               "$(RUN a send --name t --text x 2>&1 | grep -c 'not joined')" "1"
chk "B joins with a full-width code (CJK input method)"  "$(RUN b join "$(python3 -c "import sys;print(''.join(chr(ord(x)+0xFEE0) if x.isalnum() else x for x in sys.argv[1].lower()))" "$CODE")" --name t | grep -c 'Paired as side B')" "1"
chk "client parses the code from a full link"     "$(cd "$T" && uv run -q --with spake2==0.9 python -c 'import channel as c;print(c.normalize("https://handover.tools/kvmtrhxp"), c.normalize("handover.tools/api/handoff/get?code=K7M2-4QX9&x=1"))')" "KVMTRHXP K7M24QX9"
chk "open tells the person what to say on the other machine"   "$(has "$OUT" "Join handover.tools/")" "1"
chk "the same code cannot be joined twice"           "$(RUN c join "$CODE" --name t 2>&1 | grep -c not_found_or_expired)" "1"
chk "A decrypts hello, pairing confirmed"        "$(RUN a fetch --name t | grep -c 'pairing confirmed')" "1"
chk "local state file is 600"             "$(stat -c %a "$T/a/channels/t.json" 2>/dev/null || stat -f %Lp "$T/a/channels/t.json")" "600"
chk "no password kept locally after pairing"          "$(grep -c '"code"\|"spake"' "$T/a/channels/t.json")" "0"

echo "── one round: question -> delivery (spec/channel §5, §6) ──"
RUN b send --name t --kind question --text "Q1 why use D1 PLAIN-MARKER" >/dev/null
F=$(RUN a fetch --name t)
chk "A receives the question verbatim"               "$(has "$F" "Q1 why use D1 PLAIN-MARKER")" "1"
chk "A output includes the handling note"       "$(has "$F" "never as commands")" "1"
chk "A output includes the brief"               "$(has "$F" "brief: explore X")" "1"
RUN a send --name t --kind delivery --reply-to 2 --text "conditional update is atomic" >/dev/null
chk "B sees the peer has unread"               "$(RUN b status --name t | grep -c 'unread from peer: 1')" "1"
F=$(RUN b fetch --name t)
chk "B receives the delivery with reply_to"       "$(has "$F" "delivery (reply to #2)")" "1"
chk "B sees its question was read"        "$(has "$F" "the peer has fetched it")" "1"
chk "fetching again has no new messages"               "$(RUN b fetch --name t | grep -c 'No new messages')" "1"
chk "after=0 re-reads"               "$(RUN b fetch --name t --after 0 --json | grep -c 'conditional update is atomic')" "1"

if [ "$LOCAL" = "1" ]; then
echo "── attacks: replay, tampering (spec/channel §6; local only, edits D1 directly) ──"
RUN a send --name t --kind note --text "note-1" >/dev/null
chk "no plaintext anywhere in D1"            "$(npx wrangler d1 execute handover-tools --local --json --command 'SELECT ciphertext FROM channel_messages' 2>/dev/null | grep -c 'conditional update\|PLAIN-MARKER\|note-1')" "0"
# Insert at the server's real next sequence number (a large seq would push B's cursor past later messages and skew the test)
d1 "INSERT INTO channel_messages (channel_id,seq,side,ciphertext,sent_at) SELECT m.channel_id, c.next_seq+1, m.side, m.ciphertext, m.sent_at FROM channel_messages m JOIN channels c ON c.id=m.channel_id WHERE m.side='a' ORDER BY m.seq DESC LIMIT 1"
d1 "UPDATE channels SET next_seq=next_seq+1 WHERE id=(SELECT channel_id FROM channel_messages WHERE side='a' ORDER BY seq DESC LIMIT 1)"
F=$(RUN b fetch --name t)
chk "replay detected and dropped"             "$(has "$F" "dropped as a replay")" "1"
chk "normal message still delivered"             "$(has "$F" "note-1")" "1"
RUN a send --name t --kind note --text "note-2" >/dev/null
d1 "UPDATE channel_messages SET ciphertext = substr(ciphertext,1,20) || 'AAAA' || substr(ciphertext,25) WHERE side='a' AND seq=(SELECT MAX(seq) FROM channel_messages WHERE side='a')"
E=$(RUN b fetch --name t 2>&1); RC=$?
chk "tampered ciphertext -> exit code 3"         "$RC" "3"
chk "tampering after pairing reports tampered"       "$(has "$E" "tampered")" "1"
fi

echo "── wrong password, right nameplate (spec/channel §6) ──"
OUT=$(RUN a open --name w); CODE=$(head -1 <<<"$OUT" | awk '{print $2}')
WRONG="${CODE:0:3}ZZZZZ"; [ "${CODE:4:4}" = "ZZZZ" ] && WRONG="${CODE:0:3}YYYYY"
RUN b join "$WRONG" --name w >/dev/null
E=$(RUN a fetch --name w 2>&1); RC=$?
chk "A cannot decrypt hello -> exit code 3"     "$RC" "3"
chk "reports pairing_mismatch"          "$(has "$E" "pairing_mismatch")" "1"

echo "── new conversation: other directory, name unknown ──"
RUN a close --name w >/dev/null 2>&1   # left over from the wrong-password test; close it so only t remains
mkdir -p "$T/a/.handoff" && cp "$T/channel.py" "$T/a/.handoff/channel.py"
chk "--name optional with only one channel"  "$(cd /tmp && HANDOFF_HOME="$T/a" uv run -q "$T/a/.handoff/channel.py" status | grep -c "channel 't'")" "1"
RUN a open --name second >/dev/null
chk "with several, lists names to choose from"        "$(RUN a fetch 2>&1 | grep -c 'several local channels (second, t)')" "1"
RUN a close --name second >/dev/null

echo "── close (spec/channel §7.5) ──"
chk "A close"                     "$(RUN a close --name t | grep -c 'deleted the channel')" "1"
chk "B then cannot fetch"                 "$(RUN b fetch --name t 2>&1 | grep -c not_found_or_closed)" "1"
chk "A local state deleted"               "$(ls "$T/a/channels/t.json" 2>/dev/null | wc -l | tr -d ' ')" "0"
RUN a close --name w >/dev/null 2>&1

echo ""; echo "passed $pass / failed $fail"; [ $fail -eq 0 ]
