from __future__ import annotations

import difflib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("data/vnstock_financial")
RAW_VCI = ROOT / "raw_vci"
ID_MAP = ROOT / "vci_id_map.csv"
LOG_PATH = "crawl_log.txt"

TICKERS = [
    "ACB", "BAB", "BID", "BVB", "CTG", "EIB", "HDB", "LPB", "MBB", "MSB", "NAB",
    "NVB", "OCB", "PGB", "SHB", "SSB", "STB", "TCB", "TPB", "VCB", "VIB", "VPB",
]
SECTIONS = ("balance_sheet", "income_statement", "cash_flow", "ratio", "note")
# Nguong khop: ty le o trung so tren cac o ca hai ben cung co. Duoi nguong nay coi la khong ghep duoc.
MIN_SHARE = 0.95
MIN_CELLS = 8


def _log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")


def _old_path(ticker, section):
    if section == "note":
        return ROOT / "raw_note" / f"{ticker}_note_quarter.csv"
    return ROOT / "raw" / f"{ticker}_{section}_quarter.csv"


def fetch(tickers=None, sleep=1.3):
    from vnstock_data.explorer.vci.financial import Finance

    tickers = tickers or TICKERS
    RAW_VCI.mkdir(parents=True, exist_ok=True)
    ok, failed = [], []
    for ticker in tickers:
        try:
            fin = Finance(ticker, period="quarter")
            for section in SECTIONS:
                df = fin._get_raw_data(section, "quarter")
                time.sleep(sleep)
                if df.empty:
                    raise ValueError(f"{section} rong")
                df[["period", "id", "name_vi", "value"]].to_csv(
                    RAW_VCI / f"{ticker}_{section}.csv", index=False, encoding="utf-8-sig")
            time.sleep(sleep)
            ok.append(ticker)
        except Exception as exc:  # nguon co the tu choi tung ma
            failed.append((ticker, f"{type(exc).__name__}: {exc}"[:160]))
    _log(f"vci_raw fetch: {len(ok)}/{len(tickers)} ma ok, {len(failed)} loi -> {RAW_VCI}")
    return {"ok": len(ok), "failed": failed}


def _read_raw(section, tickers=None):
    frames = []
    for ticker in tickers or TICKERS:
        df = pd.read_csv(RAW_VCI / f"{ticker}_{section}.csv", encoding="utf-8-sig", dtype={"period": str})
        df["ticker"] = ticker
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    return out


def _read_old(section, tickers=None):
    frames = []
    for ticker in tickers or TICKERS:
        df = pd.read_csv(_old_path(ticker, section), encoding="utf-8-sig", dtype={"period": str}, low_memory=False)
        df["ticker"] = ticker
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    return out


def _norm_name(name):
    text = re.sub(r"^[\s ‣•◦\-]+", "", str(name)).strip().lower()
    return re.sub(r"^([ivxlcdm]+\.|[a-z]\.|\d+(\.\d+)*\.?)\s*", "", text)


def _wide(frame):
    return frame.pivot_table(index=["ticker", "period"], columns="id", values="value", aggfunc="first")


def _find_pair(a, known, b, new_ids):
    target, rows = a[known], np.nan_to_num(b[known])
    tol = np.maximum(1.5, 1e-4 * np.abs(target))[:, None]
    active = np.where((rows != 0).mean(axis=0) >= 0.1)[0]
    best, best_share = None, 0.0
    for i in active:
        share = (np.abs(target[:, None] - rows[:, [i]] - rows[:, active]) <= tol).mean(axis=0)
        share[active == i] = 0
        j = int(share.argmax())
        if share[j] > best_share:
            best, best_share = "+".join(sorted((new_ids[i], new_ids[active[j]]))), float(share[j])
    return best, best_share


def build_map():
    rows = []
    for section in SECTIONS:
        old, raw = _read_old(section), _read_raw(section)
        old_w, raw_w = _wide(old), _wide(raw)
        keys = old_w.index.intersection(raw_w.index)
        old_w, raw_w = old_w.loc[keys], raw_w.loc[keys]
        names_old = old.drop_duplicates("id", keep="last").set_index("id")["name"].map(_norm_name)
        names_raw = raw.drop_duplicates("id", keep="last").set_index("id")["name_vi"].map(_norm_name)
        new_ids = np.array(raw_w.columns)
        b = raw_w.to_numpy(dtype=float)
        for old_id in old_w.columns:
            a = old_w[old_id].to_numpy(dtype=float)
            known = np.isfinite(a) & (a != 0)
            if known.sum() < 1:
                rows.append(dict(section=section, old_id=old_id, raw_id=None, factor=None, n_old=0, n=0, share=None,
                                 status="khong_co_so", tied=None))
                continue
            scale = np.maximum(np.abs(a), 1e-12)[:, None]
            # bao cao tinh bang dong: lech <= 1,5 dong; ty so: lech tuong doi 1e-4
            tol = np.maximum(1.5 if section != "ratio" else 0.0, 1e-4 * scale)
            common = known[:, None] & np.isfinite(b)
            best = []
            for factor in (1.0, -1.0):
                hit = (np.abs(a[:, None] - factor * b) <= tol) & common
                n = common.sum(axis=0)
                share = np.divide(hit.sum(axis=0), n, out=np.zeros(b.shape[1]), where=n > 0)
                best.append((factor, n, share))
            n_need = min(MIN_CELLS, known.sum())
            cand = []
            for factor, n, share in best:
                for j in np.where((share >= MIN_SHARE) & (n >= n_need))[0]:
                    cand.append((float(share[j]), int(n[j]), factor, new_ids[j]))
            if not cand and section == "note":
                pair, share = _find_pair(a, known, b, new_ids)
                if share >= MIN_SHARE:
                    rows.append(dict(section=section, old_id=old_id, raw_id=pair, factor=1.0, n_old=int(known.sum()),
                                     n=int(known.sum()), share=round(share, 4), status="ghep", tied=""))
                    continue
            if not cand:
                top = max(((float(s.max()), f) for f, _, s in best), key=lambda x: x[0])
                rows.append(dict(section=section, old_id=old_id, raw_id=None, factor=None, n_old=int(known.sum()), n=0,
                                 share=round(top[0], 4), status="khong_ghep_duoc", tied=None))
                continue
            top_share = max(c[0] for c in cand)
            tied = [c for c in cand if c[0] >= top_share - 0.002]
            target = names_old.get(old_id, "")
            pick = max(tied, key=lambda c: (difflib.SequenceMatcher(None, target, names_raw.get(c[3], "")).ratio(), c[1]))
            rows.append(dict(section=section, old_id=old_id, raw_id=pick[3], factor=pick[2], n_old=int(known.sum()),
                             n=pick[1], share=round(pick[0], 4), status="ghep",
                             tied="|".join(sorted(c[3] for c in tied if c[3] != pick[3]))))
    out = pd.DataFrame(rows)
    out.to_csv(ID_MAP, index=False, encoding="utf-8-sig")
    done = out[out["status"] == "ghep"]
    _log(f"vci_raw map: ghep {len(done)}/{len(out)} ma cu, {int((out['status'] == 'khong_ghep_duoc').sum())} khong ghep duoc")
    return {"status": {f"{a}/{b}": int(n) for (a, b), n in out.groupby(["section", "status"]).size().items()},
            "share_min": float(done["share"].min()), "tied": int((done["tied"].fillna("") != "").sum())}


def _mapped(section, period=None):
    id_map = pd.read_csv(ID_MAP, encoding="utf-8-sig")
    id_map = id_map[(id_map["section"] == section) & (id_map["status"] == "ghep")]
    id_map = id_map.assign(raw_id=id_map["raw_id"].str.split("+")).explode("raw_id")  # ma tong hai ma tho
    raw = _read_raw(section)
    if period:
        raw = raw[raw["period"] == period]
    out = raw.merge(id_map[["raw_id", "old_id", "factor"]], left_on="id", right_on="raw_id")
    out["value"] = out["value"] * out["factor"]
    out = out.groupby(["ticker", "period", "old_id"], as_index=False)["value"].sum(min_count=1)
    return out.rename(columns={"old_id": "id"})


def add(period):
    added, skipped, empty = 0, 0, []
    for section in SECTIONS:
        values = _mapped(section, period).drop_duplicates(["ticker", "id"]).set_index(["ticker", "id"])["value"]
        for ticker in TICKERS:
            path = _old_path(ticker, section)
            df = pd.read_csv(path, encoding="utf-8-sig", dtype={"period": str}, low_memory=False)
            if period in set(df["period"]):
                skipped += 1
                continue
            quarters = sorted(p for p in df["period"].unique() if "-Q" in p)
            row = df[df["period"] == quarters[-1]].copy()
            row["period"] = period
            row["value"] = [values.get((ticker, i), np.nan) for i in row["id"]]
            if row["value"].notna().sum() == 0:
                empty.append(f"{ticker}/{section}")
                continue
            kw = {"lineterminator": "\r\n"} if section == "note" else {}
            pd.concat([row, df], ignore_index=True).to_csv(path, index=False, encoding="utf-8-sig", **kw)
            added += 1
    _log(f"vci_raw add {period}: them {added} file, bo qua {skipped}, rong {len(empty)}")
    return {"period": period, "files_added": added, "skipped": skipped, "empty": empty}


def report(path=None):
    frames = []
    for section in SECTIONS:
        new = _mapped(section)
        old = _read_old(section)[["ticker", "period", "id", "value"]]
        m = old.merge(new, on=["ticker", "period", "id"], suffixes=("_luu", "_vci"))
        a, b = m["value_luu"], m["value_vci"]
        tol = (1e-4 * a.abs()).clip(lower=1.5 if section != "ratio" else 0)
        changed = ((a - b).abs() > tol) | (a.isna() != b.isna())
        frames.append(m[changed].assign(section=section, n_chung=len(m)))
    out = pd.concat(frames, ignore_index=True)
    if path:
        out.to_csv(path, index=False, encoding="utf-8-sig")
    return {"cells_changed": len(out), "by_section": out.groupby("section").size().to_dict(),
            "by_period_top": out.groupby("period").size().sort_values(ascending=False).head(8).to_dict()}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--fetch" in sys.argv:
        print(json.dumps(fetch(), indent=2, ensure_ascii=False))
    elif "--map" in sys.argv:
        print(json.dumps(build_map(), indent=2, ensure_ascii=False, default=str))
    elif "--add" in sys.argv:
        print(json.dumps(add(sys.argv[sys.argv.index("--add") + 1]), indent=2, ensure_ascii=False))
    elif "--report" in sys.argv:
        print(json.dumps(report("data/vnstock_financial/vci_sua_lich_su.csv"), indent=2, ensure_ascii=False, default=str))
