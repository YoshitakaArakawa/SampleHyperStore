# Set up SampleHyperStore by hand

This guide puts SampleHyperStore on Tableau Cloud without an AI agent or Tableau MCP. It follows the same steps as [`setup/SETUP_FOR_AI.md`](../setup/SETUP_FOR_AI.md), written for a person to follow in order.

## Overview

| Step | What you do | Who acts | What you get |
|---|---|---|---|
| 0 | Prepare | Script, you | The raw and marts projects |
| 1 | Publish the raw layer | Script | 12 data sources `SampleHyperStore - <table>` |
| 2 | Compose the department layer | You (web editor) | 6 data sources `rpt_samplehyperstore__<department>` |
| 3 | Describe the calculated fields | Script, you | Descriptions on the department layer's calculated fields |
| 4 | Set up Tableau Knowledge (optional) | You (web UI) | A knowledge graph and 24 Business Preferences |
| 5 | Try it | You | — |

Go through steps 2 and 3 with billing first, then do the other five.

## What you need

- Tableau Cloud with the Creator role and permission to publish to a project
- Python 3.10 or later
- Access to the Tableau web editor (steps 2 to 4)
- Tableau+ (step 4 only)

## Terms and values to replace

| Written as | Meaning |
|---|---|
| Raw layer | The 12 data sources in the raw project. `--layer raw` in the scripts |
| Department layer | The 6 data sources in the marts project. `--layer rpt` in the scripts |
| `<parent project>` | Where the projects go: the path of an existing project, from the top level, with `/` between levels (for example `Sandbox/Team A`) |
| `<raw path>`, `<marts path>` | The two paths printed at the end of step 0. Paste them as they are |

For the Japanese edition, add `--data ../../ja` to every script; see `ja/docs/setup_manual.md`.

---

## Step 0. Prepare

### What to do

1. Get this repository (`git clone`, or download the ZIP from GitHub).
2. From the repository root, move to `en/setup/`. Run every command below from this folder.

   ```
   cd en/setup
   ```

3. Install the libraries. Creating a virtual environment first (`python -m venv .venv`) keeps them apart from your other projects.

   ```
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and fill in these two values. Neither is secret.
   - `SERVER`: the host part of your site's URL, for example `https://<pod>.online.tableau.com`
   - `SITE_NAME`: the name in `#/site/<here>/` of your site's URL
5. Create the projects. The first script run opens your browser; sign in to Tableau Cloud there. You sign in with OAuth and do not write any token or password into a file.

   ```
   python scripts/create_projects.py --parent "<parent project>"
   ```

   This creates the structure below. `<yyyymmdd>` is the date you run it.

   ```
   <parent project>/
     <yyyymmdd>_SampleHyperStore/
       raw/     the 12 raw data sources
       marts/   the 6 department data sources
   ```

### How to check

- The raw and marts paths are printed at the end. Note them.
- If it fails for lack of permission, create the same projects in the web UI. The paths are then `<parent project>/<yyyymmdd>_SampleHyperStore/raw` and `.../marts`.
- Do not use a project that already holds other SampleHyperStore data sources. When you later use an AI agent, it would see both.

---

## Step 1. Publish the raw layer

### What to do

Run with `--dry-run` first. It only builds the .hyper files; it does not sign in or publish. If there are no errors, run it again without `--dry-run`.

```
python scripts/publish_raw.py --project "<raw path>" --dry-run
python scripts/publish_raw.py --project "<raw path>"
```

Each of the 12 tables is published with column display names and descriptions.

### How to check

- `publish_raw.py` ends with `done`.
- Check the descriptions with the command below. It passes when every data source shows `described n/n` and the last line is `all present`.

  ```
  python scripts/check_metadata.py --project "<raw path>" --layer raw
  ```

---

## Step 2. Compose the department layer

Build the six department data sources one at a time in the Tableau web editor. `setup/metadata/rpt_layer.json` holds how to compose them and their calculated fields.

| Data source | Root table | Relationships (→ points to the table you add; the key is in brackets) |
|---|---|---|
| rpt_samplehyperstore__billing | invoices | invoices →(Invoice Id) invoice_lines →(Product Id) products; invoice_lines →(Invoice Id and Product Id) credit_memos |
| rpt_samplehyperstore__sales_orders | products | products →(Product Id) order_lines →(Order Id) orders |
| rpt_samplehyperstore__merchandising | products | same as sales_orders |
| rpt_samplehyperstore__shipments | products | products →(Product Id) shipment_lines →(Shipment Id) shipments |
| rpt_samplehyperstore__returns_refunds | returns | returns →(Product Id) products; returns →(Return Id) refunds |
| rpt_samplehyperstore__web_analytics | web_sessions | web_sessions →(Session Id) web_searches |

The root table is where the relationship tree starts. Each data source must have exactly one.

### 2-1. Compose

1. **Connect to the root**: New → Published Data Source → "On this site", connect to the root's raw data source (`SampleHyperStore - <root>`), and open the Data Source tab.
2. **Add tables and draw relationships**: Add the other tables one at a time with "Add published data source", in the order of `parent_tables` in the JSON, skipping the root. Draw each relationship right after adding the table.
   - Always draw from the "+" at the right edge of a table already in the tree to the new table. Drawing the other way makes a second root.
   - Pick the keys from the table above. No dashed line or "!" may remain.
3. **Check column names**: When column names collide, the table added later gets ` (<table>.csv)` appended. In sales_orders, check that the data pane has `Order Id (order_lines.csv)`: the calculated field "Fulfillable Orders" uses that name.
4. **Create the calculated fields**: Copy each name and formula in `calculated_fields` exactly, through the data pane menu (▾) → Create Calculated Field. Check that it says "The calculation is valid."
5. **Publish**: Name it `rpt_samplehyperstore__<department>`. In the dialog, change the project to marts (it defaults to raw). Leave "Embed credentials" off.

### 2-2. Check

1. **Calculated fields**: The command below passes when the data source you built shows `formula match n/n`. Data sources you have not built yet show `[missing]`; that is expected along the way.

   ```
   python scripts/check_metadata.py --project "<marts path>" --layer rpt
   ```

2. **Totals**: Open a new workbook from the data source's page and read these totals.

   | Data source | Field | Expected |
   |---|---|---:|
   | billing | Gross Revenue | 13,347,403.19 |
   | sales_orders | Units | 111,008 |
   | merchandising | Units / Order Lines | 115,435 / 71,007 |
   | shipments | Units | 110,762 |
   | returns_refunds | Requested Units / Received Units / Refunds | 7,944 / 6,704 / 907,537.58 |
   | web_analytics | Sessions / Transactions / Units Added to Cart | 455,057 / 24,484 / 191,594 |

   sales_orders and merchandising are composed the same way, but their Units differ: sales_orders excludes cancelled units, merchandising includes them.

3. **One root**: In the five data sources that include products (all except web_analytics), split by product category: Gross Revenue for billing, Units for the others. If every category shows the same value, the data source has two roots: redo 2-1 from item 2.

---

## Step 3. Describe the calculated fields

The web editor cannot write field descriptions. Add them in two steps.

### What to do

1. Write the descriptions with the script. Pass the data source names without `rpt_samplehyperstore__`, separated by spaces (for example `billing`, or `sales_orders shipments`). Leave `--datasources` out to do all six. The relationships drop for a moment.

   ```
   python scripts/describe_rpt.py --project "<marts path>" --datasources billing
   ```

2. Open the data source again from its page, then Edit → Publish → same name and project → Overwrite, without changes. This restores the relationships and keeps the descriptions.
   - Do not use an editor tab that was open before you ran the script in item 1: it would publish the old version.
   - If Publish does nothing on the first click, click again.

### How to check

- The command below passes when the data source shows `described n/n`.

  ```
  python scripts/check_metadata.py --project "<marts path>" --layer rpt
  ```

- The totals from 2-2 still match.

---

## Step 4. Set up Tableau Knowledge (optional)

Tableau Knowledge tells AI agents what to use when. It requires Tableau+.

### What to do

1. In Tableau Cloud, open "Tableau Knowledge" from the left menu and choose "Manage Graphs".
2. Create a graph with "New knowledge graph". Select all 18 data sources of the raw and department layers (search for `samplehyperstore`).
3. Open the graph, then choose "Actions" (top right) → "Add Business Preferences" → "Add Preference".
4. Enter the 24 items in the [appendix](#appendix-business-preferences) one at a time, and click "Save" for each:
   - Name: the "Name" column
   - Scope: leave it as "Global (all entities)"
   - Preference Rules: the "Text" column (the limit is 1,000 characters; every text fits)
   - In the first text, replace `{{RPT_PROJECT_PATH}}` with the path of the department layer's project, with " > " between levels (for example `Sandbox > 20261121_SampleHyperStore > marts`).

### How to check

- The graph has 24 Business Preferences.
- Wait about 15 minutes after your last publish before you rely on it. Knowledge reads field descriptions when a data source is published.

---

## Step 5. Try it

The setup is complete, without any AI so far.

- To check in Tableau only: the totals table in 2-2 is the check.
- To try it with an AI agent: ask an AI agent connected through Tableau MCP the questions in [`questions.md`](questions.md). See your agent's documentation for connecting Tableau MCP.

When you are done, remove the saved sign-in. It is stored outside the repository (`%LOCALAPPDATA%\samplehyperstore` on Windows, `~/.config/samplehyperstore` elsewhere).

```
python scripts/tableau_auth.py logout
```

---

## If something goes wrong

| Symptom | What to do |
|---|---|
| `publish_raw.py` ends with `check these tables: [...]` instead of `done` | Run again with `--tables` for those tables (for example `--tables orders`). If a data source for that table already exists in raw, delete it in the web UI first. |
| `check_metadata.py` shows `[missing]` | Right after publishing, wait a few minutes and run it again. Also check that the last level of the project path (raw or marts) is right. |
| Totals do not match | Review 2-1 items 2 (direction of the line) and 3 (column names with ` (<table>.csv)`). |
| Step 3 fails with an error saying the data source is connected only to published data sources | Item 2 of step 3 (the overwrite) has not been done yet. |

## Notes

- **Descriptions on the department layer**: The department layer's columns show the raw layer's column descriptions as they are (confirmed through the Metadata API). The only descriptions you add on the department layer are those of the calculated fields.
- **Default aggregation on the department layer**: The department layer's columns do not take the raw layer's default aggregations; numeric columns default to SUM there. Agents that query through Tableau MCP are not affected, because each query names its own aggregation.
- **When Tableau MCP shows no descriptions**: Tableau MCP's `get-datasource-metadata` may return no descriptions. MCP takes them from the Metadata API; when Metadata API requests are turned off (`DISABLE_METADATA_API_REQUESTS`) or the call fails, it returns the fields without descriptions and without an error. This is not a problem with your data sources. Use `check_metadata.py` to check the descriptions.
- **Data source page URLs**: They change on every overwrite. Open data sources by searching for their name.

---

## Appendix: Business Preferences

The 24 items for step 4. They match `setup/metadata/business_preferences.json`.

| # | Name | Text |
|---|---|---|
| 1 | Usage: Which data sources to use | Use the `rpt_samplehyperstore__` data sources in {{RPT_PROJECT_PATH}} for analysis; the `SampleHyperStore - <table>` data sources are raw tables for lineage only. |
| 2 | Usage: Say which metric and data source you used | Several data sources have metrics with the same name; always say which metric you used and which data source it came from. |
| 3 | Usage: Terms departments use for different metrics | Departments sometimes call different metrics by the same or a similar term. Do not pick a calculated field only because its name matches. When the question and the Business Preferences do not settle on one metric, show the user the candidate metrics and what each one is for, and let them choose. |
| 4 | Term: Default meaning of sales and revenue | "Sales" or "revenue" without a qualifier means `Revenue` in `rpt_samplehyperstore__sales_orders`; use `Revenue` in `rpt_samplehyperstore__billing` when the question mentions fiscal periods, net revenue, returns or marketplace fees. |
| 5 | Term: Fiscal periods for Finance questions | For Finance questions, "this year", "last year" and "monthly" mean fiscal periods: group by `Fiscal Month`. |
| 6 | Term: Late delivery means after the promised date | A delivery is late when `Delivered Date` is after `Promised Delivery Date`; use `Carrier Estimated Delivery Date` only for carrier performance. |
| 7 | Term: No results vs nothing in stock in search | In search questions, "no results" means `No-results Rate` (no matching product) and "nothing in stock" means `Out-of-stock Results Rate`. |
| 8 | Term: Relative dates mean relative to the end of the data | This sample's data covers 2023-01-01 to 2025-12-31 (fiscal months FY2022-P12 to FY2025-P11) and does not grow; read "this year", "last month" and "recent" relative to 2025-12-31, not today's date. Statuses such as `Delivery Status` and `Return Status` are as of 2025-12-31. |
| 9 | Method: Sales region realignment on 2025-01-01 | To compare sales regions across years spanning 2025-01-01, use `Sales Region (Current Map)` in `rpt_samplehyperstore__billing`: it places every date on the territory map in effect from 2025-01-01. To judge results on the region in effect at posting, as against targets, use `Sales Region Id`. |
| 10 | Default date: rpt_samplehyperstore__billing | In `rpt_samplehyperstore__billing`, trend metrics by `Invoice Date` (or `Fiscal Month`); exceptions: `Credits` and `Net Refund Cost` by `Credit Memo Date` (or `Fiscal Month (credit_memos.csv)`), and in Finance's posting view, all credit memo amounts by `Fiscal Month (credit_memos.csv)`, not by the original invoice's month. |
| 11 | Default date: rpt_samplehyperstore__sales_orders | In `rpt_samplehyperstore__sales_orders`, trend all metrics by `Order Date`, in calendar months. |
| 12 | Default date: rpt_samplehyperstore__merchandising | In `rpt_samplehyperstore__merchandising`, trend all metrics by `Order Date`, in calendar months. |
| 13 | Default date: rpt_samplehyperstore__shipments | In `rpt_samplehyperstore__shipments`, trend metrics by `Shipped Date` in calendar months; exception: `Perfect Order Rate` by `Order Date`. |
| 14 | Default date: rpt_samplehyperstore__returns_refunds | In `rpt_samplehyperstore__returns_refunds`, trend metrics by `Requested Date` in calendar months; exceptions: `Refunds` and `Cash Refunds` by `Refunded Date`, `Received Units` by `Received Date`, `Days from Order to Return Request` and `Returned Order Lines` by `Order Date` (order cohort). |
| 15 | Default date: rpt_samplehyperstore__web_analytics | In `rpt_samplehyperstore__web_analytics`, trend metrics by `Session Start Date` in calendar months; exceptions: `No-results Rate`, `Out-of-stock Results Rate` and `No-click Rate` by `Searched Date`, `Units Added to Cart` by `Cart Added Date`. |
| 16 | Which to use: Return rate | "Return rate" refers to four metrics, one per department: for the volume of returns customers request, the requested return rate (Customer Support); for how likely each product is to be returned, the order-cohort return rate (Merchandising); for the volume that comes back to the warehouse, the received return rate (Logistics); for month-end close figures, `Return Rate` in `rpt_samplehyperstore__billing` (Finance). |
| 17 | Cross-source metric: Requested return rate | Requested return rate (Customer Support) = `Requested Units` in `rpt_samplehyperstore__returns_refunds` by month of `Requested Date` ÷ `Units` in `rpt_samplehyperstore__sales_orders` by month of `Order Date`. |
| 18 | Cross-source metric: Order-cohort return rate | Order-cohort return rate (Merchandising) = `Requested Units` in `rpt_samplehyperstore__returns_refunds` ÷ `Net Ordered Units` in `rpt_samplehyperstore__merchandising`, both by month of `Order Date`, with the same filters on both. |
| 19 | Cross-source metric: Received return rate | Received return rate (Logistics) = `Received Units` in `rpt_samplehyperstore__returns_refunds` by month of `Received Date` ÷ `Units` in `rpt_samplehyperstore__shipments` by month of `Shipped Date`. |
| 20 | Cross-source metric: Return line incidence | Return line incidence (Merchandising) = `Returned Order Lines` in `rpt_samplehyperstore__returns_refunds` ÷ `Order Lines` in `rpt_samplehyperstore__merchandising`, by product and month of `Order Date`. |
| 21 | Cross-source metric: Net shipping cost | Net shipping cost (Finance) = `Freight Cost` in `rpt_samplehyperstore__shipments` by month of `Shipped Date` − `Shipping Billed` in `rpt_samplehyperstore__billing` by month of `Invoice Date`. |
| 22 | Cross-source metric: Orders per session | Orders per session (Sales) = `Orders` in `rpt_samplehyperstore__sales_orders` for the web and app channels by `Order Date` ÷ `Sessions` in `rpt_samplehyperstore__web_analytics` by `Session Start Date`. |
| 23 | Cross-source metric: Unit cart abandonment | Unit cart abandonment (Merchandising) = 1 − `Units` in `rpt_samplehyperstore__merchandising` for web and app orders ÷ `Units Added to Cart` in `rpt_samplehyperstore__web_analytics`, both by week (`Order Date` and `Cart Added Date`). |
| 24 | Cross-source metric: Marketplace fee rate on booked sales | Marketplace fee rate on booked sales (Sales) = `Marketplace Fees` in `rpt_samplehyperstore__billing` by month of `Invoice Date` ÷ `Revenue` in `rpt_samplehyperstore__sales_orders` for the marketplace channel by month of `Order Date`. |
