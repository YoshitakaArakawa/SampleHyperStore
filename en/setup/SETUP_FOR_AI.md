# SampleHyperStore setup — instructions for an AI agent

You are helping a user put SampleHyperStore on their own Tableau Cloud site, so that they can ask an AI agent (through Tableau MCP) analysis questions about it. Read this whole file before acting. Work from the folder `en/setup/`.

## What you will build

```
Project A (raw layer)      12 published data sources "SampleHyperStore - <table>", one per CSV,
                           with column display names and column descriptions          <- script
Project B (rpt_ layer)     6 published data sources "rpt_samplehyperstore__<dept>", each composed
                           from raw-layer data sources, with 54 calculated fields      <- user, in the web editor
                           and their descriptions                                     <- script + web editor
Tableau Knowledge (opt.)   a graph over the 18 data sources + 24 Business Preferences <- web UI + Tableau MCP
```

The 12 tables are: products, orders, order_lines, shipments, shipment_lines, returns, refunds, invoices, invoice_lines, credit_memos, web_sessions, web_searches. Their CSVs are in `../csv/in_use/`. The other 12 CSVs, in `../csv/planned/`, are not part of this setup.

## Rules

- **Ask the user before every step that writes to Tableau** (publish, overwrite, Knowledge writes). Say which project and which data sources.
- **Never ask for, or accept, a password or token in chat.** Sign-in happens in the user's browser.
- **Use a new, empty project.** Do not publish over data sources that already exist on the site.
- VizQL Data Service allows about 100 requests per hour per Creator. `query-datasource` and `get-datasource-metadata` both use it. Read metadata with `scripts/check_metadata.py` (Metadata API) and keep queries to the checks below.
- Do not edit `../csv/`. The files are checked against `../SHA256SUMS`.

## Prerequisites (confirm with the user)

| Need | Why |
|---|---|
| Tableau Cloud, Creator role, permission to publish to two projects | publishing |
| Python 3.10+ on the user's machine | scripts |
| Tableau MCP connected to this AI agent | checks, Business Preferences |
| Tableau+ (Knowledge enabled) — optional | step 6 only |
| A person (or a computer-use agent) who can use the Tableau web editor | steps 3 and 4; for a computer-use agent, the user confirms in step 2 that it can operate their site |

## Step 0. Prepare

1. **Ask the user which edition to set up**, and use it for every script below:

   | Edition | Folder | `--data` | Status |
   |---|---|---|---|
   | English | `en` | (omit) | tested on a fresh project: all 12 raw data sources, and one rpt_ data source (billing) through steps 3–4 |
   | Japanese | `ja` | `--data ../../ja` | same structure and numbers; this setup path is untested |

   The Japanese edition has Japanese column names, values, descriptions, calculated-field names and Business Preferences. Data source names stay English. In step 3, read `metadata/rpt_layer.json` from the chosen edition. Tableau Knowledge officially supports English only, so Knowledge results on the Japanese edition may be weaker.
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in `SERVER` and `SITE_NAME` (ask the user for these two values; they are not secret).
4. `python scripts/tableau_auth.py status` — if no session is cached, the first script run opens the browser for sign-in.
5. Create the projects. Ask the user under which existing project to put them (for example a sandbox project), then:

   ```
   python scripts/create_projects.py --parent "<parent project path>"
   ```

   This creates the structure below and prints the two paths you will use. Tableau MCP cannot create projects. If the script is refused (it needs site admin, or project leader on the parent), ask the user to create the same three projects in the web UI.

   ```
   <parent>/
     <yyyymmdd>_SampleHyperStore/
       raw/     12 data sources "SampleHyperStore - <table>"
       marts/   6 data sources "rpt_samplehyperstore__<dept>"
   ```

   Do not put the data sources in a project that already holds other "SampleHyperStore" data sources: an AI agent that lists data sources would see both.

## Step 1. Publish the raw layer (script)

```
python scripts/publish_raw.py --project "<raw project path>" --dry-run   # builds .hyper files only
python scripts/publish_raw.py --project "<raw project path>"
```

For each table the script publishes a .hyper extract, writes display names and descriptions from `metadata/raw_layer.json` into the data source, overwrites it, downloads it again and checks every column. It ends with `done`, or lists tables to look at; details are in `work/raw/report.json`.

To replace the data of raw data sources that already exist (after the CSVs were regenerated), use `--replace --tables <table>`: it overwrites the data and keeps each data source's id. Like the REST overwrite in step 4, this drops the table from the rpt_ data sources that use it: queries no longer find the calculated fields that read it. Run `describe_rpt.py` for those data sources (step 4, item 1), then open each one in the web editor and:

1. Refresh the data source (toolbar) if the table's new columns are missing. After the refresh the table stands apart from the tree.
2. Draw its relationship again from the parent table's "+" with the keys in step 3 (a person draws it; see step 2).
3. In the Scratchpad, every calculated field that reads the table shows "!". Edit each one, replace the whole formula with the one in `metadata/rpt_layer.json`, and wait for "The calculation is valid."
4. Publish over the same data source. The descriptions written in step 4, item 1 are kept.

Then run the totals query in step 3.

Check without spending query quota: `python scripts/check_metadata.py --project "<raw project path>" --layer raw` (Metadata API; the catalog can lag a few minutes behind a publish). Optionally query row counts for two or three data sources with Tableau MCP:

| Data source | Rows | | Data source | Rows |
|---|---:|---|---|---:|
| products | 202 | | invoices | 32,568 |
| orders | 31,281 | | invoice_lines | 68,621 |
| order_lines | 71,007 | | credit_memos | 6,717 |
| shipments | 32,568 | | web_sessions | 455,057 |
| shipment_lines | 68,621 | | web_searches | 100,524 |
| returns | 6,680 | | refunds | 6,493 |

## Step 2. Decide who does the web-editor work

Steps 3 and 4 need the Tableau web editor: composing published data sources is not available through the REST API in a form these scripts can rely on. Ask the user whether they will do it by hand or have a computer-use agent do it. Either way, give them the procedure below for one data source at a time, and wait for them to say it is published.

If the user chooses a computer-use agent:

1. Ask the user to check two things on their side before starting. You cannot check them from here.
   - Computer use is available in the AI agent they will use for this work.
   - That agent can operate pages on their Tableau Cloud site, including the web editor.
2. If either answer is no, the person does all of steps 3 and 4 by hand.
3. If both are yes, the agent still cannot do all of it. Drawing a relationship from the root's "+" worked in our runs. Dragging from the "+" of a table further down the tree did not register (step 3, item 3). For the data sources below, the person draws the lines that start from a non-root table:

   | rpt_ data source | Lines the person draws |
   |---|---|
   | billing | invoice_lines → products, invoice_lines → credit_memos |
   | sales_orders | order_lines → orders |
   | merchandising | order_lines → orders |
   | shipments | shipment_lines → shipments |

   returns_refunds and web_analytics need only lines from the root.
4. In step 3, each line is drawn right after its table is added, so the agent and the person take turns within one data source. Tell the user the order: the agent stops after adding a table whose line starts from a non-root table, the person draws that line, then the agent continues.
5. Two parts are untested with a computer-use agent: entering the calculated fields (step 3, item 5) and republishing in step 4, item 2.

## Step 3. Compose the six rpt_ data sources (web editor)

Read `metadata/rpt_layer.json`. For each data source:

| rpt_ data source | Base table (root) | Relationships |
|---|---|---|
| rpt_samplehyperstore__billing | invoices | invoices →(Invoice Id) invoice_lines →(Product Id) products; invoice_lines →(Invoice Line Id) credit_memos |
| rpt_samplehyperstore__sales_orders | products | products →(Product Id) order_lines →(Order Id) orders |
| rpt_samplehyperstore__merchandising | products | same as sales_orders |
| rpt_samplehyperstore__shipments | products | products →(Product Id) shipment_lines →(Shipment Id) shipments |
| rpt_samplehyperstore__returns_refunds | returns | returns →(Product Id) products; returns →(Return Id) refunds |
| rpt_samplehyperstore__web_analytics | web_sessions | web_sessions →(Session Id) web_searches |

Procedure for the person at the web editor:

1. New published data source → "On this site" → connect to the root's raw data source (`SampleHyperStore - <root>`). Open the Data Source tab.
2. Add the other raw data sources with "Add published data source", in the order they appear in `parent_tables` in the JSON, skipping the root. The order decides which copy of a duplicated column name gets the " (<table>.csv)" suffix, and some formulas use that suffix (for example `[Order Id (order_lines.csv)]` in sales_orders: connect products, then add orders, then order_lines).
3. **Keep exactly one base table.** Draw each relationship from the "+" at the right edge of a table that is already in the tree to the new table. Never draw from the new table into the tree: that makes it a second base table, and its measures then repeat the grand total when split by the other tables' dimensions.
   - A computer-use agent can draw from the root's "+", but dragging from the "+" of a table further down the tree did not register in our runs. Ask the person to draw those lines by hand. This affects billing, sales_orders, merchandising and shipments; the lines are listed in step 2.
4. Pick the key fields for each relationship as in the table above. No dashed line or "!" may remain.
5. Add each calculated field from `calculated_fields` in the Scratchpad: data pane menu (▾) → Create Calculated Field → name and formula exactly as written → it must say "The calculation is valid." → OK. **Create them here, in the web editor.** This applies to the first setup and to every field listed in the JSON at that time. Later, to add one calculated field to an rpt_ data source that is already set up (for example a field added to `rpt_layer.json` after the setup), the REST API also works. No script does this: download the .tdsx, add the `<column>` with its `<calculation>` (and `<desc>`) to the .tds by hand, and publish it with Overwrite the same way `describe_rpt.py` does. The overwrite drops the composition; republishing from the web editor without changes (step 4, item 2) restores it and keeps the field and its description. Then run `check_metadata.py --layer rpt` and check that the formula matches. Confirmed once on billing, 2026-11, with one row-level field that refers to one raw column. Not tried: a field that refers to another calculated field or to a column with a " (<table>.csv)" suffix, and a republish that also changes something in the editor.
6. Publish → name `rpt_samplehyperstore__<dept>`. **Choose the rpt_ project in the dialog**: it defaults to the root data source's project (the raw one). Leave "embed credentials" off. The data source description defaults to the root's; `describe_rpt.py` in step 4 replaces it with `datasource_description`.

Check after each one: `python scripts/check_metadata.py --project "<marts project path>" --layer rpt` shows the calculated fields and whether each formula matches. (Prefer this to `get-datasource-metadata` in Tableau MCP, which calls VizQL Data Service and counts against the query quota.) Then one query per data source (no dimensions) against these totals:

| Data source | Field | Expected |
|---|---|---:|
| sales_orders | Units | 111,008 |
| merchandising | Units / Order Lines | 115,435 / 71,007 |
| shipments | Units | 110,762 |
| returns_refunds | Requested Units / Received Units / Refunds | 7,944 / 6,704 / 907,537.58 |
| web_analytics | Sessions / Transactions / Units Added to Cart | 455,057 / 24,484 / 191,594 |
| billing | Gross Revenue | 13,347,403.19 |

Then one split check per data source with a product attribute (for example Units by Category). If a measure shows the same value in every category, the data source has two base tables: redo step 3.3.

## Step 4. Describe the calculated fields (script + web editor)

The web editor cannot write field descriptions, and the lineage page is unreliable for it. Use two steps per data source:

1. `python scripts/describe_rpt.py --project "<rpt_ project path>" --datasources billing` — writes the descriptions from `metadata/rpt_layer.json` and overwrites the data source through REST. This drops the composition for a moment.
2. The person at the web editor opens the data source **again from its page** (an editor tab opened before step 1 still holds the old version) → Edit → Publish → same name and project → Overwrite, with no changes. This restores the composition and keeps the descriptions. The first click on Publish sometimes does nothing; click again.

Check: `check_metadata.py --layer rpt` shows the descriptions, and the same totals query as in step 3 returns the same values. If it fails with an error about being connected only to published data sources, step 2 has not been done yet.

## Step 5. Try it

The setup is usable now. Give the user `../docs/questions.md`: all 19 questions can be asked against these six data sources.

## Step 6. Tableau Knowledge (optional, Tableau+)

1. The user creates a knowledge graph in the web UI (a site holds up to 5 graphs): Manage Graphs → New knowledge graph → Published Data Sources → search `samplehyperstore` → select all 18 → create. It does not need to be the primary graph.
2. Find the graph id with `inspect-knowledge-context` (action `status`).
3. For each item in `metadata/business_preferences.json`, call `manage-knowledge-context` with `action: create`, `isGlobal: true`, the graph id, `name` = title, `statements` = [text]. Replace `{{RPT_PROJECT_PATH}}` with the rpt_ project path written as `A > B`. Show the user the 24 items before writing.
   If Tableau MCP cannot write them, the user can add each item in the web UI instead: open the graph → Actions → Add Business Preferences → Add Preference (Name = title, Scope = Global, Preference Rules = text). The appendix of `../docs/setup_manual.md` lists all 24.
4. Check with `inspect-knowledge-context` (action `list`, `isGlobal: true`): 24 items.
5. Knowledge reads field descriptions when a data source is published. Allow about 15 minutes after the last publish before relying on it.

Knowledge is English only. Business Preferences can only be global on this setup (attaching to a field node was refused).

## When you are done

Tell the user they can remove the saved sign-in with `python scripts/tableau_auth.py logout`. The session is cached outside the repository (`%LOCALAPPDATA%\samplehyperstore` on Windows, `~/.config/samplehyperstore` elsewhere).

## Known limits

- The rpt_ data sources show the raw layer's column descriptions on their columns (confirmed through the Metadata API, 2026-11). The rpt_ layer adds only calculated-field descriptions.
- The rpt_ data sources do not take the raw layer's default aggregations: their numeric columns default to SUM (confirmed with `get-datasource-metadata`, 2026-11). This does not affect agents that query through Tableau MCP: `query-datasource` aggregates only with the function named in the query, and a field without one returns row-level values.
- `get-datasource-metadata` in Tableau MCP takes descriptions from the Metadata API; when Metadata API requests are turned off (`DISABLE_METADATA_API_REQUESTS`) or the call fails, it returns the fields without descriptions, roles or data categories, and without an error. If the result has no `role` or `dataCategory` on any field, this has happened. This is MCP behaviour, not a problem with the data sources. Check descriptions with `scripts/check_metadata.py`.
- The address of a data source page (`.../datasources/<number>`) changes on every overwrite. Open data sources by searching for their name.
