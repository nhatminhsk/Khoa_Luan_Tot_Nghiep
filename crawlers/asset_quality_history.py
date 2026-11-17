from __future__ import annotations

import json

import numpy as np
import pandas as pd

from crawlers import ocr_bctc

OUT = "data/credit/asset_quality_2012_2017.csv"
CHECKS = "data/credit/asset_quality_2012_2017_checks.json"
PANEL = "data/model/bank_panel_quarterly.csv"
HARVARD = "data/external/vn_banking_system_2002_2021_data.csv"
LOANS_OK = ("ok", "ok_lech_nguon")
DEP_OK = ("ok", "ok_tong_bang", "ok_lech_nguon")


def _prev(period: str, k: int) -> str:
    i = int(period[:4]) * 4 + int(period[-1]) - 1 - k
    return f"{i // 4}-Q{i % 4 + 1}"


def build() -> pd.DataFrame:
    res = ocr_bctc.apply_manual(pd.read_csv(ocr_bctc.OUT_ALL, encoding="utf-8-sig"))
    vnd = pd.read_csv(ocr_bctc.VND, encoding="utf-8-sig")
    for part in ("loans", "dep"):
        if f"src_{part}" not in res:
            res[f"src_{part}"] = res.pdf
            res[f"scope_{part}"] = ""
        res[f"src_{part}"] = res[f"src_{part}"].fillna(res.pdf)
    lok = res.loans_status.isin(LOANS_OK)
    dok = res.dep_status.isin(DEP_OK)
    page = lambda c: res[c].map(lambda v: "" if v != v else str(v).replace(".0", ""))  # noqa: E731
    out = pd.DataFrame({
        "ticker": res.ticker, "period": res.period,
        "npl_percent": res.npl_percent.where(lok), "loans_g2_percent": res.loans_g2_percent.where(lok),
        "npl_check": res.loans_check.where(lok), "npl_flag": np.where(res.loans_status.eq("ok_lech_nguon"), "lech_nguon", ""),
        "npl_scope": res.scope_loans.where(lok), "npl_src": (res.src_loans + ":" + page("page_loans")).where(lok),
        "casa_percent": res.casa_percent.where(dok), "casa_check": res.dep_check.where(dok),
        "casa_flag": np.where(res.dep_status.eq("ok_lech_nguon"), "lech_nguon", ""),
        "casa_scope": res.scope_dep.where(dok), "casa_src": (res.src_dep + ":" + page("page_dep")).where(dok),
    })
    grid = pd.DataFrame([(t, f"{y}-Q{q}") for t in ocr_bctc.ALL_BANKS for y, q in ocr_bctc.ALL_QUARTERS],
                        columns=["ticker", "period"])
    out = grid.merge(out, how="left", on=["ticker", "period"])
    v = vnd[["ticker", "period", "loans_gross_vnd", "loans_net_vnd", "deposits_vnd", "ldr_net_percent"]]
    out = out.merge(v, how="left", on=["ticker", "period"])
    out["ldr_gross_percent"] = (out.loans_gross_vnd / out.deposits_vnd * 100).round(4)
    for c in ("npl_percent", "loans_g2_percent", "casa_percent"):
        out[c] = pd.to_numeric(out[c], errors="coerce").round(4)
    return out.sort_values(["ticker", "period"])


def checks(d: pd.DataFrame) -> dict:
    r = {}
    cov = d.groupby("ticker").agg(npl=("npl_percent", "count"), casa=("casa_percent", "count"),
                                  ldr=("ldr_net_percent", "count"))
    r["do_phu"] = {"npl": int(d.npl_percent.notna().sum()), "casa": int(d.casa_percent.notna().sum()),
                   "ldr": int(d.ldr_net_percent.notna().sum()), "tren": len(d), "theo_nh": cov.to_dict("index")}
    # 2. ranh gioi
    pan = pd.read_csv(PANEL, encoding="utf-8-sig")[["ticker", "period", "npl_percent", "casa_percent"]]
    q4 = d[d.period == "2017-Q4"].merge(pan[pan.period == "2018-Q1"], on="ticker", suffixes=("", "_18q1"))
    pp = pan.sort_values(["ticker", "period"]).copy()
    for c in ("npl_percent", "casa_percent"):
        pp[f"d_{c}"] = pp.groupby("ticker")[c].diff()
    later_q1 = pp[pp.period.str.endswith("Q1") & (pp.period > "2018-Q4")]
    r["ranh_gioi_2017Q4_2018Q1"] = {
        c: {"n": int((q4[c].notna() & q4[f"{c}_18q1"].notna()).sum()),
            "trung_vi_abs_doi": round(float((q4[f"{c}_18q1"] - q4[c]).abs().median()), 3),
            "panel_trung_vi_abs_doi_q1": round(float(later_q1[f"d_{c}"].abs().median()), 3)}
        for c in ("npl_percent", "casa_percent")}
    # 3. Harvard cuoi nam
    h = pd.read_csv(HARVARD, encoding="utf-8-sig")
    h["npl_h"] = pd.to_numeric(h["Non-performing Loans Ratio"], errors="coerce")
    q = d[d.period.str.endswith("Q4")].assign(Year=lambda x: x.period.str[:4].astype(int))
    m = q.merge(h[["ticker", "Year", "npl_h"]], on=["ticker", "Year"]).dropna(subset=["npl_percent", "npl_h"])
    diff = (m.npl_percent - m.npl_h).abs()
    r["harvard_npl_q4"] = {"n": len(m), "lech_lt_0.01": int((diff < 0.01).sum()), "lech_lt_0.1": int((diff < 0.1).sum()),
                           "lech_lt_0.5": int((diff < 0.5).sum()),
                           "lech_lon": m.loc[diff >= 0.5, ["ticker", "period", "npl_percent", "npl_h"]].round(3).to_dict("records")}
    # 4. buoc nhay giua hai quy lien ke (ca hai deu co so)
    jumps = []
    for c, lim in (("npl_percent", 2.0), ("casa_percent", 8.0)):
        s = d[["ticker", "period", c]].dropna()
        s = s.assign(prev=s.groupby("ticker")[c].shift(), pper=s.groupby("ticker").period.shift())
        s = s[(s.pper == s.period.map(lambda p: _prev(p, 1))) & ((s[c] - s.prev).abs() > lim)]
        jumps += [dict(chi_tieu=c, ticker=t, period=p, truoc=round(a, 3), sau=round(b, 3))
                  for t, p, a, b in zip(s.ticker, s.period, s.prev, s[c])]
    r["buoc_nhay"] = jumps
    # 5. khop dung so ky truoc tren CDKT
    raw = pd.read_csv(ocr_bctc.OUT_ALL, encoding="utf-8-sig")
    vnd = pd.read_csv(ocr_bctc.VND, encoding="utf-8-sig").set_index(["ticker", "period"])
    n_prior = 0
    for x in raw[raw.loans_status.isin(LOANS_OK)].itertuples():
        tot = sum(getattr(x, f"g{k}") for k in range(1, 6)) * (x.loans_scale if x.loans_scale == x.loans_scale else 1)
        cur = vnd.loans_gross_vnd.get((x.ticker, x.period), np.nan)
        prv = [vnd.loans_gross_vnd.get((x.ticker, p), np.nan) for p in (_prev(x.period, 1), _prev(x.period, 4))]
        if any(p == p and p and abs(tot / p - 1) < 2e-5 for p in prv) and not (cur == cur and abs(tot / cur - 1) < 2e-5):
            n_prior += 1
    r["khop_ky_truoc"] = n_prior
    return r


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    d = build()
    d.to_csv(OUT, index=False, encoding="utf-8-sig")
    r = checks(d)
    json.dump(r, open(CHECKS, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(f"-> {OUT}: NPL {r['do_phu']['npl']}, CASA {r['do_phu']['casa']}, LDR {r['do_phu']['ldr']} / {r['do_phu']['tren']} o")
    print("ranh gioi:", r["ranh_gioi_2017Q4_2018Q1"])
    hv = r["harvard_npl_q4"]
    print(f"Harvard Q4: {hv['n']} o, lech <0,01: {hv['lech_lt_0.01']}, <0,1: {hv['lech_lt_0.1']}, <0,5: {hv['lech_lt_0.5']}")
    for x in hv["lech_lon"]:
        print("   ", x)
    print(f"buoc nhay: {len(r['buoc_nhay'])}")
    for x in r["buoc_nhay"]:
        print("   ", x)
    print("khop dung so ky truoc:", r["khop_ky_truoc"])


if __name__ == "__main__":
    main()
