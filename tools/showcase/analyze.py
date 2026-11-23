"""Compute the numbers the analysis showcase prints (numbers.json, key "S") from en/csv and the metadata JSON (local, no Tableau API).

Everything the page prints about a case comes from S[case]; S holds only the fields page.template.html reads.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

C = Path(__file__).resolve().parents[2] / "en" / "csv" / "in_use"


def rd(n, **k):
    return pd.read_csv(C / f"{n}.csv", **k)


def r4(x):
    return None if x is None or pd.isna(x) else round(float(x), 4)


def rl(s):
    return [round(float(v)) for v in s]


mo = lambda s: s.dt.to_period("M").astype(str)
orders = rd("orders", parse_dates=["order_date"])
prod = rd("products")
inv = rd("invoices", parse_dates=["invoice_date"])
il = rd("invoice_lines")
cm = rd("credit_memos")
ws = rd("web_sessions", usecols=["session_id", "session_start_date", "product_views", "order_id", "oos_product_views"], parse_dates=["session_start_date"])

il["rev"] = il.qty_invoiced * il.unit_price - il.discount_amount
il = il.merge(inv[["invoice_id", "invoice_date", "fiscal_month", "sales_region_id", "state_code"]], on="invoice_id")
il["year"] = il.invoice_date.dt.year

S = {}

# sales revenue as in rpt sales_orders: net of cancellations, line discounts and the order coupon (by order date)
olb = rd("order_lines").merge(orders[["order_id", "order_date", "channel", "order_discount_amount"]], on="order_id")
gross = olb.qty_ordered * olb.unit_price - olb.line_discount_amount
olb["disc_alloc"] = (olb.order_discount_amount * gross / gross.groupby(olb.order_id).transform("sum").replace(0, np.nan)).fillna(0)
olb["net_price"] = olb.unit_price - olb.line_discount_amount / olb.qty_ordered
olb["booked"] = (olb.qty_ordered - olb.qty_cancelled) * olb.net_price - olb.disc_alloc
olb["m"] = mo(olb.order_date)
sales_m = olb.groupby("m").booked.sum()

# ---- stockout (April 2025): dashboard -> sales by channel -> web/app sessions vs orders -> out-of-stock views -> search by subcategory -> their sales
fm_ = ws.assign(m=mo(ws.session_start_date), ordered=ws.order_id.notna()).groupby("m").agg(
    views=("product_views", "sum"), oos=("oos_product_views", "sum"), sessions=("session_id", "count"), ordered=("ordered", "sum"))
om = orders.assign(m=mo(orders.order_date))
first = orders.sort_values("order_at").dropna(subset=["customer_id"]).drop_duplicates("customer_id")
dash = pd.DataFrame({"sales": sales_m, "sessions": fm_.sessions, "conversion": fm_.ordered / fm_.sessions,
                     "orders": om.groupby("m").size(), "new_customers": first.groupby(mo(first.order_date)).size()})
dash["aov"] = dash.sales / dash.orders
cur_m = [str(p) for p in pd.period_range("2024-05", "2025-04", freq="M")]
ly_m = [str(p) for p in pd.period_range("2023-05", "2024-04", freq="M")]
fmt = lambda c, ms: [r4(v) for v in dash.loc[ms, c]] if c == "conversion" else rl(dash.loc[ms, c])
A, L = "2025-04", "2024-04"
chs = ["web", "app", "marketplace", "b2b"]
oc = om.groupby(["m", "channel"]).size()
sc = olb.groupby(["m", "channel"]).booked.sum()
mm = [m for m in fm_.index if "2023-01" <= m <= "2025-12"]
oos = fm_.oos / fm_.views
w23 = fm_.loc["2023-01":"2023-12"]
S["stockout"] = {
    "asof": A,
    "dash": {c: {"cur": fmt(c, cur_m), "ly": fmt(c, ly_m)} for c in ["sales", "sessions", "conversion", "orders", "new_customers", "aov"]},
    "by_channel": {"channels": chs, "orders_cur": [int(oc.get((A, c), 0)) for c in chs], "orders_ly": [int(oc.get((L, c), 0)) for c in chs],
                   "sales_cur": [round(sc.get((A, c), 0)) for c in chs], "sales_ly": [round(sc.get((L, c), 0)) for c in chs]},
    "oos_monthly": {"months": mm, "rate": [r4(oos[m]) for m in mm]},
    "oos_2023": r4(w23.oos.sum() / w23.views.sum()), "oos_apr25": r4(oos[A]),
}
# out-of-stock share of search results by subcategory (query -> the subcategory most clicked for it over all time),
# and web/app sales by subcategory; subcategories with 20%+ out-of-stock results in the as-of month vs the rest
ws_ = rd("web_searches", usecols=["searched_date", "query_text", "results_count", "results_in_stock_count", "clicked_product_id"],
         parse_dates=["searched_date"])
qsub = (ws_.merge(prod[["product_id", "subcategory"]], left_on="clicked_product_id", right_on="product_id")
        .groupby("query_text").subcategory.agg(lambda x: x.value_counts().index[0]))
ws_ = ws_.assign(m=mo(ws_.searched_date), sub=ws_.query_text.map(qsub))
sq = ws_[ws_.m.isin([A, L]) & (ws_.results_count > 0)].groupby(["sub", "m"]).agg(rc=("results_count", "sum"), ris=("results_in_stock_count", "sum"))
oos_s = (1 - sq.ris / sq.rc).unstack("m")
wa = olb[olb.m.isin([A, L]) & olb.channel.isin(["web", "app"])].merge(prod[["product_id", "subcategory"]], on="product_id")
wsales = wa.pivot_table(index="subcategory", columns="m", values="booked", aggfunc="sum")
gv = lambda df, sb, c: df.loc[sb, c] if sb in df.index and c in df.columns and pd.notna(df.loc[sb, c]) else None
subs_ = sorted(set(wsales.index) | set(oos_s.index))
subs_.sort(key=lambda sb: -(gv(oos_s, sb, A) if gv(oos_s, sb, A) is not None else -1))
S["stockout"]["search"] = {"subs": subs_, "oos25": [r4(gv(oos_s, sb, A)) for sb in subs_], "oos24": [r4(gv(oos_s, sb, L)) for sb in subs_]}
wv = lambda c: [round(float(gv(wsales, sb, c) or 0)) for sb in subs_]
S["stockout"]["webapp"] = {"subs": subs_, "sales24": wv(L), "sales25": wv(A)}
heavy_w = [sb for sb in subs_ if (gv(oos_s, sb, A) or 0) >= 0.2]
rest_w = [sb for sb in subs_ if sb not in heavy_w]
wt = lambda c, ks: round(float(wsales[c].reindex(ks).fillna(0).sum()))
# search out-of-stock share of the other subcategories, pooled (results shown out of stock / all results)
pool = lambda c: r4(1 - sq.ris.unstack("m")[c].reindex(rest_w).sum() / sq.rc.unstack("m")[c].reindex(rest_w).sum())
S["stockout"]["groups_web"] = {"heavy": heavy_w, "n_rest": len(rest_w), "heavy_ly": wt(L, heavy_w), "heavy_cur": wt(A, heavy_w),
                               "rest_ly": wt(L, rest_w), "rest_cur": wt(A, rest_w), "total_ly": wt(L, subs_), "rest_oos25": pool(A), "rest_oos24": pool(L)}

# ---- sales (Nov 2025): Sales revenue by order date vs Billing Revenue by fiscal month (credits and fee reversals go to the original invoice's month)
FMO = "FY2025-P10"
cmo = cm.assign(ofm=cm.invoice_id.map(inv.set_index("invoice_id").fiscal_month))
bill = {"gross": il.loc[il.fiscal_month == FMO, "rev"].sum(), "credits": cmo.loc[cmo.ofm == FMO, "merchandise_credit_amount"].sum(),
        "fees": inv.loc[inv.fiscal_month == FMO, "marketplace_fee_amount"].sum(), "reversals": cmo.loc[cmo.ofm == FMO, "marketplace_fee_reversal_amount"].sum()}
bill["revenue"] = bill["gross"] - bill["credits"] - bill["fees"] + bill["reversals"]
om12 = [str(p) for p in pd.period_range("2024-12", "2025-11", freq="M")]
fm12 = ["FY2024-P11", "FY2024-P12"] + [f"FY2025-P{i:02d}" for i in range(1, 11)]
bv = (il.groupby("fiscal_month").rev.sum().reindex(fm12, fill_value=0) - cmo.groupby("ofm").merchandise_credit_amount.sum().reindex(fm12, fill_value=0)
      - inv.groupby("fiscal_month").marketplace_fee_amount.sum().reindex(fm12, fill_value=0)
      + cmo.groupby("ofm").marketplace_fee_reversal_amount.sum().reindex(fm12, fill_value=0))
S["sales"] = {"sales_orders": round(sales_m["2025-11"]), "billing": {k: round(bill[k]) for k in ["credits", "fees", "revenue"]},
              "order_monthly": {"months": om12, "revenue": rl(sales_m.reindex(om12).fillna(0))}, "billing_fm": {"months": om12, "revenue": rl(bv)}}

# ---- west (2025): the R-WEST region as stamped at posting vs the West on the current map (the states R-WEST holds in 2025), both years
west_old = ["WA", "OR", "CA", "AK", "HI", "ID", "MT", "WY", "UT", "CO", "NV"]
rw = il[il.sales_region_id == "R-WEST"]
rby = rw.groupby("year").rev.sum().round()
rws = set(inv[(inv.invoice_date.dt.year == 2025) & (inv.sales_region_id == "R-WEST")].state_code)
cw = il[il.state_code.isin(rws)]
cby = cw.groupby("year").rev.sum().round()
m12 = [f"{i:02d}" for i in range(1, 13)]
rwm, cwm = (g.groupby(["year", g.invoice_date.dt.strftime("%m")]).rev.sum() for g in (rw, cw))
pick = lambda s, y: rl(s.get(y, pd.Series(dtype=float)).reindex(m12, fill_value=0))
S["west"] = {"region_yoy": r4(rby[2025] / rby[2024] - 1), "current_yoy": r4(cby[2025] / cby[2024] - 1),
             "moved": sorted(set(west_old) - rws), "kept": sorted(set(west_old) & rws),
             "monthly": {"region_cur": pick(rwm, 2025), "region_ly": pick(rwm, 2024), "current_cur": pick(cwm, 2025), "current_ly": pick(cwm, 2024)}}

# ---- what the repository ships besides the tables: metadata and business rules (counts for the top of the page)
MD = C.parents[1] / "setup" / "metadata"
raw_md = json.loads((MD / "raw_layer.json").read_text(encoding="utf-8"))
rpt_md = {k: v for k, v in json.loads((MD / "rpt_layer.json").read_text(encoding="utf-8")).items() if not k.startswith("_")}
S["meta"] = {"raw_sources": len(raw_md), "columns": sum(len(v["columns"]) for v in raw_md.values()),
             "relationships": sum(len(v["relationships"]) for v in rpt_md.values()), "calcs": sum(len(v["calculated_fields"]) for v in rpt_md.values()),
             "rules": len(json.loads((MD / "business_preferences.json").read_text(encoding="utf-8"))["items"])}

Path(__file__).with_name("numbers.json").write_text(json.dumps({"S": S}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print("ok")
