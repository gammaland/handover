#!/bin/bash
# Run the Worker locally on :8787 with a local D1 (state in .wrangler/). No Cloudflare account needed.
set -e
cd "$(dirname "$0")/.."
[ -d /opt/homebrew/opt/node@22/bin ] && export PATH="/opt/homebrew/opt/node@22/bin:$PATH"   # wrangler 4 needs Node >= 22
scripts/build.sh
exec npx wrangler dev --port 8787 "$@"
