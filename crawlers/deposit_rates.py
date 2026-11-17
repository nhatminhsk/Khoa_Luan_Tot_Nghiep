from __future__ import annotations

import io
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

OUT = Path("data/interest_rates")
RAW = OUT / "deposit_raw"
MASTER = OUT / "deposit_daily.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

SOURCE_URL = "https://laisuattietkiem.vn/"
SOURCE_NAME = "laisuattietkiem"

TERM_MAP = {
    "1 tháng": 1, "3 tháng": 3, "6 tháng": 6, "9 tháng": 9,
    "12 tháng": 12, "18 tháng": 18, "24 tháng": 24, "36 tháng": 36,
}
CHANNEL_MAP = {"Tại quầy": "quay", "Trực tuyến": "online", "Online": "online"}
# Tu 04/11/2026 trang doi bo cuc: cot "Kenh" thanh "Hinh thuc", them cot STT, nhan "Truc tuyen" thanh "Online".
CHANNEL_COLUMNS = ("Kênh", "Hình thức")

BANK_TO_TICKER = {
    "BIDV": "BID", "Vietcombank": "VCB", "Vietinbank": "CTG", "ACB": "ACB",
    "Bắc Á Bank": "BAB", "Eximbank": "EIB", "LP Bank": "LPB", "MB Bank": "MBB",
    "MSB": "MSB", "Nam A Bank": "NAB", "OCB": "OCB", "SHB": "SHB",
    "Sacombank": "STB", "TPBank": "TPB", "Techcombank": "TCB", "VIB": "VIB",
    "VP Bank": "VPB",
    "Agribank": None, "An Binh Bank": None, "Kiên Long Bank": None,
    "PVComBank": None, "VCB Neo": None, "Vietbank": None,
}

TICKERS = [
    "VCB", "BID", "CTG", "MBB", "ACB", "TCB", "VPB", "STB", "HDB", "VIB", "TPB",
    "MSB", "OCB", "LPB", "SHB", "EIB", "SSB", "BAB", "BVB", "NAB", "NVB", "PGB",
]

MIN_CREDIBLE_PERCENT = 1.0
MAX_CREDIBLE_PERCENT = 15.0
MAX_CREDIBLE_JUMP_POINT = 2.0

RATE_RE = re.compile(r"^\s*([\d.]+)%(?:Trước đó:\s*([\d.]+)%)?\s*$")

MAX_ATTEMPTS = 5


def safe_fetch(label, func):
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return func()
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            pause = min(60, 10 * (2 ** (attempt - 1)))
            print(f"{label}: attempt {attempt}/{MAX_ATTEMPTS} failed ({last_error}); waiting {pause}s")
            time.sleep(pause)
    raise RuntimeError(f"{label}: failed after {MAX_ATTEMPTS} attempts: {last_error}")


def fetch_deposit_table() -> pd.DataFrame:
    def _do():
        resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        tables = pd.read_html(io.StringIO(resp.text))
        return tables[0]

    return safe_fetch(f"fetch {SOURCE_NAME}", _do)


def parse_rate_cell(cell: str):
    if not isinstance(cell, str) or cell.strip() in ("", "-"):
        return None, None
    m = RATE_RE.match(cell.strip())
    if not m:
        return None, None
    rate = float(m.group(1))
    prev = float(m.group(2)) if m.group(2) else None
    return rate, prev


def normalize(raw_df: pd.DataFrame, run_date: str, retrieved_at: str) -> pd.DataFrame:
    df = raw_df.copy()
    df["Ngân hàng"] = df["Ngân hàng"].str.replace(r"\s*Nguồn\s*$", "", regex=True).str.strip()
    column = next((c for c in CHANNEL_COLUMNS if c in df.columns), None)
    if column is None:
        raise KeyError(f"khong thay cot kenh ({' / '.join(CHANNEL_COLUMNS)}) trong {list(df.columns)}")
    df["Kênh"] = df[column].map(CHANNEL_MAP).fillna(df[column])

    rows = []
    for _, row in df.iterrows():
        bank_name = row["Ngân hàng"]
        ticker = BANK_TO_TICKER.get(bank_name, "UNMAPPED")
        channel = row["Kênh"]
        for col, term_months in TERM_MAP.items():
            if col not in row:
                continue
            rate, prev_rate = parse_rate_cell(row[col])
            if rate is None:
                continue
            rows.append({
                "date": run_date,
                "bank_name": bank_name,
                "ticker": ticker,
                "term_months": term_months,
                "channel": channel,
                "rate_percent": rate,
                "prev_rate_percent": prev_rate,
                "source": SOURCE_NAME,
                "retrieved_at_utc": retrieved_at,
            })
    return pd.DataFrame(rows)


def run() -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    run_date = datetime.now().strftime("%Y-%m-%d")
    retrieved_at = datetime.now(timezone.utc).isoformat()

    raw_df = fetch_deposit_table()
    raw_path = RAW / f"deposit_{SOURCE_NAME}_{run_date}.csv"
    raw_df.to_csv(raw_path, index=False, encoding="utf-8-sig")

    long_df = normalize(raw_df, run_date, retrieved_at)
    master_path = MASTER
    if master_path.exists():
        existing = pd.read_csv(master_path, encoding="utf-8-sig")
        combined = pd.concat([existing, long_df], ignore_index=True)
        combined = combined.drop_duplicates(
            subset=["date", "bank_name", "term_months", "channel", "source"], keep="last"
        )
    else:
        combined = long_df
    combined.to_csv(master_path, index=False, encoding="utf-8-sig")

    n_unmapped = int((long_df["ticker"] == "UNMAPPED").sum())
    with open("crawl_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{retrieved_at}] deposit_rates: source={SOURCE_NAME} rows={len(long_df)} "
                f"unmapped={n_unmapped} -> {master_path}\n")

    return {
        "raw_rows": len(raw_df),
        "normalized_rows": len(long_df),
        "master_total_rows": len(combined),
        "unmapped_rows": n_unmapped,
        "banks_seen": sorted(long_df["bank_name"].unique().tolist()),
        "long_df": long_df,
    }


def validate(df: pd.DataFrame | None = None) -> None:
    if df is None:
        df = pd.read_csv(MASTER, encoding="utf-8-sig")

    days = sorted(df["date"].unique())
    seen = df.loc[df["ticker"].notna() & (df["ticker"] != "UNMAPPED"), "ticker"]
    print(f"{len(df)} dong, {len(days)} ngay ({days[0]} -> {days[-1]}), "
          f"{df['bank_name'].nunique()} NH, "
          f"{seen.nunique()}/{len(TICKERS)} ticker")
    print()

    stamps = pd.to_datetime(pd.Series(days))
    gaps = [(a.date(), b.date(), (b - a).days - 1)
            for a, b in zip(stamps, stamps[1:]) if (b - a).days > 1]
    print("1. Chuoi ngay lien tuc (ngay bo lo la MAT VINH VIEN):")
    if gaps:
        for a, b, n in gaps:
            print(f"   THIEU {n} ngay giua {a} va {b}")
    else:
        print(f"   khong thieu ngay nao ({len(days)}/{len(days)})")
    print()

    odd = df[(df["term_months"] >= 1) & (df["rate_percent"] < MIN_CREDIBLE_PERCENT)]
    out = df[(df["rate_percent"] < 0.1) | (df["rate_percent"] > MAX_CREDIBLE_PERCENT)]
    print(f"2. Gia tri < {MIN_CREDIBLE_PERCENT}% o ky han >= 1 thang: {len(odd)} o")
    for (bank, term, channel), g in odd.groupby(["bank_name", "term_months", "channel"]):
        rates = sorted(float(v) for v in g["rate_percent"].unique())
        print(f"   {bank} | {term} thang | {channel} = {rates} "
              f"tren {len(g)}/{len(days)} ngay  (LOI TU NGUON, khong tu sua)")
    print(f"   ngoai khoang [0.1, {MAX_CREDIBLE_PERCENT}]: {len(out)} o")
    print()

    has_prev = df[df["prev_rate_percent"].notna()].copy()
    has_prev["jump"] = (has_prev["rate_percent"] - has_prev["prev_rate_percent"]).abs()
    big = has_prev[has_prev["jump"] > MAX_CREDIBLE_JUMP_POINT]
    print(f"3. Buoc nhay > {MAX_CREDIBLE_JUMP_POINT} diem so voi Truoc-do: "
          f"{len(big)}/{len(has_prev)} o")
    for (bank, term, channel), g in big.groupby(["bank_name", "term_months", "channel"]):
        r = g.iloc[0]
        print(f"   {bank} | {term} thang | {channel}: "
              f"{r['prev_rate_percent']} -> {r['rate_percent']}")
    print()

    last = df[df["date"] == days[-1]]
    grid = last.pivot_table(index="bank_name", columns="channel",
                            values="rate_percent", aggfunc="count").fillna(0).astype(int)
    for channel in ("quay", "online"):
        if channel not in grid.columns:
            grid[channel] = 0
    holes = grid[(grid["quay"] == 0) | (grid["online"] == 0)]
    print(f"4. Do phu kenh ngay {days[-1]}: "
          f"{len(holes)}/{len(grid)} NH thieu han mot kenh")
    for bank, r in holes.iterrows():
        missing = "online" if r["online"] == 0 else "quay"
        print(f"   {bank:<22} quay={r['quay']} online={r['online']}  -> thieu {missing}")
    print()

    absent = [t for t in TICKERS if t not in set(seen)]
    print(f"5. Ticker vang mat: {len(absent)}/{len(TICKERS)} -> {absent}")
    print()

    dup = int(df.duplicated(subset=["date", "bank_name", "term_months",
                                    "channel", "source"]).sum())
    print(f"6. Dong trung khoa: {dup}")

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if "--validate" in sys.argv:
        validate()
        sys.exit(0)

    summary = run()
    print(f"raw rows: {summary['raw_rows']} -> normalized rows: {summary['normalized_rows']} "
          f"-> master total: {summary['master_total_rows']}")
    print(f"banks seen: {summary['banks_seen']}")
    print(f"unmapped-to-ticker rows: {summary['unmapped_rows']}")
