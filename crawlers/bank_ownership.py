"""Co cau so huu 22 ngan hang niem yet -- tu vnstock_data (nguon VCI).

Chieu du lieu ma toan bo kho truoc day KHONG co. Voi mot he thong ho tro chon
noi GUI TIEN, ty le so huu nha nuoc xap xi muc bao tro ngam -- kho bien minh
neu bo xot. Do duoc ngay 09/09/2026: **du 22/22 ma**.

Nhom Nha nuoc chi phoi tach han thanh mot cum rieng, khong co ma nao nam giua:

    BID 76,7%  ·  VCB 74,8%  ·  CTG 64,5%  ·  MBB 43,2%
    <<< khoang trong: khong ma nao nam giua 0,09% va 43,2% >>>
    OCB 8,6%  ·  LPB 6,5%  ·  MSB 6,4%  ·  EIB 4,2%  ·  13 ma con lai ~0%

Room ngoai cung dang chu y rieng: BVB, VIB va LPB bi chan o **5%** trong khi
phan lon duoc 30% -- rang buoc nay anh huong toi dong von ngoai va thanh khoan.

GIOI HAN -- day la ANH CHUP, khong phai chuoi thoi gian. Nguon chi tra ve trang
thai hien tai. Chay dinh ky de tich luy lich su; khoa chong trung la (ngay, ma).
Cot `update_date` trong bang co dong la moc nguon tu dong dau, khong phai moc
crawl -- co dong cua VCB co dong ghi 2020, co dong ghi 2026.

Sinh ra hai file:
    data/ownership/bank_ownership.csv     -- 1 dong/ngan hang/lan chay
    data/ownership/bank_shareholders.csv  -- 1 dong/co dong/lan chay

Chay:
    python -m crawlers.bank_ownership
    python -m crawlers.bank_ownership --validate
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import pandas as pd

TICKERS = [
    "ACB", "BAB", "BID", "BVB", "CTG", "EIB", "HDB", "LPB", "MBB", "MSB", "NAB",
    "NVB", "OCB", "PGB", "SHB", "SSB", "STB", "TCB", "TPB", "VCB", "VIB", "VPB",
]

OWNERSHIP_PATH = "data/ownership/bank_ownership.csv"
HOLDERS_PATH = "data/ownership/bank_shareholders.csv"
LOG_PATH = "crawl_log.txt"

# Nguon tra ty le dang thap phan (0,748) chu khong phai phan tram (74,8).
FRACTION_FIELDS = {
    "state_percentage": "state_own_percent",
    "foreigner_percentage": "foreign_own_percent",
    "maximum_foreign_percentage": "foreign_room_percent",
}
PLAIN_FIELDS = {
    "organ_name": "organ_name",
    "organ_short_name": "organ_short_name",
    "com_group_code": "exchange",
    "issue_share": "issue_share",
    "market_cap": "market_cap_vnd",
    "current_price": "price_vnd",
    "average_match_value1_month": "adtv_1m_vnd",
    "average_match_volume1_month": "adtv_1m_volume",
    "highest_price1_year": "high_1y",
    "lowest_price1_year": "low_1y",
}


def _log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")


def _first(frame, column):
    if column not in frame.columns:
        return None
    series = frame[column]
    if isinstance(series, pd.DataFrame):  # nguon co cot trung ten
        series = series.iloc[:, 0]
    value = series.iloc[0]
    return None if pd.isna(value) else value


def fetch(tickers=None, sleep=0.3):
    import vnstock_data as vd

    tickers = tickers or TICKERS
    today = datetime.now(timezone.utc).date().isoformat()
    now = datetime.now(timezone.utc).isoformat()
    overview_rows, holder_rows, failed = [], [], []

    for ticker in tickers:
        company = vd.Company(source="VCI", symbol=ticker)
        try:
            frame = company.overview()
            frame = frame.loc[:, ~frame.columns.duplicated()]
            row = {"date": today, "ticker": ticker}
            for src, dst in FRACTION_FIELDS.items():
                value = _first(frame, src)
                row[dst] = round(value * 100, 4) if value is not None else None
            for src, dst in PLAIN_FIELDS.items():
                row[dst] = _first(frame, src)
            row["source"] = "vnstock_data VCI Company.overview"
            row["retrieved_at_utc"] = now
            overview_rows.append(row)
        except Exception as exc:
            failed.append((ticker, "overview", f"{type(exc).__name__}: {exc}"[:90]))

        try:
            holders = company.shareholders()
            for _, holder in holders.iterrows():
                holder_rows.append({
                    "date": today,
                    "ticker": ticker,
                    "share_holder": holder.get("share_holder"),
                    "shareholder_type": holder.get("shareholder_type"),
                    "quantity": holder.get("quantity"),
                    "own_percent": (
                        round(holder["share_own_percent"] * 100, 6)
                        if pd.notna(holder.get("share_own_percent")) else None
                    ),
                    "source_update_date": str(holder.get("update_date", ""))[:10],
                    "source": "vnstock_data VCI Company.shareholders",
                    "retrieved_at_utc": now,
                })
        except Exception as exc:
            failed.append((ticker, "shareholders", f"{type(exc).__name__}: {exc}"[:90]))
        time.sleep(sleep)

    return pd.DataFrame(overview_rows), pd.DataFrame(holder_rows), failed


def _append(fresh, path, keys):
    if fresh.empty:
        return fresh, 0
    if os.path.exists(path):
        old = pd.read_csv(path, encoding="utf-8-sig")
        before = len(old)
        combined = pd.concat([old, fresh], ignore_index=True)
    else:
        before = 0
        combined = fresh
    combined = combined.drop_duplicates(subset=keys, keep="last").sort_values(keys)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    combined.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\r\n")
    return combined, len(combined) - before


def build(write=True):
    overview, holders, failed = fetch()
    if overview.empty:
        raise RuntimeError("Khong lay duoc ma nao.")

    if write:
        overview_all, new_overview = _append(
            overview, OWNERSHIP_PATH, ["date", "ticker"])
        holders_all, new_holders = _append(
            holders, HOLDERS_PATH, ["date", "ticker", "share_holder"])
        _log(
            f"bank_ownership: {len(overview)}/{len(TICKERS)} ma, "
            f"{new_overview} dong so huu moi, {new_holders} dong co dong moi, "
            f"{len(failed)} loi -> {OWNERSHIP_PATH}"
        )
    else:
        overview_all, holders_all = overview, holders
        new_overview = new_holders = len(overview)

    state = overview["state_own_percent"].dropna()
    return {
        "tickers": len(overview),
        "failed": failed,
        "new_ownership_rows": new_overview,
        "new_shareholder_rows": new_holders,
        "shareholders_total": len(holders),
        "state_owned_over_40pct": overview.loc[
            overview["state_own_percent"] > 40, "ticker"].tolist(),
        "state_percent_range": [round(float(state.min()), 2),
                                round(float(state.max()), 2)],
        "paths": [OWNERSHIP_PATH, HOLDERS_PATH],
    }


def validate():
    overview = pd.read_csv(OWNERSHIP_PATH, encoding="utf-8-sig")
    latest = overview[overview["date"] == overview["date"].max()]
    res = {
        "snapshot_date": str(overview["date"].max()),
        "snapshots": int(overview["date"].nunique()),
        "tickers": int(latest["ticker"].nunique()),
        "missing_state_percent": latest.loc[
            latest["state_own_percent"].isna(), "ticker"].tolist(),
    }

    # Khoang trong giua nhom Nha nuoc chi phoi va phan con lai.
    state = latest[["ticker", "state_own_percent"]].dropna().sort_values(
        "state_own_percent", ascending=False)
    values = state["state_own_percent"].tolist()
    gaps = [(round(values[i] - values[i + 1], 2), state["ticker"].iloc[i],
             state["ticker"].iloc[i + 1]) for i in range(len(values) - 1)]
    widest = max(gaps) if gaps else None
    res["state_ownership"] = {
        "over_40pct": state.loc[state["state_own_percent"] > 40, "ticker"].tolist(),
        "widest_gap_pp": widest[0] if widest else None,
        "gap_between": [widest[1], widest[2]] if widest else None,
    }

    # Room ngoai bi chan thap la rang buoc thuc, khong phai loi du lieu.
    room = latest[["ticker", "foreign_room_percent", "foreign_own_percent"]].dropna()
    res["foreign_room"] = {
        "capped_at_5pct": room.loc[
            room["foreign_room_percent"] <= 5.01, "ticker"].tolist(),
        "room_nearly_full": room.loc[
            room["foreign_own_percent"] >= room["foreign_room_percent"] * 0.9,
            "ticker"].tolist(),
    }

    # Kiem tinh hop ly: so huu khong duoc am hay vuot 100, va nuoc ngoai <= room.
    bad = latest[
        (latest["state_own_percent"] < 0) | (latest["state_own_percent"] > 100)
        | (latest["foreign_own_percent"] < 0) | (latest["foreign_own_percent"] > 100)
    ]["ticker"].tolist()
    over_room = room.loc[
        room["foreign_own_percent"] > room["foreign_room_percent"] + 0.01, "ticker"
    ].tolist()
    res["sanity"] = {"out_of_range": bad, "foreign_above_room": over_room}

    if os.path.exists(HOLDERS_PATH):
        holders = pd.read_csv(HOLDERS_PATH, encoding="utf-8-sig")
        recent = holders[holders["date"] == holders["date"].max()]
        totals = recent.groupby("ticker")["own_percent"].sum()
        res["shareholders"] = {
            "rows": len(recent),
            "tickers": int(recent["ticker"].nunique()),
            "disclosed_sum_percent": {
                "min": round(float(totals.min()), 2),
                "median": round(float(totals.median()), 2),
                "max": round(float(totals.max()), 2),
            },
            "types": recent["shareholder_type"].value_counts().to_dict(),
        }
    return res


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--validate" in sys.argv:
        print(json.dumps(validate(), indent=2, ensure_ascii=False, default=str))
    else:
        print(json.dumps(build(), indent=2, ensure_ascii=False, default=str))
