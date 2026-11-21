# Set up SampleHyperStore by hand

This guide puts SampleHyperStore on Tableau Cloud without an AI agent or Tableau MCP. It follows the same steps as [`setup/SETUP_FOR_AI.md`](../setup/SETUP_FOR_AI.md), written for a person to follow in order.

You end up with the raw layer and the department layer. Tableau Knowledge is not covered here, because its setup uses Tableau MCP.

## What you need

- Tableau Cloud with the Creator role and permission to publish to a project
- Python 3.10 or later
- Access to the Tableau web editor (steps 3 and 4)

## Step 0. Prepare

Run every command below from the `en/setup/` folder.

1. Install the libraries.

   ```
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in `SERVER` and `SITE_NAME`. Neither is secret.
3. Check the sign-in. If you are not signed in, the first script run opens your browser. No token or password is written to a file.

   ```
   python scripts/tableau_auth.py status
   ```

4. Create the projects. `<parent project>` is the path of an existing project, such as a sandbox.

   ```
   python scripts/create_projects.py --parent "<parent project>"
   ```

   This creates the structure below and prints the paths of the two projects. If it fails for lack of permission, create the same projects in the web UI.

   ```
   <parent project>/
     <yyyymmdd>_SampleHyperStore/
       raw/     the 12 raw data sources
       marts/   the 6 department data sources
   ```

   Do not use a project that already holds other SampleHyperStore data sources. An AI agent would see both.

## Step 1. Publish the raw layer

First run with `--dry-run`, which only builds the .hyper files, and check that there are no errors. Then publish.

```
python scripts/publish_raw.py --project "<raw path>" --dry-run
python scripts/publish_raw.py --project "<raw path>"
```

Each of the 12 tables is published as `SampleHyperStore - <table>`, with column display names and descriptions. The script ends with `done`.

Check the descriptions with the command below. Right after publishing, the catalog can take a few minutes to catch up.

```
python scripts/check_metadata.py --project "<raw path>" --layer raw
```

## Step 2. Plan the web-editor work

Steps 3 and 4 are done by hand in the Tableau web editor, one data source at a time. Go through steps 3 and 4 with billing first, then do the other five.

## Step 3. Compose the department layer

`setup/metadata/rpt_layer.json` holds how to compose the six data sources and their calculated fields.

| Data source | Base table (root) | Relationships |
|---|---|---|
| rpt_samplehyperstore__billing | invoices | invoices →(Invoice Id) invoice_lines →(Product Id) products; invoice_lines →(Invoice Id and Product Id) credit_memos |
| rpt_samplehyperstore__sales_orders | products | products →(Product Id) order_lines →(Order Id) orders |
| rpt_samplehyperstore__merchandising | products | same as sales_orders |
| rpt_samplehyperstore__shipments | products | products →(Product Id) shipment_lines →(Shipment Id) shipments |
| rpt_samplehyperstore__returns_refunds | returns | returns →(Product Id) products; returns →(Return Id) refunds |
| rpt_samplehyperstore__web_analytics | web_sessions | web_sessions →(Session Id) web_searches |

For each data source:

1. New → Published Data Source → "On this site" → connect to the root's raw data source (`SampleHyperStore - <root>`). Open the Data Source tab.
2. Add the other tables with "Add published data source", in the order of `parent_tables` in the JSON, skipping the root. When column names collide, one copy gets ` (<table>.csv)` appended. The order decides which one, and some formulas use that name.
3. Draw each relationship from the "+" at the right edge of a table already in the tree to the new table. Drawing the other way makes a second base table. Then the totals repeat when you split by the other tables' fields.
4. Pick the key fields from the table above. No dashed line or "!" may remain.
5. Create each calculated field in `calculated_fields`, copying the name and formula exactly: data pane menu (▾) → Create Calculated Field. Check that it says "The calculation is valid."
6. Publish as `rpt_samplehyperstore__<department>`. In the dialog, choose the marts project: it defaults to the raw one. Leave "Embed credentials" off.

After publishing, check that the calculated fields are there:

```
python scripts/check_metadata.py --project "<marts path>" --layer rpt
```

Then build these totals on a worksheet and compare:

| Data source | Field | Expected |
|---|---|---:|
| sales_orders | Units | 111,008 |
| merchandising | Units / Order Lines | 115,435 / 71,007 |
| shipments | Units | 110,762 |
| returns_refunds | Requested Units / Received Units / Refunds | 7,944 / 6,704 / 907,537.58 |
| web_analytics | Sessions / Transactions / Units Added to Cart | 455,057 / 24,484 / 191,594 |
| billing | Gross Revenue | 13,347,403.19 |

Last, split Units by product category. If every category shows the same value, the data source has two base tables: redo step 3.3.

## Step 4. Describe the calculated fields

The web editor cannot write field descriptions. Add them in two steps:

1. Write the descriptions with the script. The composition drops for a moment.

   ```
   python scripts/describe_rpt.py --project "<marts path>" --datasources billing
   ```

2. Open the data source again from its page, then Edit → Publish → same name and project → Overwrite, without changes. This restores the composition and keeps the descriptions. Do not use an editor tab opened before step 1: it holds the old version.

Check with `check_metadata.py --layer rpt` that the descriptions are there, and that the totals from step 3 still match.

## Step 5. Try it

The setup is ready. Ask an AI agent the questions in [`questions.md`](questions.md).

## Notes

- Column descriptions on the raw layer are not inherited by the department layer. The department layer carries only the calculated-field descriptions.
- A data source page's URL changes on every overwrite. Open data sources by searching for their name.
