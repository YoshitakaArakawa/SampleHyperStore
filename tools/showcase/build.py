"""Inject numbers.json into page.template.html.

Writes:
  docs/index.html          the published page (GitHub Pages serves docs/ on main)
  tools/showcase/out/      artifact.html, the same page without the document skeleton (git-ignored)
"""
import json
from pathlib import Path

here = Path(__file__).resolve().parent
root = here.parents[1]
d = json.loads((here / "numbers.json").read_text(encoding="utf-8"))
keep = {"S": d["S"]}
body = (here / "page.template.html").read_text(encoding="utf-8").replace("__DATA__", json.dumps(keep, separators=(",", ":")))

head = ('<!doctype html>\n<html lang="ja">\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="description" content="SampleHyperStore: ask AI business questions that span 12 tables. / 12 枚の表をまたいで、AI と業務の問いを解く。">\n'
        '<style>body{margin:0}</style>\n')
(root / "docs").mkdir(exist_ok=True)
(root / "docs" / "index.html").write_text(head + body, encoding="utf-8")

out = here / "out"
out.mkdir(exist_ok=True)
(out / "artifact.html").write_text(body, encoding="utf-8")
print(len(head + body))
