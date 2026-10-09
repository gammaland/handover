#!/bin/bash
# Build the generated modules, then deploy with wrangler.
# Needs CLOUDFLARE_API_TOKEN in the environment (a scoped token: Workers Scripts, Workers Routes, D1, DNS).
#   scripts/deploy.sh             # deploy
#   scripts/deploy.sh --dry-run   # anything else is passed to `wrangler deploy`
set -e
cd "$(dirname "$0")/.."
[ -d /opt/homebrew/opt/node@22/bin ] && export PATH="/opt/homebrew/opt/node@22/bin:$PATH"   # wrangler 4 needs Node >= 22
[ -n "$CLOUDFLARE_API_TOKEN" ] || { echo "CLOUDFLARE_API_TOKEN is not set" >&2; exit 1; }
scripts/build.sh
exec npx wrangler deploy "$@"
