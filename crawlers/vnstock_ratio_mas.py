from __future__ import annotations

import glob
import os
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

TICKERS = [
    "ACB", "BAB", "BID", "BVB", "CTG", "EIB", "HDB", "LPB", "MBB", "MSB", "NAB",
    "NVB", "OCB", "PGB", "SHB", "SSB", "STB", "TCB", "TPB", "VCB", "VIB", "VPB",
]

RAW_DIR = "data/vnstock_financial/raw_mas"
LONG_PATH = "data/vnstock_financial/ratio_mas_long.csv"
TTM_PATH = "data/vnstock_financial/ratio_mas_ttm.csv"
LOG_PATH = "crawl_log.txt"

# Chi tieu MAS thuc su co du lieu. 48 id con lai trong schema deu trong 0%.
FLOW_METRICS = {
    "RT_BANK_NIM": "nim",
    "RT_BANK_COF": "cof",
    "RT_BANK_YIEA": "earning_asset_yield",
    "RT_PRT_ROE": "roe",
    "RT_PRT_ROA": "roa",
}
# Ty le cua hai dong tien -- cong 4 quy la SAI. Dung trung binh 4 quy, gan dung.
RATIO_METRICS = {"RT_BANK_CIR": "cir"}
# Do tai mot thoi diem -- khong bien doi.
POINT_METRICS = {
    "RT_VALUE_PE": "pe",
    "RT_VALUE_PB": "pb",
    "RT_VALUE_EPS": "eps_vnd",
    "RT_VALUE_BVPS": "bvps_vnd",
    "RT_VALUE_BETA": "beta",
    "RT_VALUE_DIVIDEND_YIELD": "dividend_yield",
}
ALL_METRICS = {**FLOW_METRICS, **RATIO_METRICS, **POINT_METRICS}
# Ba chi tieu nay khong the bang 0 ve mat dinh nghia (ngan hang nao cung co thu lai, tra
# lai va chi phi), nen 0 cua MAS la ky hieu THIEU: 99 o YIEA, 57 o COF, 7 o CIR tu 2016,
# day o 2017-Q1..2018-Q3, 2021-Q2/Q3, 2022-Q1. Doi chieu WiData 31/10/2026: cong 4 quy
# coi 0 la so that thi TTM thap di trung vi 3,18 diem, lech 32/32 o so duoc.
# NIM, ROE, ROA CO Y KHONG nam trong day: ngan hang lo (NVB) co the ra 0 that.
ZERO_MEANS_MISSING = ("earning_asset_yield", "cof", "cir")

QUARTER_END = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}


def _log(msg):
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n"
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(line)


def _quarter_key(period):
    year, quarter = str(period).split("-Q")
    return int(year) * 4 + int(quarter)


def fetch(tickers=None, sleep=0.4):
    import vnstock_data as vd

    tickers = tickers or TICKERS
    os.makedirs(RAW_DIR, exist_ok=True)
    ok, failed = [], []
    for ticker in tickers:
        try:
            finance = vd.Finance(
                source="MAS", symbol=ticker, period="quarter", get_all=True
            )
            df = finance.ratio(period="quarter", lang="en", dropna=False)
            path = f"{RAW_DIR}/{ticker}_ratio_quarter.csv"
            df.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\r\n")
            ok.append((ticker, len(df), df["period"].nunique()))
        except Exception as exc:  # nguon co the tu choi tung ma
            failed.append((ticker, f"{type(exc).__name__}: {exc}"[:120]))
        time.sleep(sleep)
    _log(
        f"vnstock_ratio_mas fetch: {len(ok)}/{len(tickers)} ma ok, "
        f"{len(failed)} loi -> {RAW_DIR}"
    )
    return {"ok": len(ok), "failed": failed}


def _load_raw():
    frames = []
    for path in sorted(glob.glob(f"{RAW_DIR}/*_ratio_quarter.csv")):
        ticker = os.path.basename(path).split("_")[0]
        df = pd.read_csv(path, encoding="utf-8-sig")
        df["ticker"] = ticker
        frames.append(df)
    if not frames:
        raise FileNotFoundError(
            f"Chua co file raw nao trong {RAW_DIR} -- chay fetch truoc."
        )
    return pd.concat(frames, ignore_index=True)


def build(write=True):
    raw = _load_raw()
    raw = raw[raw["id"].isin(ALL_METRICS)].copy()
    raw = raw[raw["period"].astype(str).str.match(r"^\d{4}-Q[1-4]$")]

    long = raw[["ticker", "period", "id", "name", "unit", "value"]].copy()
    long["metric"] = long["id"].map(ALL_METRICS)
    long["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
    long = long.sort_values(["ticker", "period", "id"])

    wide = raw.pivot_table(
        index=["ticker", "period"], columns="id", values="value", aggfunc="first"
    )
    wide = wide.rename(columns=ALL_METRICS).reset_index()
    for col in ALL_METRICS.values():
        if col not in wide.columns:
            wide[col] = np.nan

    # MAS de COF va CIR dau duong, VCI de dau am. Chuan hoa ve duong o day.
    for col in ("cof", "cir"):
        wide[col] = wide[col].abs()

    # rolling(4, min_periods=4) tu ra NaN khi co mot quy thieu trong cua so.
    for col in ZERO_MEANS_MISSING:
        wide[col] = wide[col].where(wide[col] != 0)

    wide["qkey"] = wide["period"].map(_quarter_key)
    wide = wide.sort_values(["ticker", "qkey"])

    # Chi cong 4 quy khi bon quy do lien tiep that -- khong duoc cong xuyen qua khoang trong.
    contiguous = (
        wide.groupby("ticker")["qkey"].diff().eq(1).groupby(wide["ticker"])
        .rolling(3, min_periods=3).sum().reset_index(level=0, drop=True).eq(3)
    )

    out = wide[["ticker", "period", "qkey"]].copy()
    for src, name in FLOW_METRICS.items():
        col = ALL_METRICS[src]
        rolled = (
            wide.groupby("ticker")[col].rolling(4, min_periods=4).sum()
            .reset_index(level=0, drop=True)
        )
        out[f"{col}_ttm_percent"] = np.where(contiguous, rolled * 100, np.nan)
        out[f"{col}_quarter_percent"] = wide[col] * 100
    for src, name in RATIO_METRICS.items():
        col = ALL_METRICS[src]
        rolled = (
            wide.groupby("ticker")[col].rolling(4, min_periods=4).mean()
            .reset_index(level=0, drop=True)
        )
        out[f"{col}_ttm_approx_percent"] = np.where(contiguous, rolled * 100, np.nan)
        out[f"{col}_quarter_percent"] = wide[col] * 100
    for src, name in POINT_METRICS.items():
        col = ALL_METRICS[src]
        out[col] = wide[col]

    out["period_end"] = [f"{p[:4]}-{QUARTER_END[p[-1]]}" for p in out["period"]]
    out["source"] = "vnstock_data MAS ratio_quarter"
    out["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
    out = out.drop(columns=["qkey"])

    lead = ["period", "period_end", "ticker"]
    out = out[lead + [c for c in out.columns if c not in lead]]
    out = out.sort_values(["period", "ticker"])

    num = out.select_dtypes("number").columns
    out[num] = out[num].round(6)

    if write:
        os.makedirs(os.path.dirname(LONG_PATH), exist_ok=True)
        long.to_csv(LONG_PATH, index=False, encoding="utf-8-sig", lineterminator="\r\n")
        out.to_csv(TTM_PATH, index=False, encoding="utf-8-sig", lineterminator="\r\n")
        _log(
            f"vnstock_ratio_mas build: {len(long)} dong long, {len(out)} dong ttm, "
            f"{out['ticker'].nunique()} NH, {out['period'].nunique()} quy "
            f"({out['period'].min()}..{out['period'].max()}) -> {TTM_PATH}"
        )

    in_window = out[out["period"].between("2018-Q1", "2026-Q4")]
    return {
        "rows_long": len(long),
        "rows_ttm": len(out),
        "banks": int(out["ticker"].nunique()),
        "quarters": int(out["period"].nunique()),
        "range": (out["period"].min(), out["period"].max()),
        "metrics": sorted(long["metric"].unique().tolist()),
        "banks_with_2021Q2": int(
            out[out["period"] == "2021-Q2"]["ticker"].nunique()
        ),
        "nim_ttm_coverage_2018plus": round(
            100 * in_window["nim_ttm_percent"].notna().mean(), 1
        ),
        "paths": [LONG_PATH, TTM_PATH],
    }


def validate():
    mas = pd.read_csv(TTM_PATH, encoding="utf-8-sig")
    vci = pd.read_csv(
        "data/vnstock_financial/financial_long.csv", low_memory=False
    )
    vci = vci[(vci["freq"] == "quarter") & (vci["statement"] == "ratio")]

    out = {}
    pairs = [
        ("RT_BANK_NIM", "nim_ttm_percent"),
        ("RT_BANK_COF", "cof_ttm_percent"),
        ("RT_PRT_ROE", "roe_ttm_percent"),
        ("RT_PRT_ROA", "roa_ttm_percent"),
    ]
    for metric_id, col in pairs:
        left = mas[["ticker", "period", col]].dropna()
        right = vci[vci["id"] == metric_id][["ticker", "period", "value"]].dropna()
        # VCI ghi 0 khi THIEU chu khong phai 0% (114 o o COF) -- loai truoc khi so.
        right = right[right["value"] != 0].assign(
            vci=lambda d: d["value"].abs() * 100
        )
        merged = left.merge(right[["ticker", "period", "vci"]], on=["ticker", "period"])
        err = (merged[col] - merged["vci"]).abs()
        out[metric_id] = {
            "n": len(merged),
            "median_abs_err_pp": round(float(err.median()), 5),
            "p95_abs_err_pp": round(float(err.quantile(0.95)), 5),
            "median_rel_err_pct": round(
                float(100 * (err / merged["vci"].abs()).median()), 3
            ),
        }

    full = [f"{y}-Q{q}" for y in range(2018, 2027) for q in range(1, 5)][:35]
    window = mas[mas["period"].isin(full)]
    have = window.groupby("period")["ticker"].nunique()
    out["coverage"] = {
        "quarters_with_all_22_banks": int((have == 22).sum()),
        "quarters_below_22": have[have < 22].to_dict(),
        "banks_at_2021Q2": int(have.get("2021-Q2", 0)),
    }
    out["yiea_vs_derived"] = _compare_yield()
    return out


def _compare_yield():
    path = "data/interest_rates/bank_earning_asset_yield_quarterly.csv"
    if not os.path.exists(path):
        return {"note": "chua co file suy ra de doi chieu"}
    derived = pd.read_csv(path, encoding="utf-8-sig")[
        ["ticker", "period", "earning_asset_yield_ttm_percent"]
    ].rename(columns={"earning_asset_yield_ttm_percent": "derived"})
    mas = pd.read_csv(TTM_PATH, encoding="utf-8-sig")[
        ["ticker", "period", "earning_asset_yield_ttm_percent"]
    ].rename(columns={"earning_asset_yield_ttm_percent": "published"})
    merged = derived.merge(mas, on=["ticker", "period"]).dropna()
    if merged.empty:
        return {"n": 0}
    gap = merged["derived"] - merged["published"]
    return {
        "n": len(merged),
        "pearson_r": round(float(merged["derived"].corr(merged["published"])), 4),
        "median_gap_pp": round(float(gap.median()), 4),
        "median_abs_gap_pp": round(float(gap.abs().median()), 4),
        "share_within_0p25pp": round(float((gap.abs() < 0.25).mean()), 4),
    }


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--validate" in sys.argv:
        print(json.dumps(validate(), indent=2, ensure_ascii=False, default=str))
    else:
        report = {}
        if "--build-only" not in sys.argv:
            report["fetch"] = fetch()
        report["build"] = build()
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
