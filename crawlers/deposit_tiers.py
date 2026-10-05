"""Doc deposit_24hmoney_daily.csv sau khi dua moi NH ve cung MOT bac so tien: bac thap nhat,
va thay o 24hmoney chua cap nhat bang bieu chinh thuc (VPBank tu 23/09/2026).

24hmoney khong ghi bang lai suat thuoc bac so tien nao. Doi chieu voi bieu chinh thuc
ngay 15/09/2026:
  - ACB, VCB, CTG, BID, SSB: khop bac thap nhat (ACB online < 200 trieu).
  - Doi chieu them 01/10/2026: LPB (bieu 11/08) va BAB tai quay (bieu 10/07) khop; TCB lay nham
    bac PRIVATE >= 3 ty; VPB chua cap nhat bieu 23/09 (xem TIER_OVERRIDES).
  - Sacombank TRON BAC. Bieu hieu luc 26/08/2026 co 3 bac cho moi kenh. 24hmoney lay:
      tai quay 1/3/6/12 thang = 4,60 / 4,60 / 6,30 / 6,00 -> dung bac 500 trieu - 2 ty;
      online 6/12 thang       = 6,80 / 7,00            -> dung bac < 50 trieu;
      online 1/3 thang        = 4,8 / 4,75             -> bac >= 500 trieu (4,8 la 4,75 lam tron).
    Bac thap nhat: tai quay (< 500 trieu) 4,50 / 4,50 / 6,20 / 5,90; online (< 50 trieu)
    4,50 / 4,50 / 6,80 / 7,00.

Nguyen tac cua bang ghi de (giong vnstock_note.CORRECTIONS):
  - Chi ap tu ngay hieu luc cua bieu da doi chieu (`from`). Truoc ngay do khong co bieu
    de biet 24hmoney dang lay bac nao, nen giu nguyen.
  - Chi ap khi so tho van dung bang so da thay luc doi chieu (`raw`). Neu NH doi lai suat
    thi 24hmoney se ghi so khac -> bo qua, va validate bao WARN de doi chieu bieu moi.
  - Khong sua file crawl: crawler ghi lai so tho moi ngay. Moi noi dung lai suat de tinh
    toan (build_features, experiments.eda) doc qua `read()`.

Chay:
    python -m crawlers.deposit_tiers     # liet ke o da ghi de va o khong con khop nguon
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

MASTER = Path("data/interest_rates/deposit_24hmoney_daily.csv")

TIER_OVERRIDES = [
    {
        "ticker": "STB",
        "from": "2026-08-26",
        "tier": "tai quay < 500 trieu, online < 50 trieu",
        "source": "https://www.sacombank.com.vn/content/dam/sacombank/files/cong-cu/lai-suat/"
                  "tien-gui/khcn/SACOMBANK_LAISUATNIEMYETTAIQUAY_KHCN_VIE.pdf",
        "evidence": "Bieu lai suat huy dong KHCN hieu luc 07h30 26/08/2026, Phan A muc I (tai "
                    "quay) va Phan B muc I (truc tuyen), cot lai cuoi ky",
        "reviewed": "2026-09-15",
        # (kenh, ky han thang): (so 24hmoney ghi luc doi chieu, so bac thap nhat)
        "cells": {
            ("quay", 1): (4.60, 4.50),
            ("quay", 3): (4.60, 4.50),
            ("quay", 6): (6.30, 6.20),
            ("quay", 12): (6.00, 5.90),
            ("online", 1): (4.80, 4.50),
            ("online", 3): (4.75, 4.50),
        },
    },
    {
        # Techcombank chia 4 nhom khach (PRIVATE / PRIORITY / INSPIRE / KH THUONG) x 3 muc tien
        # (>= 3 ty / 1 - 3 ty / < 1 ty). Ca 24hmoney lan laisuattietkiem deu ghi cot PRIVATE >= 3 ty
        # (bac cao nhat) -> doi ve KH THUONG < 1 ty cho cung bac voi cac NH khac.
        "ticker": "TCB",
        "from": "2026-08-11",
        "tier": "KH thuong < 1 ty",
        "source": "https://techcombank.com/content/dam/techcombank/public-site/documents/"
                  "techcombank-bieu-lai-suat-tien-gui-tiet-kiem-tien-gui-co-ky-han-20260828.pdf",
        "evidence": "Bieu lai suat tien gui KHCN ap dung tu 11/08/2026 (file 28/08/2026): bang 'Tiet kiem "
                    "Phat Loc tai quay' va 'Tien gui Phat Loc Online', cot KH THUONG / NORMAL CUSTOMER < 1B",
        "reviewed": "2026-10-01",
        "cells": {
            ("quay", 1): (4.40, 4.05),
            ("quay", 3): (4.70, 4.35),
            ("quay", 6): (6.40, 6.05),
            ("quay", 12): (6.60, 6.25),
            ("quay", 18): (5.70, 5.35),
            ("quay", 24): (5.70, 5.35),
            ("quay", 36): (5.70, 5.35),
            ("online", 1): (4.50, 4.35),
            ("online", 3): (4.75, 4.65),
            ("online", 6): (6.70, 6.55),
            ("online", 12): (6.90, 6.75),
            ("online", 18): (6.00, 5.85),
            ("online", 24): (6.00, 5.85),
            ("online", 36): (6.00, 5.85),
        },
    },
    {
        # Khong phai tron bac ma la 24hmoney CHUA CAP NHAT: VPBank doi bieu tu 23/09/2026 nhung
        # 24hmoney van giu so cu (dau thoi gian trang doi moi ngay, gia tri dung yen tu 04/09).
        # Bieu chinh thuc giong nhau o moi muc tien < 1 ty ... >= 50 ty, nen so 24hmoney khong
        # khop bac nao. laisuattietkiem co so dung nhung ghi nham kenh online thanh "quay".
        "ticker": "VPB",
        "from": "2026-09-23",
        "tier": "bieu chinh thuc 23/09/2026 (24hmoney chua cap nhat), muc < 1 ty",
        "source": "https://www.vpbank.com.vn/-/media/vpbank-latest/tai-lieu-bieu-mau/lai-suat-huy-dong/"
                  "khcn/2.-20260923-Phu-luc-BLS-niem-yet--2-.pdf",
        "evidence": "Bieu lai suat huy dong von bang VND danh cho KHCN, ap dung tu 23/09/2026, muc 1 "
                    "(tiet kiem thuong, linh lai cuoi ky), bang Tai quay va Kenh Online, dong < 1 ty",
        "reviewed": "2026-10-01",
        "cells": {
            ("quay", 1): (4.75, 4.45),
            ("quay", 3): (4.75, 4.65),
            ("quay", 6): (6.20, 6.80),
            ("quay", 12): (6.20, 6.90),
            ("quay", 18): (6.00, 6.90),
            ("quay", 24): (6.00, 6.90),
            ("quay", 36): (6.00, 5.80),
            ("online", 6): (6.20, 7.00),
            ("online", 12): (6.20, 7.10),
            ("online", 18): (6.00, 7.10),
            ("online", 24): (6.00, 7.10),
            ("online", 36): (4.20, 6.00),
        },
    },
]


def read(path=MASTER) -> pd.DataFrame:
    """Nhu pd.read_csv, them `rate_raw_percent` (so nguon) va `tier_override` (ly do neu ghi de)."""
    frame = pd.read_csv(path, encoding="utf-8-sig")
    frame["rate_raw_percent"] = frame["rate_percent"]
    frame["tier_override"] = pd.Series(pd.NA, index=frame.index, dtype="string")
    for rule in TIER_OVERRIDES:
        base = (frame["ticker"] == rule["ticker"]) & (frame["effective_date"].astype(str) >= rule["from"])
        for (channel, term), (raw, value) in rule["cells"].items():
            mask = (base & (frame["channel"] == channel) & (frame["term_months"] == term)
                    & np.isclose(frame["rate_raw_percent"], raw, rtol=0, atol=1e-9))
            frame.loc[mask, "rate_percent"] = value
            frame.loc[mask, "tier_override"] = f"{rule['ticker']} {rule['tier']} (bieu {rule['from']})"
    return frame


def status(path=MASTER) -> pd.DataFrame:
    """Moi o trong bang ghi de: so ngay da ap, va o ngay moi nhat nguon con ghi dung so cu khong."""
    frame = read(path)
    latest = frame["date"].max()
    rows = []
    for rule in TIER_OVERRIDES:
        for (channel, term), (raw, value) in rule["cells"].items():
            cell = frame[(frame["ticker"] == rule["ticker"]) & (frame["channel"] == channel)
                         & (frame["term_months"] == term)]
            today = cell[cell["date"] == latest]
            raw_today = float(today["rate_raw_percent"].iloc[0]) if len(today) else np.nan
            rows.append({
                "ticker": rule["ticker"], "channel": channel, "term_months": term,
                "raw_expected": raw, "value": value, "raw_latest": raw_today, "latest_date": latest,
                "n_applied": int(cell["tier_override"].notna().sum()),
                "still_matches": bool(np.isclose(raw_today, raw)) if np.isfinite(raw_today) else False,
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pd.set_option("display.width", 200)
    print(status().to_string(index=False))
