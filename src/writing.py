"""Articles at /writing. Source: writing/<slug>.md, embedded by scripts/build.sh.

Each file starts with a front matter block (title, description, date), then Markdown. Only the subset the
articles use is rendered: ## and ### headings, paragraphs, - and 1. lists, ``` code blocks, | pipe tables |, and inline
`code`, **bold**, *italic* and [links](url). It is not a general Markdown renderer; keep articles inside it.
"""
import html
import re

import writing_src
from style import page

_CSS = """
  article { max-width:42rem; }
  article .meta { font-family:"Atkinson Mono", ui-monospace, monospace; font-size:13px; color:var(--ink-tertiary);
                  margin:0 0 28px; }
  article h2 { margin:44px 0 12px; }
  article h3 { margin:28px 0 8px; }
  article p, article li { line-height:1.7; }
  article ul, article ol { padding-left:22px; }
  article li { margin:6px 0; }
  article pre { background:var(--bg-surface-inset, var(--bg-wash)); border:1px solid var(--border-subtle);
                border-radius:8px; padding:14px 16px; overflow-x:auto; line-height:1.5; margin:18px 0; }
  article pre code { background:none; border:0; padding:0; font-size:13.5px; white-space:pre; }
  article .table { overflow-x:auto; margin:18px 0; }
  article table { border-collapse:collapse; width:100%; font-size:15px; }
  article th, article td { text-align:left; vertical-align:top; padding:9px 10px; border-bottom:1px solid var(--border-subtle);
                           line-height:1.5; }
  article td:first-child { font-weight:600; color:var(--ink-primary); min-width:9rem; }
  article td { color:var(--ink-secondary); }
  .posts { list-style:none; padding:0; }
  .posts li { padding:18px 0; border-top:1px solid var(--border-subtle); }
  .posts li:first-child { border-top:0; }
  .posts .meta { font-family:"Atkinson Mono", ui-monospace, monospace; font-size:13px; color:var(--ink-tertiary); }
  .posts a.title { font-size:20px; font-weight:700; }
  .posts p { margin:6px 0 0; color:var(--ink-secondary); }
"""


def _inline(s: str) -> str:
    """Escape HTML, then render `code`, **bold**, *italic* and [text](url). Code spans are protected first."""
    codes = []

    def keep(m):
        codes.append(m.group(1))
        return f"\0{len(codes) - 1}\0"
    s = re.sub(r"`([^`]+)`", keep, s)
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    return re.sub(r"\0(\d+)\0", lambda m: f"<code>{html.escape(codes[int(m.group(1))], quote=False)}</code>", s)


def _blocks(md: str) -> str:
    out, para, items, kind = [], [], [], None
    lines = md.split("\n")

    def flush():
        nonlocal para, items, kind
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>")
        if items:
            out.append(f"<{kind}>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + f"</{kind}>")
        para, items, kind = [], [], None

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush()
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append("<pre><code>" + html.escape("\n".join(lines[i + 1:j]), quote=False) + "</code></pre>")
            i = j + 1
            continue
        if line.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):    # skip the |---| separator row
                    rows.append(cells)
                i += 1
            head, body = rows[0], rows[1:]
            out.append('<div class="table"><table><thead><tr>' + "".join(f"<th>{_inline(c)}</th>" for c in head)
                       + "</tr></thead><tbody>" + "".join(
                           "<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in body)
                       + "</tbody></table></div>")
            continue
        if line.startswith("### "):
            flush(); out.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("## "):
            flush(); out.append(f"<h2>{_inline(line[3:])}</h2>")
        elif re.match(r"^- ", line) or re.match(r"^\d+\. ", line):
            k = "ul" if line.startswith("- ") else "ol"
            if para or (items and kind != k):
                flush()
            kind = k
            items.append(re.sub(r"^(- |\d+\. )", "", line))
        elif line.startswith("  ") and items:          # continuation of a list item
            items[-1] += " " + line.strip()
        elif not line.strip():
            flush()
        else:
            if items:
                flush()
            para.append(line.strip())
        i += 1
    flush()
    return "\n".join(out)


def _parse(src: str) -> dict:
    meta, body = {}, src
    if src.startswith("---\n"):
        head, _, body = src[4:].partition("\n---\n")
        for line in head.split("\n"):
            k, _, v = line.partition(":")
            if k.strip():
                meta[k.strip()] = v.strip()
    return {"title": meta.get("title", ""), "description": meta.get("description", ""),
            "date": meta.get("date", ""), "body": body.strip()}


POSTS = sorted(({"slug": slug, **_parse(src), "src": src} for slug, src in writing_src.POSTS.items()),
               key=lambda p: p["date"], reverse=True)

PAGES = {}
for p in POSTS:
    url = f"/writing/{p['slug']}"
    PAGES[url] = (page(
        title=f"{p['title']} | handover.tools", desc=p["description"], md=url + ".md", current=url,
        extra_css=_CSS,
        body=(f'<article><h1>{_inline(p["title"])}</h1>'
              f'<p class="meta"><time datetime="{p["date"]}">{p["date"]}</time></p>'
              f'{_blocks(p["body"])}</article>')), "text/html; charset=utf-8")
    PAGES[url + ".md"] = (f"# {p['title']}\n\n{p['date']}\n\n{p['body']}\n", "text/markdown; charset=utf-8")

PAGES["/writing"] = (page(
    title="Writing | handover.tools",
    desc="Notes on building handover.tools: end-to-end encryption for agents, Cloudflare Python Workers, and what broke.",
    current="/writing", extra_css=_CSS,
    body=('<h1>Writing</h1><p class="lede intro">Notes on how handover.tools is built, and what broke along the way.</p>'
          '<ul class="posts">' + "".join(
              f'<li><p class="meta">{p["date"]}</p><a class="title" href="/writing/{p["slug"]}">{_inline(p["title"])}</a>'
              f'<p>{_inline(p["description"])}</p></li>' for p in POSTS) + "</ul>")), "text/html; charset=utf-8")
