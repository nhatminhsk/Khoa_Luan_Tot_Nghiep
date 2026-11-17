from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

RAW = Path("data/vnstock_financial/raw")
OUT = Path("data/vnstock_financial/financial_long.csv")
AVAILABILITY = Path("data/vnstock_financial/availability.csv")

TICKERS = [
    "ACB", "BAB", "BID", "BVB", "CTG", "EIB", "HDB", "LPB", "MBB", "MSB", "NAB",
    "NVB", "OCB", "PGB", "SHB", "SSB", "STB", "TCB", "TPB", "VCB", "VIB", "VPB",
]
STATEMENTS = ("balance_sheet", "income_statement", "cash_flow", "ratio")
FREQS = ("quarter", "year")

FILENAME = re.compile(r"^(?P<ticker>[A-Z]+)_(?P<statement>.+)_(?P<freq>quarter|year)$")

COLUMNS = [
    "ticker", "statement", "freq", "period",
    "id", "name", "order", "level", "off_balance", "unit", "value",
]

READ_DTYPES = {"period": str, "off_balance": "boolean"}


def _parts(path: Path) -> tuple[str, str, str]:
    m = FILENAME.match(path.stem)
    if not m:
        raise ValueError(f"ten file khong theo mau TICKER_statement_freq: {path.name}")
    return m["ticker"], m["statement"], m["freq"]


def fetch(tickers=None, raw_dir: Path = RAW, sleep: float = 0.5, retries: int = 3) -> dict:
    import vnstock_data as vd

    tickers = tickers or TICKERS
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    keep = [c for c in COLUMNS if c not in ("ticker", "statement", "freq")]
    log, failed = [], []
    for ticker in tickers:
        fin = vd.Finance(source="VCI", symbol=ticker, period="quarter", get_all=True)
        for statement in STATEMENTS:
            for freq in FREQS:
                path = raw_dir / f"{ticker}_{statement}_{freq}.csv"
                err = None
                for attempt in range(retries):
                    try:
                        df = getattr(fin, statement)(period=freq, lang="en", dropna=False)
                        break
                    except Exception as exc:  # mang chap chon, thu lai
                        err = f"{type(exc).__name__}: {exc}"[:160]
                        time.sleep(5 * (attempt + 1))
                else:
                    failed.append((ticker, statement, freq, err))
                    log.append(dict(symbol=ticker, report=statement, requested_period=freq,
                                    status="error", rows=0, periods_found="", file="", note=err))
                    continue
                df = df[[c for c in keep if c in df.columns]]
                # Goi mien phi tra ban cut (18/84 dong can doi, xem vci_raw.py): khong ghi de file day du.
                if path.exists() and df["id"].nunique() < 0.9 * pd.read_csv(path, usecols=["id"])["id"].nunique():
                    failed.append((ticker, statement, freq, f"ban cut {df['id'].nunique()} id, giu file cu"))
                    log.append(dict(symbol=ticker, report=statement, requested_period=freq, status="error", rows=0,
                                    periods_found="", file="", note="ban cut, giu file cu"))
                    continue
                df.to_csv(path, index=False, encoding="utf-8-sig")
                log.append(dict(symbol=ticker, report=statement, requested_period=freq,
                                status="ok", rows=len(df), items=int(df["id"].nunique()),
                                periods_found="|".join(sorted(df["period"].astype(str).unique())),
                                file=str(path), note=""))
                time.sleep(sleep)
    stamp = datetime.now(timezone.utc).isoformat()
    avail = pd.DataFrame(log).assign(retrieved_at_utc=stamp)
    if Path(raw_dir) == RAW:
        avail.to_csv(AVAILABILITY, index=False, encoding="utf-8-sig")
        avail.to_json(AVAILABILITY.with_suffix(".json"), orient="records", indent=2, force_ascii=False)
    return {"files_ok": int((avail["status"] == "ok").sum()), "failed": failed,
            "items_by_statement": avail[avail["status"] == "ok"].groupby("report")["items"].max().to_dict()}


def load() -> pd.DataFrame:
    files = sorted(RAW.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"khong thay file nao trong {RAW}")

    frames = []
    for path in files:
        ticker, statement, freq = _parts(path)
        df = pd.read_csv(path, encoding="utf-8-sig")
        df.insert(0, "freq", freq)
        df.insert(0, "statement", statement)
        df.insert(0, "ticker", ticker)
        frames.append(df)

    out = pd.concat(frames, ignore_index=True)
    unexpected = set(out.columns) - set(COLUMNS)
    if unexpected:
        raise ValueError(f"cot la trong raw/: {sorted(unexpected)}")
    out = out.reindex(columns=COLUMNS)

    return out.sort_values(["ticker", "statement", "freq", "period", "order"],
                           kind="stable").reset_index(drop=True)


def validate(df: pd.DataFrame | None = None) -> None:
    if df is None:
        df = pd.read_csv(OUT, encoding="utf-8-sig", dtype=READ_DTYPES)

    raw_rows = 0
    mismatched = []
    for path in sorted(RAW.glob("*.csv")):
        ticker, statement, freq = _parts(path)
        src = pd.read_csv(path, encoding="utf-8-sig", dtype={"period": str})
        raw_rows += len(src)
        block = df[(df.ticker == ticker) & (df.statement == statement) & (df.freq == freq)]
        if len(block) != len(src):
            mismatched.append(f"{path.stem} (dong {len(src)} vs {len(block)})")
            continue
        cols = [c for c in src.columns if c not in ("period", "id")]
        a = src.set_index(["period", "id"])[cols].sort_index().astype(str)
        b = block.set_index(["period", "id"])[cols].sort_index().astype(str)
        if not a.equals(b):
            mismatched.append(path.stem)

    print(f"dong: {len(df)} (raw: {raw_rows}) {'OK' if len(df) == raw_rows else 'LECH!'}")
    print(f"doi chieu tung o voi ca {len(list(RAW.glob('*.csv')))} file nguon: "
          + ("KHOP HOAN TOAN" if not mismatched else f"LECH {len(mismatched)}: {mismatched[:5]}"))
    print(f"ticker: {df.ticker.nunique()} | statement: {sorted(df.statement.unique())}")
    print(f"freq: {sorted(df.freq.unique())}")

    for col in ("ticker", "statement", "freq", "period", "id"):
        n = df[col].isna().sum()
        print(f"  {col} rong: {n}" + ("  <-- KHONG DUOC" if n else ""))

    print("\nso dong theo (statement, freq):")
    print(df.groupby(["statement", "freq"]).size().to_string())

    print("\nky bao cao:")
    for freq, g in df.groupby("freq"):
        print(f"  {freq}: {g.period.min()} .. {g.period.max()} ({g.period.nunique()} ky)")

    ob = df[df.off_balance.notna()].statement.unique()
    print(f"\noff_balance chi co o: {sorted(ob)}")
    missing_ob = df[(df.statement == "balance_sheet") & df.off_balance.isna()]
    print(f"  dong balance_sheet thieu off_balance: {len(missing_ob)}")

    per = df.groupby("ticker").apply(
        lambda g: g.groupby(["statement", "freq"]).ngroups, include_groups=False)
    short = per[per != 8]
    print(f"\nticker du ca 8 nhom: {(per == 8).sum()}/{len(per)}")
    if not short.empty:
        print(short.to_string())

    dup = df.duplicated(subset=["ticker", "statement", "freq", "period", "id"]).sum()
    print(f"khoa trung (ticker,statement,freq,period,id): {dup}")


def run(write: bool = True) -> dict:
    df = load()
    if write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(OUT, index=False, encoding="utf-8-sig")
    return {
        "rows": len(df),
        "tickers": int(df.ticker.nunique()),
        "files": len(list(RAW.glob("*.csv"))),
        "out": str(OUT),
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--validate" in sys.argv:
        validate()
    else:
        if "--fetch" in sys.argv:
            print(fetch())
        print(run())
