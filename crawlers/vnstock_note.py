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

RAW_DIR = "data/vnstock_financial/raw_note"
OUT_PATH = "data/credit/bank_asset_quality_quarterly.csv"
LONG_PATH = "data/vnstock_financial/note_long.csv"
LOG_PATH = "crawl_log.txt"

GRADE = {
    "NT_BS_CURRENT": "loans_g1_vnd",
    "NT_BS_SPECIAL_MENTIONED": "loans_g2_vnd",
    "NT_BS_SUBSTANDARD": "loans_g3_vnd",
    "NT_BS_DOUBTFUL": "loans_g4_vnd",
    "NT_BS_BAD": "loans_g5_vnd",
    "NT_BS_LOANS_AND_ADVANCES_BY_GRADING": "loans_by_grade_total_vnd",
}
DEPOSIT = {
    "NT_BS_CURRENT_DEPOSITS": "deposits_current_vnd",
    "NT_BS_TERM_DEPOSITS": "deposits_term_vnd",
    "NT_BS_DEPOSITS_BY_TYPE_OF_DEPOSITS": "deposits_by_type_total_vnd",
    "NT_BS_DEPOSITS_BY_CURRENCY": "deposits_by_currency_total_vnd",
    "NT_BS_DEPOSITS_BY_CURRENCY_DENOMINATED_IN_VND": "deposits_vnd_only_vnd",
}
MATURITY = {
    "NT_BS_SHORT_TERM_LOANS": "loans_short_vnd",
    "NT_BS_MEDIUM_TERM_LOANS": "loans_medium_vnd",
    "NT_BS_LONG_TERM_LOANS": "loans_long_vnd",
    "NT_BS_LOANS_AND_ADVANCES_BY_MATURITY": "loans_by_maturity_total_vnd",
}
INCOME = {"NT_IS_DEPOSIT_INTEREST_EXPENSES": "deposit_interest_expense_vnd"}

KEEP = {**GRADE, **DEPOSIT, **MATURITY, **INCOME}
QUARTER_END = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}

# O nguon VCI ghi sai, da doi chieu voi BCTC goc (static2.vietstock.vn). Chi ap khi
# gia tri tho van dung bang `wrong` - neu VCI da sua nguon thi bo qua va ghi log,
# khong ghi de len so moi. raw_note/ va note_long.csv giu nguyen ban sao cua nguon.
# Tien gui VND = tong - (vang, ngoai te), cung dinh nghia VCI dung o cac quy khac.
CORRECTIONS = {
    ("STB", "2026-Q2", "NT_BS_DEPOSITS_BY_CURRENCY_DENOMINATED_IN_VND"): {
        "wrong": 17_312_686e6,
        "value": 631_099_200e6,
        "evidence": "BCTC hop nhat Q2/2026, thuyet minh 9 (trang 27): tong 647.939.224 "
                    "trieu; KKH bang vang, ngoai te 6.930.832 + CKH bang vang va ngoai te "
                    "9.909.192 = 16.840.024 -> VND 631.099.200 (97,40%). VCI ghi 17.312.686 "
                    "(2,67%), cac quy lien ke 97,2-97,4%",
        "source": "https://static2.vietstock.vn/data/HOSE/2026/BCTC/VN/QUY%202/"
                  "STB_Baocaotaichinh_Q2_2026_Hopnhat.pdf",
        "reviewed": "2026-09-15",
    },
    ("BAB", "2022-Q1", "NT_BS_DEPOSITS_BY_CURRENCY_DENOMINATED_IN_VND"): {
        "wrong": 95_140_873e6,
        "value": 94_921_961e6,
        "evidence": "BCTC hop nhat Q1/2022, thuyet minh 15 (trang 24): tong 95.031.417 "
                    "trieu; ngoai te 13.317 (KKH) + 96.125 (tiet kiem CKH) + 14 (ky quy) "
                    "= 109.456 -> VND 94.921.961 (99,88%). VCI ghi 95.140.873 = tong "
                    "CONG ngoai te, vuot tong tien gui",
        "source": "https://static2.vietstock.vn/data/HNX/2022/BCTC/VN/QUY%201/"
                  "BAB_Baocaotaichinh_Q1_2022_Hopnhat.pdf",
        "reviewed": "2026-09-15",
    },
    ("PGB", "2022-Q3", "NT_BS_DEPOSITS_BY_CURRENCY_DENOMINATED_IN_VND"): {
        "wrong": 14_312_507e6,
        "value": 28_534_390e6,
        "evidence": "BCTC Q3/2022 ban dinh chinh, thuyet minh 18 (trang 25): tong 28.937.613 "
                    "trieu; KKH bang ngoai te, vang 190.702 + CKH bang ngoai te, vang 212.521 "
                    "= 403.223 -> VND 28.534.390 (98,61%). VCI ghi 14.312.507 (49,46%), hai "
                    "quy lien ke 98,66% va 98,52%",
        "source": "https://www.pgbank.com.vn/uploads/5102022/"
                  "8108aeb3-7d5b-407a-bd2a-e2cda349586c.pdf",
        "reviewed": "2026-09-15",
    },
    # Cho vay theo doi tuong khach hang: VCI chuyen nham 10.000 ty tu dong ca nhan sang dong
    # cong ty TNHH + co phan (tong giu nguyen). Ty trong ca nhan 22,8% -> 31,1%.
    ("MSB", "2022-Q4", "NT_BS_INDIVIDUALS"): {
        "wrong": 27_563_927e6,
        "value": 37_563_927e6,
        "evidence": "BCTC hop nhat kiem toan 2022, thuyet minh 10.3 (trang 37): ca nhan "
                    "37.563.927 trieu (31,14%), tong 120.643.542. BCTC 2023 cot dau nam ghi "
                    "cung so. VCI ghi 27.563.927; hai quy lien ke 29,5% va 30,0%",
        "source": "https://static2.vietstock.vn/data/HOSE/2022/BCTC/VN/NAM/"
                  "MSB_Baocaotaichinh_2022_Kiemtoan_Hopnhat.pdf",
        "reviewed": "2026-10-08",
    },
    ("MSB", "2022-Q4", "NT_BS_LIMITED_AND_JOINT_STOCK_COMPANIES"): {
        "wrong": 88_936_306e6,
        "value": 78_936_306e6,
        "evidence": "Cung bang 10.3: cong ty TNHH tu nhan 29.215.085 + cong ty co phan khac "
                    "49.721.221 = 78.936.306 trieu. VCI ghi 88.936.306 (thua dung 10.000.000 "
                    "trieu ma dong ca nhan thieu)",
        "source": "https://static2.vietstock.vn/data/HOSE/2022/BCTC/VN/NAM/"
                  "MSB_Baocaotaichinh_2022_Kiemtoan_Hopnhat.pdf",
        "reviewed": "2026-10-08",
    },
}


def _apply_corrections(raw):
    raw = raw.copy()
    raw["value"] = pd.to_numeric(raw["value"], errors="coerce")
    applied, skipped = [], []
    ids = set(raw["id"])
    for (ticker, period, item), fix in CORRECTIONS.items():
        if item not in ids:
            continue
        mask = ((raw["ticker"] == ticker) & (raw["period"].astype(str) == period)
                & (raw["id"] == item))
        current = raw.loc[mask, "value"]
        if current.empty:
            skipped.append(f"{ticker} {period} {item}: khong con o nay")
        elif not np.isclose(current, fix["wrong"], rtol=0, atol=1e6).all():
            skipped.append(f"{ticker} {period} {item}: nguon da doi thanh "
                           f"{current.iloc[0]:,.0f}, khong ghi de")
        else:
            raw.loc[mask, "value"] = fix["value"]
            applied.append(f"{ticker} {period} {item}")
    return raw, applied, skipped


def _log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")


def _safe_div(num, den):
    den = den.replace(0, np.nan)
    return 100 * num / den


def fetch(tickers=None, sleep=0.3):
    import vnstock_data as vd

    tickers = tickers or TICKERS
    os.makedirs(RAW_DIR, exist_ok=True)
    ok, failed = [], []
    for ticker in tickers:
        try:
            finance = vd.Finance(
                source="VCI", symbol=ticker, period="quarter", get_all=True
            )
            df = finance.note(period="quarter", lang="vi", dropna=False)
            # Goi mien phi tra ma tho nob1.. (xem vci_raw.py): build() khong doc duoc, khong ghi de file cu.
            if not df["id"].astype(str).str.startswith("NT_").any():
                raise ValueError("thuyet minh mang ma tho, giu file cu")
            df.to_csv(
                f"{RAW_DIR}/{ticker}_note_quarter.csv",
                index=False, encoding="utf-8-sig", lineterminator="\r\n",
            )
            ok.append(ticker)
        except Exception as exc:
            failed.append((ticker, f"{type(exc).__name__}: {exc}"[:120]))
        time.sleep(sleep)
    _log(
        f"vnstock_note fetch: {len(ok)}/{len(tickers)} ma ok, {len(failed)} loi "
        f"-> {RAW_DIR}"
    )
    return {"ok": len(ok), "failed": failed}


def _load_raw():
    frames = []
    for path in sorted(glob.glob(f"{RAW_DIR}/*_note_quarter.csv")):
        ticker = os.path.basename(path).split("_")[0]
        df = pd.read_csv(path, encoding="utf-8-sig")
        df["ticker"] = ticker
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"Chua co file raw nao trong {RAW_DIR}.")
    return pd.concat(frames, ignore_index=True)


def build_long(raw=None, write=True):
    raw = _load_raw() if raw is None else raw
    cols = ["ticker", "period", "id", "name", "order", "level", "unit", "value"]
    out = raw[[c for c in cols if c in raw.columns]].copy()
    out["period"] = out["period"].astype(str)
    out = out.sort_values(["ticker", "period", "order"], kind="stable")
    if write:
        out.to_csv(LONG_PATH, index=False, encoding="utf-8-sig")
    filled = out[out["value"].notna() & (out["value"] != 0)]
    return {"rows": len(out), "ids": int(out["id"].nunique()),
            "ids_with_data": int(filled["id"].nunique()), "path": LONG_PATH}


def build(write=True):
    raw = _load_raw()
    report_long = build_long(raw, write=write)
    raw = raw[raw["id"].isin(KEEP)]
    raw = raw[raw["period"].astype(str).str.match(r"^\d{4}-Q[1-4]$")]
    raw, applied, skipped = _apply_corrections(raw)
    if write and (applied or skipped):
        _log(f"vnstock_note CORRECTIONS: sua {len(applied)} o {applied}; "
             f"bo qua {len(skipped)} {skipped}")

    wide = raw.pivot_table(
        index=["ticker", "period"], columns="id", values="value", aggfunc="first"
    ).rename(columns=KEEP).reset_index()
    for col in KEEP.values():
        if col not in wide.columns:
            wide[col] = np.nan

    npl_amount = wide[["loans_g3_vnd", "loans_g4_vnd", "loans_g5_vnd"]].sum(
        axis=1, min_count=3
    )
    wide["npl_vnd"] = npl_amount
    wide["npl_percent"] = _safe_div(npl_amount, wide["loans_by_grade_total_vnd"])
    wide["loans_g2_percent"] = _safe_div(
        wide["loans_g2_vnd"], wide["loans_by_grade_total_vnd"]
    )
    wide["casa_percent"] = _safe_div(
        wide["deposits_current_vnd"], wide["deposits_by_type_total_vnd"]
    )
    for tenor in ("short", "medium", "long"):
        wide[f"loans_{tenor}_share_percent"] = _safe_div(
            wide[f"loans_{tenor}_vnd"], wide["loans_by_maturity_total_vnd"]
        )
    wide["vnd_deposit_share_percent"] = _safe_div(
        wide["deposits_vnd_only_vnd"], wide["deposits_by_currency_total_vnd"]
    )

    wide["qkey"] = [
        int(p[:4]) * 4 + int(p[-1]) for p in wide["period"]
    ]
    wide = wide.sort_values(["ticker", "qkey"])
    contiguous = (
        wide.groupby("ticker")["qkey"].diff().eq(1).groupby(wide["ticker"])
        .rolling(3, min_periods=3).sum().reset_index(level=0, drop=True).eq(3)
    )
    rolled = (
        wide.groupby("ticker")["deposit_interest_expense_vnd"]
        .rolling(4, min_periods=4).sum().reset_index(level=0, drop=True)
    )
    wide["deposit_interest_expense_ttm_vnd"] = np.where(contiguous, rolled, np.nan)
    avg_dep = (
        wide.groupby("ticker")["deposits_by_type_total_vnd"]
        .rolling(4, min_periods=4).mean().reset_index(level=0, drop=True)
    )
    wide["deposit_cost_implied_ttm_percent"] = np.where(
        contiguous,
        100 * wide["deposit_interest_expense_ttm_vnd"].abs() / avg_dep.replace(0, np.nan),
        np.nan,
    )

    wide["period_end"] = [f"{p[:4]}-{QUARTER_END[p[-1]]}" for p in wide["period"]]
    wide["source"] = "vnstock_data VCI note_quarter"
    wide["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()

    lead = ["period", "period_end", "ticker"]
    ratios = [
        "npl_percent", "loans_g2_percent", "casa_percent",
        "loans_short_share_percent", "loans_medium_share_percent",
        "loans_long_share_percent", "vnd_deposit_share_percent",
        "deposit_cost_implied_ttm_percent",
    ]
    amounts = [c for c in wide.columns if c.endswith("_vnd")]
    out = wide[lead + ratios + amounts + ["source", "retrieved_at_utc"]]
    out = out.sort_values(["period", "ticker"])
    out[ratios] = out[ratios].round(4)

    if write:
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        out.to_csv(OUT_PATH, index=False, encoding="utf-8-sig", lineterminator="\r\n")
        _log(
            f"vnstock_note build: {len(out)} dong, {out['ticker'].nunique()} NH, "
            f"{out['period'].nunique()} quy ({out['period'].min()}.."
            f"{out['period'].max()}), NPL phu "
            f"{out['npl_percent'].notna().sum()} o -> {OUT_PATH}"
        )

    full = [f"{y}-Q{q}" for y in range(2018, 2027) for q in range(1, 5)][:35]
    window = out[out["period"].isin(full)]
    return {
        "rows": len(out),
        "banks": int(out["ticker"].nunique()),
        "quarters": int(out["period"].nunique()),
        "range": (out["period"].min(), out["period"].max()),
        "coverage_2018plus_of_748": {
            col: round(100 * window[col].notna().mean(), 1) for col in ratios
        },
        "banks_at_2021Q2": {
            col: int(window[(window["period"] == "2021-Q2") & window[col].notna()]
                     ["ticker"].nunique())
            for col in ("npl_percent", "casa_percent", "loans_short_share_percent")
        },
        "path": OUT_PATH,
        "note_long": report_long,
        "corrections": {"applied": applied, "skipped": skipped},
    }


def validate():
    out = pd.read_csv(OUT_PATH, encoding="utf-8-sig")
    res = {}

    old_path = "data/credit/bank_credit_quarterly.csv"
    if os.path.exists(old_path):
        old = pd.read_csv(old_path, encoding="utf-8-sig")[
            ["ticker", "period", "npl_percent"]
        ].rename(columns={"npl_percent": "npl_old"})
        merged = out[["ticker", "period", "npl_percent"]].merge(
            old, on=["ticker", "period"]
        ).dropna()
        gap = (merged["npl_percent"] - merged["npl_old"]).abs()
        res["npl_vs_existing"] = {
            "n": len(merged),
            "median_abs_gap_pp": round(float(gap.median()), 5),
            "share_within_0p05": round(float((gap < 0.05).mean()), 4),
            "max_abs_gap_pp": round(float(gap.max()), 4),
            "new_cells_gained": int(
                out["npl_percent"].notna().sum() - len(old.dropna())
            ),
        }

    cof_path = "data/interest_rates/bank_cost_of_funds_quarterly.csv"
    if os.path.exists(cof_path):
        cof = pd.read_csv(cof_path, encoding="utf-8-sig")
        merged = out.merge(cof[["ticker", "period", "cof_ttm_percent"]],
                           on=["ticker", "period"])
        latest = merged[merged["period"] == merged["period"].max()]
        both = merged[["casa_percent", "cof_ttm_percent"]].dropna()
        res["casa_vs_cof"] = {
            "n_all_quarters": len(both),
            "pearson_r_all": round(float(both["casa_percent"].corr(
                both["cof_ttm_percent"])), 4),
            "pearson_r_latest_quarter": round(float(
                latest["casa_percent"].corr(latest["cof_ttm_percent"])), 4),
            "latest_quarter": str(merged["period"].max()),
        }
        implied = merged[
            ["deposit_cost_implied_ttm_percent", "cof_ttm_percent"]
        ].dropna()
        if len(implied):
            res["implied_deposit_cost_vs_cof"] = {
                "n": len(implied),
                "pearson_r": round(float(
                    implied["deposit_cost_implied_ttm_percent"].corr(
                        implied["cof_ttm_percent"])), 4),
                "median_gap_pp": round(float((
                    implied["deposit_cost_implied_ttm_percent"]
                    - implied["cof_ttm_percent"]).median()), 3),
            }

    # Kiem tinh nhat quan noi bo: tong 5 nhom no phai bang tong du no theo chat luong.
    raw = out.dropna(subset=["loans_by_grade_total_vnd"])
    parts = raw[["loans_g1_vnd", "loans_g2_vnd", "loans_g3_vnd",
                 "loans_g4_vnd", "loans_g5_vnd"]].sum(axis=1, min_count=5)
    rel = ((parts - raw["loans_by_grade_total_vnd"]).abs()
           / raw["loans_by_grade_total_vnd"].abs().replace(0, np.nan))
    res["grade_sum_check"] = {
        "n": int(rel.notna().sum()),
        "share_within_0p1pct": round(float((rel < 0.001).mean()), 4),
        "max_rel_gap": round(float(rel.max()), 6),
    }
    return res


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
