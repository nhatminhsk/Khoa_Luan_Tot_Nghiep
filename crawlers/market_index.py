"""Chi so thi truong (VN-Index, VN30) -- nhan to thi truong cho mo hinh.

Kho da co gia OHLCV cua 22 ngan hang nhung chua co gi de tach phan bien dong
CHUNG cua thi truong ra khoi phan rieng cua tung ngan hang. Khong co no thi moi
so sanh loi suat co phieu giua cac ngan hang deu lan voi xu the chung.

Do duoc ngay 09/09/2026, ca hai deu lui duoc ve 2015:
    VNINDEX  2.915 phien  2015-01-05 -> 2026-09-09   (trung khop cua so gia co phieu)
    VN30     2.915 phien  2015-01-05 -> 2026-09-09

Hai chuoi khac nhau o ca 2.915 phien (VNINDEX dong 1.827,12 vs VN30 1.967,64 tai
09/09/2026) -- kiem lai vi hai file co cung so dong nen de nhin nham la trung.
Do dai phu thuoc tham so `start`: hoi voi start=2018 thi VN30 chi tra 2.166
phien, de tuong nham la chuoi bat dau tu 2018.

Do phu: **0 phien nao co trong du lieu gia ngan hang ma thieu o chi so**.

Dung chung quy uoc voi crawlers/price.py: moi lan chay **lam moi cua so 7 ngay
gan nhat** chu khong chi noi them. Ly do da ghi trong price.py -- dong cua phien
moi nhat thuong duoc chup giua phien, va VCI con dieu chinh nhe khoi luong vai
ngay sau.

`Listing().all_indices()` liet ke 29 chi so neu can them (VNMID, VNSML, VN100,
VNALL, cac chi so nganh...). O day chi lay hai cai can cho mo hinh.

Chay:
    python -m crawlers.market_index
    python -m crawlers.market_index --backfill     # keo lai tu 2015
    python -m crawlers.market_index --validate
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

OUT = Path("data/market")
LOG_PATH = "crawl_log.txt"
COLUMNS = ["time", "open", "high", "low", "close", "volume"]

INDICES = ["VNINDEX", "VN30"]
BACKFILL_START = "2015-01-01"
TIME_SUFFIX = " 07:00:00"

REFRESH_DAYS = 7
SECONDS_BETWEEN_CALLS = 2.0
MAX_ATTEMPTS = 3


def _log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")


def path_for(symbol):
    return OUT / f"{symbol}.csv"


def _fetch(symbol, start, end):
    from vnstock_data import Quote

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            frame = Quote(symbol=symbol, source="VCI").history(
                start=start, end=end, interval="1D"
            )
            if not isinstance(frame, pd.DataFrame):
                raise TypeError(f"expected DataFrame, got {type(frame).__name__}")
            return frame
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < MAX_ATTEMPTS:
                time.sleep(5 * attempt)
    raise RuntimeError(f"{symbol}: that bai sau {MAX_ATTEMPTS} lan: {last_error}")


def _normalise(frame):
    out = frame.copy()
    out["time"] = pd.to_datetime(out["time"]).dt.strftime("%Y-%m-%d") + TIME_SUFFIX
    for col in COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[COLUMNS]


def update_symbol(symbol, refresh_days=REFRESH_DAYS, backfill=False):
    path = path_for(symbol)
    existing = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=COLUMNS)

    end = date.today()
    if backfill or existing.empty:
        start = BACKFILL_START
    else:
        # Lui ve truoc phien cuoi da luu (khong chi `refresh_days` ngay): neu may tat hay task
        # khong chay nhieu ngay thi van lay du phan bi thieu. Truoc 01/10/2026 chi lui 7 ngay
        # nen VN-Index tung hong 10/09 -> 23/09.
        last = date.fromisoformat(str(existing["time"].max())[:10])
        start = min(end - timedelta(days=refresh_days), last - timedelta(days=1)).isoformat()
    fresh = _normalise(_fetch(symbol, start, end.isoformat()))

    before = len(existing)
    combined = pd.concat([existing, fresh], ignore_index=True)
    # Lam moi: dong moi thang dong cu o cung mot phien.
    combined = combined.drop_duplicates(subset=["time"], keep="last")
    combined = combined.sort_values("time").reset_index(drop=True)

    corrected = 0
    if before:
        old_idx = existing.set_index("time")
        new_idx = combined.set_index("time")
        shared = old_idx.index.intersection(new_idx.index)
        if len(shared):
            diff = (old_idx.loc[shared, "close"].astype(float)
                    != new_idx.loc[shared, "close"].astype(float))
            corrected = int(diff.sum())

    OUT.mkdir(parents=True, exist_ok=True)
    combined.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\r\n")
    return {
        "symbol": symbol,
        "rows": len(combined),
        "added": len(combined) - before,
        "corrected": corrected,
        "range": (combined["time"].min()[:10], combined["time"].max()[:10]),
    }


def build(backfill=False):
    results, failed = [], []
    for symbol in INDICES:
        try:
            results.append(update_symbol(symbol, backfill=backfill))
        except Exception as exc:
            failed.append((symbol, f"{type(exc).__name__}: {exc}"[:110]))
        time.sleep(SECONDS_BETWEEN_CALLS)
    _log(
        f"market_index: {len(results)}/{len(INDICES)} chi so ok, "
        + ", ".join(f"{r['symbol']} {r['rows']} phien (+{r['added']}, "
                    f"{r['corrected']} sua)" for r in results)
        + (f", loi: {failed}" if failed else "")
    )
    return {"indices": results, "failed": failed, "dir": str(OUT)}


def validate():
    res = {}
    for symbol in INDICES:
        path = path_for(symbol)
        if not path.exists():
            res[symbol] = {"error": "chua co file"}
            continue
        frame = pd.read_csv(path)
        frame["date"] = pd.to_datetime(frame["time"]).dt.date
        close = frame["close"].astype(float)
        ret = close.pct_change()
        res[symbol] = {
            "rows": len(frame),
            "range": (str(frame["date"].min()), str(frame["date"].max())),
            "duplicate_dates": int(frame["date"].duplicated().sum()),
            "non_positive_close": int((close <= 0).sum()),
            "abs_return_over_10pct": int((ret.abs() > 0.10).sum()),
            "annualised_vol_percent": round(float(ret.std() * (252 ** 0.5) * 100), 2),
        }

    # Chi so phai phu duoc cac phien co trong du lieu gia ngan hang.
    bank_path = Path("data/price/VCB.csv")
    index_path = path_for("VNINDEX")
    if bank_path.exists() and index_path.exists():
        bank = pd.read_csv(bank_path)
        index = pd.read_csv(index_path)
        bank_days = set(pd.to_datetime(bank["time"]).dt.date)
        index_days = set(pd.to_datetime(index["time"]).dt.date)
        missing = sorted(bank_days - index_days)
        res["coverage_vs_bank_prices"] = {
            "bank_sessions": len(bank_days),
            "index_sessions": len(index_days),
            "bank_days_missing_from_index": len(missing),
            "examples": [str(d) for d in missing[:5]],
        }
    return res


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--validate" in sys.argv:
        print(json.dumps(validate(), indent=2, ensure_ascii=False, default=str))
    else:
        print(json.dumps(build(backfill="--backfill" in sys.argv),
                         indent=2, ensure_ascii=False, default=str))
