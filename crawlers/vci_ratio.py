from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("data/vnstock_financial/raw")
RAW_NOTE = Path("data/vnstock_financial/raw_note")

# Quy binh thuong co 0-2 chi tieu trung quy truoc, quy chep lai co 21-22 (do
# 15/09/2026 tren 628 NH-quy). 10 nam giua hai nhom, xa ca hai phia.
STALE_MIN_IDS = 10
# Bao phu o t+1 phai gan thuyet minh quy t hon quy t+1 it nhat 2 lan.
SHIFT_RATIO = 0.5

NPL_PARTS = ["NT_BS_SUBSTANDARD", "NT_BS_DOUBTFUL", "NT_BS_BAD"]
NPL_TOTAL = "NT_BS_LOANS_AND_ADVANCES_BY_GRADING"
PROVISION = "BS_PROVISION_LOANS_TO_CUSTOMERS"


def _qkey(period: str) -> int:
    return int(period[:4]) * 4 + int(period[-1])


def _next_period(period: str) -> str:
    year, quarter = int(period[:4]), int(period[-1])
    return f"{year + 1}-Q1" if quarter == 4 else f"{year}-Q{quarter + 1}"


@lru_cache(maxsize=None)
def _note_evidence(ticker: str) -> pd.DataFrame:
    note_path = RAW_NOTE / f"{ticker}_note_quarter.csv"
    bs_path = RAW / f"{ticker}_balance_sheet_quarter.csv"
    if not note_path.exists() or not bs_path.exists():
        return pd.DataFrame(columns=["npl", "coverage"])
    note = pd.read_csv(note_path, encoding="utf-8-sig", dtype={"period": str})
    note["value"] = pd.to_numeric(note["value"], errors="coerce")
    grade = note[note["id"].isin(NPL_PARTS + [NPL_TOTAL])].pivot_table(
        index="period", columns="id", values="value", aggfunc="first")
    for col in NPL_PARTS + [NPL_TOTAL]:
        if col not in grade:
            grade[col] = np.nan
    amount = grade[NPL_PARTS].sum(axis=1, min_count=3)
    bs = pd.read_csv(bs_path, encoding="utf-8-sig", dtype={"period": str})
    bs["value"] = pd.to_numeric(bs["value"], errors="coerce")
    provision = bs[bs["id"] == PROVISION].groupby("period")["value"].last()
    return pd.DataFrame({
        "npl": amount / grade[NPL_TOTAL].replace(0, np.nan),
        "coverage": provision.abs() / amount.replace(0, np.nan),
    })


def _shift_evidence(ticker, wide, t, t_next):
    note = _note_evidence(ticker)
    if t not in note.index or t_next not in note.index:
        return False, {"reason": "thieu thuyet minh de doi chieu"}

    def gap(vci_id, note_col, period, sign=1.0):
        if vci_id not in wide.columns:
            return np.nan
        return abs(sign * wide.at[t_next, vci_id] - note.at[period, note_col])

    npl_t, npl_next = gap("RT_BANK_NPL", "npl", t), gap("RT_BANK_NPL", "npl", t_next)
    cov_t = gap("RT_BANK_NPL_COVERAGE", "coverage", t, -1.0)
    cov_next = gap("RT_BANK_NPL_COVERAGE", "coverage", t_next, -1.0)
    evidence = {
        "npl_gap_to_t_pp": round(npl_t * 100, 4),
        "npl_gap_to_next_pp": round(npl_next * 100, 4),
        "coverage_gap_to_t_pp": round(cov_t * 100, 3),
        "coverage_gap_to_next_pp": round(cov_next * 100, 3),
    }
    if not np.isfinite([npl_t, npl_next, cov_t, cov_next]).all():
        evidence["reason"] = "thieu NPL/bao phu o mot trong hai quy"
        return False, evidence
    shifted = npl_t <= npl_next and cov_t <= SHIFT_RATIO * cov_next
    return bool(shifted), evidence


def _period(key: int) -> str:
    year, quarter = divmod(key - 1, 4)
    return f"{year}-Q{quarter + 1}"


@lru_cache(maxsize=None)
def _repair(ticker: str):
    path = RAW / f"{ticker}_ratio_quarter.csv"
    raw = pd.read_csv(path, encoding="utf-8-sig", dtype={"period": str})
    raw["value"] = pd.to_numeric(raw["value"], errors="coerce")
    quarterly = raw["period"].str.match(r"^\d{4}-Q[1-4]$", na=False)
    wide = raw[quarterly].pivot_table(
        index="period", columns="id", values="value", aggfunc="last")
    keys = sorted(_qkey(p) for p in wide.index)
    # Chi tieu tinh theo gia thi truong va CASA: VCI van tinh dung quy, khong bao
    # gio nam trong nhom bi chep (do tren ca 20 dong chep lai).
    movable = [c for c in wide.columns
               if not (c.startswith("RT_VALUE_") or c == "RT_BANK_CASA")]

    repairs = []
    blanked = set()
    for key in range(keys[0] + 1, keys[-1] + 1):
        t, prev, t_next = _period(key), _period(key - 1), _period(key + 1)
        if t in blanked:
            continue

        if t in wide.index and prev in wide.index:
            # Dang 1: quy t chep nguyen quy t-1.
            a, b = wide.loc[prev], wide.loc[t]
            usable = a.notna() & b.notna() & (a != 0) & (b != 0)
            ids = list(a[usable & (a == b)].index)
            if len(ids) < STALE_MIN_IDS:
                continue
            kind, source = "chep lai", prev
        elif t not in wide.index and t_next in wide.index:
            # Dang 2: quy t trong, quy t+1 co the dang mang so cua t (BAB, BVB
            # 2021-Q4). Chi chuyen khi thuyet minh xac nhan; o 2021-Q2 thi khong.
            ids = [c for c in movable if pd.notna(wide.at[t_next, c])]
            kind, source = "trong", None
        else:
            continue

        shifted, evidence = False, {"reason": f"khong co quy {t_next}"}
        if t_next in wide.index:
            shifted, evidence = _shift_evidence(ticker, wide, t, t_next)
        if kind == "trong" and not shifted:
            continue
        if shifted:
            if t not in wide.index:
                wide.loc[t] = np.nan
            wide.loc[t, ids] = wide.loc[t_next, ids].to_numpy()
            wide.loc[t_next, ids] = np.nan
            blanked.add(t_next)
        else:
            wide.loc[t, ids] = np.nan
        repairs.append({
            "ticker": ticker, "stale_period": t, "kind": kind, "copied_from": source,
            "n_ids": len(ids),
            "action": f"lay {t_next} lam {t}, de trong {t_next}" if shifted
                      else f"de trong {t}",
            **evidence,
        })

    long = wide.stack(future_stack=True).rename("value_fixed").reset_index()
    out = raw.merge(long, on=["period", "id"], how="left")
    out.loc[quarterly, "value"] = out.loc[quarterly, "value_fixed"]
    out = out.drop(columns="value_fixed")

    # Quy trong duoc lap bang so chuyen ve: tao dong moi theo khuon cua quy t+1.
    added = [r for r in repairs if r["kind"] == "trong"]
    if added:
        frames = [out]
        for r in added:
            t, t_next = r["stale_period"], _next_period(r["stale_period"])
            template = raw[raw["period"] == t_next].copy()
            template["period"] = t
            template["value"] = template["id"].map(wide.loc[t])
            frames.append(template)
        out = pd.concat(frames, ignore_index=True)
    return out, repairs


def read(path) -> pd.DataFrame:
    ticker = os.path.basename(str(path)).split("_")[0]
    frame, _ = _repair(ticker)
    return frame.copy()


def repairs(tickers=None) -> pd.DataFrame:
    if tickers is None:
        tickers = sorted(p.name.split("_")[0] for p in RAW.glob("*_ratio_quarter.csv"))
    rows = []
    for ticker in tickers:
        rows.extend(_repair(ticker)[1])
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pd.set_option("display.width", 250)
    table = repairs()
    if table.empty:
        print("khong co quy nao bi chep lai hay lech quy")
    else:
        print(f"{len(table)} NH-quy loi ({(table['kind'] == 'chep lai').sum()} chep lai, "
              f"{(table['kind'] == 'trong').sum()} trong roi lech quy), "
              f"{table['action'].str.startswith('lay').sum()} chuyen duoc so that ve dung quy")
        print(table.to_string(index=False))
