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
    # 24hmoney dung o bang 29/10/2026 (moc "19:30:02 29/10/2026" van y nguyen ngay 03/11) va chua ghi dot giam lai
    # 20-22/10 o 11 o chua co bieu chinh thuc (BIDV khong dang bang online; Bac A online, MB online, VCB 18T chua doc
    # duoc bieu). Bang tong hop tren blog Techcombank (crawlers/deposit_techcombank.py) da giam ca 11 o so voi ban
    # Wayback 17/10; BID online khop laisuattietkiem 02/11 (6,60 / 6,80). Nguoi dung duyet dua len web ngay 03/11/2026.
    # Ngay giam that khong biet (giua 17/10 va 02/11), nen chi ap tu bang 24hmoney cuoi cung, khong viet lai lich su.
    *[{
        "ticker": ticker,
        "from": "2026-10-29",
        "tier": "bang tong hop Techcombank 03/11/2026 (24hmoney chua cap nhat)",
        "source": "https://techcombank.com/thong-tin/blog/lai-suat-tiet-kiem",
        "evidence": "Bang 'Lai suat gui tiet kiem cua 30+ ngan hang hom nay 3/11/2026' (Last-Modified 20:43 02/11/2026), "
                    "luu o data/interest_rates/deposit_techcombank_daily.csv",
        "reviewed": "2026-11-03",
        "cells": cells,
    } for ticker, cells in {
        "BID": {("online", 6): (7.20, 6.60), ("online", 12): (7.40, 6.80)},
        "BAB": {("online", 6): (7.05, 6.55), ("online", 12): (7.10, 6.60), ("online", 18): (7.10, 6.60),
                ("online", 24): (7.10, 6.60), ("online", 36): (7.10, 6.60)},
        "MBB": {("online", 6): (5.70, 5.20), ("online", 12): (6.30, 5.80)},
        "VCB": {("online", 18): (5.90, 5.40), ("quay", 18): (5.90, 5.50)},
    }.items()],
]


# Bac lai suat theo SO TIEN GUI (bieu chinh thuc). deposit_rates giu bac thap nhat cho moi NH (so sanh
# cung bac); bang nay cho trang gui tiet kiem tinh dung lai theo so tien nguoi dung nhap.
#   tiers: (nguong duoi bang dong, nhan); bac dau = bac thap nhat = so trong deposit_rates.
#   rates: ky han -> lai tung bac (cung thu tu voi tiers).
# Chi xuat bac cua o nao ma so trong deposit_rates (sau ghi de) BANG bac thap nhat cua bieu: neu NH doi
# bieu thi o do lech -> khong xuat (tranh ghep bac cu vao so moi) va validate bao WARN.
AMOUNT_TIERS = [
    {
        "ticker": "ACB", "channel": "online", "from": "2026-10-22",
        "source": "https://acb.com.vn/lai-suat-tien-gui",
        "evidence": "Muc II.3 Tien gui Online, lai cuoi ky (doc 22/10/2026, sau dot giam lai; trang khong ghi ngay)",
        "reviewed": "2026-10-22",
        "tiers": [(0, "Dưới 200 triệu"), (200_000_000, "Từ 200 triệu"), (1_000_000_000, "Từ 1 tỷ"),
                  (5_000_000_000, "Từ 5 tỷ")],
        "rates": {1: (4.40, 4.50, 4.55, 4.60), 3: (4.40, 4.50, 4.55, 4.60), 6: (4.40, 4.50, 4.55, 4.60),
                  9: (4.60, 4.70, 4.75, 4.80), 12: (5.20, 5.30, 5.35, 5.40)},
    },
    {
        # Tai quay khong co bang rieng theo muc tien ma co "lai suat thuong bac thang" cho ky 1-12T:
        # +0,10 / +0,15 / +0,20 tren lai TK truyen thong; ky < 6T van theo tran 4,75%.
        "ticker": "ACB", "channel": "quay", "from": "2026-10-22",
        "source": "https://acb.com.vn/lai-suat-tien-gui",
        "evidence": "Muc II.1 (TK truyen thong, lai cuoi ky) + II.2 Lai suat thuong bac thang (doc 22/10/2026)",
        "reviewed": "2026-10-22",
        "tiers": [(0, "Dưới 200 triệu"), (200_000_000, "Từ 200 triệu"), (1_000_000_000, "Từ 1 tỷ"),
                  (5_000_000_000, "Từ 5 tỷ")],
        "rates": {1: (4.00, 4.10, 4.15, 4.20), 3: (4.00, 4.10, 4.15, 4.20), 6: (4.00, 4.10, 4.15, 4.20),
                  9: (4.20, 4.30, 4.35, 4.40), 12: (4.80, 4.90, 4.95, 5.00)},
    },
    {
        "ticker": "STB", "channel": "online", "from": "2026-10-20",
        "source": "https://www.sacombank.com.vn/content/dam/sacombank/files/cong-cu/lai-suat/tien-gui/khcn/"
                  "SACOMBANK_LAISUATNIEMYETTAIQUAY_KHCN_VIE.pdf",
        "evidence": "Bieu hieu luc 07h30 20/10/2026, Phan B muc I (truc tuyen), cot lai cuoi ky",
        "reviewed": "2026-10-22",
        "tiers": [(0, "Dưới 50 triệu"), (50_000_000, "Từ 50 triệu"), (500_000_000, "Từ 500 triệu")],
        "rates": {1: (4.50, 4.60, 4.75), 3: (4.50, 4.60, 4.75), 6: (6.30, 6.60, 6.70), 9: (6.30, 6.60, 6.70),
                  12: (6.50, 6.80, 7.00), 13: (6.50, 6.80, 7.00), 18: (6.50, 6.80, 7.00),
                  24: (6.70, 7.00, 7.30), 36: (6.70, 7.00, 7.30)},
    },
    {
        "ticker": "STB", "channel": "quay", "from": "2026-10-20",
        "source": "https://www.sacombank.com.vn/content/dam/sacombank/files/cong-cu/lai-suat/tien-gui/khcn/"
                  "SACOMBANK_LAISUATNIEMYETTAIQUAY_KHCN_VIE.pdf",
        "evidence": "Bieu hieu luc 07h30 20/10/2026, Phan A muc I (tai quay), cot lai cuoi ky",
        "reviewed": "2026-10-22",
        "tiers": [(0, "Dưới 500 triệu"), (500_000_000, "Từ 500 triệu"), (2_000_000_000, "Từ 2 tỷ")],
        "rates": {1: (4.50, 4.60, 4.75), 3: (4.50, 4.60, 4.75), 6: (5.70, 5.80, 5.90), 9: (5.70, 5.80, 5.90),
                  12: (5.40, 5.50, 5.60), 13: (5.40, 5.50, 5.60), 18: (5.50, 5.60, 5.70),
                  24: (6.20, 6.30, 6.40), 36: (6.20, 6.30, 6.40)},
    },
    {
        # KH thuong: online khong chia bac (ba cot bang nhau); tai quay chi bac >= 3 ty cao hon 0,10.
        "ticker": "TCB", "channel": "quay", "from": "2026-10-24",
        "source": "https://techcombank.com/content/dam/techcombank/public-site/documents/"
                  "tcb-bieu-lai-suat-tien-gui-tiet-kiem-tien-gui-co-ky-han-20261024.pdf",
        "evidence": "Bieu ap dung tu 24/10/2026 (thay bieu 22/10), bang Tiet kiem Phat Loc tai quay, cot KH THUONG "
                    "(>=3B / 1-3B / <1B)",
        "reviewed": "2026-11-06",
        "tiers": [(0, "Dưới 3 tỷ"), (3_000_000_000, "Từ 3 tỷ")],
        "rates": {1: (4.05, 4.15), 3: (4.35, 4.45), 6: (5.55, 5.65), 9: (5.55, 5.65), 12: (5.75, 5.85),
                  13: (4.85, 4.95), 18: (4.85, 4.95), 24: (4.85, 4.95), 36: (4.85, 4.95)},
    },
    {
        # "So tien tu tren 1 ty" -> bac 2 bat dau tu 1 ty + 1 dong. Bang I (mac dinh); bang II cho chi nhanh
        # mien Trung, Nam cao hon 0,1 diem o ky 1-11T, khong dung o day.
        "ticker": "MBB", "channel": "quay", "from": "2026-10-21",
        "source": "https://www.mbbank.com.vn/Fee",
        "evidence": "Bieu lai suat huy dong hieu luc 21/10/2026, muc I.1 (VND, lai tra sau)",
        "reviewed": "2026-10-22",
        "tiers": [(0, "Đến 1 tỷ"), (1_000_000_001, "Trên 1 tỷ")],
        "rates": {1: (3.70, 3.90), 3: (4.10, 4.30), 6: (4.10, 4.30), 9: (4.10, 4.30), 12: (5.70, 5.80),
                  13: (5.70, 5.80), 18: (5.70, 5.80)},
    },
    {
        "ticker": "SHB", "channel": "quay", "from": "2026-10-20",
        "source": "https://www.shb.com.vn/wp-content/uploads/2023/02/01.-BIEU-LS-HDV-VND-KHCN-Thang-10.pdf",
        "evidence": "QD 3991/2026/QD-TGD hieu luc 20/10/2026, muc 1 Tiet kiem bac thang (< 2 ty / >= 2 ty), "
                    "lai cuoi ky",
        "reviewed": "2026-10-22",
        "tiers": [(0, "Dưới 2 tỷ"), (2_000_000_000, "Từ 2 tỷ")],
        "rates": {1: (4.40, 4.50), 3: (4.50, 4.60), 6: (5.30, 5.40), 9: (5.30, 5.40), 12: (5.70, 5.80),
                  13: (5.80, 5.90), 18: (5.80, 5.90), 24: (5.90, 6.00), 36: (6.00, 6.10)},
    },
    {
        # Bac dau 10 trieu (online 2 trieu) - duoi muc do gan nhu moi so tien nguoi dung nhap; chi ky 1-5T chia bac.
        "ticker": "VIB", "channel": "quay", "from": "2026-10-21",
        "source": "https://www.vib.com.vn/vn/tiet-kiem",
        "evidence": "Bang Tien gui tai quay > Tien gui co ky han (API PwsStaticData/api/saving-rate/core, "
                    "effectDate 2026-10-21)",
        "reviewed": "2026-10-22",
        "tiers": [(0, "Dưới 300 triệu"), (300_000_000, "Từ 300 triệu"), (3_000_000_000, "Từ 3 tỷ")],
        "rates": {1: (4.25, 4.30, 4.35), 3: (4.35, 4.40, 4.45)},
    },
    {
        "ticker": "VIB", "channel": "online", "from": "2026-06-12",
        "source": "https://www.vib.com.vn/vn/tiet-kiem",
        "evidence": "Bang Tien gui truc tuyen (API saving-rate/core, effectDate 2026-06-12; chua giam dot 20/10)",
        "reviewed": "2026-10-22",
        "tiers": [(0, "Dưới 300 triệu"), (300_000_000, "Từ 300 triệu"), (3_000_000_000, "Từ 3 tỷ")],
        "rates": {1: (4.35, 4.40, 4.45), 3: (4.45, 4.50, 4.55)},
    },
]


# Anh chup bieu chinh thuc doc tay tren web/PDF cua tung NH (data/interest_rates/deposit_official_manual.csv).
# Lam ra sau dot giam lai 20-22/10/2026 (CV 9608/NHNN-CSTT): 24hmoney KHONG doi o nao tu 17/10 trong khi 18/20 NH
# doc duoc da doi bieu. Cung nguyen tac voi TIER_OVERRIDES:
#   - Chi ap tu effective_from (ngay hieu luc in tren bieu; bieu khong ghi ngay thi lay ngay doc `checked`).
#   - Chi ap khi so 24hmoney van bang so da thay luc doc bieu (`raw_24h`): 24hmoney cap nhat thi o do tu ngung ghi de
#     va validate bao WARN deposit.official.
#   - O 24hmoney khong niem yet (STB, BVB ky 18/24/36T) thi them dong moi, nhung chi trong OFFICIAL_MAX_AGE_DAYS ngay
#     ke tu ngay doc: khong co nguon thu hai de biet khi nao NH doi bieu, nen het han thi o do trong lai.
#   - Chi dung dong lowest_tier (bac so tien thap nhat, cung bac voi 21 NH con lai) va source_type = bieu_chinh_thuc;
#     dong "bao" (so bao chi khi web NH khong co bang) chi de doi chieu.
OFFICIAL = Path("data/interest_rates/deposit_official_manual.csv")
OFFICIAL_MAX_AGE_DAYS = 30


def _official(path=OFFICIAL) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame()
    table = pd.read_csv(path, dtype={"effective_from": str, "tier": str})
    table = table[table["lowest_tier"].astype(bool) & (table["source_type"] == "bieu_chinh_thuc")].copy()
    table["start"] = table["effective_from"].fillna(table["checked"]).astype(str)
    return table


def _apply_official(frame: pd.DataFrame, path=OFFICIAL) -> pd.DataFrame:
    table = _official(path)
    if table.empty:
        return frame
    latest = str(frame["date"].max())
    # Chi them o cho ky han 24hmoney DANG theo doi (ngay moi nhat): 9T va 13T da ngung tu 06/2026 va 01/2025,
    # them lai cho vai ngay cuoi se tao ky han chi co o vai NH.
    terms = set(frame.loc[frame["date"].astype(str) == latest, "term_months"].dropna().astype(int))
    added = []
    for row in table.itertuples(index=False):
        if int(row.term_months) not in terms:
            continue
        label = f"{row.ticker} bieu chinh thuc {row.start}"
        cell = ((frame["ticker"] == row.ticker) & (frame["channel"] == row.channel)
                & (frame["term_months"] == row.term_months))
        if pd.notna(row.raw_24h):
            mask = (cell & (frame["effective_date"].astype(str) >= row.start)
                    & _matches(frame["rate_raw_percent"], row.raw_24h))
            frame.loc[mask, "rate_percent"] = row.rate_percent
            frame.loc[mask, "tier_override"] = label
            continue
        until = (pd.Timestamp(row.checked) + pd.Timedelta(days=OFFICIAL_MAX_AGE_DAYS)).strftime("%Y-%m-%d")
        bank_days = frame[(frame["ticker"] == row.ticker) & (frame["date"].astype(str) >= row.start)
                          & (frame["date"].astype(str) <= min(latest, until))]
        days = bank_days.drop_duplicates("date")
        have = set(frame.loc[cell, "date"].astype(str))
        for day in days.itertuples(index=False):
            if str(day.date) in have:
                continue
            added.append({**day._asdict(), "channel": row.channel, "term_months": row.term_months,
                          "rate_percent": row.rate_percent, "rate_raw_percent": np.nan,
                          "source": "bieu NH", "source_url": row.source_url, "tier_override": label})
    if added:
        extra = pd.DataFrame(added, columns=frame.columns)
        extra["tier_override"] = extra["tier_override"].astype("string")
        frame = pd.concat([frame, extra], ignore_index=True)
    return frame


def official_status(path=OFFICIAL, frame: pd.DataFrame | None = None) -> pd.DataFrame:
    table = _official(path)
    if table.empty:
        return pd.DataFrame()
    frame = read() if frame is None else frame
    latest = _last_24h_date(frame)
    today = frame[(frame["date"].astype(str) == latest)].drop_duplicates(["ticker", "channel", "term_months"])
    raw = today.set_index(["ticker", "channel", "term_months"])["rate_raw_percent"]
    terms = set(today.loc[today["rate_raw_percent"].notna(), "term_months"].astype(int))
    table = table[table["term_months"].astype(int).isin(terms)]  # ky han 24hmoney khong theo doi (9, 13, 15T) bo qua
    rows = []
    for row in table.itertuples(index=False):
        now = raw.get((row.ticker, row.channel, row.term_months), np.nan)
        rows.append({
            "ticker": row.ticker, "channel": row.channel, "term_months": int(row.term_months),
            "official": row.rate_percent, "raw_at_check": row.raw_24h, "raw_latest": now, "latest_date": latest,
            "checked": row.checked, "age_days": (pd.Timestamp(latest) - pd.Timestamp(row.checked)).days,
            "added_cell": pd.isna(row.raw_24h),
            "still_matches": bool(pd.isna(row.raw_24h) or (pd.notna(now) and _matches([now], row.raw_24h)[0])),
        })
    return pd.DataFrame(rows)


def _accepted(raw) -> tuple[float, ...]:
    return tuple(raw) if isinstance(raw, (tuple, list)) else (raw,)


def _matches(values, raw):
    values = np.asarray(values, dtype=float)
    return np.any([np.isclose(values, r, rtol=0, atol=1e-9) for r in _accepted(raw)], axis=0)


# ---------------------------------------------------------------------------
# Tu 07/11/2026: bieu lai suat doc THANG tu web tung NH (crawlers/deposit_official.py) thay 24hmoney.
# 24hmoney dung o bang 29/10/2026 (khong doi ca dau thoi gian) va cac trang tong hop khac deu dung / sai mot phan
# (xem docstring deposit_official). Tu ngay chup bieu dau tien, read() bo dong 24hmoney va lap mot mat cat day du
# moi ngay chup: 22 NH x 2 kenh x 7 ky han, moi o lay nguon tot nhat con dung duoc:
#   1. bieu NH doc hom do;
#   2. bieu NH doc trong OFFICIAL_CARRY_DAYS ngay truoc (NH loi crawl vai ngay: giu so bieu gan nhat);
#   3. anh chup bieu doc tay (deposit_official_manual.csv, bac thap nhat) con trong OFFICIAL_MAX_AGE_DAYS ngay;
#   4. bang tong hop blog Techcombank (deposit_techcombank_daily.csv) -- CHI cho kenh ma NH khong co o nao o 1-3
#      (NH khong dang bang online: BID, CTG, MBB, BAB; hoac crawl hong qua lau). Nguoi dung da duyet dung blog cho
#      o NH khong cong bo ngay 03/11/2026. Bo dong TCB cua blog (lech cot, xem doi-chieu 06/11).
# Ky han NH khong niem yet trong kenh da co bieu (ACB online 18-36T, VCB online 18/36T) de trong, khong bu.
OFFICIAL_DAILY = Path("data/interest_rates/deposit_official_daily.csv")
BLOG_DAILY = Path("data/interest_rates/deposit_techcombank_daily.csv")
OFFICIAL_CARRY_DAYS = 7
BLOG_MAX_AGE_DAYS = 3
BLOG_EXCLUDE = {"TCB"}
LISTED = ["VCB", "BID", "CTG", "MBB", "ACB", "TCB", "VPB", "STB", "HDB", "VIB", "TPB",
          "MSB", "OCB", "LPB", "SHB", "EIB", "SSB", "BAB", "BVB", "NAB", "NVB", "PGB"]
SHEET_TERMS = (1, 3, 6, 12, 18, 24, 36)


def _sheet_days(frame: pd.DataFrame, path=OFFICIAL_DAILY) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame(columns=frame.columns)
    sheet = pd.read_csv(path, encoding="utf-8-sig", dtype={"date": str, "effective_date": str})
    if sheet.empty:
        return pd.DataFrame(columns=frame.columns)
    sheet["term_months"] = sheet["term_months"].astype(int)
    manual = _official()
    blog = pd.read_csv(BLOG_DAILY, encoding="utf-8-sig", dtype={"effective_date": str}) if BLOG_DAILY.exists() \
        else pd.DataFrame(columns=["effective_date", "ticker", "term_months", "channel", "rate_percent", "source_url"])
    blog = blog[blog["ticker"].isin(LISTED) & ~blog["ticker"].isin(BLOG_EXCLUDE)]
    names = (frame.dropna(subset=["ticker"]).sort_values("date").drop_duplicates("ticker", keep="last")
             .set_index("ticker")["bank_name"].to_dict())
    rows = []
    for day in sorted(sheet["date"].unique()):
        lo = (pd.Timestamp(day) - pd.Timedelta(days=OFFICIAL_CARRY_DAYS)).strftime("%Y-%m-%d")
        recent = sheet[(sheet["date"] <= day) & (sheet["date"] >= lo)].sort_values("date")
        best = recent.drop_duplicates(["ticker", "channel", "term_months"], keep="last")
        have = {(r.ticker, r.channel) for r in best.itertuples()}
        picked = {(r.ticker, r.channel, r.term_months): (r.rate_percent, "bieu NH" if r.date == day else f"bieu NH {r.date}",
                                                          r.effective_date, r.source_url)
                  for r in best.itertuples()}
        # 3. anh chup doc tay cho kenh chua co bieu tu dong
        if not manual.empty:
            alive = manual[(manual["start"] <= day) & (pd.to_datetime(manual["checked"])
                                                        + pd.Timedelta(days=OFFICIAL_MAX_AGE_DAYS) >= pd.Timestamp(day))]
            alive = alive.sort_values("checked").drop_duplicates(["ticker", "channel", "term_months"], keep="last")
            for r in alive.itertuples():
                if (r.ticker, r.channel) in have or int(r.term_months) not in SHEET_TERMS:
                    continue
                picked[(r.ticker, r.channel, int(r.term_months))] = (r.rate_percent, f"bieu NH doc tay {r.checked}",
                                                                     r.start, r.source_url)
            have |= {(t, c) for t, c, _ in picked}
        # 4. blog Techcombank cho kenh NH khong co o nao
        lo_blog = (pd.Timestamp(day) - pd.Timedelta(days=BLOG_MAX_AGE_DAYS)).strftime("%Y-%m-%d")
        fresh = blog[(blog["effective_date"] <= day) & (blog["effective_date"] >= lo_blog)]
        fresh = fresh.sort_values("effective_date").drop_duplicates(["ticker", "channel", "term_months"], keep="last")
        for r in fresh.itertuples():
            if (r.ticker, r.channel) in have or int(r.term_months) not in SHEET_TERMS:
                continue
            picked[(r.ticker, r.channel, int(r.term_months))] = (r.rate_percent, "blog Techcombank",
                                                                 r.effective_date, r.source_url)
        for (ticker, channel, term), (rate, source, effective, url) in picked.items():
            if ticker not in LISTED or term not in SHEET_TERMS:
                continue
            rows.append({"date": day, "effective_date": effective if isinstance(effective, str) and effective else day,
                         "bank_24hmoney": "", "bank_name": names.get(ticker, ""), "ticker": ticker,
                         "term_months": term, "channel": channel, "rate_percent": float(rate), "source": source,
                         "source_updated_at": "", "source_url": url, "retrieved_at_utc": "",
                         "rate_raw_percent": float(rate)})
    out = pd.DataFrame(rows, columns=[c for c in frame.columns if c != "tier_override"])
    out["tier_override"] = pd.Series(pd.NA, index=out.index, dtype="string")
    return out[frame.columns]


def _last_24h_date(frame: pd.DataFrame) -> str:
    return str(frame.loc[frame["source"] == "24hmoney", "date"].max())


def read(path=MASTER) -> pd.DataFrame:
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
    frame = _apply_official(frame)
    sheet = _sheet_days(frame)
    if not sheet.empty:
        frame = pd.concat([frame[frame["date"].astype(str) < sheet["date"].min()], sheet], ignore_index=True)
    # Ky han 1 den duoi 6 thang khong duoc vuot tran NHNN (4,75% tu 19/06/2023). 24hmoney lam tron 1 chu so nen ghi 4,75
    # thanh 4,8 (CTG, BID, MSB ngay 13/10/2026) -- nhin nhu cao hon 10 NH dung tran trong khi bang nhau. O vuot tran
    # khong qua muc lam tron -> dua ve tran; vuot hon (loi nguon) giu nguyen de validate bao.
    from crawlers.validate import DEPOSIT_CAP_ROUNDING_PP, SBV_DEPOSIT_CAPS
    day = frame["effective_date"].fillna(frame["date"]).astype(str)
    cap = pd.Series(np.nan, index=frame.index)
    for start, value, _ in SBV_DEPOSIT_CAPS:
        cap[day >= start] = value
    excess = frame["rate_percent"] - cap
    rounded = frame["term_months"].between(1, 5) & (excess > 1e-9) & (excess <= DEPOSIT_CAP_ROUNDING_PP + 1e-9)
    frame.loc[rounded, "rate_percent"] = cap[rounded]
    frame.loc[rounded & frame["tier_override"].isna(), "tier_override"] = "lam tron vuot tran NHNN -> tran"
    return frame


def status(path=MASTER) -> pd.DataFrame:
    frame = read(path)
    latest = _last_24h_date(frame)
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
