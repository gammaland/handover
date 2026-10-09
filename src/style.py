"""Shared styles, header and page skeleton for every HTML page (a precision-instrument design system).

Design tokens:
    - surfaces: --bg-canvas, --bg-surface, --bg-surface-elevated, --bg-surface-inset, --bg-wash
    - colour: a technical grey scale + one international-orange signal (--signal-orange) + E2EE green (--signal-green) + read-once amber (--signal-amber)
    - shadows and hairline borders: layered surfaces instead of thin rules cutting across a blank page (--border-subtle, --shadow-sm/md/console)
    - type: self-hosted Atkinson Next / Mono, tabular figures, tuned weights, kerning and line height
    - components: console, beacon, the exchange track (.script), spec cards (.facts)
"""
import fonts_src
import icons

_F = {k: v[1] for k, v in fonts_src.FONTS.items()}   # file name -> content hash (cache busting)

CSS = """
  @font-face { font-family:"Atkinson Next"; font-weight:200 800; font-display:swap;
               src:url(/fonts/atkinson-hyperlegible-next.woff2?v=%(next)s) format("woff2"); }
  @font-face { font-family:"Atkinson Mono"; font-weight:200 800; font-display:swap;
               src:url(/fonts/atkinson-hyperlegible-mono.woff2?v=%(mono)s) format("woff2"); }

  /* ==========================================================================
     DESIGN TOKENS (HIGH-PRECISION INSTRUMENT AESTHETIC)
     ========================================================================== */
  :root {
    /* Surfaces & Backgrounds */
    --bg-canvas: #f8f9fa;
    --bg-surface: #ffffff;
    --bg-surface-elevated: #ffffff;
    --bg-surface-inset: #f1f3f6;
    --bg-wash: #f3f5f7;
    --bg-wash-hover: #eaecee;

    /* Inks & Text */
    --ink-primary: #121417;
    --ink-secondary: #4d535e;
    --ink-tertiary: #646a75;   /* 5.2:1 on canvas; the old #7c8390 was only 3.6 */
    --ink-muted: #9da4b0;

    /* Borders & Dividers */
    --border-subtle: rgba(18, 20, 23, 0.08);
    --border-default: rgba(18, 20, 23, 0.14);
    --border-strong: rgba(18, 20, 23, 0.28);
    --border-focus: #ff5414;

    /* Signals & Indicators */
    --signal-orange: #ff5414;
    --signal-orange-dim: rgba(255, 84, 20, 0.08);
    --signal-orange-border: rgba(255, 84, 20, 0.28);
    --signal-orange-glow: rgba(255, 84, 20, 0.22);

    --signal-green: #047857;   /* label text >= 4.5:1; the old #059669 was only 3.4 */
    --signal-green-dim: rgba(16, 185, 129, 0.1);
    --signal-green-border: rgba(5, 150, 105, 0.28);

    --signal-amber: #9a5b00;   /* labels / Not protected >= 4.5:1; the old #d97706 was only 3.0 */
    --signal-amber-dim: rgba(245, 158, 11, 0.1);
    --signal-amber-border: rgba(217, 119, 6, 0.28);

    /* Elevation & Shadows */
    --shadow-xs: 0 1px 2px rgba(18, 20, 23, 0.04);
    --shadow-sm: 0 1px 3px rgba(18, 20, 23, 0.06), 0 1px 2px rgba(18, 20, 23, 0.04);
    --shadow-md: 0 4px 16px -2px rgba(18, 20, 23, 0.07), 0 2px 6px -1px rgba(18, 20, 23, 0.04);
    --shadow-console: 0 16px 40px -10px rgba(18, 20, 23, 0.09), 0 0 0 1px var(--border-default);
    --shadow-cell: inset 0 2px 4px rgba(18, 20, 23, 0.04), 0 1px 1px rgba(255, 255, 255, 0.8);
    --shadow-cell-focus: 0 0 0 3px var(--signal-orange-glow), 0 0 0 1px var(--signal-orange);

    /* Typography Stacks */
    --sans: "Atkinson Next", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --mono: "Atkinson Mono", ui-monospace, SFMono-Regular, Menlo, monospace;

    /* Backward compatibility mapping */
    --paper: var(--bg-surface);
    --wash: var(--bg-surface-inset);
    --ink: var(--ink-primary);
    --graphite: var(--ink-secondary);
    --rule: var(--border-subtle);
    --signal: var(--signal-orange);
    --signal-wash: var(--signal-orange-dim);
    --plain: var(--signal-amber);
    --plain-wash: var(--signal-amber-dim);
    --enc: var(--signal-green);
    --enc-wash: var(--signal-green-dim);
  }

  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg-canvas: #0c0e12;
      --bg-surface: #13161c;
      --bg-surface-elevated: #1a1e26;
      --bg-surface-inset: #08090c;
      --bg-wash: #171b22;
      --bg-wash-hover: #1e232c;

      --ink-primary: #f0f2f5;
      --ink-secondary: #9da5b2;
      --ink-tertiary: #868e9c;
      --ink-muted: #4e5563;

      --border-subtle: rgba(255, 255, 255, 0.08);
      --border-default: rgba(255, 255, 255, 0.14);
      --border-strong: rgba(255, 255, 255, 0.25);
      --border-focus: #ff6835;

      --signal-orange: #ff6835;
      --signal-orange-dim: rgba(255, 104, 53, 0.15);
      --signal-orange-border: rgba(255, 104, 53, 0.35);
      --signal-orange-glow: rgba(255, 104, 53, 0.28);

      --signal-green: #34d399;
      --signal-green-dim: rgba(52, 211, 153, 0.12);
      --signal-green-border: rgba(52, 211, 153, 0.28);

      --signal-amber: #fbbf24;
      --signal-amber-dim: rgba(251, 191, 36, 0.12);
      --signal-amber-border: rgba(251, 191, 36, 0.28);

      --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.3);
      --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.4), 0 1px 2px rgba(0, 0, 0, 0.3);
      --shadow-md: 0 6px 20px -3px rgba(0, 0, 0, 0.5);
      --shadow-console: 0 20px 48px -12px rgba(0, 0, 0, 0.65), 0 0 0 1px var(--border-default);
      --shadow-cell: inset 0 2px 4px rgba(0, 0, 0, 0.4);
      --shadow-cell-focus: 0 0 0 3px var(--signal-orange-glow), 0 0 0 1px var(--signal-orange);
    }
  }

  :root[data-theme="dark"] {
    --bg-canvas: #0c0e12;
    --bg-surface: #13161c;
    --bg-surface-elevated: #1a1e26;
    --bg-surface-inset: #08090c;
    --bg-wash: #171b22;
    --bg-wash-hover: #1e232c;

    --ink-primary: #f0f2f5;
    --ink-secondary: #9da5b2;
    --ink-tertiary: #868e9c;
    --ink-muted: #4e5563;

    --border-subtle: rgba(255, 255, 255, 0.08);
    --border-default: rgba(255, 255, 255, 0.14);
    --border-strong: rgba(255, 255, 255, 0.25);
    --border-focus: #ff6835;

    --signal-orange: #ff6835;
    --signal-orange-dim: rgba(255, 104, 53, 0.15);
    --signal-orange-border: rgba(255, 104, 53, 0.35);
    --signal-orange-glow: rgba(255, 104, 53, 0.28);

    --signal-green: #34d399;
    --signal-green-dim: rgba(52, 211, 153, 0.12);
    --signal-green-border: rgba(52, 211, 153, 0.28);

    --signal-amber: #fbbf24;
    --signal-amber-dim: rgba(251, 191, 36, 0.12);
    --signal-amber-border: rgba(251, 191, 36, 0.28);

    --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.3);
    --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.4), 0 1px 2px rgba(0, 0, 0, 0.3);
    --shadow-md: 0 6px 20px -3px rgba(0, 0, 0, 0.5);
    --shadow-console: 0 20px 48px -12px rgba(0, 0, 0, 0.65), 0 0 0 1px var(--border-default);
    --shadow-cell: inset 0 2px 4px rgba(0, 0, 0, 0.4);
    --shadow-cell-focus: 0 0 0 3px var(--signal-orange-glow), 0 0 0 1px var(--signal-orange);
  }

  * { box-sizing:border-box; }
  body {
    margin:0; padding:0 24px 100px;
    background:var(--bg-canvas); color:var(--ink-primary);
    font:16px/1.6 var(--sans); -webkit-font-smoothing:antialiased;
    -webkit-text-size-adjust:100%%;
  }
  main { max-width:820px; margin:0 auto; }

  /* Links and focus */
  a {
    color:inherit; text-decoration:underline;
    text-decoration-color:color-mix(in srgb, currentColor 28%%, transparent);
    text-underline-offset:3px; text-decoration-thickness:1px;
    transition:color 0.15s ease, text-decoration-color 0.15s ease;
  }
  a:hover { color:var(--signal-orange); text-decoration-color:var(--signal-orange); }
  :focus-visible { outline:2px solid var(--signal-orange); outline-offset:3px; border-radius:4px; }
  code {
    font-family:var(--mono); font-size:.88em;
    background:var(--bg-wash); border:1px solid var(--border-subtle);
    border-radius:5px; padding:2px 6px; font-feature-settings:"tnum" 1;
  }

  /* Header */
  .top {
    display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between;
    gap:12px 24px; padding:24px 0 20px; margin-bottom:44px;
    border-bottom:1px solid var(--border-subtle);
  }
  .brand {
    display:inline-flex; align-items:center; gap:9px;
    font:700 16px/1 var(--mono); letter-spacing:-.01em;
    color:var(--ink-primary); text-decoration:none;
  }
  .brand-icon { flex-shrink:0; color:var(--ink-primary); transition:transform .2s ease; }
  .brand:hover .brand-icon { transform:scale(1.05); }
  .icon { display:inline-block; vertical-align:-2px; flex-shrink:0; }
  .top nav { display:flex; align-items:center; gap:6px; }
  .top nav a {
    font-size:14.5px; font-weight:500; color:var(--ink-secondary);
    text-decoration:none; padding:6px 12px; border-radius:7px;
    transition:all 0.15s ease;
  }
  .top nav a:hover { color:var(--ink-primary); background:var(--bg-wash); }
  .top nav a.nav-gh { display:inline-flex; align-items:center; padding:7px 8px; }
  .top nav a.nav-gh .icon { vertical-align:0; }
  @media (max-width:640px) { .top nav { gap:0; margin-left:-8px; } .top nav a { padding:6px 8px; font-size:14px; } }
  .top nav a[aria-current] {
    color:var(--ink-primary); background:var(--bg-wash);
    font-weight:600; box-shadow:inset 0 0 0 1px var(--border-subtle);
  }

  /* Type scale and hierarchy */
  h1 { font-size:34px; line-height:1.15; font-weight:700; letter-spacing:-.025em; margin:0 0 10px; color:var(--ink-primary); }
  h2 { font-size:22px; line-height:1.3; font-weight:700; letter-spacing:-.015em; margin:52px 0 16px; color:var(--ink-primary); }
  h3 { font-size:17px; line-height:1.35; font-weight:700; margin:0 0 8px; color:var(--ink-primary); }
  .lede { font-size:18px; line-height:1.5; color:var(--ink-secondary); margin:0; max-width:36em; }
  p, li { max-width:40em; color:var(--ink-secondary); }
  p strong, li strong { color:var(--ink-primary); }
  .small, .fine { font-size:13.5px; color:var(--ink-tertiary); line-height:1.5; }
  .fine { margin-top:12px; }
  @media (max-width:640px) { h1 { font-size:28px; } .top { margin-bottom:32px; } }

  /* Grid and panels */
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
  @media (max-width:640px) { .grid { grid-template-columns:1fr; } }
  .grid > * { min-width:0; }
  .panel {
    background:var(--bg-surface); border:1px solid var(--border-subtle);
    border-radius:12px; padding:22px 24px; box-shadow:var(--shadow-xs);
  }

  /* Status pills */
  .tag {
    display:inline-flex; align-items:center; font-size:12px; font-weight:600;
    border-radius:9999px; padding:2px 9px; margin-left:8px;
    vertical-align:1px; white-space:nowrap; letter-spacing:0.02em;
    border:1px solid transparent;
  }
  .tag.plain {
    color:var(--signal-amber); background:var(--signal-amber-dim);
    border-color:var(--signal-amber-border);
  }
  .tag.enc {
    color:var(--signal-green); background:var(--signal-green-dim);
    border-color:var(--signal-green-border);
  }

  /* Tables */
  .tbl {
    overflow-x:auto; margin:16px 0; border:1px solid var(--border-subtle);
    border-radius:10px; background:var(--bg-surface); box-shadow:var(--shadow-xs);
  }
  table { border-collapse:collapse; width:100%%; font-size:14.5px; }
  th, td { text-align:left; vertical-align:top; padding:12px 18px; border-bottom:1px solid var(--border-subtle); }
  th { font-size:13px; font-weight:700; color:var(--ink-secondary); background:var(--bg-wash); letter-spacing:.02em; }
  tr:last-child td { border-bottom:0; }
  tr:hover td { background:var(--bg-wash); }

  /* Call log / exchange cards (.script) */
  .script { list-style:none; margin:16px 0 24px; padding:0; display:flex; flex-direction:column; gap:12px; }
  .script > li {
    display:grid; grid-template-columns:160px 1fr; gap:16px 24px;
    padding:16px 20px; background:var(--bg-surface);
    border:1px solid var(--border-subtle); border-radius:10px;
    box-shadow:var(--shadow-xs); max-width:none; transition:border-color .15s ease;
  }
  .script > li:hover { border-color:var(--border-default); }
  .script .who {
    display:inline-flex; align-items:center; font:600 13px/1.4 var(--mono);
    color:var(--ink-secondary); letter-spacing:.02em;
    background:var(--bg-wash); padding:4px 10px; border-radius:6px;
    border:1px solid var(--border-subtle); height:fit-content; width:fit-content;
  }
  .script .line { margin:0; font-size:18px; line-height:1.4; font-weight:700; color:var(--ink-primary); }
  .script .then { margin:6px 0 0; color:var(--ink-secondary); font-size:14.5px; line-height:1.5; }
  .script > li.optional { border-style:dashed; background:transparent; }
  .script > li.optional .line { font-weight:500; }

  /* Spec definition list (.facts: one spec-sheet card) */
  .facts {
    margin:16px 0 28px; padding:0;
    background:var(--bg-surface);
    border:1px solid var(--border-subtle);
    border-radius:12px;
    box-shadow:var(--shadow-xs);
    overflow:hidden;
  }
  .facts > div {
    display:grid; grid-template-columns:180px 1fr; gap:12px 24px;
    padding:14px 22px;
    border-bottom:1px solid var(--border-subtle);
    transition:background 0.15s ease;
  }
  .facts > div:last-child { border-bottom:0; }
  .facts > div:hover { background:var(--bg-wash); }
  .facts dt { font:600 14px/1.4 var(--sans); color:var(--ink-secondary); padding-top:2px; }
  .facts dd { margin:0; font-size:14.5px; color:var(--ink-secondary); line-height:1.5; }
  .facts dd strong, .facts dd b { color:var(--ink-primary); }
  .facts dt.warn { color:var(--signal-amber); font-weight:700; }

  @media (max-width:640px) {
    .script > li, .facts > div { grid-template-columns:1fr; gap:8px; padding:14px 16px; }
    .script .line { font-size:16px; }
  }

  /* Small tag for the 8-letter code (.chip) */
  .chip {
    font:700 .9em/1 var(--mono); letter-spacing:.08em; white-space:nowrap;
    color:var(--ink-primary); background:var(--bg-wash);
    border:1px solid var(--border-default); border-radius:6px;
    padding:3px 7px; box-shadow:var(--shadow-xs);
  }


  /* Theme toggle */
  .theme-btn {
    display:inline-flex; align-items:center; justify-content:center;
    width:32px; height:32px; padding:0; margin-left:4px;
    background:var(--bg-surface); border:1px solid var(--border-default);
    border-radius:8px; color:var(--ink-secondary); cursor:pointer;
    box-shadow:var(--shadow-xs); transition:all .15s ease;
  }
  .theme-btn:hover {
    color:var(--ink-primary); border-color:var(--border-strong);
    background:var(--bg-wash);
  }
  .theme-btn .moon { display:block; }
  .theme-btn .sun { display:none; }
  @media (prefers-color-scheme:dark) {
    :root:not([data-theme="light"]) .theme-btn .moon { display:none; }
    :root:not([data-theme="light"]) .theme-btn .sun { display:block; }
  }
  :root[data-theme="dark"] .theme-btn .moon { display:none; }
  :root[data-theme="dark"] .theme-btn .sun { display:block; }
  :root[data-theme="light"] .theme-btn .moon { display:block; }
  :root[data-theme="light"] .theme-btn .sun { display:none; }

  /* Footer */
  footer {
    margin-top:80px; padding:24px 0 0; border-top:1px solid var(--border-subtle);
    font-size:13.5px; color:var(--ink-tertiary);
  }
  footer p { margin:0 0 6px; max-width:none; color:var(--ink-tertiary); }
  footer a { color:var(--ink-secondary); }
  footer a.gh { white-space:nowrap; }
  footer a.gh .icon { vertical-align:-2px; margin-right:5px; }
""" % {"next": _F.get("atkinson-hyperlegible-next.woff2", ""),
       "mono": _F.get("atkinson-hyperlegible-mono.woff2", "")}

SITE = "handover.tools"   # the product site (D47)
REPO = "https://github.com/gammaland/handover"
_NAV = [("/guide", "Guide"), ("/security", "Security"), ("/writing", "Writing"), ("/llms.txt", "For agents")]


def header(current: str = "", site: str = SITE) -> str:
    nav = _NAV if site == SITE else []
    links = "".join(
        f'<a href="{href}"{" aria-current=page" if href == current else ""}>{label}</a>'
        for href, label in nav)
    toggle = ('<button id="theme-btn" class="theme-btn" aria-label="Toggle theme" title="Toggle theme">'
              '<svg class="sun" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>'
              '<svg class="moon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>'
              '</button>')
    gh = (f'<a class="nav-gh" href="{REPO}" aria-label="Source on GitHub" title="Source on GitHub">'
          + icons.ICON_GITHUB.replace('width="14" height="14"', 'width="18" height="18"') + '</a>') if nav else ""
    return (f'<header class="top"><a class="brand" href="/">{icons.BRAND_ICON}{site}</a>'
            f'<nav>{links}{gh}{toggle}</nav></header>')


def page(*, title: str, desc: str, body: str, current: str = "", md: str = "",
         extra_css: str = "", script: str = "", agents_footer: bool = True, site: str = SITE) -> str:
    """agents_footer=False: the page body already has a For agents section (the homepage), so the footer doesn't repeat it."""
    alt = (f'<link rel="alternate" type="text/markdown" href="{md}" '
           f'title="Markdown version for LLMs">') if md else ""
    foot_md = f', or <a href="{md}">this page as Markdown</a>' if md else ""
    preload = "".join(
        f'<link rel="preload" href="/fonts/{n}?v={h}" as="font" type="font/woff2" crossorigin>'
        for n, h in _F.items())
    agents_line = (f'  <p>Agents: start with <a href="/llms.txt">/llms.txt</a>{foot_md}. '
                   f'MCP endpoint <code>https://{SITE}/mcp</code>.</p>\n') if agents_footer else ""
    theme_init = """<script>
(function(){
  try {
    var t = localStorage.getItem('theme');
    if (t) document.documentElement.setAttribute('data-theme', t);
  } catch(e){}
})();
document.addEventListener('DOMContentLoaded', function(){
  var b = document.getElementById('theme-btn');
  if (!b) return;
  b.addEventListener('click', function(){
    var c = document.documentElement.getAttribute('data-theme');
    var d = c === 'dark' || (!c && window.matchMedia('(prefers-color-scheme: dark)').matches);
    var n = d ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', n);
    try { localStorage.setItem('theme', n); } catch(e){}
  });
});
</script>"""
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{desc}">
<link rel="canonical" href="https://{site}{current or '/'}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{site}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="https://{site}{current or '/'}">
<meta property="og:image" content="https://{SITE}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="handover.tools: one agent writes it, another reads it, you carry an 8-letter link">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
{preload}
{alt}
<title>{title}</title>
{theme_init}
<style>{CSS}{extra_css}</style>
<main>
{header(current, site)}
{body}
<footer>
{agents_line}  <p>No account, no key. <a href="/terms">Terms</a> · <a href="/privacy">Privacy</a> · <a href="/changelog">Changelog</a> · <a href="/writing">Writing</a> · <a class="gh" href="{REPO}">{icons.ICON_GITHUB}Source on GitHub</a>. Report abuse: <a href="mailto:abuse@handover.tools">abuse@handover.tools</a></p>
</footer>
</main>
{script}
"""
