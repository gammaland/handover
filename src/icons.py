"""Geometric SVG icon set shared by the site and the handoff tool.

Principles:
    - precise geometry, matching the engineering-instrument typography of Atkinson Next / Mono
    - one stroke width and viewport: viewBox 0 0 24 24, stroke-width 1.8, round caps
    - colour is inherited: stroke="currentColor" adapts to light and dark themes; signal dots use theme variables
    - no external dependencies: inline SVG only, no external requests, never leaks a visitor's IP
"""

# Logo: two endpoints joined by a beacon channel, with an orange signal core in the middle
BRAND_ICON = (
    '<svg class="brand-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M6 7L2 12l4 5"/>'
    '<path d="M18 7l4 5-4 5"/>'
    '<line x1="6" y1="12" x2="9" y2="12"/>'
    '<line x1="15" y1="12" x2="18" y2="12"/>'
    '<circle cx="12" cy="12" r="2.25" fill="var(--signal-orange)" stroke="none"/>'
    '</svg>'
)

# Favicon SVG (adapts to light/dark), served at /favicon.svg; the PNG/ICO for search results come from assets/gen_icons.sh
FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<style>'
    ':root { --stroke: #121417; }'
    '@media (prefers-color-scheme: dark) { :root { --stroke: #f0f2f5; } }'
    '</style>'
    '<path d="M9 9L3 16l6 7M23 9l6 7-6 7M8 16h5M19 16h5" fill="none" stroke="var(--stroke)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
    '<circle cx="16" cy="16" r="3.5" fill="#ff5414"/>'
    '</svg>'
)

# One-shot mode icon: a single directed delivery (read once)
ICON_ONESHOT = (
    '<svg class="icon icon-oneshot" width="18" height="18" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<polygon points="22 2 15 22 11 13 2 9 22 2"/>'
    '<line x1="22" y1="2" x2="11" y2="13"/>'
    '</svg>'
)

# Channel mode icon: a two-way encrypted pipe
ICON_CHANNEL = (
    '<svg class="icon icon-channel" width="18" height="18" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>'
    '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'
    '</svg>'
)

# Terminal / agent prompt icon (>_)
ICON_TERMINAL = (
    '<svg class="icon icon-terminal" width="16" height="16" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<polyline points="4 17 10 11 4 5"/>'
    '<line x1="12" y1="19" x2="20" y2="19"/>'
    '</svg>'
)

# Shield icon (E2EE verification, the Security page)
ICON_SHIELD = (
    '<svg class="icon icon-shield" width="16" height="16" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
    '</svg>'
)

# Copy icon (two stacked cards)
ICON_COPY = (
    '<svg class="icon icon-copy" width="14" height="14" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>'
    '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'
    '</svg>'
)

# Success check icon
ICON_CHECK = (
    '<svg class="icon icon-check" width="14" height="14" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<polyline points="20 6 9 17 4 12"/>'
    '</svg>'
)


# Arrow / link icon
ICON_ARROW_RIGHT = (
    '<svg class="icon icon-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<line x1="5" y1="12" x2="19" y2="12"/>'
    '<polyline points="12 5 19 12 12 19"/>'
    '</svg>'
)


# Node icon: a terminal device (device / machine)
ICON_DEVICE = (
    '<svg class="icon icon-device" width="16" height="16" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<rect x="2" y="4" width="20" height="13" rx="2" ry="2"/>'
    '<line x1="8" y1="20" x2="16" y2="20"/>'
    '<line x1="12" y1="17" x2="12" y2="20"/>'
    '</svg>'
)

# Node icon: a phone (the sender in the homepage example)
ICON_PHONE = (
    '<svg class="icon icon-phone" width="16" height="16" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<rect x="6" y="2" width="12" height="20" rx="2.5" ry="2.5"/>'
    '<line x1="11" y1="18" x2="13" y2="18"/>'
    '</svg>'
)

# Node icon: the relay server (server / relay)
ICON_SERVER = (
    '<svg class="icon icon-server" width="16" height="16" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>'
    '<rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>'
    '<line x1="6" y1="6" x2="6.01" y2="6"/>'
    '<line x1="6" y1="18" x2="6.01" y2="18"/>'
    '</svg>'
)
