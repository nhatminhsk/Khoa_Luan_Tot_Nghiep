from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd

PANEL = "data/model/bank_panel_quarterly.csv"
CREDIT = "data/credit/bank_credit_quarterly.csv"
NOTE = "data/credit/bank_asset_quality_quarterly.csv"
FIN_LONG = "data/vnstock_financial/financial_long.csv"
CAR_HALF = "data/credit/bank_car_halfyear.csv"
DEPOSIT_LSTK = "data/interest_rates/deposit_daily.csv"
DEPOSIT_24H = "data/interest_rates/deposit_24hmoney_daily.csv"
# Nguon chinh lai tien gui tu 07/11/2026 (bieu doc thang tu web tung NH, crawlers/deposit_official.py)
DEPOSIT_SHEET = "data/interest_rates/deposit_official_daily.csv"
DEPOSIT_SHEET_MAX_AGE_DAYS = 2
PRICE_DIR = "data/price"
MARKET_DIR = "data/market"
LOG_PATH = "crawl_log.txt"

ERROR, WARN, INFO = "ERROR", "WARN", "INFO"
LEVEL_ORDER = {ERROR: 0, WARN: 1, INFO: 2}

QUARTERS = [f"{y}-Q{q}" for y in range(2018, 2027) for q in range(1, 5)][:35]
N_BANKS, N_QUARTERS = 22, 35

# --------------------------------------------------------------------------
# Nguong mien gia tri.
#
# HARD = khong the dung ve mat dinh nghia hoac ve mat ke toan. Vuot = ERROR.
# SOFT = con nam trong pham vi co the xay ra, nhung hiem den muc phai co nguoi
#        nhin. Vuot = WARN.
#
# Cac nguong SOFT duoi day duoc chon sau khi do tren toan bo 748 o ngay
# 2026-09-10, sao cho chung bat dung nhom gia tri cuc doan da doi chieu tay
# (NVB, VCB 2022-Q2, BAB 2022-Q1) va khong bat gi khac.
# --------------------------------------------------------------------------
HARD_BOUNDS = {
    "npl_percent": (0.0, 100.0),
    "casa_percent": (0.0, 100.0),
    "ldr_computed_percent": (0.0, 500.0),
    "nim_ttm_percent": (-20.0, 30.0),
    "cof_ttm_percent": (0.0, 30.0),
    "earning_asset_yield_ttm_percent": (0.0, 40.0),
    "roa_ttm_percent": (-50.0, 50.0),
    "roe_ttm_percent": (-300.0, 300.0),
    "cir_ttm_approx_percent": (0.0, 5000.0),
    "car_percent": (0.0, 100.0),
    "npl_coverage_percent": (0.0, 5000.0),
    "provision_over_loans_percent": (0.0, 50.0),
    # Ty trong: cho phep 0.5 diem sai so lam tron giua tu va mau.
    "loans_short_share_percent": (-0.01, 100.5),
    "loans_medium_share_percent": (-0.01, 100.5),
    "loans_long_share_percent": (-0.01, 100.5),
    "vnd_deposit_share_percent": (-0.01, 100.5),
    "pb": (0.0, 100.0),
}

SOFT_BOUNDS = {
    "npl_percent": (0.0, 15.0),
    "casa_percent": (0.0, 60.0),
    "ldr_computed_percent": (30.0, 200.0),
    "nim_ttm_percent": (0.0, 12.0),
    "cof_ttm_percent": (0.0, 12.0),
    "earning_asset_yield_ttm_percent": (0.0, 20.0),
    "roa_ttm_percent": (-10.0, 10.0),
    "roe_ttm_percent": (-60.0, 60.0),
    "cir_ttm_approx_percent": (0.0, 150.0),
    # Nguong duoi 8% la muc von toi thieu theo Thong tu 41; duoi do la
    # su kien phai giai thich, khong phai bien dong thong thuong.
    "car_percent": (8.0, 30.0),
    "npl_coverage_percent": (0.0, 500.0),
    "provision_over_loans_percent": (0.0, 10.0),
    "loans_short_share_percent": (0.0, 100.0),
    "loans_medium_share_percent": (0.0, 100.0),
    "loans_long_share_percent": (0.0, 100.0),
    "vnd_deposit_share_percent": (0.0, 100.0),
    "loans_yoy_percent": (-50.0, 150.0),
    "pe": (-100.0, 300.0),
    "pb": (0.0, 15.0),
}

# Do phu da ghi nhan ngay 2026-09-10. Chi kiem chieu GIAM: mot crawler mat dan
# dong sau moi lan chay khong bao loi, chi lo ra khi so voi muc nen nay.
# Tang la binh thuong (them quy moi) - cap nhat lai bang nay khi do phu tang on dinh.
COVERAGE_BASELINE = {
    "loans_vnd": 748, "deposits_vnd": 748, "total_assets_vnd": 748,
    "ldr_computed_percent": 748, "provision_over_loans_percent": 748,
    "npl_percent": 737, "casa_percent": 737,
    # cof 738 -> 689, loi suat 738 -> 662, cir 738 -> 737 ngay 31/10/2026: 0 cua MAS la
    # thieu, truoc do bi cong nhu so that (vnstock_ratio_mas.ZERO_MEANS_MISSING).
    "nim_ttm_percent": 738, "cof_ttm_percent": 689,
    "earning_asset_yield_ttm_percent": 662, "roe_ttm_percent": 738,
    "roa_ttm_percent": 738, "cir_ttm_approx_percent": 737,
    # npl_coverage 649 -> 737 ngay 15/09/2026: build_panel tinh lap bao phu tu
    # thuyet minh o nhung o VCI trong (ke ca 2021-Q2 va quy lech 2022-Q1).
    "loans_short_share_percent": 736, "npl_coverage_percent": 737,
    "loans_yoy_percent": 660, "vnd_deposit_share_percent": 522,
    "car_percent": 291,
}

# Hinh dang da do cua file ratio thoi (2026-09-10). Day KHONG phai danh sach
# loi can sua - day la TRIPWIRE: build_panel dang chuan hoa dua tren dung nhung
# gia dinh nay (nhan 100, lay tri tuyet doi, coi 0 la thieu). Neu nguon am tham
# doi cach luu, cac gia dinh do tro thanh sai va phai duoc xem lai NGAY.
#
# `decimal_max` phai dat rieng cho tung chi tieu, khong dung chung mot nguong.
# Ly do: mot ty le luu dang thap phan van co the vuot 1,0 neu ban than ty le do
# vuot 100%. NPL Coverage that su chay toi 504% (= 5,04 thap phan) va CIR toi
# 348%; dat chung nguong 1,5 se bao sai cho ca hai. Nguong duoi day = tran hop
# ly cua chi tieu, quy ve thang thap phan.
RATIO_SHAPE = {
    # Khop theo `id`: tu 14/09/2026 raw/ lay ban day du va cot `name` la tieng Viet,
    # khop theo ten tieng Anh nhu truoc se bao "mat chi tieu" gia.
    # NIM va COF khong bao gio vuot vai chuc phan tram -> 1,5 la du rong.
    "Cost of Funds": {"id": "RT_BANK_COF", "decimal_max": 1.5, "mostly_negative": True},
    "Net Interest Margin": {"id": "RT_BANK_NIM", "decimal_max": 1.5},
    "Capital Adequacy Ratio": {"id": "RT_BANK_CAR", "decimal_max": 1.5, "mostly_zero": True},
    # Hai chi tieu duoi day vuot 100% la binh thuong.
    "NPL Coverage": {"id": "RT_BANK_NPL_COVERAGE", "decimal_max": 50.0, "mostly_negative": True},
    "Cost to Income": {"id": "RT_BANK_CIR", "decimal_max": 50.0, "mostly_negative": True},
}

# Lech toi da chap nhan duoc giua hai nguon lai suat doc lap, tinh bang diem %.
# Do tren 1.274 cap so sanh duoc ngay 2026-09-10: trung vi 0,0 va 98,4% so cap
# lech duoi 0,5 diem. Nguong nay bat dung ba o thuc su mau thuan.
DEPOSIT_XSOURCE_TOLERANCE_PP = 0.5

# Bien do toi da con coi la sai lech DIEU CHINH cua nha cung cap thay vi du lieu
# hong. Do tren 54 phien vi pham ngay 2026-09-10: lech trung vi 0,50% va lon
# nhat 2,42%. Vuot 5% thi khong con giai thich duoc bang dieu chinh co tuc.
OHLC_MAX_DEVIATION_PERCENT = 5.0

# Nhung o mau thuan giua hai nguon DA duoc phan dinh bang bang chung, kem ly do.
# Day khong phai co che tat canh bao: o da phan dinh van hien ra, chi ha xuong
# WARN va di kem can cu. O CHUA phan dinh van la ERROR de con phai quyet dinh.
# Bo mot muc khoi bang nay = o do quay lai ERROR.
# Cot ma gia tri 0 la KY HIEU THIEU chu khong phai so do duoc, kem cot mau dung
# de chung minh dieu do. Da doi chieu ngay 2026-09-10 voi phien giao dich dau
# tien trong data/price: toan bo o pe=0 va pb=0 nam trong giai doan truoc niem
# yet, khong o nao sau do.
#
# `dividend_yield` CO Y KHONG nam trong bang nay: 508 trong 576 o bang 0 cua no
# nam sau ngay niem yet va la su that - ngan hang khong tra co tuc tien mat.
# Them no vao day se xoa mat mot su that thay vi vach ra mot loi.
ZERO_MEANS_MISSING = {
    "pe": "eps_vnd",
    "pb": "bvps_vnd",
}

# Tran lai suat tien gui ky han 1 den duoi 6 thang cua NHNN, theo ngay hieu luc.
# Niem yet vuot tran la bat kha thi -> ERROR. Rieng vuot <= 0,05 diem la dau vet
# 24hmoney lam tron 4,75 thanh 4,8 (1 chu so thap phan) -> WARN.
SBV_DEPOSIT_CAPS = [
    ("2022-10-25", 6.00, "QĐ 1813/QĐ-NHNN"),
    ("2023-04-03", 5.50, "QĐ 574/QĐ-NHNN"),
    ("2023-05-25", 5.00, "QĐ 951/QĐ-NHNN"),
    ("2023-06-19", 4.75, "QĐ 1124/QĐ-NHNN ky 16/06/2023"),
    # Kiem 14/10/2026: van hieu luc, chua co quyet dinh moi (bao 27/02/2026: hon 10 NH "kich tran 4,75%" ky han 1 thang;
    # 13/10/2026: 10 NH ghi dung 4,75 online 1 thang, khong o nao tren 4,8). QD 2411 thay QD 1124, giu muc.
    ("2024-11-20", 4.75, "QĐ 2411/QĐ-NHNN ky 01/11/2024 theo TT 48/2024/TT-NHNN (thay QĐ 1124)"),
]
DEPOSIT_CAP_ROUNDING_PP = 0.05

# O vuot tran da xem xet. `dates` = None nghia la moi ngay (loi lap lai hang ngay
# cua cung mot nguon); co tap ngay thi chi mien dung nhung ngay do.
DEPOSIT_CAP_RESOLVED = {
    ("deposit_daily", "ACB", 3, "online"): {
        "dates": None,
        "evidence": "acb.com.vn/lai-suat-tien-gui ngay 15/09/2026, muc 3 'Tien gui online': "
                    "3 thang 4,70 (<200 trieu) den 4,75 (>=5 ty); 5,10 la muc 6 thang bac "
                    ">=5 ty -> laisuattietkiem lech ky han. 24hmoney ghi 4,70, khop web. "
                    "Dac trung khong dung deposit_daily",
        "reviewed": "2026-09-15",
    },
    **{
        ("deposit_24hmoney", ticker, term, channel): {
            "dates": {"2023-08-05"},
            "evidence": "ban chup Wayback cua 24hmoney ngay 05/08/2023 vuot tran 4,75% "
                        "dang co hieu luc; khong con nguon goc de kiem lai. Dac trung chi "
                        "dung ky han 12 thang nen khong anh huong mo hinh",
            "reviewed": "2026-09-15",
        }
        for ticker, term, channel in (("ACB", 3, "online"), ("PGB", 1, "quay"),
                                      ("PGB", 3, "quay"))
    },
}

# Cot ty trong co cau: nhay manh mot quy roi quay ve gan nhu nguyen cho gan nhu
# chac chan la nguon ghi nham dong (STB 2026-Q2 tien gui VND 2,67%, PGB 2022-Q3
# 49,46% giua hai quy ~98,6%). Do tren panel 15/09/2026: voi nguong 10 diem, chi
# bat dung hai o do. KHONG ap cho bao phu no xau - cot do nhay quy 2/quy 4 that.
SHARE_JUMP_COLUMNS = ["vnd_deposit_share_percent", "casa_percent",
                      "loans_short_share_percent", "loans_medium_share_percent",
                      "loans_long_share_percent"]
SHARE_JUMP_PP = 10.0

XSOURCE_RESOLVED = {
    ("STB", 1, "quay"): {
        "winner": "deposit_24hmoney",
        "evidence": "ba tin hieu doc lap cung chi ve 24hmoney: (1) chinh "
                    "laisuattietkiem ghi prev_rate = 4,75 cho o nay, (2) cau truc "
                    "ky han cua lstk gay dut o dung 1 thang (0,50 roi 4,75 o 3 "
                    "thang), (3) 24hmoney cho duong cong lien tuc 4,6 / 4,6 / 6,3",
        "reviewed": "2026-09-10",
    },
    ("BID", 3, "quay"): {
        "winner": "deposit_24hmoney",
        "evidence": "phep thu cat ngang: buoc nhay 1 thang -> 3 thang tai quay "
                    "cua 22 NH co trung vi 0,10 diem va cao nhat 0,50 diem "
                    "(SSB); KHONG ngan hang nao vuot 2,0 diem. lstk khai BID "
                    "nhay +2,35 diem - gap 4,7 lan muc cao nhat toan nganh. "
                    "24hmoney khai +0,30 diem, nam trong khoang binh thuong",
        "reviewed": "2026-09-10",
    },
    ("BID", 6, "quay"): {
        "winner": "deposit_24hmoney",
        "evidence": "cung mot duong cong hong voi o 3 thang: lstk cho BID "
                    "2,10 / 4,45 / 4,75 / 5,90 con 24hmoney cho 2,10 / 2,40 / "
                    "3,50 / 5,90 - hai nguon khop nhau o 1 thang va 12 thang, "
                    "chi lech o hai o giua. Ngoai ra lstk quay 6 thang (4,75) "
                    "trung dung gia tri 24hmoney ghi cho kenh ONLINE 3 thang, "
                    "dau hieu lstk lech kenh hoac lech ky han o rieng BID",
        "reviewed": "2026-09-10",
    },
    ("VPB", 6, "quay"): {
        "winner": "bieu chinh thuc (deposit_tiers.TIER_OVERRIDES)",
        "evidence": "bieu chinh thuc VPBank ap dung tu 23/09/2026 (KHCN, lai cuoi ky, < 1 ty): tai quay "
                    "6/12/24 thang = 6,80 / 6,90 / 6,90; online = 7,00 / 7,10 / 7,10. KHONG nguon nao "
                    "dung: lstk ghi so ONLINE vao kenh quay (lstk khong co dong online nao cua VPB), "
                    "24hmoney giu so cu tu truoc 23/09. Du lieu dung qua deposit_tiers.TIER_OVERRIDES",
        "reviewed": "2026-10-01",
    },
    ("VPB", 12, "quay"): {
        "winner": "bieu chinh thuc (deposit_tiers.TIER_OVERRIDES)",
        "evidence": "bieu chinh thuc VPBank ap dung tu 23/09/2026 (KHCN, lai cuoi ky, < 1 ty): tai quay "
                    "6/12/24 thang = 6,80 / 6,90 / 6,90; online = 7,00 / 7,10 / 7,10. KHONG nguon nao "
                    "dung: lstk ghi so ONLINE vao kenh quay (lstk khong co dong online nao cua VPB), "
                    "24hmoney giu so cu tu truoc 23/09. Du lieu dung qua deposit_tiers.TIER_OVERRIDES",
        "reviewed": "2026-10-01",
    },
    ("VPB", 24, "quay"): {
        "winner": "bieu chinh thuc (deposit_tiers.TIER_OVERRIDES)",
        "evidence": "bieu chinh thuc VPBank ap dung tu 23/09/2026 (KHCN, lai cuoi ky, < 1 ty): tai quay "
                    "6/12/24 thang = 6,80 / 6,90 / 6,90; online = 7,00 / 7,10 / 7,10. KHONG nguon nao "
                    "dung: lstk ghi so ONLINE vao kenh quay (lstk khong co dong online nao cua VPB), "
                    "24hmoney giu so cu tu truoc 23/09. Du lieu dung qua deposit_tiers.TIER_OVERRIDES",
        "reviewed": "2026-10-01",
    },
    **{("SHB", term, "online"): {
        "winner": "deposit_24hmoney",
        "evidence": "nguoi dung tu kiem tra 14/10/2026 va xac nhan so 24hmoney (6T 7,7, 12T 7,8). Bieu PDF dang "
                    "tren shb.com.vn (file 01/07/2026, QD 1221/2026 hieu luc 11/4) van ghi 6,20 / 6,50 nen lstk "
                    "khop bieu cu; khong ghi de truoc 20/10. TU 20/10/2026 co bieu moi (QD 3990/2026/QD-TGD, online "
                    "6T 5,70 / 12T 6,00, VietnamNet 21/10 cung ghi vay) -> tu ngay do lay deposit_tiers.OFFICIAL",
        "reviewed": "2026-10-22",
    } for term in (6, 12)},
    # Dot giam lai 20-22/10/2026 (CV 9608/NHNN-CSTT): lstk cap nhat, 24hmoney dung yen tu 17/10. Bieu chinh thuc
    # doc ngay 22/10 khop lstk o TPB quay 6T (5,00), ACB online 12T (5,20), LPB online 18T (6,55); SHB online
    # 18-36T lstk ghi so lanh lai hang thang (5,94 / 6,02) con bieu cuoi ky la 6,10 / 6,20.
    **{key: {
        "winner": "bieu chinh thuc (deposit_tiers.OFFICIAL, doc 22/10/2026)",
        "evidence": "24hmoney khong cap nhat sau dot giam lai 20-22/10/2026; so dung qua anh chup bieu chinh thuc "
                    "data/interest_rates/deposit_official_manual.csv",
        "reviewed": "2026-10-22",
    } for key in [("ACB", 12, "online"), ("LPB", 18, "online"), ("SHB", 18, "online"), ("SHB", 24, "online"),
                  ("SHB", 36, "online"), ("TPB", 6, "quay"), ("TPB", 12, "online")]},
    ("BAB", 6, "quay"): {
        "winner": "deposit_daily",
        "evidence": "Bieu tai quay tren baca-bank.vn (trang lai-xuat.aspx, doc 23/10/2026, hieu luc 19/10) ghi 6T 6,55 = "
                    "lstk; 24hmoney 5,55. Da ghi vao deposit_tiers.OFFICIAL",
        "reviewed": "2026-10-23",
    },
    **{("OCB", term, "online"): {
        "winner": "deposit_daily",
        "evidence": "Bang lai suat OCB hieu luc 20/10/2026 (webocb-api.ocb.com.vn/Resources/Files/20261019184205_3-"
                    "20.10.2026-...pdf), bac duoi 100 trieu online 6T 6,0 / 12T 6,3 = lstk; 24hmoney dung yen 6,7 / 7,0",
        "reviewed": "2026-10-23",
    } for term in (6, 12)},
    **{("BID", term, "online"): {
        "winner": "deposit_24hmoney toi 28/10; tu 29/10 bang tong hop Techcombank (deposit_tiers.TIER_OVERRIDES)",
        "evidence": "BIDV tang lai online thang 8/2026: 6-11T va 13-36T len 7,2, 12T len 7,4 (bai 24hmoney "
                    "04/08/2026 20:37 va 05/08/2026 11:02; cafeland 'BIDV tang manh lai suat tien gui online'). "
                    "24hmoney cap nhat tre tu 05/10 (7,2 / 7,4), lstk van giu so truoc dot tang (6,6 / 6,8). "
                    "BIDV khong dang bang online tren bidv.com.vn. Sau dot giam lai 20-22/10, bang Techcombank "
                    "03/11 ghi 6,6 / 6,8 (ban Wayback 17/10 con 7,2 / 7,4), trung lstk; 24hmoney dung o 29/10",
        "reviewed": "2026-11-03",
    } for term in (6, 12)},
    **{("BID", term, "online"): {
        "winner": "deposit_24hmoney",
        "evidence": "21-23/10/2026 lstk chep nguyen bieu TAI QUAY moi cua BIDV (bidv.com.vn doc 22/10: 2,10 / 2,40 / "
                    "3,00 / 5,40 / 5,40 / 5,50 / 5,50) vao kenh online; truoc 21/10 va tu 24/10 lstk online lai khop "
                    "24hmoney (4,75 / 4,75 / 6,6 / 6,8 / 6,8). Ky 1-3T 24hmoney 4,8 la 4,75 lam tron, read() dua ve tran",
        "reviewed": "2026-11-06",
    } for term in (1, 3, 18, 24, 36)},
    **{("TCB", term, "online"): {
        "winner": "bieu chinh thuc 24/10/2026 (deposit_tiers.OFFICIAL)",
        "evidence": "Bieu KHCN Techcombank ap dung tu 24/10/2026 (tcb-bieu-lai-suat-tien-gui-tiet-kiem-tien-gui-co-ky-"
                    "han-20261024.pdf, doc 06/11): online KH THUONG 4,25 / 4,55 / 6,05 / 6,25 / 5,35 (1/3/6/12/13-36T). "
                    "KHONG nguon nao dung: lstk ghi cot PRIVATE (4,40 / 4,65 / 6,20 / 6,40 / 5,50), 24hmoney tu 27/10 "
                    "chep lech cot tu blog Techcombank (12T 5,35 la so 13-36T; tai quay 18-36T 5,35 la so online)",
        "reviewed": "2026-11-06",
    } for term in (1, 3, 6, 12, 18, 24, 36)},
}


@dataclass
class Finding:
    level: str
    check: str
    table: str
    message: str
    sample: list = field(default_factory=list)

    def as_dict(self):
        return {
            "level": self.level, "check": self.check, "table": self.table,
            "message": self.message, "sample": self.sample,
        }


def _log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")


def _read(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False, **kw)


def _round(value, digits=4):
    if isinstance(value, float) and np.isfinite(value):
        return round(value, digits)
    return value


def _has(frame, cols):
    return all(c in frame.columns for c in cols)


def _sample(frame, cols, limit=6):
    cols = [c for c in cols if c in frame.columns]
    head = frame[cols].head(limit)
    records = head.astype(object).where(head.notna(), None).to_dict("records")
    return [{k: _round(v) for k, v in row.items()} for row in records]


# --------------------------------------------------------------------------
# Cac phep kiem tren panel
# --------------------------------------------------------------------------
def check_panel_keys(panel):
    out = []
    if not _has(panel, ["ticker", "period"]):
        return [Finding(ERROR, "panel.keys", PANEL,
                        "thieu cot khoa 'ticker' hoac 'period' - panel khong "
                        "dung duoc, moi phep kiem khac deu vo nghia")]

    dup = panel[panel.duplicated(["ticker", "period"], keep=False)]
    if len(dup):
        out.append(Finding(
            ERROR, "panel.keys", PANEL,
            f"{len(dup)} dong trung khoa (ticker, period)",
            _sample(dup, ["ticker", "period"])))

    missing = sorted(set(QUARTERS) - set(panel["period"]))
    if missing:
        out.append(Finding(
            ERROR, "panel.keys", PANEL,
            f"thieu {len(missing)} quy trong luoi: {missing}"))

    expected = N_BANKS * N_QUARTERS
    if len(panel) != expected:
        out.append(Finding(
            ERROR, "panel.keys", PANEL,
            f"{len(panel)} dong, ky vong {expected} = {N_BANKS} NH x {N_QUARTERS} quy"))

    uneven = panel.groupby("ticker").size()
    uneven = uneven[uneven != N_QUARTERS]
    if len(uneven):
        out.append(Finding(
            ERROR, "panel.keys", PANEL,
            f"{len(uneven)} NH khong du {N_QUARTERS} quy",
            [{"ticker": t, "n_quarters": int(n)} for t, n in uneven.items()]))

    if not out:
        out.append(Finding(
            INFO, "panel.keys", PANEL,
            f"khoa sach: {len(panel)} dong = {N_BANKS} x {N_QUARTERS}, "
            f"khong trung, khong thieu quy"))
    return out


def check_panel_bounds(panel):
    out = []
    hard_hits = {}
    for col, (lo, hi) in HARD_BOUNDS.items():
        if col not in panel.columns:
            continue
        bad = panel[(panel[col] < lo) | (panel[col] > hi)]
        if len(bad):
            hard_hits[col] = set(bad.index)
            out.append(Finding(
                ERROR, "panel.bounds", PANEL,
                f"{col}: {len(bad)} o ngoai mien co the co [{lo}, {hi}] "
                f"(thuc te {panel[col].min():.4f} .. {panel[col].max():.4f})",
                _sample(bad, ["ticker", "period", col])))

    for col, (lo, hi) in SOFT_BOUNDS.items():
        if col not in panel.columns:
            continue
        bad = panel[(panel[col] < lo) | (panel[col] > hi)]
        bad = bad.drop(index=hard_hits.get(col, set()), errors="ignore")
        if len(bad):
            if "ticker" in bad.columns:
                banks = sorted(bad["ticker"].unique())
                where = f"o {len(banks)} NH ({', '.join(banks)})"
            else:
                where = ""
            out.append(Finding(
                WARN, "panel.bounds", PANEL,
                f"{col}: {len(bad)} o ngoai nguong thuong gap [{lo}, {hi}] "
                f"{where} - kiem tay truoc khi loc",
                _sample(bad.sort_values(col), ["ticker", "period", col])))
    return out


def check_panel_identities(panel):
    out = []
    money = ["loans_vnd", "deposits_vnd", "total_assets_vnd"]

    if _has(panel, money + ["ldr_computed_percent"]):
        ok = panel["deposits_vnd"] > 0
        recomputed = panel.loc[ok, "loans_vnd"] / panel.loc[ok, "deposits_vnd"] * 100
        gap = (recomputed - panel.loc[ok, "ldr_computed_percent"]).abs()
        off = panel.loc[ok][gap > 0.01]
        if len(off):
            out.append(Finding(
                ERROR, "panel.identity", PANEL,
                f"ldr_computed_percent khong khop du no/tien gui o {len(off)} dong "
                f"(lech toi da {gap.max():.4f} diem)",
                _sample(off, ["ticker", "period", "ldr_computed_percent"])))

    shares = ["loans_short_share_percent", "loans_medium_share_percent",
              "loans_long_share_percent"]
    if _has(panel, shares):
        # Chi kiem duoc nhung dong co DU ca ba thanh phan; thieu mot phan thi
        # tong khong noi len dieu gi. Bao so dong khong kiem duoc de con biet.
        has = panel[shares].notna().all(axis=1)
        partial = panel[shares].notna().any(axis=1) & ~has
        total = panel.loc[has, shares].sum(axis=1)
        off = panel.loc[has][(total < 99.5) | (total > 100.5)]
        if len(off):
            out.append(Finding(
                ERROR, "panel.identity", PANEL,
                f"ty trong ky han cho vay khong cong bang 100% o {len(off)}/"
                f"{int(has.sum())} dong kiem duoc",
                _sample(off, ["ticker", "period"] + shares)))
        if int(partial.sum()):
            out.append(Finding(
                WARN, "panel.identity", PANEL,
                f"{int(partial.sum())} dong chi co mot phan ty trong ky han - "
                f"khong kiem duoc tong 100%",
                _sample(panel[partial], ["ticker", "period"] + shares)))

    if _has(panel, money):
        nonpos = panel[(panel["loans_vnd"] <= 0) | (panel["deposits_vnd"] <= 0)
                       | (panel["total_assets_vnd"] <= 0)]
        if len(nonpos):
            out.append(Finding(
                ERROR, "panel.identity", PANEL,
                f"{len(nonpos)} dong co du no, tien gui hoac tong tai san <= 0",
                _sample(nonpos, ["ticker", "period"] + money)))

        over = panel[panel["loans_vnd"] > panel["total_assets_vnd"]]
        if len(over):
            out.append(Finding(
                ERROR, "panel.identity", PANEL,
                f"{len(over)} dong co du no lon hon tong tai san",
                _sample(over, ["ticker", "period", "loans_vnd",
                               "total_assets_vnd"])))

    rates = ["earning_asset_yield_ttm_percent", "nim_ttm_percent"]
    if _has(panel, rates):
        # NIM = loi suat - chi phi lai / tai san sinh lai, ma chi phi lai khong am. Sau khi
        # sua 0 cua MAS: 45 o vi pham -> 0, khoang cach nho nhat 1,73 diem, nen khong can dung sai.
        under = panel[panel[rates[0]] < panel[rates[1]]]
        if len(under):
            out.append(Finding(
                ERROR, "panel.identity", PANEL,
                f"{len(under)} dong co loi suat tai san sinh lai thap hon NIM - bat kha thi, "
                f"thuong la quy thieu bi cong nhu so 0 khi dung TTM",
                _sample(under, ["ticker", "period", "yield_src", "nim_src"] + rates)))

    if not out:
        out.append(Finding(
            INFO, "panel.identity", PANEL,
            "cac dang thuc noi bo deu dung: LDR khop, ty trong ky han cong 100%, "
            "khong co gia tri am, du no khong vuot tong tai san, loi suat khong thap hon NIM"))
    return out


def check_degenerate_ratios(panel):
    out = []
    for ratio_col, base_col in ZERO_MEANS_MISSING.items():
        if not _has(panel, [ratio_col, base_col]):
            continue
        bad = panel[(panel[ratio_col] == 0) & (panel[base_col] != 0)
                    & panel[base_col].notna()]
        if len(bad):
            banks = sorted(bad["ticker"].unique()) if "ticker" in bad else []
            out.append(Finding(
                ERROR, "panel.degenerate", PANEL,
                f"{ratio_col}: {len(bad)} o bang DUNG 0 trong khi {base_col} van "
                f"khac 0 ({len(banks)} NH: {', '.join(banks)}). Nguon dang dung 0 "
                f"lam ky hieu thieu - de nguyen thi min-max se cham nhung o nay la "
                f"tot nhat thang do",
                _sample(bad, ["ticker", "period", ratio_col, base_col])))

    if "eps_vnd" in panel.columns and "pe" in panel.columns:
        bad = panel[(panel["eps_vnd"] == 0) & panel["pe"].notna()]
        if len(bad):
            out.append(Finding(
                ERROR, "panel.degenerate", PANEL,
                f"{len(bad)} dong co eps_vnd = 0 nhung van co P/E "
                f"(len toi {panel['pe'].max():,.0f}). P/E nay la rac: phai coi la "
                f"NaN truoc moi phep chuan hoa, neu khong mot o se nuot tron "
                f"bien do min-max cua ca 22 NH",
                _sample(bad, ["ticker", "period", "eps_vnd", "pe"])))

    if "bvps_vnd" in panel.columns and "pb" in panel.columns:
        bad = panel[(panel["bvps_vnd"] == 0) & panel["pb"].notna()]
        if len(bad):
            out.append(Finding(
                ERROR, "panel.degenerate", PANEL,
                f"{len(bad)} dong co bvps_vnd = 0 nhung van co P/B",
                _sample(bad, ["ticker", "period", "bvps_vnd", "pb"])))
    return out


def check_coverage_regression(panel):
    out = []
    drops = []
    for col, base in COVERAGE_BASELINE.items():
        if col not in panel.columns:
            out.append(Finding(
                ERROR, "panel.coverage", PANEL, f"mat han cot {col}"))
            continue
        now = int(panel[col].notna().sum())
        if now < base:
            drops.append({"column": col, "baseline": base, "now": now,
                          "lost": base - now})
    if drops:
        worst = max(d["lost"] for d in drops)
        out.append(Finding(
            ERROR, "panel.coverage", PANEL,
            f"{len(drops)} cot tut do phu so voi muc nen 2026-09-10 "
            f"(mat nhieu nhat {worst} o)", drops[:8]))
    else:
        out.append(Finding(
            INFO, "panel.coverage", PANEL,
            f"do phu khong tut o ca {len(COVERAGE_BASELINE)} cot theo doi"))
    return out


def check_panel_share_jumps(panel):
    out = []
    if not _has(panel, ["ticker", "period"]):
        return out
    frame = panel.assign(
        _q=panel["period"].str[:4].astype(int) * 4 + panel["period"].str[-1].astype(int))
    hits = []
    for col in [c for c in SHARE_JUMP_COLUMNS if c in frame.columns]:
        for ticker, group in frame.dropna(subset=[col]).groupby("ticker"):
            group = group.sort_values("_q")
            q, v = group["_q"].to_numpy(), group[col].to_numpy()
            for i in range(1, len(v) - 1):
                if q[i] - q[i - 1] != 1 or q[i + 1] - q[i] != 1:
                    continue
                if (abs(v[i] - v[i - 1]) > SHARE_JUMP_PP and abs(v[i] - v[i + 1]) > SHARE_JUMP_PP
                        and abs(v[i + 1] - v[i - 1]) <= SHARE_JUMP_PP / 4):
                    hits.append({"ticker": ticker, "period": group["period"].iloc[i],
                                 "column": col, "before": _round(float(v[i - 1])),
                                 "value": _round(float(v[i])), "after": _round(float(v[i + 1]))})
            # Quy truoc co the trong mot vai o (STB 2025-Q3): lay toi da 4 gia tri
            # co that trong 6 quy lien truoc, can it nhat 3.
            recent = (q[:-1] >= q[-1] - 6) if len(q) > 1 else np.array([], dtype=bool)
            base = v[:-1][recent][-4:]
            if len(base) >= 3:
                if (np.ptp(base) <= SHARE_JUMP_PP / 4
                        and abs(v[-1] - np.median(base)) > SHARE_JUMP_PP):
                    hits.append({"ticker": ticker, "period": group["period"].iloc[-1],
                                 "column": col, "before": _round(float(np.median(base))),
                                 "value": _round(float(v[-1])), "after": None})
    if hits:
        out.append(Finding(
            WARN, "panel.jump", PANEL,
            f"{len(hits)} o ty trong co cau nhay qua {SHARE_JUMP_PP:g} diem roi quay ve "
            f"(hoac lech khoi 4 quy truoc on dinh) - gan nhu chac la nguon ghi nham dong, "
            f"doi chieu thuyet minh BCTC roi ghi vao vnstock_note.CORRECTIONS", hits[:8]))
    else:
        out.append(Finding(
            INFO, "panel.jump", PANEL,
            f"khong o ty trong co cau nao nhay qua {SHARE_JUMP_PP:g} diem roi quay ve "
            f"({len(SHARE_JUMP_COLUMNS)} cot)"))
    return out


# --------------------------------------------------------------------------
# Loi rieng cua nguon VCI
# --------------------------------------------------------------------------
def check_vci_stale_rows():
    out = []
    if not os.path.exists(CREDIT):
        return [Finding(WARN, "vci.stale", CREDIT, "khong tim thay file")]
    cols = ["npl_percent", "npl_coverage_percent", "ldr_percent", "nim_percent"]
    credit = _read(CREDIT)
    if not _has(credit, ["ticker", "period"] + cols):
        return [Finding(WARN, "vci.stale", CREDIT, "thieu cot de kiem")]
    credit = credit.assign(
        _q=credit["period"].str[:4].astype(int) * 4 + credit["period"].str[-1].astype(int)
    ).sort_values(["ticker", "_q"])
    prev = credit.groupby("ticker")[cols + ["_q"]].shift(1)
    consecutive = (credit["_q"] - prev["_q"]) == 1
    same = sum((credit[c] == prev[c]) & credit[c].notna() for c in cols)
    stale = credit[consecutive & (same >= 3)]
    if len(stale):
        out.append(Finding(
            ERROR, "vci.stale", CREDIT,
            f"{len(stale)} NH-quy co >= 3/4 ty le trung dung quy truoc - dong chep lai "
            f"cua VCI lot qua lop sua; kiem module nao doc raw/*_ratio_quarter.csv "
            f"khong qua crawlers.vci_ratio.read", _sample(stale, ["ticker", "period"] + cols)))
    else:
        try:
            from crawlers import vci_ratio
            fixed = vci_ratio.repairs()
            detail = (f"; lop sua da xu ly {len(fixed)} NH-quy chep lai/lech quy "
                      f"({int(fixed['action'].str.startswith('lay').sum())} chuyen so that ve "
                      f"dung quy)") if len(fixed) else ""
        except Exception as exc:  # thieu raw/ khong duoc lam hong ca bao cao
            detail = f"; khong doc duoc bang sua ({type(exc).__name__})"
        out.append(Finding(
            INFO, "vci.stale", CREDIT,
            f"khong con dong ratio nao chep nguyen quy truoc{detail}"))
    return out


def check_note_currency_identity():
    out = []
    if not os.path.exists(NOTE):
        return [Finding(WARN, "note.identity", NOTE, "khong tim thay file")]
    note = _read(NOTE)
    cols = ["deposits_vnd_only_vnd", "deposits_by_currency_total_vnd"]
    if not _has(note, ["ticker", "period"] + cols):
        return [Finding(WARN, "note.identity", NOTE, "thieu cot tien gui theo loai tien")]
    both = note.dropna(subset=cols)
    # VND la mot phan cua tong, khong co sai so lam tron nao dua no vuot tong. BAB
    # 2022-Q1 chi vuot 0,12% (= dung phan ngoai te) - dung sai phai sat 0.
    over = both[both[cols[0]] > both[cols[1]] * (1 + 1e-6)]
    if len(over):
        out.append(Finding(
            ERROR, "note.identity", NOTE,
            f"{len(over)} NH-quy co tien gui VND lon hon tong tien gui - nguon cong "
            f"nham ngoai te vao; doi chieu thuyet minh roi ghi vnstock_note.CORRECTIONS",
            _sample(over, ["ticker", "period"] + cols)))
    else:
        out.append(Finding(
            INFO, "note.identity", NOTE,
            f"{len(both)} NH-quy: tien gui VND khong vuot tong tien gui"))
    return out


# --------------------------------------------------------------------------
# Tripwire cho bay don vi / dau
# --------------------------------------------------------------------------
def check_ratio_shape():
    out = []
    if not os.path.exists(FIN_LONG):
        return [Finding(WARN, "ratio.shape", FIN_LONG, "khong tim thay file")]

    frame = _read(FIN_LONG, usecols=["statement", "id", "unit", "value"])
    ratio = frame[frame["statement"] == "ratio"]
    if ratio.empty:
        return [Finding(ERROR, "ratio.shape", FIN_LONG,
                        "khong con dong nao co statement='ratio'")]

    for label, shape in RATIO_SHAPE.items():
        rows = ratio[ratio["id"] == shape["id"]]
        if rows.empty:
            out.append(Finding(
                ERROR, "ratio.shape", FIN_LONG,
                f"khong con chi tieu '{label}' ({shape['id']}) - nguon da doi id, "
                f"build_panel se lay thieu am tham"))
            continue

        values = pd.to_numeric(rows["value"], errors="coerce").dropna()
        if values.empty:
            out.append(Finding(ERROR, "ratio.shape", FIN_LONG,
                               f"'{label}': khong con gia tri so nao"))
            continue

        ceiling = shape.get("decimal_max")
        if ceiling is not None and values.abs().max() > ceiling:
            out.append(Finding(
                ERROR, "ratio.shape", FIN_LONG,
                f"'{label}': gia tri khong con o thang thap phan "
                f"(|max| = {values.abs().max():.4f}, tran ky vong {ceiling}). "
                f"build_panel dang nhan 100 cho cot nay - phai xem lai truoc khi "
                f"chay tiep"))

        if shape.get("mostly_negative"):
            share = float((values < 0).mean())
            if share < 0.5:
                out.append(Finding(
                    ERROR, "ratio.shape", FIN_LONG,
                    f"'{label}': chi con {share:.1%} gia tri am (truoc day phan "
                    f"lon am). build_panel dang lay tri tuyet doi - neu nguon da "
                    f"sua dau thi phep do tro thanh sai"))
            else:
                out.append(Finding(
                    INFO, "ratio.shape", FIN_LONG,
                    f"'{label}': {share:.1%} gia tri am, thang thap phan, "
                    f"{int((values == 0).sum())} o bang 0 - dung nhu gia dinh"))
        elif not shape.get("mostly_zero"):
            out.append(Finding(
                INFO, "ratio.shape", FIN_LONG,
                f"'{label}': thang thap phan, |max| = {values.abs().max():.4f} "
                f"tren {len(values)} gia tri - dung nhu gia dinh"))

        if shape.get("mostly_zero"):
            share = float((values == 0).mean())
            level = INFO if share > 0.5 else WARN
            out.append(Finding(
                level, "ratio.shape", FIN_LONG,
                f"'{label}': {share:.1%} o bang dung 0 tren {len(values)} gia tri "
                f"- cot nay khong dung duoc, panel lay CAR tu {CAR_HALF}"))
    return out


# --------------------------------------------------------------------------
# Doi chung cheo giua cac nguon doc lap
# --------------------------------------------------------------------------
def check_deposit_cross_source():
    out = []
    for path in (DEPOSIT_LSTK, DEPOSIT_24H):
        if not os.path.exists(path):
            return [Finding(WARN, "deposit.xsource", path, "khong tim thay file")]

    lstk = _read(DEPOSIT_LSTK)
    h24 = _read(DEPOSIT_24H)
    lstk = lstk[lstk["ticker"].notna()]
    h24 = h24[h24["ticker"].notna()]

    keys = ["ticker", "term_months", "channel", "date"]
    shared_days = sorted(set(lstk["date"]) & set(h24["date"]))
    if not shared_days:
        return [Finding(
            WARN, "deposit.xsource", DEPOSIT_LSTK,
            "hai nguon khong co ngay nao trung nhau - khong doi chung duoc")]

    left = lstk[lstk["date"].isin(shared_days)].drop_duplicates(keys)
    right = h24[h24["date"].isin(shared_days)].drop_duplicates(keys)
    merged = left[keys + ["rate_percent"]].merge(
        right[keys + ["rate_percent"]], on=keys, suffixes=("_lstk", "_24h"))
    if merged.empty:
        return [Finding(WARN, "deposit.xsource", DEPOSIT_LSTK,
                        "khong ghep duoc cap nao tren khoa day du")]

    merged["gap"] = (merged["rate_percent_lstk"] - merged["rate_percent_24h"]).abs()
    bad = merged[merged["gap"] > DEPOSIT_XSOURCE_TOLERANCE_PP]

    if len(bad):
        cells = (bad.groupby(["ticker", "term_months", "channel"])
                 .agg(n_days=("gap", "size"), max_gap=("gap", "max"),
                      lstk=("rate_percent_lstk", "median"),
                      h24=("rate_percent_24h", "median"))
                 .reset_index().sort_values("max_gap", ascending=False)
                 .round({"max_gap": 2, "lstk": 2, "h24": 2}))
        cells["key"] = list(zip(cells["ticker"], cells["term_months"],
                                cells["channel"]))
        settled = cells[cells["key"].isin(XSOURCE_RESOLVED)]
        open_cells = cells[~cells["key"].isin(XSOURCE_RESOLVED)]

        if len(open_cells):
            out.append(Finding(
                ERROR, "deposit.xsource", f"{DEPOSIT_LSTK} vs {DEPOSIT_24H}",
                f"{len(open_cells)} o mau thuan qua "
                f"{DEPOSIT_XSOURCE_TOLERANCE_PP} diem va CHUA phan dinh duoc "
                f"(tren {len(merged)} cap so sanh duoc, trung vi lech "
                f"{merged['gap'].median():.2f} diem). Hai nguon deu khop nhau o "
                f"cac ky han khac cua chinh ngan hang do, nen khong nguon nao "
                f"sai toan cuc - phai doi chieu bang cong bo cua ngan hang roi "
                f"ghi ket qua vao XSOURCE_RESOLVED",
                open_cells.drop(columns="key").head(8).to_dict("records")))

        for _, row in settled.iterrows():
            note = XSOURCE_RESOLVED[row["key"]]
            out.append(Finding(
                WARN, "deposit.xsource", f"{DEPOSIT_LSTK} vs {DEPOSIT_24H}",
                f"{row['ticker']} {row['term_months']} thang {row['channel']}: "
                f"lstk = {row['lstk']} vs 24hmoney = {row['h24']} "
                f"(lech {row['max_gap']} diem tren {row['n_days']} ngay). Da phan "
                f"dinh {note['reviewed']} - lay theo {note['winner']}; "
                f"{note['evidence']}"))
    else:
        out.append(Finding(
            INFO, "deposit.xsource", f"{DEPOSIT_LSTK} vs {DEPOSIT_24H}",
            f"{len(merged)} cap so sanh duoc, khong o nao lech qua "
            f"{DEPOSIT_XSOURCE_TOLERANCE_PP} diem"))
    return out


def _cap_on(day):
    cap = None
    for start, value, basis in SBV_DEPOSIT_CAPS:
        if day >= start:
            cap = (value, basis)
    return cap


def check_deposit_caps():
    out = []
    sources = (("deposit_24hmoney", DEPOSIT_24H, "effective_date"),
               ("deposit_daily", DEPOSIT_LSTK, "date"),
               ("deposit_official", DEPOSIT_SHEET, "date"))
    for name, path, day_col in sources:
        if not os.path.exists(path):
            out.append(Finding(WARN, "deposit.cap", path, "khong tim thay file"))
            continue
        frame = _read(path)
        if not _has(frame, ["ticker", "term_months", "channel", "rate_percent", day_col]):
            out.append(Finding(WARN, "deposit.cap", path, f"thieu cot de kiem ({day_col})"))
            continue
        frame = frame[frame["ticker"].notna() & (frame["term_months"] >= 1)
                      & (frame["term_months"] < 6)].copy()
        caps = frame[day_col].astype(str).map(_cap_on)
        frame["cap"] = [c[0] if c else np.nan for c in caps]
        frame["excess"] = (frame["rate_percent"] - frame["cap"]).round(4)
        over = frame[frame["excess"] > 1e-9]
        if over.empty:
            out.append(Finding(
                INFO, "deposit.cap", path,
                f"{len(frame)} o ky han duoi 6 thang, khong o nao vuot tran NHNN"))
            continue

        rounding = over[over["excess"] <= DEPOSIT_CAP_ROUNDING_PP]
        real = over[over["excess"] > DEPOSIT_CAP_ROUNDING_PP].copy()
        if len(rounding):
            banks = sorted(rounding["ticker"].unique())
            out.append(Finding(
                WARN, "deposit.cap", path,
                f"{len(rounding)} o ghi {rounding['rate_percent'].max():g} khi tran la "
                f"{rounding['cap'].max():g} ({len(banks)} NH: {', '.join(banks)}) - nguon "
                f"lam tron 1 chu so thap phan, gia tri that la muc tran",
                _sample(rounding.drop_duplicates(["ticker", "term_months", "channel"]),
                        ["ticker", "term_months", "channel", day_col, "rate_percent", "cap"])))
        if real.empty:
            continue

        def resolved(row):
            note = DEPOSIT_CAP_RESOLVED.get(
                (name, row["ticker"], int(row["term_months"]), row["channel"]))
            if note is None:
                return None
            if note["dates"] is not None and str(row[day_col]) not in note["dates"]:
                return None
            return note

        real["note"] = real.apply(resolved, axis=1)
        open_cells = real[real["note"].isna()]
        if len(open_cells):
            out.append(Finding(
                ERROR, "deposit.cap", path,
                f"{len(open_cells)} o vuot tran NHNN qua {DEPOSIT_CAP_ROUNDING_PP} diem - "
                f"bat kha thi voi lai suat niem yet; doi chieu web ngan hang roi ghi vao "
                f"DEPOSIT_CAP_RESOLVED",
                _sample(open_cells, ["ticker", "term_months", "channel", day_col,
                                     "rate_percent", "cap"])))
        settled = real[real["note"].notna()]
        for key, group in settled.groupby(["ticker", "term_months", "channel"]):
            note = group["note"].iloc[0]
            out.append(Finding(
                WARN, "deposit.cap", path,
                f"{key[0]} {key[1]} thang {key[2]}: {group['rate_percent'].max():g} vuot "
                f"tran {group['cap'].max():g} o {len(group)} ngay. Da xem xet "
                f"{note['reviewed']}: {note['evidence']}"))
    return out


def check_deposit_amount_tiers():
    try:
        from crawlers import deposit_tiers
        table = deposit_tiers.amount_tier_status()
    except Exception as exc:
        return [Finding(WARN, "deposit.amount_tier", DEPOSIT_24H,
                        f"khong doc duoc bang bac theo so tien ({type(exc).__name__}: {exc})")]
    present = table[table["present"]]
    stale = present[~present["matches"]]
    if len(stale):
        return [Finding(
            WARN, "deposit.amount_tier", DEPOSIT_24H,
            f"{len(stale)}/{len(present)} o bac theo so tien khong con khop bac thap nhat ngay "
            f"{table['latest_date'].iloc[0]} - doi chieu bieu moi roi sua deposit_tiers.AMOUNT_TIERS",
            _sample(stale, ["ticker", "channel", "term_months", "lowest_tier", "current"]))]
    banks = sorted(present["ticker"].unique())
    return [Finding(
        INFO, "deposit.amount_tier", DEPOSIT_24H,
        f"{len(present)} o co bac theo so tien ({', '.join(banks)}) khop bac thap nhat; "
        f"{int((~table['present']).sum())} ky han trong bieu khong co trong du lieu")]


def check_deposit_official():
    try:
        from crawlers import deposit_tiers
        table = deposit_tiers.official_status()
    except Exception as exc:
        return [Finding(WARN, "deposit.official", DEPOSIT_24H,
                        f"khong doc duoc anh chup bieu chinh thuc ({type(exc).__name__}: {exc})")]
    if table.empty:
        return [Finding(INFO, "deposit.official", DEPOSIT_24H, "chua co anh chup bieu chinh thuc")]
    out = []
    stale = table[~table["still_matches"]]
    if len(stale):
        out.append(Finding(
            WARN, "deposit.official", DEPOSIT_24H,
            f"{len(stale)}/{len(table)} o bieu chinh thuc khong con khop so 24hmoney ngay "
            f"{table['latest_date'].iloc[0]} - doc lai bieu NH roi cap nhat {deposit_tiers.OFFICIAL}",
            _sample(stale, ["ticker", "channel", "term_months", "official", "raw_at_check", "raw_latest"])))
    old = table[table["age_days"] > deposit_tiers.OFFICIAL_MAX_AGE_DAYS]
    if len(old):
        out.append(Finding(
            WARN, "deposit.official", DEPOSIT_24H,
            f"anh chup bieu chinh thuc cu hon {deposit_tiers.OFFICIAL_MAX_AGE_DAYS} ngay "
            f"({', '.join(sorted(old['ticker'].unique()))}) - o them moi da het han, doc lai bieu"))
    if not out:
        out.append(Finding(
            INFO, "deposit.official", DEPOSIT_24H,
            f"{len(table)} o bieu chinh thuc ({table['ticker'].nunique()} NH, doc {table['checked'].max()}) van "
            f"khop nguon; {int(table['added_cell'].sum())} o them moi"))
    return out


def check_deposit_sheet():
    if not os.path.exists(DEPOSIT_SHEET):
        return [Finding(WARN, "deposit.sheet", DEPOSIT_SHEET, "khong tim thay file - chay "
                        "`python -m crawlers.deposit_official`")]
    try:
        from crawlers import deposit_official
    except Exception as exc:
        return [Finding(WARN, "deposit.sheet", DEPOSIT_SHEET, f"khong nap duoc crawler ({type(exc).__name__}: {exc})")]
    sheet = _read(DEPOSIT_SHEET)
    latest = str(sheet["date"].max())
    age = (pd.Timestamp.now().normalize() - pd.Timestamp(latest)).days
    out = []
    if age > DEPOSIT_SHEET_MAX_AGE_DAYS:
        out.append(Finding(WARN, "deposit.sheet", DEPOSIT_SHEET,
                           f"anh chup bieu NH moi nhat la {latest} ({age} ngay truoc) - crawl hang ngay co chay khong?"))
    today = sheet[sheet["date"].astype(str) == latest]
    missing = sorted(set(deposit_official.BANKS) - set(today["ticker"]))
    if missing:
        out.append(Finding(WARN, "deposit.sheet", DEPOSIT_SHEET,
                           f"{latest}: khong doc duoc bieu cua {', '.join(missing)} (xem crawl_log.txt; "
                           f"`python -m crawlers.deposit_official {' '.join(missing)}` de thu lai)"))
    out.append(Finding(INFO, "deposit.sheet", DEPOSIT_SHEET,
                       f"{latest}: {today['ticker'].nunique()}/{len(deposit_official.BANKS)} NH doc tu dong, "
                       f"{len(today)} o; chua tu dong: {', '.join(sorted(deposit_official.GAPS))} "
                       f"(bu bang anh chup doc tay / blog Techcombank)"))
    return out


def check_deposit_tier_overrides():
    try:
        from crawlers import deposit_tiers
        table = deposit_tiers.status()
    except Exception as exc:  # thieu file lai suat khong duoc lam hong ca bao cao
        return [Finding(WARN, "deposit.tier", DEPOSIT_24H,
                        f"khong doc duoc bang ghi de bac ({type(exc).__name__}: {exc})")]
    stale = table[~table["still_matches"]]
    if len(stale):
        return [Finding(
            WARN, "deposit.tier", DEPOSIT_24H,
            f"{len(stale)}/{len(table)} o ghi de bac lai suat khong con khop so 24hmoney ngay "
            f"{table['latest_date'].iloc[0]} - ngan hang da doi bieu; doi chieu bieu moi roi sua "
            f"deposit_tiers.TIER_OVERRIDES",
            _sample(stale, ["ticker", "channel", "term_months", "raw_expected", "raw_latest"]))]
    banks = sorted(table["ticker"].unique())
    return [Finding(
        INFO, "deposit.tier", DEPOSIT_24H,
        f"{len(table)} o ghi de bac thap nhat ({', '.join(banks)}) van khop nguon, da ap cho "
        f"{int(table['n_applied'].sum())} dong")]


def check_npl_cross_source(panel):
    out = []
    if not os.path.exists(CREDIT):
        return [Finding(WARN, "npl.xsource", CREDIT, "khong tim thay file")]
    if not _has(panel, ["ticker", "period", "npl_percent", "npl_src"]):
        return [Finding(WARN, "npl.xsource", PANEL,
                        "panel thieu cot NPL hoac npl_src - bo qua phep doi chung")]

    vci = _read(CREDIT)[["ticker", "period", "npl_percent"]].rename(
        columns={"npl_percent": "npl_vci"}).dropna()
    merged = panel[["ticker", "period", "npl_percent", "npl_src"]].merge(
        vci, on=["ticker", "period"]).dropna(subset=["npl_percent", "npl_vci"])
    both = merged[merged["npl_src"] == "note"]
    if both.empty:
        return [Finding(WARN, "npl.xsource", PANEL,
                        "khong co o nao co ca hai nguon de doi chung")]

    gap = (both["npl_percent"] - both["npl_vci"]).abs()
    far = both[gap > 1.0]
    if len(far):
        out.append(Finding(
            WARN, "npl.xsource", f"{PANEL} vs {CREDIT}",
            f"{len(far)}/{len(both)} o co NPL tu thuyet minh lech qua 1 diem so "
            f"voi NPL cua VCI (trung vi lech {gap.median():.4f} diem)",
            _sample(far.assign(gap=gap[far.index]),
                    ["ticker", "period", "npl_percent", "npl_vci", "gap"])))
    else:
        out.append(Finding(
            INFO, "npl.xsource", f"{PANEL} vs {CREDIT}",
            f"{len(both)} o doi chung duoc, lech trung vi {gap.median():.4f} diem, "
            f"{(gap < 0.05).mean():.1%} khop trong 0,05 diem"))
    return out


# --------------------------------------------------------------------------
# OHLC
# --------------------------------------------------------------------------
def check_ohlc(directory, label):
    out = []
    if not os.path.isdir(directory):
        return [Finding(WARN, "ohlc", directory, "khong tim thay thu muc")]

    impossible, drifted, checked = [], [], 0
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".csv"):
            continue
        frame = _read(os.path.join(directory, name))
        if not {"open", "high", "low", "close", "time"} <= set(frame.columns):
            continue
        checked += 1
        symbol = name[:-4]

        inverted = frame[frame["high"] < frame["low"]]
        for _, row in inverted.iterrows():
            impossible.append({
                "symbol": symbol, "time": str(row["time"])[:10],
                "high": float(row["high"]), "low": float(row["low"]),
            })

        outside = frame[((frame["close"] > frame["high"])
                         | (frame["close"] < frame["low"])
                         | (frame["open"] > frame["high"])
                         | (frame["open"] < frame["low"]))
                        & (frame["high"] >= frame["low"])]
        for _, row in outside.iterrows():
            gap = max(row["close"] - row["high"], row["low"] - row["close"],
                      row["open"] - row["high"], row["low"] - row["open"])
            pct = gap / row["close"] * 100 if row["close"] else float("inf")
            drifted.append({
                "symbol": symbol, "time": str(row["time"])[:10],
                "field": "close" if (row["close"] > row["high"]
                                     or row["close"] < row["low"]) else "open",
                "gap": _round(float(gap)), "gap_percent": _round(float(pct), 3),
            })

        nonpos = frame[frame[["open", "high", "low", "close"]].le(0).any(axis=1)]
        if len(nonpos):
            out.append(Finding(
                ERROR, "ohlc", f"{directory}/{name}",
                f"{symbol}: {len(nonpos)} phien co gia <= 0",
                _sample(nonpos, ["time", "open", "high", "low", "close"])))

        dup = frame[frame.duplicated("time", keep=False)]
        if len(dup):
            out.append(Finding(
                ERROR, "ohlc", f"{directory}/{name}",
                f"{symbol}: {dup['time'].nunique()} ngay bi lap",
                _sample(dup, ["time", "close", "volume"])))

    if impossible:
        symbols = sorted({v["symbol"] for v in impossible})
        out.append(Finding(
            ERROR, "ohlc", directory,
            f"{label}: {len(impossible)} phien co high < low o {len(symbols)} ma "
            f"({', '.join(symbols)}) - bat kha thi ve cau truc, phai lay lai tu nguon",
            impossible[:10]))

    if drifted:
        symbols = sorted({v["symbol"] for v in drifted})
        worst = max(v["gap_percent"] for v in drifted)
        severe = [v for v in drifted if v["gap_percent"] > OHLC_MAX_DEVIATION_PERCENT]
        if severe:
            out.append(Finding(
                ERROR, "ohlc", directory,
                f"{label}: {len(severe)} phien co open/close lech khoi [low, high] "
                f"qua {OHLC_MAX_DEVIATION_PERCENT}% - qua lon de la sai lech dieu "
                f"chinh, phai lay lai tu nguon", severe[:10]))
        rest = [v for v in drifted if v["gap_percent"] <= OHLC_MAX_DEVIATION_PERCENT]
        if rest:
            fields = sorted({v["field"] for v in rest})
            out.append(Finding(
                WARN, "ohlc", directory,
                f"{label}: {len(rest)} phien co {'/'.join(fields)} nam ngoai "
                f"[low, high] o {len(symbols)} ma, lech toi da {worst}% - dau vet "
                f"nha cung cap dieu chinh mot truong ma khong dieu chinh cac truong "
                f"con lai. Khong dung de tinh bien do trong phien; cac phep tinh "
                f"tren rieng gia dong cua van dung", rest[:8]))

    if checked and not impossible and not drifted:
        out.append(Finding(
            INFO, "ohlc", directory,
            f"{label}: {checked} chuoi, khong phien nao vi pham [low, high]"))
    return out


# --------------------------------------------------------------------------
# Thoi gian
# --------------------------------------------------------------------------
def _is_date_column(name):
    low = name.lower()
    if low.startswith("retrieved") or low.endswith("_utc"):
        return False
    return low in {"date", "time", "period_end", "as_of_date",
                   "effective_date", "month"} or low.endswith("_date")


def check_future_dates(paths):
    out = []
    today = pd.Timestamp.now(tz="UTC").normalize()
    hits = []
    for path in paths:
        if not os.path.exists(path):
            continue
        frame = _read(path)
        for col in frame.columns:
            if not _is_date_column(col):
                continue
            stamps = pd.to_datetime(frame[col], errors="coerce", utc=True)
            future = stamps[stamps > today]
            if len(future):
                hits.append({"table": path, "column": col, "n": int(len(future)),
                             "max": str(future.max())})
    if hits:
        out.append(Finding(
            ERROR, "time.future", "nhieu bang",
            f"{len(hits)} cot co gia tri ngay vuot qua hom nay", hits[:8]))
    else:
        out.append(Finding(
            INFO, "time.future", "nhieu bang",
            f"khong cot ngay nao vuot hom nay tren {len(paths)} bang da quet"))
    return out


# --------------------------------------------------------------------------
# Dieu phoi
# --------------------------------------------------------------------------
PANEL_CHECKS = ("panel.keys", "panel.bounds", "panel.identity",
                "panel.degenerate", "panel.coverage", "panel.jump", "npl.xsource")


def run(scope="all"):
    if not os.path.exists(PANEL):
        return [Finding(ERROR, "panel.keys", PANEL,
                        "chua co panel - chay `python -m crawlers.build_panel` truoc")]

    panel = _read(PANEL)
    findings = []
    findings += check_panel_keys(panel)
    findings += check_panel_bounds(panel)
    findings += check_panel_identities(panel)
    findings += check_degenerate_ratios(panel)
    findings += check_coverage_regression(panel)
    findings += check_panel_share_jumps(panel)
    findings += check_npl_cross_source(panel)

    if scope != "panel":
        findings += check_ratio_shape()
        findings += check_vci_stale_rows()
        findings += check_note_currency_identity()
        findings += check_deposit_cross_source()
        findings += check_deposit_caps()
        findings += check_deposit_tier_overrides()
        findings += check_deposit_official()
        findings += check_deposit_sheet()
        findings += check_deposit_amount_tiers()
        findings += check_ohlc(PRICE_DIR, "gia co phieu")
        findings += check_ohlc(MARKET_DIR, "chi so thi truong")
        findings += check_future_dates([
            PANEL, CREDIT, NOTE, CAR_HALF, DEPOSIT_LSTK, DEPOSIT_24H])

    findings.sort(key=lambda f: (LEVEL_ORDER[f.level], f.check))
    return findings


def summarize(findings):
    counts = {level: sum(1 for f in findings if f.level == level)
              for level in (ERROR, WARN, INFO)}
    return {
        "counts": counts,
        "passed": counts[ERROR] == 0,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "findings": [f.as_dict() for f in findings],
    }


def report(findings, quiet=False):
    counts = {level: sum(1 for f in findings if f.level == level)
              for level in (ERROR, WARN, INFO)}
    print(f"{counts[ERROR]} ERROR - {counts[WARN]} WARN - {counts[INFO]} INFO")
    print()

    levels = [ERROR] if quiet else [ERROR, WARN, INFO]
    headings = {
        ERROR: "ERROR - phai sua truoc khi mo hinh hoa",
        WARN: "WARN - gia tri cuc doan, kiem tay roi moi quyet dinh (KHONG loc bo mac dinh)",
        INFO: "INFO - do phu va thong ke nen",
    }
    index = 0
    for level in levels:
        block = [f for f in findings if f.level == level]
        if not block:
            continue
        print(headings[level])
        print("-" * len(headings[level]))
        for finding in block:
            index += 1
            print(f"{index}. [{finding.check}] {finding.table}")
            print(f"   {finding.message}")
            for row in finding.sample[:6]:
                cells = "  ".join(
                    f"{k}={v}" for k, v in row.items() if v is not None)
                print(f"     {cells}")
        print()

    if counts[ERROR] == 0:
        print("Ket luan: khong con ERROR - panel dung duoc cho mo hinh hoa.")
    else:
        print(f"Ket luan: con {counts[ERROR]} ERROR - xu ly truoc khi dung panel.")


if __name__ == "__main__":
    import argparse
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Cong kiem tra chat luong du lieu truoc khi mo hinh hoa")
    parser.add_argument("--scope", choices=("all", "panel"), default="all",
                        help="'panel' chi chay cac phep kiem chan duoc mo hinh hoa")
    parser.add_argument("--json", action="store_true", help="in JSON cho CI")
    parser.add_argument("--quiet", action="store_true", help="chi in ERROR")
    args = parser.parse_args()

    results = run(scope=args.scope)
    summary = summarize(results)

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    else:
        report(results, quiet=args.quiet)

    _log(f"validate --scope {args.scope}: "
         f"{summary['counts'][ERROR]} ERROR, {summary['counts'][WARN]} WARN")
    sys.exit(0 if summary["passed"] else 1)
