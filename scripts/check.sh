#!/bin/bash
# Repository rules that CI enforces (AGENTS.md):
#   1. No Chinese (or other CJK) text in tracked files. Full-width Latin letters are allowed: tests use them as input.
#   2. Every decision number (Dxx) referenced anywhere has a section in docs/decisions.md.
set -e
cd "$(dirname "$0")/.."
git ls-files -z | python3 -c '
import re, sys
files = [f for f in sys.stdin.read().split("\0") if f]
# CJK ideographs, CJK punctuation, full-width punctuation. Built with chr() so this file contains none of them.
ranges = [(0x4E00, 0x9FFF), (0x3000, 0x303F), (0xFF01, 0xFF0F), (0xFF1A, 0xFF20)]
cjk = re.compile("[" + "".join(re.escape(chr(a)) + "-" + re.escape(chr(b)) for a, b in ranges) + "]")
dref = re.compile(r"\bD\d{1,2}\b")
bad, refs = 0, {}
for f in files:
    try:
        text = open(f, encoding="utf-8").read()
    except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
        continue
    for i, line in enumerate(text.split("\n"), 1):
        if cjk.search(line):
            print(f"{f}:{i}: CJK text: {line.strip()[:80]}"); bad += 1
    for d in dref.findall(text):
        refs.setdefault(d, f)
headings = "\n".join(l for l in open("docs/decisions.md", encoding="utf-8").read().split("\n") if l.startswith("### "))
have = set(dref.findall(headings))
for d, f in sorted(refs.items()):
    if d != "D1" and d not in have:   # D1 is the Cloudflare database, not a decision
        print(f"{f}: refers to {d}, which has no section in docs/decisions.md"); bad += 1
if bad:
    sys.exit(f"{bad} problem(s)")
print(f"check: {len(files)} files OK")
'
