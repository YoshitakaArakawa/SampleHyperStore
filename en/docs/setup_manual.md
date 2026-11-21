# Set up SampleHyperStore by hand

This guide puts SampleHyperStore on Tableau Cloud without an AI agent or Tableau MCP. It follows the same steps as [`setup/SETUP_FOR_AI.md`](../setup/SETUP_FOR_AI.md), written for a person to follow in order.

You end up with two layers:

| Layer | Tableau project | Data source names | Name in the scripts |
|---|---|---|---|
| Raw layer | raw | `SampleHyperStore - <table>` (12) | `--layer raw` |
| Department layer | marts | `rpt_samplehyperstore__<department>` (6) | `--layer rpt` |

Tableau Knowledge is not covered here, because its setup uses Tableau MCP.

## What you need

- Tableau Cloud with the Creator role and permission to publish to a project
- Python 3.10 or later
- Access to the Tableau web editor (steps 2 and 3)

## Step 0. Prepare

1. Get this repository (`git clone`, or download the ZIP from GitHub).
2. From the repository root, move to `en/setup/`. Run every command below from this folder.

   ```
   cd en/setup
   ```

   For the Japanese edition, add `--data ../../ja` to each command; see `ja/docs/setup_manual.md`.

3. Install the libraries. Creating a virtual environment first (`python -m venv .venv`) keeps them apart from your other projects.

   ```
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and fill in these two values. Neither is secret.
   - `SERVER`: the host part of your site's URL, for example `https://<pod>.online.tableau.com`
   - `SITE_NAME`: the name in `#/site/<here>/` of your site's URL
5. Check the sign-in. If you are not signed in, the first script run opens your browser. You sign in with OAuth; you do not write any token or password into a file.

   ```
   python scripts/tableau_auth.py status
   ```

6. Create the projects. `<parent project>` is the path of an existing project, such as a sandbox. Write it from the top level, with `/` between levels (for example `Sandbox/Team A`).

   ```
   python scripts/create_projects.py --parent "<parent project>"
   ```

   This creates the structure below. `<yyyymmdd>` is the date you run it. Note the raw and marts paths printed at the end, and paste them wherever `<raw path>` and `<marts path>` appear below.

   ```
   <parent project>/
     <yyyymmdd>_SampleHyperStore/
       raw/     the 12 raw data sources
       marts/   the 6 department data sources
   ```

   If it fails for lack of permission, create the same projects in the web UI. The paths are then `<parent project>/<yyyymmdd>_SampleHyperStore/raw` and `.../marts`.

   Do not use a project that already holds other SampleHyperStore data sources. When you later use an AI agent, it would see both.

## Step 1. Publish the raw layer

Run with `--dry-run` first. It only builds the .hyper files; it does not sign in or publish. If there are no errors, run it again without `--dry-run`.

```
python scripts/publish_raw.py --project "<raw path>" --dry-run
python scripts/publish_raw.py --project "<raw path>"
```

Each of the 12 tables is published as `SampleHyperStore - <table>`, with column display names and descriptions. The script ends with `done`. If it prints `check these tables: [...]` instead, look at those tables.

Check the descriptions:

```
python scripts/check_metadata.py --project "<raw path>" --layer raw
```

It passes when every data source shows `described n/n` and the last line is `all present`. Right after publishing, the catalog can take a few minutes to catch up. If you see `[missing]`, wait a few minutes and run it again.

## Step 2. Compose the department layer

Build the six department data sources one at a time in the Tableau web editor. Go through steps 2 and 3 with billing first, then do the other five.

`setup/metadata/rpt_layer.json` holds how to compose them and their calculated fields.

| Data source | Root table | Relationships (→ points to the table you add; the key is in brackets) |
|---|---|---|
| rpt_samplehyperstore__billing | invoices | invoices →(Invoice Id) invoice_lines →(Product Id) products; invoice_lines →(Invoice Id and Product Id) credit_memos |
| rpt_samplehyperstore__sales_orders | products | products →(Product Id) order_lines →(Order Id) orders |
| rpt_samplehyperstore__merchandising | products | same as sales_orders |
| rpt_samplehyperstore__shipments | products | products →(Product Id) shipment_lines →(Shipment Id) shipments |
| rpt_samplehyperstore__returns_refunds | returns | returns →(Product Id) products; returns →(Return Id) refunds |
| rpt_samplehyperstore__web_analytics | web_sessions | web_sessions →(Session Id) web_searches |

The root table is where the relationship tree starts. Each data source must have exactly one.

For each data source:

1. In Tableau Cloud, choose New → Published Data Source. In the connection list choose "On this site", and connect to the root's raw data source (`SampleHyperStore - <root>`). Open the Data Source tab.
2. Add the other tables one at a time, in the order of `parent_tables` in the JSON, skipping the root. Use "Add published data source".
3. Right after adding each table, draw its relationship. Always draw from the "+" at the right edge of a table already in the tree to the new table. Drawing the other way makes a second root, and totals then repeat when you split by the other tables' fields.
4. Pick the key fields from the table above. No dashed line or "!" may remain.
5. When column names collide, the table added later gets ` (<table>.csv)` appended. The order decides which one. In sales_orders, check that the data pane has `Order Id (order_lines.csv)`: the calculated field "Fulfillable Orders" uses that name.
6. Create each calculated field in `calculated_fields`, copying the name and formula exactly: data pane menu (▾) → Create Calculated Field. Check that it says "The calculation is valid."
7. Publish as `rpt_samplehyperstore__<department>`. In the dialog, change the project to marts: it defaults to raw. Leave "Embed credentials" off.

After publishing, check the calculated fields:

```
python scripts/check_metadata.py --project "<marts path>" --layer rpt
```

It passes when the data source you built shows `formula match n/n`. Data sources you have not built yet show `[missing]`; that is expected along the way. Once all six are built, the last line is `all present`.

Then check the totals. Open a new workbook from the data source's page, put the field below on the sheet, and read the total:

| Data source | Field | Expected |
|---|---|---:|
| billing | Gross Revenue | 13,347,403.19 |
| sales_orders | Units | 111,008 |
| merchandising | Units / Order Lines | 115,435 / 71,007 |
| shipments | Units | 110,762 |
| returns_refunds | Requested Units / Received Units / Refunds | 7,944 / 6,704 / 907,537.58 |
| web_analytics | Sessions / Transactions / Units Added to Cart | 455,057 / 24,484 / 191,594 |

sales_orders and merchandising are composed the same way, but their Units differ: sales_orders excludes cancelled units, merchandising includes them.

Last, in the five data sources that include products (all except web_analytics), split by product category: Gross Revenue for billing, Units for the others. If every category shows the same value, the data source has two roots: redo this step from item 3.

## Step 3. Describe the calculated fields

The web editor cannot write field descriptions. Add them in two steps:

1. Write the descriptions with the script. Pass the data source names without `rpt_samplehyperstore__`, separated by spaces (for example `billing`, or `sales_orders shipments`). Leave `--datasources` out to do all six. The relationships drop for a moment.

   ```
   python scripts/describe_rpt.py --project "<marts path>" --datasources billing
   ```

2. Open the data source again from its page, then Edit → Publish → same name and project → Overwrite, without changes. This restores the relationships and keeps the descriptions. If Publish does nothing on the first click, click again.

   Do not use an editor tab that was open before you ran the script in item 1: it would publish the old version.

Check that the descriptions are there: the data source shows `described n/n`. Then check that the totals from step 2 still match.

```
python scripts/check_metadata.py --project "<marts path>" --layer rpt
```

If an error says the data source is connected only to published data sources, item 2 has not been done yet.

## Step 4. Try it

The setup is complete, without any AI so far.

- To check in Tableau only: the totals table in step 2 is the check.
- To try it with an AI agent: ask an AI agent connected through Tableau MCP the questions in [`questions.md`](questions.md). See your agent's documentation for connecting Tableau MCP.

When you are done, remove the saved sign-in. It is stored outside the repository (`%LOCALAPPDATA%\samplehyperstore` on Windows, `~/.config/samplehyperstore` elsewhere).

```
python scripts/tableau_auth.py logout
```

## If something goes wrong

- `check these tables: [...]` instead of `done`: run again with `--tables` for those tables (for example `--tables orders`). If a data source for that table already exists in raw, delete it in the web UI first.
- `[missing]` from `check_metadata.py`: right after publishing, wait a few minutes and run it again. Also check that the last level of the project path (raw or marts) is right.
- Totals do not match: review items 3 (direction of the line) and 5 (column names with ` (<table>.csv)`) of step 2.

## Notes

- Column descriptions on the raw layer are not inherited by the department layer. The department layer carries only the calculated-field descriptions.
- A data source page's URL changes on every overwrite. Open data sources by searching for their name.
