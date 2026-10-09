#!/bin/bash
# Generate crawlable site icons: assets/img/favicon.ico (16/32/48), icon-192.png, apple-touch-icon.png (180).
# Why not only the data: URI SVG: Google search results need an icon at a URL Googlebot can crawl (a multiple of 48 in size);
# a data: URI doesn't count, and the result shows a grey globe. The dark tile keeps it visible on both light and dark result pages.
# Run by hand only when the icon design changes; the outputs are committed and gen_fonts.sh embeds them in the Worker at deploy time.
set -e
cd "$(dirname "$0")"
uv run -q --with playwright --with pillow python - <<'PY'
import io
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

# The same shape as _FAVICON_SVG in src/icons.py, with fixed colours + a rounded dark tile
SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="512" height="512">'
       '<rect width="32" height="32" rx="7" fill="#121417"/>'
       '<path d="M9 9L3 16l6 7M23 9l6 7-6 7M8 16h5M19 16h5" fill="none" stroke="#f0f2f5" stroke-width="2.5" '
       'stroke-linecap="round" stroke-linejoin="round"/>'
       '<circle cx="16" cy="16" r="3.5" fill="#ff5414"/></svg>')
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 512, "height": 512})
    pg.set_content(f'<style>html,body{{margin:0;background:transparent}}</style>{SVG}')
    png = pg.screenshot(omit_background=True)
    b.close()
big = Image.open(io.BytesIO(png)).convert("RGBA")
big.resize((192, 192), Image.LANCZOS).save("img/icon-192.png", optimize=True)
big.resize((180, 180), Image.LANCZOS).save("img/apple-touch-icon.png", optimize=True)
big.save("img/favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
for n in ("favicon.ico", "icon-192.png", "apple-touch-icon.png"):
    print("assets/img/" + n, Path("img", n).stat().st_size, "bytes")
PY
