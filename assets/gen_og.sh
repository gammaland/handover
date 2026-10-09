#!/bin/bash
# Screenshot assets/og.html into the 1200x630 social preview image assets/img/og.png (uses the system Chrome).
# Run by hand only when the card design changes; the output is committed and gen_fonts.sh embeds it in the Worker at deploy time.
set -e
cd "$(dirname "$0")"
uv run -q --with playwright python - <<'PY'
from pathlib import Path
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1200, "height": 630})
    pg.goto(Path("og.html").resolve().as_uri()); pg.wait_for_timeout(300)
    pg.screenshot(path="img/og.png")
    b.close()
print("assets/img/og.png", Path("img/og.png").stat().st_size // 1024, "KB")
PY
