"""python -m app.cli file.pdf [out.json]"""
import json
import sys

from .pipeline import extract

if len(sys.argv) < 2:
    sys.exit("usage: python -m app.cli file.pdf [out.json]")
r = extract(sys.argv[1], lambda p, m: print(f"{p:4.0%} {m}", file=sys.stderr))
for w in r["warnings"]:
    print("warning:", w, file=sys.stderr)
for p in r["pages"]:
    print(f"page {p['pageNum']}:", p["stats"], file=sys.stderr)
if len(sys.argv) > 2:
    open(sys.argv[2], "w").write(json.dumps(r, indent=2))
else:
    print(r["text"])
