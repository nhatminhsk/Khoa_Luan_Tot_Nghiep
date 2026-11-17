import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
EXP = REPO / "data/model/experiments"
sys.stdout.reconfigure(encoding="utf-8")


def eda():
    p = pd.read_csv(REPO / "data/model/bank_panel_quarterly.csv", encoding="utf-8-sig").sort_values(["ticker", "period"])
    p["q"] = p.period.str[-1].astype(int)
    d = p[p.period >= "2019-Q1"]
    print("== EDA")
    for c in ("npl_percent", "casa_percent", "ldr_computed_percent"):
        m = p.groupby("period")[c].median()
        print(f"{c}: trung vị 2019+ {d[c].median():.2f}; theo quý", {k: round(m[k], 2) for k in
              ("2018-Q1", "2022-Q4", "2023-Q4", "2026-Q2", "2026-Q3")}, "| số NH có Q3:",
              int(p[p.period == "2026-Q3"][c].notna().sum()))
    for c in ("npl_percent", "casa_percent"):
        g = pd.DataFrame({"q": p.q, "d": p.groupby("ticker")[c].diff(), "period": p.period}).dropna()
        g = g[g.period >= "2019-Q1"]
        print(c, "trung vị thay đổi theo quý", g.groupby("q").d.median().round(2).to_dict(),
              "tỷ lệ giảm", g.groupby("q").d.apply(lambda x: (x < 0).mean()).round(2).to_dict())
    cot = ["npl_percent", "loans_g2_percent", "casa_percent", "cof_ttm_percent", "nim_ttm_percent", "roa_ttm_percent"]
    r = d[cot].corr(method="spearman")
    print("Spearman CASA–COF", round(r.at["casa_percent", "cof_ttm_percent"], 2), "NIM–ROA",
          round(r.at["nim_ttm_percent", "roa_ttm_percent"], 2), "NPL–nhóm 2",
          round(r.at["npl_percent", "loans_g2_percent"], 2))
    for c in ("npl_percent", "casa_percent", "ldr_computed_percent"):
        x = d.assign(sau=d.groupby("ticker")[c].shift(-1))[[c, "sau"]].dropna()
        print(c, "r(t, t+1) =", round(x.corr().iloc[0, 1], 2))
    q3 = p[p.period == "2026-Q3"].set_index("ticker")
    print("NPL Q3 thấp nhất/cao nhất", q3.npl_percent.idxmin(), round(q3.npl_percent.min(), 2), q3.npl_percent.idxmax(),
          round(q3.npl_percent.max(), 2), "| CASA", q3.casa_percent.idxmin(), round(q3.casa_percent.min(), 2),
          q3.casa_percent.idxmax(), round(q3.casa_percent.max(), 2))
    v = pd.read_csv(REPO / "data/model/eda/variance.csv")
    print("phân rã phương sai:\n", v[v.feature.isin(["casa_percent", "ldr_computed_percent", "npl_percent"])]
          [["feature", "bank_share", "quarter_share", "resid_share"]].round(3).to_string(index=False))


def mo_hinh():
    print("== Mô hình")
    s = pd.read_csv(EXP / "forecast_selection.csv", encoding="utf-8-sig")
    s = s[s.indicator.isin(["npl_percent", "casa_percent", "ldr_computed_percent"])]
    print(s.pivot(index="indicator", columns="h", values="coverage_test").round(3))
    print(s.pivot(index="indicator", columns="h", values="method"))
    print(s.pivot(index="indicator", columns="h", values="base"))
    b = pd.read_csv(REPO / "khoa_luan/bang/rf_theo_tam.csv", encoding="utf-8-sig")
    b = b[b.indicator.isin(["npl_percent", "casa_percent", "ldr_computed_percent"])]
    print(b[["indicator", "h", "base", "chon", "n", "mae_base", "mae_chon", "gain", "lo", "hi"]].round(4).to_string(index=False))
    c = pd.read_csv(REPO / "khoa_luan/bang/so_sanh_mo_hinh.csv", encoding="utf-8-sig")
    c = c[c.chi_tieu.isin(["NPL", "CASA", "LDR"])]
    print(c[["chi_tieu", "h", "naive", "mae_co_so", "base_ten", "mae_ridge", "mae_lgbm", "mae_rf", "rf_chon", "n_rf",
             "n_ab"]].round(3).to_string(index=False))
    print(pd.read_csv(REPO / "khoa_luan/bang/quan_trong.csv", encoding="utf-8-sig", index_col=0).mul(100).round(1))
    f = pd.read_csv(EXP / "forecasts_de_xuat.csv")
    p = pd.read_csv(REPO / "data/model/bank_panel_quarterly.csv", encoding="utf-8-sig").set_index(["ticker", "period"])
    for ind, col in (("npl", "npl_percent"), ("casa", "casa_percent")):
        d = f[(f.indicator == ind) & (f.horizon == 1)].copy()
        d["now"] = [p[col].get((t, o)) for t, o in zip(d.ticker, d.origin_period)]
        d["chg"] = d.value - d.now
        d["w"] = d.upper - d.lower
        print(ind, "số NH", len(d), "giảm", int((d.chg < 0).sum()), "tăng", int((d.chg > 0).sum()))
        print(d.sort_values("chg")[["ticker", "now", "value", "lower", "upper", "chg", "w"]].round(2).head(4).to_string(index=False))
        print(d.sort_values("w")[["ticker", "lower", "upper", "w"]].round(2).tail(2).to_string(index=False))


def xep_hang():
    print("== Xếp hạng")
    k = pd.read_csv(EXP / "xep_hang_voi_du_bao.csv", encoding="utf-8-sig")
    for th, g in k.groupby("truong_hop"):
        top_a = g.nsmallest(3, "mean_rank_cong_bo").ticker.tolist()
        top_b = g.nsmallest(3, "mean_rank_du_bao").ticker.tolist()
        dp = (g.p_top1_du_bao - g.p_top1_cong_bo).abs()
        print(th, "rho", round(g.rho_hang.iloc[0], 4), top_a, top_b, "max dP", round(dp.max(), 4),
              g.ticker.iloc[dp.values.argmax()])


if __name__ == "__main__":
    eda()
    mo_hinh()
    if (EXP / "xep_hang_voi_du_bao.csv").exists():
        xep_hang()
