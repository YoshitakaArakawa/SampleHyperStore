"""Publish the SampleHyperStore raw layer: one published data source per CSV, with display names and descriptions.

For each table in setup/metadata/raw_layer.json (12 tables):
  1. Build a .hyper extract from csv/in_use/<table>.csv (column types from columns.yaml).
  2. Publish it as "SampleHyperStore - <table>" with the data source description (REST, CreateNew).
  3. Download the published .tdsx, write the column display names and descriptions into its .tds,
     drop the "Number of Records" field Tableau adds to a published .hyper, and publish it again over
     the same data source (Overwrite). The data source keeps its id.
  4. Download it once more and check that every column has its display name, description and
     default aggregation (the "default_aggregation" of the table in raw_layer.json, if any).

With --update, the data sources already exist: each one is downloaded with its extract, given the
display names, descriptions and default aggregations again, and overwritten (steps 3-4 only). Its id
stays the same, so the rpt_ data sources composed from it keep working.

With --replace, the data sources already exist and only their rows change: the new .hyper is sent with
the REST call "Update Data in Hyper Data Source" and one "replace" action, which empties the table and
inserts the new rows in one job. The data source definition (.tds) is not republished, so its logical
table, display names and descriptions stay. The rpt_ data sources composed from it keep reading the
old rows until each one is opened in the web editor and published again without changes; their
relationships and calculated fields stay. The columns (names and types) must not change; the script
checks every table first and stops before writing if one differs.

With --republish, the data sources already exist and their columns changed: the new .hyper is published
over each one (Overwrite, id kept) and the metadata is written again (steps 3-4). Each rpt_ data source
that uses the table then needs the web editor (see SETUP_FOR_AI.md, step 1).

Usage (from en/setup):
    python scripts/publish_raw.py --project "SampleHyperStore/raw" --dry-run
    python scripts/publish_raw.py --project "SampleHyperStore/raw"
    python scripts/publish_raw.py --project "SampleHyperStore/raw" --tables orders order_lines
    python scripts/publish_raw.py --project "SampleHyperStore/raw" --tables orders --update
    python scripts/publish_raw.py --project "SampleHyperStore/raw" --tables orders --replace
    python scripts/publish_raw.py --project "SampleHyperStore/raw" --tables orders --republish

--project is the path of an existing project, levels separated by "/".
Sign-in: scripts/tableau_auth.py (browser sign-in; .env holds SERVER and SITE_NAME only).
Work files go to setup/work/ (git-ignored).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
import zipfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SETUP = HERE.parent
ROOT = SETUP.parent  # en
WORK = SETUP / "work" / "raw"
sys.path.insert(0, str(HERE))


# ----------------------------------------------------------------- inputs
def dataset_dir(path: str | None) -> Path:
    """The dataset folder: en (English, default) or ja."""
    return Path(path).resolve() if path else ROOT


def load_inputs(data: Path = ROOT):
    raw = json.loads((data / "setup" / "metadata" / "raw_layer.json").read_text(encoding="utf-8"))
    cols = yaml.safe_load((data / "columns.yaml").read_text(encoding="utf-8"))
    return raw, cols


def caption(col: str) -> str:
    return " ".join(w[:1].upper() + w[1:] for w in col.split("_"))


# ----------------------------------------------------------------- 1. hyper
def csv_files(data: Path, table: str) -> list[Path]:
    """csv/<folder>/<table>.csv, or csv/<folder>/<table>_<part>.csv when a large table is split (e.g. by year)."""
    one = sorted((data / "csv").glob(f"*/{table}.csv"))
    return one if one else sorted((data / "csv").glob(f"*/{table}_[0-9]*.csv"))


def build_hyper(table: str, columns: list[list[str]], out: Path, data: Path = ROOT) -> int:
    from tableauhyperapi import (Connection, CreateMode, HyperProcess, SqlType, TableDefinition,
                                 TableName, Telemetry, escape_string_literal)

    def sql_type(t: str):
        if t == "string":
            return SqlType.text()
        if t == "integer":
            return SqlType.big_int()
        if t.startswith("decimal"):
            return SqlType.double()
        if t == "date":
            return SqlType.date()
        if t == "datetime":
            return SqlType.timestamp()
        if t == "boolean":
            return SqlType.bool()
        raise ValueError(f"unknown type {t} in {table}")

    files = csv_files(data, table)
    if not files:
        raise SystemExit(f"{table}: no CSV in {data / 'csv'}")
    for f in files:
        header = f.open(encoding="utf-8").readline().strip().split(",")
        if header != [c[0] for c in columns]:
            raise SystemExit(f"{f.name}: CSV header differs from columns.yaml")
    out.parent.mkdir(parents=True, exist_ok=True)
    tdef = TableDefinition(TableName("Extract", "Extract"),
                           [TableDefinition.Column(c, sql_type(t)) for c, t in columns])
    # keep Hyper's log (it records local paths) in the git-ignored work folder
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU,
                      parameters={"log_dir": str(out.parent)}) as hp:
        with Connection(hp.endpoint, out, CreateMode.CREATE_AND_REPLACE) as con:
            con.catalog.create_schema("Extract")
            con.catalog.create_table(tdef)
            n = 0
            for f in files:
                n += con.execute_command(
                    f"COPY {tdef.table_name} FROM {escape_string_literal(str(f))} "
                    "WITH (format csv, header true, NULL '')")
    return n


# ----------------------------------------------------------------- 3. tds edits
def _esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("'", "&apos;").replace('"', "&quot;"))


def _desc_block(text: str) -> str:
    return ("\n    <desc>\n      <formatted-text>\n"
            f"        <run>{_esc(text)}</run>\n"
            "      </formatted-text>\n    </desc>\n  ")


def _metadata(txt: str) -> dict:
    """remote-name -> (local id without brackets, local-type)."""
    out = {}
    for m in re.finditer(r"<metadata-record class='column'>(.*?)</metadata-record>", txt, re.S):
        body = m.group(1)
        rn = re.search(r"<remote-name>(.*?)</remote-name>", body, re.S)
        ln = re.search(r"<local-name>\[(.*?)\]</local-name>", body, re.S)
        lt = re.search(r"<local-type>(.*?)</local-type>", body, re.S)
        if rn and ln:
            out[rn.group(1)] = (ln.group(1), lt.group(1) if lt else "string")
    return out


def name_logical_table(txt: str, table: str) -> str:
    """Name the single logical table "<table>.csv".

    The rpt_ formulas refer to duplicated columns as "<Column> (<table>.csv)"; Tableau builds that
    suffix from the logical table's caption, so it must match the name used on the reference site.
    """
    objs = re.findall(r"<object caption='[^']*' id='[^']*'>", txt)
    if len(set(objs)) != 1:
        raise ValueError(f"expected one logical table, found {len(set(objs))}")
    new = re.sub(r"caption='[^']*'", f"caption='{_esc(table)}.csv'", objs[0], count=1)
    return txt.replace(objs[0], new)


AGG = {"SUM": "Sum", "AVG": "Avg"}


def _agg_attr(cap: str, aggregations: dict) -> str:
    return f" aggregation='{AGG[aggregations[cap]]}'" if cap in aggregations else ""


NUMREC = re.compile(r"\n?[ \t]*<column\b[^>]*user:auto-column='numrec'[^>]*?(/>|>.*?</column>)", re.S)


def strip_numrec(txt: str) -> str:
    return NUMREC.sub("", txt)


def annotate_tds(txt: str, columns: list[str], descriptions: dict, aggregations: dict | None = None) -> str:
    """Give every column its display name (caption), description and default aggregation at the data-source level.

    Also drop the "Number of Records" column Tableau adds when a .hyper is published
    (user:auto-column='numrec'): the rpt_ data sources would carry it as a calculated field.
    """
    aggregations = aggregations or {}
    txt = strip_numrec(txt)
    meta = _metadata(txt)
    for col in columns:
        cap = caption(col)
        if col not in meta:
            raise ValueError(f"column {col} not found in the downloaded .tds")
        local, dtype = meta[col]
        desc = _desc_block(descriptions[cap])
        name_attr = f"name='[{_esc(local)}]'"
        # existing <column ... name='[local]' ...> (self-closing or open)
        m = re.search(r"<column\b[^>]*" + re.escape(name_attr) + r"[^>]*?(/?)>", txt)
        if m:
            tag = m.group(0)
            new_tag = re.sub(r"\s+(caption|aggregation)='[^']*'", "", tag)
            new_tag = new_tag.replace("<column", f"<column{_agg_attr(cap, aggregations)} caption='{_esc(cap)}'", 1)
            if tag.endswith("/>"):
                new = new_tag[:-2].rstrip() + ">" + desc + "</column>"
                txt = txt[:m.start()] + new + txt[m.end():]
            else:
                end = txt.index("</column>", m.end())
                body = re.sub(r"\s*<desc>.*?</desc>", "", txt[m.end():end], flags=re.S)
                txt = txt[:m.start()] + new_tag + desc + body.strip() + "\n  " + txt[end:]
        else:
            role, typ = (("measure", "quantitative") if dtype in ("integer", "real")
                         else ("dimension", "nominal" if dtype in ("string", "boolean") else "ordinal"))
            block = (f"  <column{_agg_attr(cap, aggregations)} caption='{_esc(cap)}' datatype='{dtype}' {name_attr} "
                     f"role='{role}' type='{typ}'>{desc}</column>\n")
            anchor = "<aliases enabled='yes' />"
            if anchor in txt:
                txt = txt.replace(anchor, anchor + "\n" + block, 1)
            else:
                i = txt.index("</connection>") + len("</connection>")
                txt = txt[:i] + "\n" + block + txt[i:]
    return txt


def read_tdsx(path: Path):
    z = zipfile.ZipFile(path)
    name = next(n for n in z.namelist() if n.endswith(".tds"))
    return z, name, z.read(name).decode("utf-8")


def write_tdsx(z: zipfile.ZipFile, tds_name: str, txt: str, out: Path):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
        for item in z.infolist():
            data = txt.encode("utf-8") if item.filename == tds_name else z.read(item.filename)
            zo.writestr(item, data)


def check_tds(txt: str, columns: list[str], descriptions: dict, aggregations: dict | None = None) -> list[str]:
    aggregations = aggregations or {}
    meta = _metadata(txt)
    missing = []
    for col in columns:
        local = meta.get(col, (col, ""))[0]
        m = re.search(r"<column\b[^>]*name='\[" + re.escape(_esc(local)) + r"\]'[^>]*>(.*?)</column>", txt, re.S)
        cap = caption(col)
        if not m or f"caption='{_esc(cap)}'" not in m.group(0) or _esc(descriptions[cap]) not in m.group(1):
            missing.append(cap)
        elif _agg_attr(cap, aggregations) and _agg_attr(cap, aggregations).strip() not in m.group(0):
            missing.append(f"{cap} (aggregation)")
    return missing


def schema_diff(txt: str, columns: list[list[str]]) -> list[str]:
    """Differences between the published columns (.tds) and columns.yaml; empty when they match."""
    meta = _metadata(txt)
    want = {c: ("real" if t.startswith("decimal") else t) for c, t in columns}
    diff = [f"new column {c}" for c in want if c not in meta]
    diff += [f"column {c} is gone" for c in meta if c not in want]
    diff += [f"{c}: {meta[c][1]} -> {want[c]}" for c in want if c in meta and meta[c][1] != want[c]]
    return diff


def tds_fingerprint(txt: str) -> dict:
    """What the rpt_ data sources depend on: logical table ids and captions, and each column's
    caption, description and aggregation. The server reorders and renames other parts of the .tds
    (column order, connection name, dbname) when it stores new rows, so those are left out."""
    cols = {}
    for m in re.finditer(r"<column\b([^>]*?)(/>|>(.*?)</column>)", txt, re.S):
        attrs, body = m.group(1), m.group(3) or ""
        name = re.search(r"name='([^']*)'", attrs)
        if not name:
            continue
        cap = re.search(r"caption='([^']*)'", attrs)
        agg = re.search(r"aggregation='([^']*)'", attrs)
        desc = re.findall(r"<run>(.*?)</run>", body, re.S)
        cols[name.group(1)] = (cap.group(1) if cap else None, agg.group(1) if agg else None, tuple(desc))
    objects = sorted(set(re.findall(r"<object caption='([^']*)' id='([^']*)'", txt)))
    return {"objects": objects, "columns": cols}


def numrec_count(txt: str) -> int:
    return txt.count("user:auto-column='numrec'")


def download_tds(server, ds_id: str, out: Path) -> str:
    f = Path(server.datasources.download(ds_id, filepath=str(out), include_extract=False))
    z, _, txt = read_tdsx(f)
    z.close()
    return txt


def replace_rows(server, ds, hyper: Path) -> None:
    """Replace every row of the published table Extract.Extract with the rows of the local .hyper (one job)."""
    actions = [{"action": "replace", "source-schema": "Extract", "source-table": "Extract",
                "target-schema": "Extract", "target-table": "Extract"}]
    job = server.datasources.update_hyper_data(ds, request_id=str(uuid.uuid4()), actions=actions,
                                               payload=str(hyper))
    server.jobs.wait_for_job(job)  # raises JobFailedException / JobCancelledException


# ----------------------------------------------------------------- Tableau
def find_project(server, path: str):
    import tableauserverclient as TSC
    parts = [p for p in path.split("/") if p]
    projects = list(TSC.Pager(server.projects))
    parent = None
    for p in parts:
        hit = [x for x in projects if x.name == p and x.parent_id == (parent.id if parent else None)]
        if not hit:
            raise SystemExit(f"project not found: {path} (create it first)")
        parent = hit[0]
    return parent


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", required=True, help='existing project path, e.g. "SampleHyperStore/raw"')
    ap.add_argument("--tables", nargs="*", help="subset of tables (default: all 12)")
    ap.add_argument("--dry-run", action="store_true", help="build the .hyper files only; do not sign in")
    ap.add_argument("--update", action="store_true",
                    help="the data sources exist: rewrite names, descriptions and aggregations, and overwrite them")
    ap.add_argument("--replace", action="store_true",
                    help="the data sources exist and the columns did not change: replace their rows only")
    ap.add_argument("--republish", action="store_true",
                    help="the data sources exist and the columns changed: overwrite them with the new .hyper "
                         "(ids kept), then rewrite metadata; rpt_ data sources need the web editor afterwards")
    ap.add_argument("--name-format", default="SampleHyperStore - {table}", help=argparse.SUPPRESS)  # test runs only
    ap.add_argument("--data", help="dataset folder (default: en; the Japanese edition: ../../ja)")
    a = ap.parse_args()
    if a.update + a.replace + a.republish > 1:
        raise SystemExit("use only one of --update, --replace and --republish")

    data = dataset_dir(a.data)
    raw, cols = load_inputs(data)
    tables = a.tables or list(raw)
    unknown = [t for t in tables if t not in raw]
    if unknown:
        raise SystemExit(f"not in raw_layer.json: {unknown}")

    hyper, rows = {}, {}
    for t in ([] if a.update else tables):
        hyper[t] = WORK / t / f"{t}.hyper"
        rows[t] = build_hyper(t, cols[t], hyper[t], data)
        print(f"[hyper] {t}: {rows[t]:,} rows")
    if a.dry_run:
        print("dry run: nothing published")
        return

    import tableauserverclient as TSC
    from tableau_auth import signed_in_server

    def existing(server, project, ds_name):
        opts = TSC.RequestOptions()
        opts.filter.add(TSC.Filter(TSC.RequestOptions.Field.Name, TSC.RequestOptions.Operator.Equals, ds_name))
        hits = [x for x in TSC.Pager(server.datasources, opts) if x.project_id == project.id]
        if len(hits) != 1:
            raise SystemExit(f"{ds_name}: expected one data source in the project, found {len(hits)}")
        return hits[0]

    report = {}
    with signed_in_server() as server:
        project = find_project(server, a.project)
        if a.replace:
            report = replace_all(server, project, tables, raw, cols, hyper, rows, a.name_format, existing)
        for t in ([] if a.replace else tables):
            spec = raw[t]
            ds_name = a.name_format.format(table=t)
            colnames = [c[0] for c in cols[t]]
            aggs = spec.get("default_aggregation", {})
            d = WORK / t
            d.mkdir(parents=True, exist_ok=True)
            if a.update or a.republish:
                ds = existing(server, project, ds_name)
                print(f"[{'republish' if a.republish else 'update'}] {ds_name} ({ds.id})")
                if a.republish:
                    item = TSC.DatasourceItem(project.id, name=ds_name)
                    item.description = spec["datasource_description"]
                    new = server.datasources.publish(item, str(hyper[t]), TSC.Server.PublishMode.Overwrite)
                    if new.id != ds.id:
                        raise SystemExit(f"{ds_name}: overwrite changed the id ({ds.id} -> {new.id})")
            else:
                item = TSC.DatasourceItem(project.id, name=ds_name)
                item.description = spec["datasource_description"]
                ds = server.datasources.publish(item, str(hyper[t]), TSC.Server.PublishMode.CreateNew)
                print(f"[publish] {ds_name} -> {ds.id}")

            first = Path(server.datasources.download(ds.id, filepath=str(d / "published")))
            z, tds_name, txt = read_tdsx(first)
            (d / "published.tds").write_text(txt, encoding="utf-8")
            edited = annotate_tds(name_logical_table(txt, t), colnames, spec["columns"], aggs)
            (d / "edited.tds").write_text(edited, encoding="utf-8")
            write_tdsx(z, tds_name, edited, d / "edited.tdsx")
            z.close()

            item2 = TSC.DatasourceItem(project.id, name=ds_name)
            item2.description = spec["datasource_description"]
            ds2 = server.datasources.publish(item2, str(d / "edited.tdsx"), TSC.Server.PublishMode.Overwrite)

            back = Path(server.datasources.download(ds2.id, filepath=str(d / "verified"), include_extract=False))
            z3, _, txt3 = read_tdsx(back)
            z3.close()
            missing = check_tds(txt3, colnames, spec["columns"], aggs)
            report[t] = {"luid": ds2.id, "same_id": ds2.id == ds.id, "columns": len(colnames),
                         "numrec_after": numrec_count(txt3), "missing_caption_or_description": missing}
            print(f"[verify] {t}: id kept={ds2.id == ds.id}, columns={len(colnames)}, missing={missing}")
    (WORK / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    bad = [t for t, r in report.items()
           if r.get("failed") or r["missing_caption_or_description"] or not r["same_id"]
           or not r.get("tds_unchanged", True) or r.get("numrec_after", 0) > r.get("numrec_before", 0)]
    print("done" if not bad else f"check these tables: {bad}")
    sys.exit(1 if bad else 0)


def replace_all(server, project, tables, raw, cols, hyper, rows, name_format, existing) -> dict:
    """--replace: check every table's columns first, then replace the rows table by table."""
    plan = []
    for t in tables:
        ds = existing(server, project, name_format.format(table=t))
        d = WORK / t
        d.mkdir(parents=True, exist_ok=True)
        before = download_tds(server, ds.id, d / "before")
        (d / "before.tds").write_text(before, encoding="utf-8")
        diff = schema_diff(before, cols[t])
        if diff:
            raise SystemExit(f"{ds.name}: the columns changed ({'; '.join(diff)}). Nothing was replaced. "
                             "Use --republish for this table (see SETUP_FOR_AI.md, step 1).")
        plan.append((t, ds, before))

    report = {}
    for t, ds, before in plan:
        print(f"[replace] {ds.name} ({ds.id}): {rows[t]:,} rows")
        try:
            replace_rows(server, ds, hyper[t])
        except Exception as e:  # job failed or cancelled: keep what was done so far in report.json
            report[t] = {"luid": ds.id, "same_id": True, "failed": f"{type(e).__name__}: {e}",
                         "missing_caption_or_description": []}
            print(f"[replace] {t}: failed ({type(e).__name__}); the tables after it were not replaced")
            break
        after = download_tds(server, ds.id, WORK / t / "after")
        (WORK / t / "after.tds").write_text(after, encoding="utf-8")
        spec = raw[t]
        missing = check_tds(after, [c[0] for c in cols[t]], spec["columns"], spec.get("default_aggregation", {}))
        unchanged = tds_fingerprint(after) == tds_fingerprint(before)
        report[t] = {"luid": ds.id, "same_id": True, "rows": rows[t], "columns": len(cols[t]),
                     "tds_unchanged": unchanged, "numrec_before": numrec_count(before),
                     "numrec_after": numrec_count(after), "missing_caption_or_description": missing}
        print(f"[verify] {t}: logical table and columns unchanged={unchanged}, missing={missing}, "
              f"Number of Records columns {numrec_count(before)} -> {numrec_count(after)}")
        if missing:
            print(f"  {t}: names or descriptions differ from raw_layer.json (--replace does not write them; "
                  "run --update for this table)")
    return report


if __name__ == "__main__":
    main()
