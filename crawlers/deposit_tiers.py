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
  - Chi ap khi so tho van dung bang so da thay luc doi chieu (`raw`; mot so hoac tuple cac so da
    kiem, vi nguon co the doi sang mot so sai khac). Neu NH doi lai suat thi 24hmoney se ghi so
    khac -> bo qua, va validate bao WARN de doi chieu bieu moi.
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
        # Ngay 05/10 24hmoney cap nhat NUA VOI: ky 18/24/36T va quay 3/36T da dung bieu, nhung
        # online 6/12T ghi 6,75 va quay 1/6/12T ghi 4,50/6,30/6,30 -- khong khop dong nao cua bieu
        # 23/09 (van la bieu duy nhat tren API tai lieu VPBank ngay 06/10; Thuong Gia 10/2026 cung
        # ghi online 12T 7,1, quay 6,9). Moi o nhan ca so cu lan so moi.
        "ticker": "VPB",
        "from": "2026-09-23",
        "tier": "bieu chinh thuc 23/09/2026 (24hmoney chua cap nhat), muc < 1 ty",
        "source": "https://www.vpbank.com.vn/-/media/vpbank-latest/tai-lieu-bieu-mau/lai-suat-huy-dong/"
                  "khcn/2.-20260923-Phu-luc-BLS-niem-yet--2-.pdf",
        "evidence": "Bieu lai suat huy dong von bang VND danh cho KHCN, ap dung tu 23/09/2026, muc 1 "
                    "(tiet kiem thuong, linh lai cuoi ky), bang Tai quay va Kenh Online, dong < 1 ty",
        "reviewed": "2026-10-06",
        # (so 24hmoney truoc 05/10, so tu 05/10); o nao so moi da bang bieu thi ghi de la no-op.
        "cells": {
            ("quay", 1): ((4.75, 4.50), 4.45),
            ("quay", 3): ((4.75, 4.65), 4.65),
            ("quay", 6): ((6.20, 6.30), 6.80),
            ("quay", 12): ((6.20, 6.30), 6.90),
            ("quay", 18): ((6.00, 6.90), 6.90),
            ("quay", 24): ((6.00, 6.90), 6.90),
            ("quay", 36): ((6.00, 5.80), 5.80),
            ("online", 6): ((6.20, 6.75), 7.00),
            ("online", 12): ((6.20, 6.75), 7.10),
            ("online", 18): ((6.00, 7.10), 7.10),
            ("online", 24): ((6.00, 7.10), 7.10),
            ("online", 36): ((4.20, 6.00), 6.00),
        },
    },
    {
        # ACB online chia 4 bac (< 200tr / 200tr-1 ty / 1-5 ty / >= 5 ty). Den 04/10 24hmoney lay bac thap
        # nhat; tu 05/10 doi sang bac 200tr-1 ty (4,60/4,75/5,00/5,80) trong khi bieu ACB doc 05-06/10 van
        # ghi < 200tr 4,50/4,70/4,90/5,70. Bang online cua ACB chi toi 12T; 24hmoney chep so 12T vao
        # 18/24/36T nen ba o do cung dua ve so 12T bac thap nhat (nhu truoc 05/10).
        "ticker": "ACB",
        "from": "2026-10-05",
        "tier": "online < 200 trieu",
        "source": "https://acb.com.vn/lai-suat-tien-gui",
        "evidence": "Trang lai suat tien gui KHCN cua ACB (doc 05/10 va 06/10/2026), muc II.3 Tien gui "
                    "Online lai cuoi ky, dong < 200 trieu",
        "reviewed": "2026-10-06",
        "cells": {
            ("online", 1): (4.60, 4.50),
            ("online", 3): (4.75, 4.70),
            ("online", 6): (5.00, 4.90),
            ("online", 12): (5.80, 5.70),
            ("online", 18): (5.80, 5.70),
            ("online", 24): (5.80, 5.70),
            ("online", 36): (5.80, 5.70),
        },
    },
]


# Bac lai suat theo SO TIEN GUI (bieu chinh thuc). deposit_rates giu bac thap nhat cho moi NH (so sanh
# cung bac); bang nay cho trang gui tiet kiem tinh dung lai theo so tien nguoi dung nhap.
#   tiers: (nguong duoi bang dong, nhan); bac dau = bac thap nhat = so trong deposit_rates.
#   rates: ky han -> lai tung bac (cung thu tu voi tiers).
# Chi xuat bac cua o nao ma so trong deposit_rates (sau ghi de) BANG bac thap nhat cua bieu: neu NH doi
# bieu thi o do lech -> khong xuat (tranh ghep bac cu vao so moi) va validate bao WARN.
AMOUNT_TIERS = [
    {
        "ticker": "ACB", "channel": "online", "from": "2026-10-01",
        "source": "https://acb.com.vn/lai-suat-tien-gui",
        "evidence": "Muc II.3 Tien gui Online, lai cuoi ky (doc 05/10/2026)",
        "reviewed": "2026-10-06",
        "tiers": [(0, "Dưới 200 triệu"), (200_000_000, "Từ 200 triệu"), (1_000_000_000, "Từ 1 tỷ"),
                  (5_000_000_000, "Từ 5 tỷ")],
        "rates": {1: (4.50, 4.60, 4.65, 4.75), 3: (4.70, 4.75, 4.75, 4.75), 6: (4.90, 5.00, 5.05, 5.10),
                  9: (5.10, 5.20, 5.25, 5.30), 12: (5.70, 5.80, 5.85, 5.90)},
    },
    {
        # Tai quay khong co bang rieng theo muc tien ma co "lai suat thuong bac thang" cho ky 1-12T:
        # +0,10 / +0,15 / +0,20 tren lai TK truyen thong; ky < 6T van theo tran 4,75%.
        "ticker": "ACB", "channel": "quay", "from": "2026-10-01",
        "source": "https://acb.com.vn/lai-suat-tien-gui",
        "evidence": "Muc II.1 (TK truyen thong, lai cuoi ky) + II.2 Lai suat thuong bac thang (doc 05/10/2026)",
        "reviewed": "2026-10-06",
        "tiers": [(0, "Dưới 200 triệu"), (200_000_000, "Từ 200 triệu"), (1_000_000_000, "Từ 1 tỷ"),
                  (5_000_000_000, "Từ 5 tỷ")],
        "rates": {1: (4.00, 4.10, 4.15, 4.20), 3: (4.40, 4.50, 4.55, 4.60), 6: (4.50, 4.60, 4.65, 4.70),
                  9: (4.70, 4.80, 4.85, 4.90), 12: (5.30, 5.40, 5.45, 5.50)},
    },
    {
        "ticker": "STB", "channel": "online", "from": "2026-08-26",
        "source": "https://www.sacombank.com.vn/content/dam/sacombank/files/cong-cu/lai-suat/tien-gui/khcn/"
                  "SACOMBANK_LAISUATNIEMYETTAIQUAY_KHCN_VIE.pdf",
        "evidence": "Bieu hieu luc 07h30 26/08/2026, Phan B muc I (truc tuyen), cot lai cuoi ky",
        "reviewed": "2026-10-06",
        "tiers": [(0, "Dưới 50 triệu"), (50_000_000, "Từ 50 triệu"), (500_000_000, "Từ 500 triệu")],
        "rates": {1: (4.50, 4.60, 4.75), 3: (4.50, 4.60, 4.75), 6: (6.80, 7.10, 7.20), 9: (6.80, 7.10, 7.20),
                  12: (7.00, 7.30, 7.50), 13: (7.00, 7.30, 7.50), 18: (7.00, 7.30, 7.50),
                  24: (7.20, 7.50, 7.80), 36: (7.20, 7.50, 7.80)},
    },
    {
        "ticker": "STB", "channel": "quay", "from": "2026-08-26",
        "source": "https://www.sacombank.com.vn/content/dam/sacombank/files/cong-cu/lai-suat/tien-gui/khcn/"
                  "SACOMBANK_LAISUATNIEMYETTAIQUAY_KHCN_VIE.pdf",
        "evidence": "Bieu hieu luc 07h30 26/08/2026, Phan A muc I (tai quay), cot lai cuoi ky",
        "reviewed": "2026-10-06",
        "tiers": [(0, "Dưới 500 triệu"), (500_000_000, "Từ 500 triệu"), (2_000_000_000, "Từ 2 tỷ")],
        "rates": {1: (4.50, 4.60, 4.75), 3: (4.50, 4.60, 4.75), 6: (6.20, 6.30, 6.40), 9: (6.20, 6.30, 6.40),
                  12: (5.90, 6.00, 6.10), 13: (5.90, 6.00, 6.10), 18: (6.00, 6.10, 6.20),
                  24: (6.70, 6.80, 6.90), 36: (6.70, 6.80, 6.90)},
    },
    {
        # KH thuong: online khong chia bac (ba cot bang nhau); tai quay chi bac >= 3 ty cao hon 0,10.
        "ticker": "TCB", "channel": "quay", "from": "2026-08-11",
        "source": "https://techcombank.com/content/dam/techcombank/public-site/documents/"
                  "techcombank-bieu-lai-suat-tien-gui-tiet-kiem-tien-gui-co-ky-han-20260828.pdf",
        "evidence": "Bieu ap dung tu 11/08/2026, bang Tiet kiem Phat Loc tai quay, cot KH THUONG (>=3B / 1-3B / <1B)",
        "reviewed": "2026-10-06",
        "tiers": [(0, "Dưới 3 tỷ"), (3_000_000_000, "Từ 3 tỷ")],
        "rates": {1: (4.05, 4.15), 3: (4.35, 4.45), 6: (6.05, 6.15), 9: (6.05, 6.15), 12: (6.25, 6.35),
                  13: (5.35, 5.45), 18: (5.35, 5.45), 24: (5.35, 5.45), 36: (5.35, 5.45)},
    },
    {
        # "So tien tu tren 1 ty" -> bac 2 bat dau tu 1 ty + 1 dong. Bang I (mac dinh); bang II cho chi nhanh
        # mien Trung, Nam cao hon 0,1 diem o ky 1-11T, khong dung o day.
        "ticker": "MBB", "channel": "quay", "from": "2026-09-11",
        "source": "https://www.mbbank.com.vn/Fee",
        "evidence": "Bieu lai suat huy dong hieu luc 11/09/2026, muc I.1 (VND, lai tra sau)",
        "reviewed": "2026-10-06",
        "tiers": [(0, "Đến 1 tỷ"), (1_000_000_001, "Trên 1 tỷ")],
        "rates": {1: (3.70, 3.90), 3: (4.10, 4.30), 6: (4.60, 4.80), 9: (4.60, 4.80), 12: (6.20, 6.30),
                  13: (6.20, 6.30), 18: (6.20, 6.30)},
    },
    {
        "ticker": "SHB", "channel": "quay", "from": "2026-04-11",
        "source": "https://www.shb.com.vn/wp-content/uploads/2023/02/01.-BI%E1%BB%82U-LS-H%C4%90V-VND-KHCN-11.4.26.pdf",
        "evidence": "Bieu ap dung tu 11/04/2026, muc 1 Tiet kiem bac thang (< 2 ty / >= 2 ty), lai cuoi ky",
        "reviewed": "2026-10-06",
        "tiers": [(0, "Dưới 2 tỷ"), (2_000_000_000, "Từ 2 tỷ")],
        "rates": {1: (4.40, 4.50), 3: (4.50, 4.60), 6: (5.80, 5.90), 9: (5.80, 5.90), 12: (6.20, 6.30),
                  13: (6.30, 6.40), 18: (6.30, 6.40), 24: (6.40, 6.50), 36: (6.50, 6.60)},
    },
]


def _accepted(raw) -> tuple[float, ...]:
    """So tho da kiem cua mot o: mot so, hoac tuple nhieu so (nguon doi sang so sai khac)."""
    return tuple(raw) if isinstance(raw, (tuple, list)) else (raw,)


def _matches(values, raw):
    """Mask: gia tri trung mot trong cac so tho da kiem."""
    values = np.asarray(values, dtype=float)
    return np.any([np.isclose(values, r, rtol=0, atol=1e-9) for r in _accepted(raw)], axis=0)


def read(path=MASTER) -> pd.DataFrame:
    """Nhu pd.read_csv, them `rate_raw_percent` (so nguon) va `tier_override` (ly do neu ghi de)."""
    frame = pd.read_csv(path, encoding="utf-8-sig")
    frame["rate_raw_percent"] = frame["rate_percent"]
    frame["tier_override"] = pd.Series(pd.NA, index=frame.index, dtype="string")
    for rule in TIER_OVERRIDES:
        base = (frame["ticker"] == rule["ticker"]) & (frame["effective_date"].astype(str) >= rule["from"])
        for (channel, term), (raw, value) in rule["cells"].items():
            mask = (base & (frame["channel"] == channel) & (frame["term_months"] == term)
                    & _matches(frame["rate_raw_percent"], raw))
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
                "raw_expected": "/".join(f"{r:g}" for r in _accepted(raw)), "value": value,
                "raw_latest": raw_today, "latest_date": latest,
                "n_applied": int(cell["tier_override"].notna().sum()),
                "still_matches": bool(_matches([raw_today], raw)[0]) if np.isfinite(raw_today) else False,
            })
    return pd.DataFrame(rows)


def amount_tier_status(frame: pd.DataFrame | None = None) -> pd.DataFrame:
    """Moi (NH, kenh, ky han) trong AMOUNT_TIERS o ngay moi nhat: so dang dung co bang bac thap nhat
    cua bieu khong (`matches`). Khong co so ngay do (nguon khong niem yet ky han nay) -> `present` False."""
    frame = read() if frame is None else frame
    latest = frame["date"].max()
    today = frame[frame["date"] == latest]
    rows = []
    for rule in AMOUNT_TIERS:
        cells = today[(today["ticker"] == rule["ticker"]) & (today["channel"] == rule["channel"])]
        current = cells.set_index("term_months")["rate_percent"]
        for term, rates in rule["rates"].items():
            present = term in current.index
            value = float(current[term]) if present else np.nan
            rows.append({
                "ticker": rule["ticker"], "channel": rule["channel"], "term_months": term,
                "lowest_tier": rates[0], "current": value, "latest_date": latest, "present": present,
                "matches": bool(present and np.isclose(value, rates[0], rtol=0, atol=1e-9)),
            })
    return pd.DataFrame(rows)


def amount_tiers(frame: pd.DataFrame | None = None) -> pd.DataFrame:
    """Cac bac tren bac thap nhat, cho ngay moi nhat, chi o nao `amount_tier_status` khop.
    Bac co lai bang bac lien duoi bi bo (khong doi gi khi tang so tien)."""
    frame = read() if frame is None else frame
    status_table = amount_tier_status(frame)
    ok = {(r.ticker, r.channel, r.term_months) for r in status_table.itertuples() if r.matches}
    rows = []
    for rule in AMOUNT_TIERS:
        for term, rates in rule["rates"].items():
            if (rule["ticker"], rule["channel"], term) not in ok:
                continue
            for (min_amount, label), rate, below in zip(rule["tiers"][1:], rates[1:], rates[:-1]):
                if np.isclose(rate, below, rtol=0, atol=1e-9):
                    continue
                rows.append({
                    "ticker": rule["ticker"], "term_months": term, "channel": rule["channel"],
                    "min_amount_vnd": int(min_amount), "rate_percent": rate, "base_rate_percent": rates[0],
                    "tier_label": label, "valid_from": rule["from"], "source": rule["source"],
                })
    return pd.DataFrame(rows, columns=["ticker", "term_months", "channel", "min_amount_vnd", "rate_percent",
                                       "base_rate_percent", "tier_label", "valid_from", "source"])


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pd.set_option("display.width", 200)
    print(status().to_string(index=False))
    print("\nBac theo so tien (AMOUNT_TIERS), ngay moi nhat:")
    print(amount_tier_status().to_string(index=False))
