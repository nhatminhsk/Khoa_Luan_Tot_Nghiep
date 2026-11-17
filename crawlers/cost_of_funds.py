from __future__ import annotations

import glob
import io
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from crawlers import vci_ratio

RAW = "data/vnstock_financial/raw"
OUT_PATH = "data/interest_rates/bank_cost_of_funds_quarterly.csv"
FIELD = "RT_BANK_COF"

QUARTER_END = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}


def _load(period_kind):
    frames = []
    for path in sorted(glob.glob(f"{RAW}/*_ratio_{period_kind}.csv")):
        ticker = os.path.basename(path).split("_")[0]
        # Chi file quy co loi quy chep lai (xem crawlers/vci_ratio.py).
        if period_kind == "quarter":
            df = vci_ratio.read(path)
        else:
            df = pd.read_csv(path, encoding="utf-8-sig")
        sub = df[df["id"] == FIELD][["period", "value"]].copy()
        sub["ticker"] = ticker
        frames.append(sub)
    out = pd.concat(frames, ignore_index=True)
    out["cof_ttm_percent"] = (-out["value"]) * 100
    out.loc[out["value"] == 0, "cof_ttm_percent"] = np.nan
    return out


def build(write=True):
    quarterly = _load("quarter")
    kept = quarterly.dropna(subset=["cof_ttm_percent"]).copy()

    kept["period_end"] = [
        f"{p[:4]}-{QUARTER_END[p[-1]]}" for p in kept["period"]
    ]
    kept["source"] = "vnstock ratio_quarter RT_BANK_COF"
    kept["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
    kept["cof_ttm_percent"] = kept["cof_ttm_percent"].round(4)

    cols = ["period", "period_end", "ticker", "cof_ttm_percent", "source", "retrieved_at_utc"]
    kept = kept[cols].sort_values(["period", "ticker"])

    if write:
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        kept.to_csv(OUT_PATH, index=False, encoding="utf-8-sig", lineterminator="\r\n")

    return {
        "rows": len(kept),
        "dropped_placeholder_zeros": int((quarterly["value"] == 0).sum()),
        "banks": kept["ticker"].nunique(),
        "quarters": kept["period"].nunique(),
        "range": (kept["period"].min(), kept["period"].max()),
        "path": OUT_PATH,
    }


def validate():
    out = {}

    q, y = _load("quarter"), _load("year")
    q = q.dropna(subset=["cof_ttm_percent"])
    y = y.dropna(subset=["cof_ttm_percent"])
    q["year"] = q["period"].str[:4].astype(int)
    q["q"] = q["period"].str[-1]
    ann = y.rename(columns={"period": "year", "cof_ttm_percent": "annual"})[["ticker", "year", "annual"]]
    basis = {}
    for qq in "1234":
        m = q[q["q"] == qq].merge(ann, on=["ticker", "year"])
        d = (m["cof_ttm_percent"] - m["annual"]).abs()
        basis[f"Q{qq}"] = {"n": len(m), "median_abs_diff": round(d.median(), 4),
                           "exact_matches": int((d < 0.01).sum())}
    out["basis_vs_annual"] = basis

    h = pd.read_csv("data/external/vn_banking_system_2002_2021_data.csv", encoding="utf-8-sig")
    h.columns = [c.strip() for c in h.columns]
    for c in ["Interest Expenses", "Total Deposits"]:
        h[c] = pd.to_numeric(h[c].astype(str).str.replace(r"[,\s]", "", regex=True), errors="coerce")
    h = h[(h["Total Deposits"] > 0) & h["Interest Expenses"].notna()]
    h["ie_over_deposits"] = h["Interest Expenses"] / h["Total Deposits"] * 100
    m = h.merge(ann, left_on=["ticker", "Year"], right_on=["ticker", "year"])  # cot ticker: ma Harvard da quy doi
    gap = m["ie_over_deposits"] - m["annual"]
    out["cross_vendor_harvard"] = {
        "n_bank_years": len(m),
        "pearson_r": round(m["ie_over_deposits"].corr(m["annual"]), 4),
        "median_gap_pp": round(gap.median(), 3),
        "gap_positive_share": round(float((gap > 0).mean()), 3),
    }

    med = q.groupby("period")["cof_ttm_percent"].median()
    s = pd.read_csv("data/loan_rates/loan_industry_avg.csv", encoding="utf-8-sig")
    s["mid"] = (s["deposit_6_to_12m_min"] + s["deposit_6_to_12m_max"]) / 2
    s = s.assign(dt=pd.to_datetime(s["date"])).sort_values("dt").set_index("dt")
    ttm = s["mid"].rolling(12).mean().resample("QE").last().dropna()
    ttm.index = [f"{d.year}-Q{d.quarter}" for d in ttm.index]
    j = pd.concat([med.rename("cof"), ttm.rename("sbv")], axis=1).dropna()
    out["cross_source_sbv"] = {
        "n_quarters": len(j),
        "pearson_r": round(j["cof"].corr(j["sbv"]), 4),
        "cof_below_sbv_every_quarter": bool((j["cof"] < j["sbv"]).all()),
        "median_gap_pp": round((j["cof"] - j["sbv"]).median(), 3),
    }
    return out


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--validate" in sys.argv:
        print(json.dumps(validate(), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(build(), indent=2, ensure_ascii=False, default=str))
