"""Check that the SampleHyperStore files agree with each other, without Tableau.

Checks:
  1. tables   en/ja raw_layer.json tables == the CSVs in csv/in_use/; every columns.yaml table has one CSV
  2. columns  raw_layer.json columns == columns.yaml (as display captions, same order);
              rpt_layer.json parent tables, relationship keys and formula field references exist
  3. en-ja    the English and Japanese metadata JSON have the same structure
  4. counts   hand-written counts and row counts in the documents match the files

Usage (from the repository root, or anywhere):
    python .claude/skills/updating-dataset/scripts/check_consistency.py
    python .claude/skills/updating-dataset/scripts/check_consistency.py --skip-rows   # skip CSV row counting

Exit code 0 when everything matches, 1 otherwise. Needs PyYAML (in tools/requirements.txt).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]  # .claude/skills/updating-dataset/scripts -> repository root
EDITIONS = ("en", "ja")
WORDS = {"six": 6, "twelve": 12}
errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def load_json(rel: str):
    return json.loads(read(rel))


def caption(col: str) -> str:
    """Same rule as en/setup/scripts/publish_raw.py: snake_case -> Title Case; Japanese names stay as they are."""
    return " ".join(w[:1].upper() + w[1:] for w in col.split("_"))


def csv_table(path: Path) -> str:
    """Table name of a CSV file. A large table may be split by year: <table>_<yyyy>.csv."""
    return re.sub(r"_\d{4}$", "", path.stem)


def datasources(rpt: dict) -> dict:
    return {k: v for k, v in rpt.items() if not k.startswith("_")}


# ----------------------------------------------------------------- 1. tables
def check_tables(ed: str) -> None:
    raw = load_json(f"{ed}/setup/metadata/raw_layer.json")
    cols = yaml.safe_load(read(f"{ed}/columns.yaml"))
    in_use = {csv_table(p) for p in (ROOT / ed / "csv" / "in_use").glob("*.csv")}
    planned = {csv_table(p) for p in (ROOT / ed / "csv" / "planned").glob("*.csv")}
    if set(raw) != in_use:
        err(f"[tables] {ed}: raw_layer.json and csv/in_use/ differ: only in JSON {sorted(set(raw) - in_use)}, "
            f"only in CSV {sorted(in_use - set(raw))}")
    if in_use & planned:
        err(f"[tables] {ed}: in both in_use/ and planned/: {sorted(in_use & planned)}")
    if set(cols) != in_use | planned:
        err(f"[tables] {ed}: columns.yaml tables and CSVs differ: no CSV {sorted(set(cols) - in_use - planned)}, "
            f"not in columns.yaml {sorted(in_use | planned - set(cols))}")


# ----------------------------------------------------------------- 2. columns
def check_columns(ed: str) -> None:
    raw = load_json(f"{ed}/setup/metadata/raw_layer.json")
    rpt = load_json(f"{ed}/setup/metadata/rpt_layer.json")
    cols = yaml.safe_load(read(f"{ed}/columns.yaml"))
    caps = {}
    for t, spec in raw.items():
        want = [caption(c) for c, _ in cols.get(t, [])]
        got = list(spec["columns"])
        caps[t] = want
        if got != want:
            err(f"[columns] {ed}: {t}: raw_layer.json columns differ from columns.yaml: "
                f"missing {[c for c in want if c not in got]}, extra {[c for c in got if c not in want]}"
                + ("" if set(got) != set(want) else " (order only)"))
        for c, d in spec["columns"].items():
            if not str(d).strip():
                err(f"[columns] {ed}: {t}.{c}: empty description")
    for ds, spec in datasources(rpt).items():
        parents = spec["parent_tables"]
        for t in parents:
            if t not in raw:
                err(f"[columns] {ed}: {ds}: parent table {t} is not in raw_layer.json")
        if spec["root"] not in parents:
            err(f"[columns] {ed}: {ds}: root {spec['root']} is not in parent_tables")
        for r in spec["relationships"]:
            for side, t in (("from", r["from"]), ("to", r["to"])):
                if t not in parents:
                    err(f"[columns] {ed}: {ds}: relationship {side} {t} is not in parent_tables")
            for a, b in r["keys"]:
                if a not in caps.get(r["from"], []) or b not in caps.get(r["to"], []):
                    err(f"[columns] {ed}: {ds}: key {a} / {b} not found in {r['from']} / {r['to']}")
        # A formula may use a column of a parent table, the same column with the " (<table>.csv)" suffix
        # that Tableau adds to a duplicated name, or another calculated field of the same data source.
        allowed = {c for t in parents for c in caps.get(t, [])}
        allowed |= {f"{c} ({t}.csv)" for t in parents for c in caps.get(t, [])}
        allowed |= {f["name"] for f in spec["calculated_fields"]}
        for f in spec["calculated_fields"]:
            for ref in re.findall(r"\[([^\]]+)\]", f["formula"]):
                if ref not in allowed:
                    err(f"[columns] {ed}: {ds}: calculated field {f['name']!r} uses unknown field [{ref}]")
            if not f.get("description", "").strip():
                err(f"[columns] {ed}: {ds}: calculated field {f['name']!r} has no description")


# ----------------------------------------------------------------- 3. en-ja
def check_en_ja() -> None:
    tr = yaml.safe_load(read("tools/build_ja/translation/columns.yaml"))
    to_ja = {caption(en): ja for cl in tr.values() for en, ja, _ in cl}

    raw = {ed: load_json(f"{ed}/setup/metadata/raw_layer.json") for ed in EDITIONS}
    if list(raw["en"]) != list(raw["ja"]):
        err(f"[en-ja] raw_layer.json tables differ: en {list(raw['en'])}, ja {list(raw['ja'])}")
    for t in raw["en"]:
        if t in raw["ja"] and raw["en"][t]["datasource_name"] != raw["ja"][t]["datasource_name"]:
            err(f"[en-ja] raw_layer.json {t}: datasource_name differs (data source names stay English)")

    rpt = {ed: load_json(f"{ed}/setup/metadata/rpt_layer.json") for ed in EDITIONS}
    if list(rpt["en"]) != list(rpt["ja"]):
        err(f"[en-ja] rpt_layer.json keys differ: en {list(rpt['en'])}, ja {list(rpt['ja'])}")
    for ds, e in datasources(rpt["en"]).items():
        j = rpt["ja"].get(ds)
        if j is None:
            continue
        for k in ("parent_tables", "root"):
            if e[k] != j[k]:
                err(f"[en-ja] {ds}: {k} differs")
        er = [(r["from"], r["to"], [[to_ja.get(a), to_ja.get(b)] for a, b in r["keys"]]) for r in e["relationships"]]
        jr = [(r["from"], r["to"], r["keys"]) for r in j["relationships"]]
        if er != jr:
            err(f"[en-ja] {ds}: relationships differ (keys compared through tools/build_ja/translation/columns.yaml)")
        if len(e["calculated_fields"]) != len(j["calculated_fields"]):
            err(f"[en-ja] {ds}: {len(e['calculated_fields'])} calculated fields in en, {len(j['calculated_fields'])} in ja")

    bp = {ed: load_json(f"{ed}/setup/metadata/business_preferences.json") for ed in EDITIONS}
    if len(bp["en"]["items"]) != len(bp["ja"]["items"]):
        err(f"[en-ja] business_preferences.json: {len(bp['en']['items'])} items in en, {len(bp['ja']['items'])} in ja")


# ----------------------------------------------------------------- 4. counts
def actual_counts() -> dict:
    raw = load_json("en/setup/metadata/raw_layer.json")
    rpt = datasources(load_json("en/setup/metadata/rpt_layer.json"))
    cols = yaml.safe_load(read("en/columns.yaml"))
    return {
        "in_use": len(raw),
        "planned": len(cols) - len(raw),
        "all_tables": len(cols),
        "rpt": len(rpt),
        "datasources": len(raw) + len(rpt),
        "calcs": sum(len(v["calculated_fields"]) for v in rpt.values()),
        "prefs": len(load_json("en/setup/metadata/business_preferences.json")["items"]),
        "questions": len(re.findall(r"^\| Q\d+ ", read("en/docs/questions.md"), re.M)),
    }


N = r"(\d+|six|twelve)"
# (file, pattern with one number group, count key). Every match must equal the actual count, and each
# pattern must match at least once: when a sentence is rewritten, update its pattern here.
COUNT_PATTERNS = [
    ("README.md", rf"besides the {N} tables", "in_use"),
    ("README.md", rf"{N} のテーブルとメタデータ", "in_use"),
    ("en/README.md", rf"The {N} tables the Tableau setup uses", "in_use"),
    ("en/README.md", rf"{N} more tables, not used", "planned"),
    ("en/README.md", rf"besides the {N} tables", "in_use"),
    ("en/README.md", rf"The {N} tables in `csv/in_use/`", "in_use"),
    ("en/README.md", rf'"{N} data sources<br/>SampleHyperStore', "in_use"),
    ("en/README.md", rf'"{N} data sources<br/>rpt_', "rpt"),
    ("en/README.md", rf"graph of the {N} data sources", "datasources"),
    ("en/README.md", rf"{N} Business Preferences", "prefs"),
    ("en/README.md", rf"The {N} department data sources", "rpt"),
    ("ja/README.md", rf"セットアップで使う {N} テーブル", "in_use"),
    ("ja/README.md", rf"使っていない {N} テーブル", "planned"),
    ("ja/README.md", rf"`csv/in_use/` の {N} テーブル", "in_use"),
    ("ja/README.md", rf"{N} のテーブルとメタデータ", "in_use"),
    ("ja/README.md", rf'"{N} データソース<br/>SampleHyperStore', "in_use"),
    ("ja/README.md", rf'"{N} データソース<br/>rpt_', "rpt"),
    ("ja/README.md", rf"{N} データソースの<br/>", "datasources"),
    ("ja/README.md", rf"ビジネス設定 {N} 件", "prefs"),
    ("en/setup/SETUP_FOR_AI.md", rf'{N} published data sources "SampleHyperStore', "in_use"),
    ("en/setup/SETUP_FOR_AI.md", rf'{N} published data sources "rpt_', "rpt"),
    ("en/setup/SETUP_FOR_AI.md", rf"with {N} calculated fields", "calcs"),
    ("en/setup/SETUP_FOR_AI.md", rf"graph over the {N} data sources", "datasources"),
    ("en/setup/SETUP_FOR_AI.md", rf"\+ {N} Business Preferences", "prefs"),
    ("en/setup/SETUP_FOR_AI.md", rf"The {N} tables are:", "in_use"),
    ("en/setup/SETUP_FOR_AI.md", rf"The other {N} CSVs", "planned"),
    ("en/setup/SETUP_FOR_AI.md", rf"all {N} raw data sources", "in_use"),
    ("en/setup/SETUP_FOR_AI.md", rf'{N} data sources "SampleHyperStore - <table>"', "in_use"),
    ("en/setup/SETUP_FOR_AI.md", rf'{N} data sources "rpt_samplehyperstore__<dept>"', "rpt"),
    ("en/setup/SETUP_FOR_AI.md", rf"Compose the {N} rpt_ data sources", "rpt"),
    ("en/setup/SETUP_FOR_AI.md", rf"all {N} questions", "questions"),
    ("en/setup/SETUP_FOR_AI.md", rf"against these {N} data sources", "rpt"),
    ("en/setup/SETUP_FOR_AI.md", rf"select all {N}", "datasources"),
    ("en/setup/SETUP_FOR_AI.md", rf"the {N} items", "prefs"),
    ("en/setup/SETUP_FOR_AI.md", rf"\): {N} items", "prefs"),
    ("en/setup/SETUP_FOR_AI.md", rf"lists all {N}", "prefs"),
    ("en/docs/setup_manual.md", rf"{N} data sources `SampleHyperStore", "in_use"),
    ("en/docs/setup_manual.md", rf"{N} data sources `rpt_", "rpt"),
    ("en/docs/setup_manual.md", rf"{N} Business Preferences", "prefs"),
    ("en/docs/setup_manual.md", rf"The {N} data sources in the raw", "in_use"),
    ("en/docs/setup_manual.md", rf"The {N} data sources in the marts", "rpt"),
    ("en/docs/setup_manual.md", rf"the {N} raw data sources", "in_use"),
    ("en/docs/setup_manual.md", rf"the {N} department data sources", "rpt"),
    ("en/docs/setup_manual.md", rf"Each of the {N} tables", "in_use"),
    ("en/docs/setup_manual.md", rf"Build the {N} department data sources", "rpt"),
    ("en/docs/setup_manual.md", rf"all {N} data sources of the raw", "datasources"),
    ("en/docs/setup_manual.md", rf"the {N} items", "prefs"),
    ("en/docs/setup_manual.md", rf"The {N} items for step 4", "prefs"),
    ("ja/docs/setup_manual.md", rf"生の層 {N} 本", "in_use"),
    ("ja/docs/setup_manual.md", rf"{N} データソース `SampleHyperStore", "in_use"),
    ("ja/docs/setup_manual.md", rf"{N} データソース `rpt_", "rpt"),
    ("ja/docs/setup_manual.md", rf"ビジネス設定 {N} 件", "prefs"),
    ("ja/docs/setup_manual.md", rf"raw にある {N} データソース", "in_use"),
    ("ja/docs/setup_manual.md", rf"marts にある {N} データソース", "rpt"),
    ("ja/docs/setup_manual.md", rf"生の層の {N} データソース", "in_use"),
    ("ja/docs/setup_manual.md", rf"部門の層の {N} データソース", "rpt"),
    ("ja/docs/setup_manual.md", rf"{N} テーブルそれぞれ", "in_use"),
    ("ja/docs/setup_manual.md", rf"層の {N} 本（", "datasources"),
    ("ja/docs/setup_manual.md", rf"付録\]\(#[^)]*\)の{N}件", "prefs"),
    ("ja/docs/setup_manual.md", rf"{N} 件あること", "prefs"),
    ("ja/docs/setup_manual.md", rf"入力する{N}件", "prefs"),
    ("en/docs/data_dictionary.md", rf"{N} tables, one CSV each", "all_tables"),
    ("en/docs/data_dictionary.md", rf"the {N} tables that `setup/`", "in_use"),
    ("en/docs/data_dictionary.md", rf"The other {N} are not used", "planned"),
    ("ja/docs/data_dictionary.md", rf"{N} テーブル、テーブルごと", "all_tables"),
    ("ja/docs/data_dictionary.md", rf"パブリッシュする {N} テーブル", "in_use"),
    ("ja/docs/data_dictionary.md", rf"残りの {N} テーブル", "planned"),
    ("en/docs/questions.md", rf"^{N} analysis questions", "questions"),
    ("ja/docs/questions.md", rf"投げる {N} の分析の問い", "questions"),
    ("en/columns.yaml", rf"of the {N} CSVs", "all_tables"),
    ("ja/columns.yaml", rf"of the {N} CSVs", "all_tables"),
    ("tools/build_ja/build_jp.py", rf"of the {N} CSVs", "all_tables"),
    ("tools/README.md", rf"writes the {N} English CSVs", "all_tables"),
    ("en/setup/scripts/publish_raw.py", rf"raw_layer\.json \({N} tables\)", "in_use"),
    ("en/setup/scripts/describe_rpt.py", rf"# all {N}", "rpt"),
    ("tools/showcase/build.py", rf"span {N} tables", "in_use"),
    ("tools/showcase/build.py", rf"{N} 枚の表をまたいで", "in_use"),
    ("tools/showcase/page.template.html", rf"{N} のテーブルをまたいで", "in_use"),
    ("tools/showcase/page.template.html", rf"Webの{N}のテーブル", "in_use"),
    ("tools/showcase/page.template.html", rf"(?:across|span|into) {N} tables", "in_use"),
]


def check_count_patterns(actual: dict) -> None:
    for rel, pat, key in COUNT_PATTERNS:
        hits = re.findall(pat, read(rel), re.M)
        if not hits:
            err(f"[counts] {rel}: pattern not found, update COUNT_PATTERNS: {pat}")
        for h in hits:
            n = WORDS.get(h.lower()) if not h.isdigit() else int(h)
            if n != actual[key]:
                err(f"[counts] {rel}: says {h} for {key}, actual {actual[key]} (pattern {pat})")


def check_lists() -> None:
    """Lists written out in the documents: table names, Business Preference names."""
    raw = load_json("en/setup/metadata/raw_layer.json")
    m = re.search(r"tables are: ([a-z_, ]+)\.", read("en/setup/SETUP_FOR_AI.md"))
    if not m or {t.strip() for t in m.group(1).split(",")} != set(raw):
        err("[lists] en/setup/SETUP_FOR_AI.md: the list after 'The N tables are:' differs from raw_layer.json")

    template = read("tools/showcase/page.template.html")
    for ed, readme, ref in (("en", "en/README.md", r'Business Preference "([^"]+)"'),
                            ("ja", "ja/README.md", r"ビジネス設定「([^」]+)」")):
        items = load_json(f"{ed}/setup/metadata/business_preferences.json")["items"]
        titles = [i["title"] for i in items]
        # Appendix of setup_manual.md: one row per item, same name and text as the JSON.
        manual = read(f"{ed}/docs/setup_manual.md")
        rows = re.findall(r"^\| (\d+) \| (.+?) \| (.+) \|$", manual.split("\n## ")[-1], re.M)
        if [(r[1], r[2]) for r in rows] != [(i["title"], i["text"]) for i in items]:
            err(f"[lists] {ed}/docs/setup_manual.md: appendix differs from business_preferences.json")
        # The showcase page restates every Business Preference in plain words (L.<ed>.prefs), so only the count is checked.
        block = re.search(rf"\n  {ed}: {{.*?\n    prefs: \[(.*?)\n    \],", template, re.S)
        shown = sum(len(re.findall(r'"[^"]*"', inner)) for inner in re.findall(r'\[\s*"[^"]*",\s*\[(.*?)\]\]', block.group(1), re.S)) if block else -1
        if shown != len(items):
            err(f"[lists] page.template.html: L.{ed}.prefs shows {shown} Business Preferences, business_preferences.json has {len(items)}")
        for name in re.findall(ref, read(readme)):
            if not any(name in t for t in titles):
                err(f"[lists] {readme}: Business Preference {name!r} is not in business_preferences.json")


def count_rows(path: Path) -> int:
    with path.open(encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1  # minus the header


def check_rows() -> None:
    """Row counts and file locations written in data_dictionary.md and SETUP_FOR_AI.md."""
    raw = load_json("en/setup/metadata/raw_layer.json")
    rows, folder = {}, {}
    for p in sorted((ROOT / "en" / "csv").glob("*/*.csv")):
        t = csv_table(p)
        rows[t] = rows.get(t, 0) + count_rows(p)
        folder[t] = p.parent.name
    fmt = lambda n: f"{n:,}"
    for ed, file_re in (("en", r"- File: `csv/(\w+)/(\w+)\.csv` \(([\d,]+) rows\)"),
                        ("ja", r"- ファイル: `csv/(\w+)/(\w+)\.csv`（([\d,]+) 行）")):
        rel = f"{ed}/docs/data_dictionary.md"
        text = read(rel)
        seen = set()
        for t, n, flag in re.findall(r"^\| \[`(\w+)`\]\(#\w+\) \|.*\| ([\d,]+) \| *(yes)? *\|$", text, re.M):
            seen.add(t)
            if n != fmt(rows.get(t, -1)):
                err(f"[rows] {rel}: table list says {t} has {n} rows, CSV has {fmt(rows.get(t, -1))}")
            if (flag == "yes") != (t in raw):
                err(f"[rows] {rel}: Tableau column of {t} is {'yes' if flag else 'empty'}, raw_layer.json disagrees")
        if seen != set(rows):
            err(f"[rows] {rel}: table list differs from the CSVs: {sorted(seen ^ set(rows))}")
        seen = set()
        for f, t, n in re.findall(file_re, text):
            seen.add(t)
            if f != folder.get(t):
                err(f"[rows] {rel}: {t} is said to be in csv/{f}/, but it is in csv/{folder.get(t)}/")
            if n != fmt(rows.get(t, -1)):
                err(f"[rows] {rel}: File line says {t} has {n} rows, CSV has {fmt(rows.get(t, -1))}")
        if seen != set(rows):
            err(f"[rows] {rel}: File lines differ from the CSVs: {sorted(seen ^ set(rows))}")
    text = read("en/setup/SETUP_FOR_AI.md")
    pairs = re.findall(r"\| (\w+) \| ([\d,]+) \|", text)
    table_rows = {t: n for t, n in pairs if t in rows}
    if set(table_rows) != set(raw):
        err(f"[rows] en/setup/SETUP_FOR_AI.md: row-count table lists {sorted(table_rows)}, raw_layer.json has {sorted(raw)}")
    for t, n in table_rows.items():
        if n != fmt(rows[t]):
            err(f"[rows] en/setup/SETUP_FOR_AI.md: says {t} has {n} rows, CSV has {fmt(rows[t])}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--skip-rows", action="store_true", help="skip counting CSV rows (the slowest check)")
    a = ap.parse_args()
    for ed in EDITIONS:
        check_tables(ed)
        check_columns(ed)
    check_en_ja()
    actual = actual_counts()
    check_count_patterns(actual)
    check_lists()
    if not a.skip_rows:
        check_rows()
    print("actual counts: " + ", ".join(f"{k}={v}" for k, v in actual.items()))
    if errors:
        print(f"{len(errors)} problem(s):")
        for e in errors:
            print("  " + e)
        return 1
    print("all consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
