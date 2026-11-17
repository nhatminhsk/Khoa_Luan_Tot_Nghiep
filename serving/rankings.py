from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from experiments import montecarlo_ranking as mc

TOP = Path("data/model/experiments/montecarlo_top.csv")
TOP_AMOUNT = Path("data/model/experiments/montecarlo_top_so_tien.csv")
OUT = Path("data/serving/rankings.csv")
REPORT_DIR = Path("data/model/experiments")
ALGOS = list(mc.COMPENSATORY)
SCENARIO = "quanh_mac_dinh"
METHOD_VERSION = "MCDM×MC (SAW, TOPSIS, VIKOR, PROMETHEE II)"
CHANNEL = {"online": "ONLINE", "counter": "COUNTER"}
LABELS = {  # ten hien tren web cho tieu chi (catalog web chi co mot phan cac tieu chi nay)
    "car_asof_percent": "CAR", "equity_to_assets_pct": "Vốn chủ / tổng tài sản", "npl_percent": "Nợ xấu",
    "loans_g2_percent": "Nợ nhóm 2", "credit_cost_ttm_pct": "Chi phí tín dụng",
    "accrued_interest_to_assets_pct": "Lãi dự thu / tổng tài sản", "cir_ttm_pct": "Chi phí / thu nhập (CIR)",
    "state_own_percent": "Sở hữu nhà nước", "roa_ttm_percent": "ROA", "ldr_computed_percent": "Cho vay / tiền gửi (LDR)",
    "liquid_assets_pct": "Tài sản thanh khoản", "casa_percent": "CASA", "corp_bond_to_assets_pct": "Trái phiếu DN / tổng tài sản",
    "log_total_assets": "Quy mô tài sản", "lending_avg_pct": "Lãi cho vay bình quân",
    "loan_yield_ttm_pct": "Lợi suất cho vay", "retail_loan_share_pct": "Tỷ trọng cho vay cá nhân",
}


def aggregate(top: pd.DataFrame) -> pd.DataFrame:
    t = top[(top.scenario == SCENARIO) & top.algorithm.isin(ALGOS)]
    pr = t.pivot(index="ticker", columns="algorithm", values="point_rank")[ALGOS]
    g = t.groupby("ticker")
    out = pr.assign(hang_TB_4=pr.mean(1), P_top1=g.p_top1.mean(), P_top3=g.p_top3.mean(),
                    min_p05_4=g.p05.min(), max_p95_4=g.p95.max())
    out = out.reset_index().sort_values(["hang_TB_4", "P_top3", "ticker"], ascending=[True, False, True])
    out.insert(1, "hang", range(1, len(out) + 1))
    return out.set_index("ticker")


def drivers(inp: dict, spec: dict, center: dict, scale: dict | None = None) -> pd.DataFrame:
    cols, _, _ = mc._structure(spec)
    dirs = np.array([spec[c][0] for c in cols], float)
    Nm = mc.normalise(mc._draw_data(inp, cols, None, 1, dirs), dirs)[0]
    W, _ = mc.draw_weights(spec, center, "center", None, 1, scale)
    C = pd.DataFrame(W[0] * (Nm - Nm.mean(0)), index=inp["banks"], columns=cols)
    label = lambda c: LABELS.get(c, "Lãi suất kỳ hạn này" if c.startswith("dep") else c)
    return pd.DataFrame({"top_positive": [label(C.loc[b].idxmax()) if C.loc[b].max() > 0 else None for b in C.index],
                         "top_negative": [label(C.loc[b].idxmin()) if C.loc[b].min() < 0 else None for b in C.index]},
                        index=C.index)


def missing_note(inp: dict, spec: dict) -> pd.Series:
    v = inp["vals"][[c for c in spec if c in inp["vals"]]]
    return v.isna().apply(lambda r: ", ".join(LABELS.get(c, c) for c in r.index[r]), axis=1)


def _safety_weight(u: float | None) -> float:
    f = 1.0 if u is None else max(u, mc.BHTG_FLOOR)
    s = mc.DEPOSIT_TOP["an toan"] * f
    return s / (mc.DEPOSIT_TOP["lai"] + s)


def build(ranking: str) -> pd.DataFrame:
    inp = mc.build_inputs(ranking=ranking)
    period = pd.read_csv(ranking, encoding="utf-8-sig").latest_period.max()
    lending_asof = inp["vals"].index.map(
        pd.read_csv(ranking, encoding="utf-8-sig").set_index("ticker").lending_asof).dropna().max()
    top = pd.read_csv(TOP, encoding="utf-8-sig")
    amount = pd.read_csv(TOP_AMOUNT, encoding="utf-8-sig") if TOP_AMOUNT.exists() else None
    rows = []

    def emit(agg: pd.DataFrame, drv: pd.DataFrame, **keys) -> None:
        for t, r in agg.iterrows():
            rows.append(dict(as_of_period=period, **keys, ticker=t, rank=int(r.hang), rank_low=int(r.min_p05_4),
                             rank_high=int(r.max_p95_4), score=None, group_label=None,
                             top_positive=drv.top_positive.get(t), top_negative=drv.top_negative.get(t),
                             method_version=METHOD_VERSION, p_top1=round(r.P_top1, 4), p_top3=round(r.P_top3, 4)))

    for (term, ch), g in top[top.part == "gui"].groupby(["term_months", "channel"]):
        term = int(term)
        keep = list(g.ticker.unique())
        drv = drivers(mc.subset_inputs(inp, keep), mc.deposit_spec(term, ch), mc.DEPOSIT_TOP)
        emit(aggregate(g), drv, purpose="SAVINGS", term_months=term, channel=CHANNEL[ch], amount_vnd=None,
             rates_as_of=inp["rate_date"], uninsured_share=None, safety_weight=round(_safety_weight(None), 4))
        if term == mc.DEFAULT_TERM and ch == mc.DEFAULT_CHANNEL:
            _report_table(aggregate(g), inp, mc.deposit_spec(term, ch), f"gui{term}T_{ch}", ranking,
                          {f"lai_{term}T_{ch}": mc.rate_col(term, ch)})
    if amount is not None:  # file khong ghi anh chup: phai chay --so-tien tren cung anh chup voi montecarlo_top
        for (amt, term, ch, u), g in amount.groupby(["so_tien_vnd", "term_months", "channel", "phan_khong_bao_hiem"]):
            term = int(term)
            ia = mc.subset_inputs(mc.with_amount(inp, amt), list(g.ticker.unique()))
            drv = drivers(ia, mc.deposit_spec(term, ch), mc.DEPOSIT_TOP, {"an toan": max(u, mc.BHTG_FLOOR)})
            emit(aggregate(g), drv, purpose="SAVINGS", term_months=term, channel=CHANNEL[ch], amount_vnd=int(amt),
                 rates_as_of=inp["rate_date"], uninsured_share=round(u, 4), safety_weight=round(_safety_weight(u), 4))
    spec, center = mc.loan_spec()
    g = top[top.part == "vay"]
    emit(aggregate(g), drivers(inp, spec, center), purpose="LOAN", term_months=None, channel=None, amount_vnd=None,
         rates_as_of=lending_asof, uninsured_share=None, safety_weight=None)
    _report_table(aggregate(g), inp, spec, "vay", ranking,
                  {"lai_vay_TB": "lending_avg_pct", "loi_suat_cho_vay": "loan_yield_ttm_pct"})
    df = pd.DataFrame(rows)
    for c in ("term_months", "amount_vnd", "rank", "rank_low", "rank_high"):
        df[c] = df[c].astype("Int64")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, encoding="utf-8")
    return df


def _report_table(agg: pd.DataFrame, inp: dict, spec: dict, name: str, ranking: str, show: dict) -> None:
    tab = agg.copy()
    for col, src in show.items():
        tab.insert(2 + list(show).index(col) + 1, col, inp["vals"][src].reindex(tab.index).round(2))
    note = missing_note(inp, spec).reindex(tab.index)
    tab["ghi_chu"] = note.map(lambda s: f"o thieu dien trung vi: {s}" if s else "")
    tab = tab[["hang", "hang_TB_4", *show, *ALGOS, "P_top1", "P_top3", "min_p05_4", "max_p95_4", "ghi_chu"]]
    stamp = Path(ranking).stem.replace("features_ranking_", "")
    tab.round(4).to_csv(REPORT_DIR / f"xep_hang_{name}_{stamp}.csv", encoding="utf-8-sig")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    snap = sys.argv[sys.argv.index("--ranking") + 1] if "--ranking" in sys.argv else mc.RANKING
    out = build(snap)
    print(f"{OUT}: {len(out)} dong; {out.groupby(['purpose', 'amount_vnd'], dropna=False).ticker.count().to_dict()}")
