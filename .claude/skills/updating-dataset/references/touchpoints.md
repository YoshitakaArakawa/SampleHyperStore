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

`tools/showcase/page.template.html` takes every figure from `S` in `numbers.json` (`__DATA__`; `build.py` injects only `S`). Texts hold `{path:format}` placeholders filled from `S`, and the charts read `S` directly, so a B change only needs `analyze.py` and `build.py` re-run. Still read the texts after a B change: a sentence such as "sales fell in the subcategories shown out of stock" can stop being true even though its numbers update. Both languages are in one file, in the `L` object (`L.ja` and `L.en`).

| Where | Holds | Kind | Script |
|---|---|---|---|
| `L.*.stockout`, `L.*.returns`, `L.*.sales`, `L.*.uses`, `L.*.cat` | The analysis example (steps, answer), the two AI behaviour examples, what the analysis uses, the example questions; sentences with `{path:format}` placeholders and Business Preference names | B, C | — |
| `STEPS_A`, `MINI` (chart code) | The charts of the analysis steps and of the AI behaviour examples: axis ranges, the months shown | B | — |
| `const X` | Numbers derived from `S` in the browser (ranges, shares, which subcategories to name) | B | — |
| `analyze.py` section "case stories" (`S`) | The as-of month of the analysis example, the comparison months, the subcategory grouping rules | B | — |
| `L.*.h1`, `sub`, `title`; `class="count"` spans | Count of tables | A | counts |
| `S.meta` (from the metadata JSON) | Counts of column descriptions, relationships, calculated fields and Business Preferences shown at the top | A, C | — |
| `L.*.prefs` | All Business Preferences, by category, in plain words (not their titles) | C | — |
| `EDGES`, node positions, `L.*.tables`, `keys`, `doms` | The join diagram of the in-use tables | A | — |
| `tools/showcase/build.py` | Meta description with the count of tables | A | counts |
| `tools/showcase/analyze.py` | The calculations behind `numbers.json`; reads the in-use CSVs and the metadata JSON | B | — |
