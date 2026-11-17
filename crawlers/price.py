from __future__ import annotations

import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

OUT = Path("data/price")
COLUMNS = ["time", "open", "high", "low", "close", "volume"]

BANKS = [
    "VCB", "BID", "CTG", "MBB", "ACB", "TCB", "VPB", "STB", "HDB", "VIB", "TPB",
    "MSB", "OCB", "LPB", "SHB", "EIB", "SSB", "BAB", "BVB", "NAB", "NVB", "PGB",
]

TIME_SUFFIX = " 07:00:00"

REFRESH_DAYS = 7
FULL_START = "2010-01-01"  # truoc phien dau tien cua moi ma
SECONDS_BETWEEN_CALLS = 2.0
MAX_ATTEMPTS = 3


def path_for(symbol: str) -> Path:
    return OUT / f"{symbol}.csv"


def _fetch(symbol: str, start: str, end: str) -> pd.DataFrame:
    from vnstock_data import Quote

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            df = Quote(symbol=symbol, source="VCI").history(
                start=start, end=end, interval="1D"
            )
            if not isinstance(df, pd.DataFrame):
                raise TypeError(f"expected DataFrame, got {type(df).__name__}")
            return df
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < MAX_ATTEMPTS:
                time.sleep(5 * attempt)
    raise RuntimeError(f"{symbol}: failed after {MAX_ATTEMPTS} attempts: {last_error}")


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["time"] = pd.to_datetime(out["time"]).dt.strftime("%Y-%m-%d") + TIME_SUFFIX
    # Lich su day du cua VCI co phien khoi luong 0 (237 phien ngay 14/10/2026, BAB 39, NVB 179): OHLC do nguon tu
    # dien, open lech toi 11% khoi [low, high]. File chua bao gio luu phien nhu vay -> bo.
    return out.loc[out["volume"] > 0, COLUMNS]


def update_symbol(symbol: str, refresh_days: int = REFRESH_DAYS) -> dict:
    path = path_for(symbol)
    existing = (pd.read_csv(path) if path.exists()
                else pd.DataFrame(columns=COLUMNS))

    end = date.today()
    recent_from = (end - timedelta(days=refresh_days)).isoformat()
    fresh = _normalise(_fetch(symbol, FULL_START, end.isoformat()))

    before = existing.set_index("time") if len(existing) else pd.DataFrame(columns=COLUMNS[1:])
    changed, added, adjusted = [], [], 0
    for _, row in fresh.iterrows():
        stamp = row["time"]
        if stamp in before.index:
            old = before.loc[stamp]
            if not all(float(old[c]) == float(row[c]) for c in COLUMNS[1:]):
                if stamp[:10] >= recent_from:
                    changed.append(stamp[:10])
                else:
                    adjusted += 1
        else:
            added.append(stamp[:10])
    # dong da luu ma VCI khong tra nua: giu lai (khong mat du lieu) nhung co the chua dieu chinh -> bao ra
    stale = int((~existing["time"].isin(fresh["time"])).sum()) if len(existing) else 0

    merged = pd.concat([existing, fresh], ignore_index=True)
    merged = merged.drop_duplicates(subset=["time"], keep="last").sort_values("time")
    merged.to_csv(path, index=False)

    return {"symbol": symbol, "rows": len(merged), "added": added, "changed": changed,
            "adjusted": adjusted, "stale": stale, "last": merged["time"].iloc[-1][:10]}


def update_all(symbols: list[str] | None = None, refresh_days: int = REFRESH_DAYS) -> pd.DataFrame:
    OUT.mkdir(parents=True, exist_ok=True)
    results, failures = [], []
    for symbol in (symbols or BANKS):
        try:
            summary = update_symbol(symbol, refresh_days)
            results.append(summary)
            flags = []
            if summary["added"]:
                flags.append("them " + ",".join(summary["added"]))
            if summary["changed"]:
                flags.append("sua " + ",".join(summary["changed"]))
            if summary["adjusted"]:
                flags.append(f'VCI dieu chinh {summary["adjusted"]} phien cu')
            if summary["stale"]:
                flags.append(f'{summary["stale"]} phien VCI khong tra nua (giu ban cu)')
            print(f'{symbol:5s} {summary["rows"]:>5} dong  den {summary["last"]}  '
                  f'{" | ".join(flags) or "khong doi"}')
        except Exception as exc:
            failures.append((symbol, str(exc)[:120]))
            print(f"{symbol:5s} LOI: {str(exc)[:120]}")
        time.sleep(SECONDS_BETWEEN_CALLS)

    if failures:
        print(f"\n{len(failures)} ma that bai:")
        for symbol, message in failures:
            print(f"  {symbol}: {message}")
    return pd.DataFrame(results)


def run() -> dict:
    from datetime import datetime, timezone

    retrieved_at = datetime.now(timezone.utc).isoformat()
    frame = update_all()

    ok = len(frame)
    n_added = int(sum(len(x) for x in frame["added"])) if ok else 0
    n_changed = int(sum(len(x) for x in frame["changed"])) if ok else 0
    n_adjusted = int(frame["adjusted"].sum()) if ok else 0
    latest = frame["last"].max() if ok else ""

    with open("crawl_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{retrieved_at}] price: {ok}/{len(BANKS)} symbols ok, "
                f"{n_added} rows added, {n_changed} rows corrected, "
                f"{n_adjusted} older rows re-adjusted by VCI, latest={latest}\n")

    if ok < len(BANKS):
        raise RuntimeError(f"price: chi {ok}/{len(BANKS)} ma thanh cong")

    return {"symbols_ok": ok, "rows_added": n_added, "rows_corrected": n_changed,
            "rows_adjusted": n_adjusted, "latest_session": latest}


if __name__ == "__main__":
    frame = update_all()
    if not frame.empty:
        n_added = sum(len(x) for x in frame["added"])
        n_changed = sum(len(x) for x in frame["changed"])
        print(f"\n{len(frame)}/{len(BANKS)} ma OK | {n_added} dong moi | {n_changed} dong duoc sua")
        print(f"phien moi nhat: {frame['last'].max()}")
