"""Compute headline numbers for the analysis showcase from en/csv (local, no Tableau API)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

C = Path(__file__).resolve().parents[2] / "en" / "csv" / "in_use"
P = C.parent / "planned"


def rd(n, **k):
    return pd.read_csv(C / f"{n}.csv", **k)


out = {}

orders = rd("orders", parse_dates=["order_date", "promised_delivery_date"])
ol = rd("order_lines")
prod = rd("products")
ship = rd("shipments", parse_dates=["shipped_date", "delivered_date", "promised_delivery_date", "carrier_estimated_delivery_date", "order_date"])
inv = rd("invoices", parse_dates=["invoice_date"])
il = rd("invoice_lines")
ret = rd("returns", parse_dates=["requested_date", "order_date", "delivered_date"])
ref = rd("refunds", parse_dates=["refunded_date"])
cm = rd("credit_memos", parse_dates=["credit_memo_date"])

ol["rev"] = (ol.qty_ordered - ol.qty_cancelled) * ol.unit_price - ol.line_discount_amount
ol = ol.merge(orders[["order_id", "order_date", "channel", "state_code", "customer_id"]], on="order_id")
ol["m"] = ol.order_date.dt.to_period("M").astype(str)

# 1. three "sales" for Oct 2025
il["rev"] = il.qty_invoiced * il.unit_price - il.discount_amount
il = il.merge(inv[["invoice_id", "invoice_date", "fiscal_month", "channel", "sales_region_id", "state_code"]], on="invoice_id")
ws = rd("web_sessions", usecols=["session_id", "session_start_date", "traffic_source", "channel", "product_views", "cart_added_date",
                                 "checkout_started_date", "order_id", "tracked_order_amount", "oos_product_views"], parse_dates=["session_start_date"])


def oct_(s):
    return (s.dt.year == 2025) & (s.dt.month == 10)


out["three_sales_oct2025"] = {
    "order_based": round(ol.loc[oct_(ol.order_date), "rev"].sum()),
    "invoice_based": round(il.loc[oct_(il.invoice_date), "rev"].sum()),
    "invoice_fiscal_P9": round(il.loc[il.fiscal_month == "FY2025-P9", "rev"].sum()),
    "web_tracked": round(ws.loc[oct_(ws.session_start_date), "tracked_order_amount"].sum()),
}

# 2. monthly by channel + marketplace fee
mch = ol.groupby(["m", "channel"]).rev.sum().unstack(fill_value=0).round()
out["monthly_channel"] = {"months": list(mch.index), **{c: mch[c].tolist() for c in mch.columns}}
mk = il[il.channel == "marketplace"]
fee = inv[inv.channel == "marketplace"].marketplace_fee_amount.sum()
out["marketplace"] = {"rev": round(mk.rev.sum()), "fees": round(fee), "fee_share": round(fee / mk.rev.sum(), 4)}
y = ol.groupby([ol.order_date.dt.year, "channel"]).rev.sum().unstack(fill_value=0)
out["yearly_channel"] = {int(k): {c: round(v) for c, v in r.items()} for k, r in y.iterrows()}
fee_y = inv[inv.channel == "marketplace"].groupby(inv.invoice_date.dt.year).marketplace_fee_amount.sum()
out["mk_fee_by_year"] = {int(k): round(v) for k, v in fee_y.items()}

# 3. region reorg
il["year"] = il.invoice_date.dt.year
reg = il.groupby(["year", "sales_region_id"]).rev.sum().unstack(fill_value=0).round()
out["region_by_year"] = {int(k): dict(r.items()) for k, r in reg.iterrows()}
west_old = ["WA", "OR", "CA", "AK", "HI", "ID", "MT", "WY", "UT", "CO", "NV"]
ow = il[il.state_code.isin(west_old)].groupby("year").rev.sum()
out["old_west_states_by_year"] = {int(k): round(v) for k, v in ow.items()}
out["region_states"] = {r: sorted(g.state_code.unique().tolist()) for r, g in inv[inv.invoice_date.dt.year == 2025].groupby("sales_region_id")}

# 4. delivery late rate by warehouse x month; carrier mix at WH-C
d = ship[ship.delivered_date.notna()].copy()
d["late"] = d.delivered_date > d.promised_delivery_date
d["m"] = d.shipped_date.dt.to_period("M").astype(str)
lw = d.groupby(["m", "warehouse_id"]).late.mean().unstack().round(4)
out["late_by_wh_month"] = {"months": list(lw.index), **{w: lw[w].tolist() for w in lw.columns}}
whc = d[d.warehouse_id == "WH-C"].groupby(["m", "carrier_id"]).size().unstack(fill_value=0)
out["whc_carrier_mix"] = {"months": list(whc.index), **{c: whc[c].tolist() for c in whc.columns}}

# 5. late -> repeat purchase within 90 days (orders placed 2025-01..2025-08)
first = d.groupby("order_id").agg(late=("late", "max"), cust=("customer_id", "first"), od=("order_date", "first"))
first = first[first.cust.notna()]
oc = orders[orders.customer_id.notna()][["customer_id", "order_date"]]
win = first[(first.od >= "2025-01-01") & (first.od < "2025-09-01")].reset_index()
mm = win.merge(oc, left_on="cust", right_on="customer_id")
mm = mm[(mm.order_date > mm.od) & (mm.order_date <= mm.od + pd.Timedelta(days=90))]
win["rep"] = win.order_id.isin(mm.order_id)
r = win.groupby("late").rep.agg(["mean", "size"])
out["repeat_90d"] = {("late" if k else "on_time"): {"rate": round(v["mean"], 4), "n": int(v["size"])} for k, v in r.iterrows()}

# 6. returns: cohort rate, lag before/after window change, reasons
olr = ol.groupby("m").order_line_id.count()
rr = ret.copy()
rr["m"] = rr.order_date.dt.to_period("M").astype(str)
coh = (rr.groupby("m").order_line_id.nunique() / olr).fillna(0).round(4)
out["return_cohort"] = {"months": list(coh.index), "rate": coh.tolist()}
rr["lag"] = (rr.requested_date - rr.delivered_date).dt.days
rr["era"] = np.where(rr.order_date < "2024-07-01", "before", "after")
out["return_lag_hist"] = {e: np.histogram(rr.loc[rr.era == e, "lag"].dropna().clip(0, 69), bins=range(0, 75, 5))[0].tolist() for e in ["before", "after"]}
out["return_window_values"] = {f"{a}|{b}": int(v) for (a, b), v in rr.groupby("era").return_window_days.value_counts().items()}
reas = rr.merge(prod[["product_id", "category"]], on="product_id").groupby(["category", "return_reason"]).size().unstack(fill_value=0)
out["return_reasons"] = {c: {k: int(v) for k, v in r.items()} for c, r in reas.iterrows()}

# 7. support refunds vs finance credit memos 2025Q3
def q3(s):
    return (s >= "2025-07-01") & (s < "2025-10-01")


out["refund_vs_credit_q3"] = {
    "refunds_merch": round(ref.loc[q3(ref.refunded_date), "merchandise_refund_amount"].sum()),
    "credit_memos_merch": round(cm.loc[q3(cm.credit_memo_date), "merchandise_credit_amount"].sum()),
    "refunds_by_type": ref.loc[q3(ref.refunded_date)].groupby("refund_type").merchandise_refund_amount.sum().round().to_dict(),
    "credits_by_type": cm.loc[q3(cm.credit_memo_date)].groupby("memo_type").merchandise_credit_amount.sum().round().to_dict(),
}

# 8. tents: OOS searches + West split shipments
srch = rd("web_searches", usecols=["searched_date", "query_text", "results_count", "results_in_stock_count"], parse_dates=["searched_date"])
srch["oos"] = (srch.results_count > 0) & (srch.results_in_stock_count == 0)
srch["m"] = srch.searched_date.dt.to_period("M").astype(str)
tent = srch[srch.query_text.str.contains("tent", case=False, na=False)]
t = tent.groupby("m").oos.mean().round(4)
out["tent_search_oos"] = {"months": list(t.index), "rate": t.tolist()}
out["oos_top_terms_2024"] = srch[(srch.searched_date.dt.year == 2024) & srch.oos].query_text.value_counts().head(8).to_dict()
tent_orders = set(ol[ol.product_id.isin(prod[prod.subcategory == "tents"].product_id)].order_id)
so = ship[ship.order_id.isin(tent_orders)].groupby("order_id").agg(n=("shipment_id", "nunique"), st=("state_code", "first"), od=("order_date", "first"))
so = so[so.st.isin(west_old)]
so["q"] = so.od.dt.to_period("Q").astype(str)
sp = (so.n > 1).groupby(so.q).mean().round(4)
out["west_tent_split"] = {"q": list(sp.index), "rate": sp.tolist()}

# 9. funnel by traffic source 2024
w24 = ws[ws.session_start_date.dt.year == 2024]
f = w24.groupby("traffic_source").agg(
    sessions=("session_id", "count"), view=("product_views", lambda s: (s > 0).sum()),
    cart=("cart_added_date", lambda s: s.notna().sum()), checkout=("checkout_started_date", lambda s: s.notna().sum()),
    order=("order_id", lambda s: s.notna().sum()))
out["funnel_2024"] = {k: {c: int(v) for c, v in r.items()} for k, r in f.sort_values("sessions", ascending=False).iterrows()}

# 10b. ad platform claims vs own last-click orders (planned tables)
cd_ = pd.read_csv(P / "campaign_daily.csv")
cp_ = pd.read_csv(P / "campaigns.csv")
a = (cd_.groupby("campaign_id")[["spend_amount", "platform_conversions"]].sum()
     .join(orders.groupby("campaign_id").size().rename("lastclick"))
     .join(cp_.set_index("campaign_id")[["marketing_channel"]]))
g = a.groupby("marketing_channel")[["platform_conversions", "lastclick"]].sum()
g = g[g.platform_conversions > 0]
out["attribution"] = {k: {"platform": int(r.platform_conversions), "lastclick": int(r.lastclick)} for k, r in g.iterrows()}

# 10c. tents supply chain (planned tables): stock by warehouse, zero-stock share at WH-W, lead time by PO quarter
tents = set(prod[prod.subcategory == "tents"].product_id)
invd = pd.read_csv(P / "inventory_daily.csv", usecols=["snapshot_date", "warehouse_id", "product_id", "qty_on_hand"])
tv = invd[invd.product_id.isin(tents)].copy()
tv["m"] = tv.snapshot_date.str[:7]
stock = tv.groupby(["m", "warehouse_id", "snapshot_date"]).qty_on_hand.sum().groupby(["m", "warehouse_id"]).mean().unstack().round()
out["tent_stock"] = {"months": list(stock.index), **{w: stock[w].tolist() for w in stock.columns}}
tw = tv[tv.warehouse_id == "WH-W"]
out["tent_zero_share_whw"] = (tw.qty_on_hand <= 0).groupby(tw.m).mean().round(3).to_dict()
po = pd.read_csv(P / "purchase_orders.csv", usecols=["po_id", "po_date"])
rc = pd.read_csv(P / "receipts.csv", usecols=["po_id", "warehouse_id", "product_id", "received_date", "qty_received"]).merge(po, on="po_id")
rc = rc[rc.product_id.isin(tents)].copy()
rc["lead"] = (pd.to_datetime(rc.received_date) - pd.to_datetime(rc.po_date)).dt.days
rc["pq"] = pd.PeriodIndex(rc.po_date, freq="Q").astype(str)
lt = rc.groupby(["pq", "warehouse_id"]).lead.median().unstack()
out["tent_lead_by_po_q"] = {q: {w: (None if pd.isna(v) else float(v)) for w, v in r.items()} for q, r in lt.iterrows()}
out["tent_receipts_whw_2024"] = rc[(rc.warehouse_id == "WH-W") & rc.received_date.str.startswith("2024")].groupby(rc.received_date.str[:7]).qty_received.sum().to_dict()

# 10d. "where is my order" tickets per 1,000 shipments, and arrived_late returns, by warehouse
st = pd.read_csv(P / "support_tickets.csv", usecols=["category", "created_date", "shipment_id"])
wism = st[st.category == "where_is_my_order"].merge(ship[["shipment_id", "warehouse_id"]], on="shipment_id")
wism["m"] = wism.created_date.str[:7]
shm = ship.assign(m=ship.shipped_date.dt.to_period("M").astype(str)).groupby(["m", "warehouse_id"]).size()
wr = (wism.groupby(["m", "warehouse_id"]).size() / shm * 1000).unstack().round(1)
out["wismo_per_1000"] = {"months": list(wr.index), **{w: wr[w].tolist() for w in wr.columns}}
alr = ret[ret.return_reason == "arrived_late"].copy()
alr["era"] = np.where(alr.requested_date < "2025-05-01", "before", "after")
out["arrived_late_returns_whc"] = alr[alr.warehouse_id == "WH-C"].groupby(alr.requested_date.dt.to_period("M").astype(str)).size().to_dict()

# 10e. monthly series for the in-use-only page
mo = lambda s: s.dt.to_period("M").astype(str)
three = pd.DataFrame({
    "order": ol.groupby("m").rev.sum(),
    "invoice": il.groupby(mo(il.invoice_date)).rev.sum(),
    "web": ws.groupby(mo(ws.session_start_date)).tracked_order_amount.sum(),
}).loc["2024-01":"2025-12"].round()
out["three_monthly"] = {"months": list(three.index), **{c: three[c].tolist() for c in three.columns}}
feem = inv[inv.channel == "marketplace"].groupby(mo(inv.invoice_date)).marketplace_fee_amount.sum().reindex(mch.index, fill_value=0).round()
out["mk_fee_monthly"] = feem.tolist()
out["monthly_channel"] = {"months": list(mch.index), **{c: mch[c].tolist() for c in mch.columns}}
wt = ol[ol.product_id.isin(tents) & ol.state_code.isin(west_old)]
g = wt.groupby("m")[["qty_cancelled", "qty_backordered", "qty_ordered"]].sum()
out["west_tent_cancel_monthly"] = {"months": list(g.index), "rate": (g.qty_cancelled / g.qty_ordered).round(4).tolist()}
so["m"] = so.od.dt.to_period("M").astype(str)
spm = (so.n > 1).groupby(so.m).mean().round(4)
out["west_tent_split_monthly"] = {"months": list(spm.index), "rate": spm.tolist()}
tq = srch[srch.query_text.str.contains("tent", case=False, na=False)]
tqm = tq.groupby("m").oos.mean().round(4)
out["tent_search_oos_monthly"] = {"months": list(tqm.index), "rate": tqm.tolist()}
out["arrived_late_returns_by_wh"] = {w: g_.groupby(g_.requested_date.dt.to_period("M").astype(str)).size().to_dict()
                                     for w, g_ in ret[ret.return_reason == "arrived_late"].groupby("warehouse_id")}

# 10. planned tables: columns only
for n in ["campaigns", "campaign_daily", "customers", "support_tickets", "inventory_daily", "promotions", "sales_targets", "purchase_orders", "receipts"]:
    out[f"cols_{n}"] = list(pd.read_csv(P / f"{n}.csv", nrows=1).columns)

Path(__file__).with_name("numbers.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print("ok")
