---
name: updating-dataset
description: Guides a maintainer through changing the SampleHyperStore dataset and keeps every dependent file in step. Covers three kinds of change — putting a planned table into the Tableau setup (or taking one out), regenerating the data from the generator, and editing descriptions, relationships, calculated fields or Business Preferences — and checks the result locally with a consistency script. Use when asked to add or move a table, use a csv/planned table, regenerate or change the CSVs, change world_spec.yaml or the seed, add or rename columns, edit raw_layer.json, rpt_layer.json or business_preferences.json, or fix counts and row numbers in the docs (「planned の表を使いたい」「データを作り直す」「計算フィールドを足す」「メタデータを直す」).
---

# Updating the dataset

## Rules

- **Ask the user before anything that writes to Tableau**: `publish_raw.py`, `describe_rpt.py`, a republish from the web editor, a deletion, a Knowledge write. Name the project and the data sources, and wait for a yes.
- **Keep the planted events out of the files.** What the events are lives only in `tools/generator/world_spec.yaml` and the git-ignored `tools/generator/answer_key/`. Do not copy it into `en/`, `ja/`, commit messages or this skill: the agent under test can read them.
- **Edit English and Japanese as a pair.** Only `ja/csv/`, `ja/columns.yaml` and `ja/SHA256SUMS` are generated (by `tools/build_ja/build_jp.py`). The Japanese metadata JSON and docs are translated by hand.
- **Never edit a CSV by hand.** CSVs come from the generator and are checked against `SHA256SUMS`.
- **Do not copy procedures here.** Generation is in `tools/README.md`; publishing is in `en/setup/SETUP_FOR_AI.md`. Follow them.

## Identify the kind of change

| Kind | The request touches | Go to |
|---|---|---|
| A. Tables in the setup | Which tables Tableau uses (`csv/in_use/` vs `csv/planned/`), or a new rpt_ data source | [A](#a-change-which-tables-the-setup-uses) |
| B. The data itself | `world_spec.yaml`, generator code, the seed, `columns.yaml` | [B](#b-regenerate-the-data) |
| C. Metadata only | Descriptions, default aggregations, relationships, calculated fields, Business Preferences | [C](#c-change-metadata-only) |

One request can be several kinds. Do them in the order B → A → C: A moves the CSVs that B writes, and C describes the tables A selects. Run the final check once at the end.

[references/touchpoints.md](references/touchpoints.md) lists every file to update, what it holds and what it depends on. Open it while working.

## A. Change which tables the setup uses

`en/setup/metadata/raw_layer.json` decides the tables. `generate.py` (`folder_of`) and `publish_raw.py` both read it.

1. Add (or remove) the table in `raw_layer.json`, English and Japanese. List every column of `columns.yaml`, in order, as its display caption: English `order_id` → `Order Id`; Japanese uses the name in `ja/columns.yaml` unchanged.
2. Move the files:
   1. `git mv` the CSV between `en/csv/planned/` and `en/csv/in_use/`.
   2. Rewrite `en/SHA256SUMS`: from `en/csv/`, run `sha256sum -b */*.csv > ../SHA256SUMS`. Confirm with `generate.py --check`.
   3. Rebuild the Japanese CSVs with `build_jp.py`.
3. Decide which rpt_ data sources use the table. Edit `rpt_layer.json` in both languages as in [C](#c-change-metadata-only).
4. Update the documents in the "A" rows of touchpoints.md: counts, table lists, the ER and join diagrams, `data_dictionary.md`, the showcase page.
5. Run the [final check](#final-check).
6. On Tableau, after the user agrees:
   - Adding: `SETUP_FOR_AI.md` step 1 with `--tables <table>`, then steps 3–4 for each affected rpt_ data source.
   - Removing: delete the raw data source in the web UI, and recompose the rpt_ data sources that used it.
   - Either way, recreate the Knowledge graph over the new set of data sources (step 6).
   - Replace the expected totals in `SETUP_FOR_AI.md` and both `setup_manual.md` with the values Tableau returns.

## B. Regenerate the data

1. Copy `tools/generator/answer_key/` aside if you will compare old and new: `generate.py` overwrites it.
2. For a new column or a new categorical value, first update `columns.yaml` and `tools/build_ja/translation/` (`build_jp.py` stops on anything missing). Add the column to `raw_layer.json` (both languages) when the table is in use, and to the column tables of both `data_dictionary.md`.
3. Generate, check and copy the output into `en/csv/` as in `tools/README.md`. Only the intended tables should differ from `en/SHA256SUMS`. Rewrite `en/SHA256SUMS` as in A-2 and rebuild the Japanese edition.
4. Confirm the questions still hold: compare `answer_key/` with `en/docs/questions.md`. A question whose event no longer shows in the data must be changed or removed, in both languages.
5. If the first or last date of the data changed, update the Business Preference "Term: Relative dates mean relative to the end of the data" in both languages (descriptions do not state the period).
6. Rebuild the showcase page (`analyze.py`, then `build.py`). Read its texts again: the figures update by themselves, but a sentence can stop being true ([the showcase page](references/touchpoints.md#the-showcase-page)).
7. Run the [final check](#final-check). Row counts are checked by the script; the expected totals are not.
8. On Tableau, after the user agrees: load the new rows into the existing raw data sources ("Data sources that already exist" in `SETUP_FOR_AI.md` step 1: `--replace` when the columns did not change, `--republish` when B-2 added or changed a column; a new categorical value alone keeps the columns, so `--replace`), republish each affected rpt_ data source from the web editor as described there, and query the totals (step 3). Write the new totals into `SETUP_FOR_AI.md` and both `setup_manual.md`.

## C. Change metadata only

1. Edit the English JSON in `en/setup/metadata/`, then the same place in `ja/setup/metadata/`. In `rpt_layer.json`, the order of `parent_tables` decides which duplicated column gets the ` (<table>.csv)` suffix that formulas use.
2. Update what repeats the metadata:
   - the relationship tables in `SETUP_FOR_AI.md` and both `setup_manual.md`;
   - the counts of calculated fields and Business Preferences;
   - the appendix of both `setup_manual.md` (a copy of `business_preferences.json`);
   - the Business Preference names in the READMEs and on the showcase page.
3. Run the [final check](#final-check).
4. On Tableau, after the user agrees:
   - Raw column or data source descriptions, or default aggregations: `publish_raw.py --tables <table> --update` (rewrites the existing data sources in place; their ids stay, so the rpt_ data sources keep working). It also drops a leftover "Number of Records" field; then republish each rpt_ data source that uses the table from the web editor without changes, and the field disappears there too.
   - rpt_ data source descriptions and calculated-field descriptions: `describe_rpt.py`, then the republish (`SETUP_FOR_AI.md` step 4).
   - Relationships or calculated fields: rebuild or edit the data source in the web editor (step 3), then step 4.
   - Business Preferences: change or delete the item in the knowledge graph's web UI; new items as in step 6. Wait about 15 minutes after the last publish.
   - Confirm with `check_metadata.py`.

## Final check

```
python ${CLAUDE_SKILL_DIR}/scripts/check_consistency.py
```

It needs PyYAML only and runs in a few seconds without Tableau. What it covers is the "Script" column of touchpoints.md.

`pattern not found` means a sentence holding a count was reworded. Update its entry in `COUNT_PATTERNS` in the script, then run again. A new sentence that states a count needs a new entry.
