from __future__ import annotations

import glob
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from crawlers import vci_ratio

RAW = "data/vnstock_financial/raw"
OUT_PATH = "data/interest_rates/bank_earning_asset_yield_quarterly.csv"
PUBLISHED = "data/interest_rates/bank_lending_rates_monthly.csv"

QUARTER_END = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}

IBL_FIELDS = [
    "BS_CUSTOMER_DEPOSITS",
    "BS_PLACEMENTS_AND_BORROWINGS_FROM_CREDIT_INSTITUTIONS",
    "BS_VALUABLE_PAPERS_ISSUED",
]
EA_BASE = "BS_TOTAL_ASSETS"
EA_SUBTRACT = ["BS_CASH_AND_PRECIOUS_METALS", "BS_FIXED_ASSETS", "BS_BALANCES_WITH_SBV"]


def _field(statement: str, name: str, period_kind: str = "quarter") -> pd.DataFrame:
    frames = []
    for path in sorted(glob.glob(f"{RAW}/*_{statement}_{period_kind}.csv")):
        ticker = os.path.basename(path).split("_")[0]
        # ratio quy co loi quy chep lai (xem crawlers/vci_ratio.py).
        if statement == "ratio" and period_kind == "quarter":
            df = vci_ratio.read(path)
        else:
            df = pd.read_csv(path, encoding="utf-8-sig")
        sub = df[df["id"] == name][["period", "value"]].copy()
        sub["ticker"] = ticker
        frames.append(sub.rename(columns={"value": name}))
    return pd.concat(frames, ignore_index=True)


def _load(period_kind: str = "quarter") -> pd.DataFrame:
    df = None
    for name in IBL_FIELDS + [EA_BASE] + EA_SUBTRACT:
        f = _field("balance_sheet", name, period_kind)
        df = f if df is None else df.merge(f, on=["period", "ticker"], how="outer")
    for name in ["RT_BANK_NIM", "RT_BANK_COF"]:
        df = df.merge(_field("ratio", name, period_kind), on=["period", "ticker"], how="outer")

    df["nim_ttm_percent"] = df["RT_BANK_NIM"] * 100
    df.loc[df["RT_BANK_NIM"] == 0, "nim_ttm_percent"] = np.nan
    df["cof_ttm_percent"] = (-df["RT_BANK_COF"]) * 100
    df.loc[df["RT_BANK_COF"] == 0, "cof_ttm_percent"] = np.nan

    df["ibl"] = sum(df[c].fillna(0) for c in IBL_FIELDS)
    df["earning_assets"] = df[EA_BASE] - sum(df[c].fillna(0) for c in EA_SUBTRACT)
    df.loc[df["earning_assets"] <= 0, "earning_assets"] = np.nan
    df["ibl_over_earning_assets"] = df["ibl"] / df["earning_assets"]

    df["earning_asset_yield_ttm_percent"] = (
        df["nim_ttm_percent"] + df["cof_ttm_percent"] * df["ibl_over_earning_assets"]
    )
    return df


def build(write: bool = True) -> dict:
    df = _load("quarter")
    kept = df.dropna(subset=["earning_asset_yield_ttm_percent"]).copy()

    kept["period_end"] = [f"{p[:4]}-{QUARTER_END[p[-1]]}" for p in kept["period"]]
    kept["source"] = "derived: RT_BANK_NIM + RT_BANK_COF * (IBL/EA) from vnstock_financial/raw"
    kept["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for column in ["earning_asset_yield_ttm_percent", "nim_ttm_percent", "cof_ttm_percent"]:
        kept[column] = kept[column].round(4)
    kept["ibl_over_earning_assets"] = kept["ibl_over_earning_assets"].round(4)

    cols = ["period", "period_end", "ticker", "earning_asset_yield_ttm_percent",
            "nim_ttm_percent", "cof_ttm_percent", "ibl_over_earning_assets",
            "source", "retrieved_at_utc"]
    kept = kept[cols].sort_values(["period", "ticker"])

    if write:
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        kept.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")

    return {
        "rows": len(kept),
        "banks": int(kept["ticker"].nunique()),
        "quarters": int(kept["period"].nunique()),
        "range": (kept["period"].min(), kept["period"].max()),
        "path": OUT_PATH,
    }


def validate() -> None:
    df = _load("quarter")
    ok = df.dropna(subset=["earning_asset_yield_ttm_percent"])
    print(f"{len(ok)} bank-quarter, {ok['ticker'].nunique()} NH, "
          f"{ok['period'].min()} -> {ok['period'].max()}\n")

    print(f"loi suat: {ok['earning_asset_yield_ttm_percent'].min():.2f}% - "
          f"{ok['earning_asset_yield_ttm_percent'].max():.2f}%, "
          f"trung vi {ok['earning_asset_yield_ttm_percent'].median():.2f}%")
    k = df["ibl_over_earning_assets"].dropna()
    print(f"IBL/EA: trung vi {k.median():.3f}, 5-95% {k.quantile(.05):.2f}-{k.quantile(.95):.2f} "
          "(bang can doi ngan hang thuc te nam trong khoang nay)")
    per_bank = ok.groupby("ticker").size()
    print(f"so quy moi NH: thap nhat {per_bank.min()} ({per_bank.idxmin()}), "
          f"cao nhat {per_bank.max()} -- ke thua y nguyen do phu lech cua COF")

    year = _load("year")
    ann = year.dropna(subset=["nim_ttm_percent"]).rename(
        columns={"period": "year", "nim_ttm_percent": "annual"})[["ticker", "year", "annual"]]
    ann["year"] = ann["year"].astype(int)
    q = df.dropna(subset=["nim_ttm_percent"]).copy()
    q["year"] = q["period"].str[:4].astype(int)
    q["q"] = q["period"].str[-1]
    print("\nco so tinh NIM (neu TTM thi Q4 == so ca nam):")
    for qq in "1234":
        m = q[q["q"] == qq].merge(ann, on=["ticker", "year"])
        d = (m["nim_ttm_percent"] - m["annual"]).abs()
        print(f"  Q{qq}: n={len(m):3d}  lech trung vi {d.median():.4f}  "
              f"khop tuyet doi {int((d < 0.01).sum())}/{len(m)}")

    if not os.path.exists(PUBLISHED):
        print("\n(chua co bank_lending_rates_monthly.csv de doi chieu)")
        return
    pub = pd.read_csv(PUBLISHED, encoding="utf-8-sig", dtype={"month": str})
    pub = pub.dropna(subset=["lending_avg_percent"])
    pub = pub[pub["ticker"].notna() & (pub["ticker"].astype(str).str.strip() != "")]
    pub["period"] = (pub["month"].str[:4] + "-Q"
                     + ((pub["month"].str[5:].astype(int) - 1) // 3 + 1).astype(str))
    pubq = pub.groupby(["ticker", "period"])["lending_avg_percent"].mean().reset_index()
    m = pubq.merge(ok, on=["ticker", "period"])
    if len(m) < 5:
        print("\n(khong du cap de doi chieu)")
        return

    gap = m["earning_asset_yield_ttm_percent"] - m["lending_avg_percent"]
    print(f"\ndoi chieu voi lai suat cho vay CONG BO ({len(m)} cap bank-quarter):")
    print(f"  tuong quan chung r = {m['earning_asset_yield_ttm_percent'].corr(m['lending_avg_percent']):.4f}")
    print(f"  chenh lech trung vi {gap.median():+.2f} diem "
          f"(khoang {gap.min():+.2f}..{gap.max():+.2f})")
    print(f"  loi suat THAP HON lai suat cong bo o {(gap < 0).mean():.1%} so cap "
          "-- dung ky vong: tai san sinh loi con gom trai phieu va tien gui lien NH")
    print("\n  tuong quan CHEO NGAN HANG trong tung quy (day moi la thu TOPSIS can):")
    for period, g in m.groupby("period"):
        if len(g) >= 5:
            r = g["earning_asset_yield_ttm_percent"].corr(g["lending_avg_percent"])
            print(f"    {period}: n={len(g):2d}  r={r:+.3f}")
    print("\n  chenh lech theo tung NH (KHONG phai hang so - dung bu offset):")
    by_bank = m.groupby("ticker").apply(
        lambda g: pd.Series({
            "n": len(g),
            "loi_suat": round(g["earning_asset_yield_ttm_percent"].mean(), 2),
            "cong_bo": round(g["lending_avg_percent"].mean(), 2),
            "lech": round((g["earning_asset_yield_ttm_percent"] - g["lending_avg_percent"]).mean(), 2),
        }), include_groups=False).sort_values("lech")
    print(by_bank.to_string())


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--validate" in sys.argv:
        validate()
    else:
        print(json.dumps(build(), indent=2, ensure_ascii=False, default=str))
