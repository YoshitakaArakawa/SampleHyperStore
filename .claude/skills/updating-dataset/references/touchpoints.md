---
purpose: Every file that has to change when the SampleHyperStore dataset changes, with what it holds and what it depends on
note: Kinds are A (tables in the setup), B (the data itself), C (metadata only), as in SKILL.md. "Script" says whether scripts/check_consistency.py checks the file. Paths are from the repository root; "en/ja" means both editions.
---

# Touchpoints

## Sources of truth

| File | Holds | Read by | Kind |
|---|---|---|---|
| `en/setup/metadata/raw_layer.json` | The tables Tableau uses; data source and column descriptions; default aggregations of numeric columns | `generate.py` (`folder_of`), `publish_raw.py`, `check_metadata.py` | A, C |
| `en/setup/metadata/rpt_layer.json` | The six rpt_ data sources: `parent_tables`, `root`, `relationships`, `calculated_fields` | `describe_rpt.py`, `check_metadata.py`, the person at the web editor | A, C |
| `en/setup/metadata/business_preferences.json` | Business Preferences for Tableau Knowledge. "Term: Relative dates mean relative to the end of the data" states the period of the data, the only place that does | `SETUP_FOR_AI.md` step 6 | B (period changed), C |
| `ja/setup/metadata/*.json` | Hand translation of the three files above. Same keys and structure; column names are the Japanese ones | the same scripts with `--data ../../ja` | A, C |
| `en/columns.yaml` | Column order and type of all tables | generator, `publish_raw.py`, `build_jp.py` | B |
| `tools/build_ja/translation/columns.yaml`, `values.yaml` | English → Japanese column names and values | `build_jp.py` | B (new column or value) |
| `tools/generator/world_spec.yaml`, `tools/generator/gen/` | The simulated world and its seed | `generate.py` | B |

## Generated files

| File | Made by | Kind | Script |
|---|---|---|---|
| `en/csv/in_use/`, `en/csv/planned/` | `generate.py` → `out/`, copied by hand. Folder chosen from `raw_layer.json` | A (move), B | tables, rows |
| `en/SHA256SUMS` | By hand: `sha256sum -b */*.csv` from `en/csv/`. Lines carry the folder | A, B | — (`generate.py --check`) |
| `ja/csv/`, `ja/columns.yaml`, `ja/SHA256SUMS` | `build_jp.py` (removes stale files itself) | A, B | tables |
| `tools/generator/answer_key/` (git-ignored) | `generate.py`. What each event touched | B | — |
| `tools/showcase/numbers.json` (git-ignored) | `analyze.py`, from `en/csv/` | B | — |
| `docs/index.html` | `build.py`, from `page.template.html` and `numbers.json` | A, B, C | — |

## Documents with hand-written content

| File | Holds | Kind | Script |
|---|---|---|---|
| `README.md` | Count of tables (both languages) | A | counts |
| `en/README.md`, `ja/README.md` | `csv/in_use/` and `csv/planned/` counts; mermaid ER diagram of the in-use tables; setup diagram (data sources, Business Preferences); Business Preference names in "Where agents trip up" | A, C | counts, pref names (not the ER diagram) |
| `en/docs/data_dictionary.md`, `ja/docs/data_dictionary.md` | Table list (rows, `Tableau` yes/blank); per table: `File:` line with folder and rows, column table | A, B | counts, rows, folders (not the column tables) |
| `en/setup/SETUP_FOR_AI.md` | Counts of tables, data sources, calculated fields, Business Preferences, questions; list of the in-use tables; raw row-count table; rpt_ relationship table; expected totals | A, B, C | counts, table list, row table (not relationships or totals) |
| `en/docs/setup_manual.md`, `ja/docs/setup_manual.md` | Counts; rpt_ relationship table; expected totals; appendix copying `business_preferences.json` | A, B, C | counts, appendix (not relationships or totals) |
| `en/docs/questions.md`, `ja/docs/questions.md` | The questions; the count; which questions the showcase page answers | A, B | counts |
| `tools/README.md`, `en/columns.yaml`, `tools/build_ja/build_jp.py` | Count of all CSVs | B (table added) | counts |
| `en/setup/scripts/publish_raw.py`, `describe_rpt.py` | Counts in the docstrings | A | counts |

## The showcase page

`tools/showcase/page.template.html` mixes figures injected from `numbers.json` (`__DATA__`, the keys listed in `build.py`) with figures written by hand. After any B change, compare the hand-written ones with a fresh `numbers.json`. Both languages are in one file, in the `L` object (`L.ja` and `L.en`).

| Where | Holds | Kind | Script |
|---|---|---|---|
| `L.*.cases.*`: `answer`, `kpis`, `trap`, `prefs` | Answer sentences, KPI values, Business Preference names per case | B, C | — |
| `L.*.ch` (chart labels) | Values and periods written into labels and notes | B | — |
| `DRAW` (chart code) | Periods to shade or mark, axis ranges, the window each chart shows | B | — |
| `L.*.h1`, `sub`, `title`, `hsStat`; `class="count"` spans | Count of tables and Business Preferences; count of joins and key kinds | A, C | counts (not joins or key kinds) |
| `L.*.prefs` | All Business Preference names, by category | C | pref names |
| `EDGES`, node positions, `L.*.tables`, `keys`, `doms` | The join diagram of the in-use tables | A | — |
| `tools/showcase/build.py` | Meta description with the count of tables | A | counts |
| `tools/showcase/analyze.py` | The calculations behind `numbers.json`; reads in-use and planned CSVs | B | — |
