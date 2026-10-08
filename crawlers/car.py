"""Ty le an toan von (CAR) theo tung ngan hang -- don vi ky la NUA NAM.

DON VI KY: '2025-H1' (chot 30/06) va '2025-H2' (chot 31/12), KHONG phai quy.
Day khong phai lua chon tuy tien ma theo dung nhip cong bo cua nguon: 21/22 ngan
hang cong bo 6 thang/lan, VIB con ghi thang trong bao cao la "dang tai 6 thang mot
lan". De schema theo quy thi hai o moi nam se rong vinh vien voi gan het bang, va
o rong do dai dien cho MOT KY KHONG TON TAI chu khong phai du lieu bi thieu -- doc
gia se hieu nham la crawler cao sot.

Rieng VPBank cong bo theo quy (17 ban 2022-Q1 -> 2026-Q1). Cac o Q1/Q3 cua NH nay
khong bi vut di: chung duoc dung lam KY THAY THE khi nua nam do thieu ky chot, va
khi ay dong duoc danh dau dung_ky_thay_the=True kem as_of_date THAT. Xem to_half()
va collapse_to_half(). Vi vay dung gia dinh moi dong H1 deu chot ngay 30/06 --
LUON doc cot as_of_date khi tinh khoang cach thoi gian.

Vi sao can module rieng, khong dung thang car_percent trong bank_credit_quarterly.csv:

  1. vnstock CHI co o Q2, tuc chi H1. 88/88 quan sat chot ngay 30/06 -- khong phai
     chuoi bi hut ma la nha cung cap chi lay mot ky moi nam. Ban H2 (chot 31/12) co
     that va cac NH deu cong bo: vnstock dang bo mat mot nua so quan sat.

  2. vnstock dung o 2025-H1 (14/22 NH). Ban do chinh ngan hang cong bo thi moi hon
     -- VPBank da co 2026-H1.

  3. Cross-check da lam: so trich tu ban Tru cot 3 do ngan hang tu cong bo KHOP
     TUYET DOI voi vnstock o ca 5 o doi chieu duoc (HDB, TPB va VPB x3 ky). Nghia la car_percent cua vnstock chinh la ban HOP
     NHAT do ngan hang cong bo, khong phai so uoc luong cua nha cung cap -- nen gop
     hai nguon la hop le, khong lech co so.

Ba cai bay da gap khi di lay, deu da xu ly trong module nay:

  a. TEN FILE KHONG PHAI NGAY DU LIEU. File VIB dat ten "...30.06.2026.pdf" nhung
     NOI DUNG la 30/06/2025. Cung loai bay date vs effective_date cua 24hmoney.
     parse() luon doc ky bao cao TU TRONG FILE, khong lay tu URL.

  b. ~40% ban cong bo la PDF SCAN, khong co lop text (ACB, STB, NAB, HDBank).
     parse() tra ve scanned=True de goi y render anh doc tay, KHONG doan.

  c. DUT GAY CO SO TT41 -> TT14. Thong tu 14/2025/TT-NHNN thay Thong tu 41/2016 tu
     15/09/2025. VIB cong bo CAR theo TT14 tai 31/12/2025 la 12,2% -- CAO HON 1 diem
     so voi chinh CAR theo TT41 cung ngay. Tu 2026 cac NH chuyen dan, nen chuoi CAR
     se co HAI co so. Cot thong_tu la bat buoc; KHONG so CAR giua hai co so.

Rieng le vs hop nhat: moi ban cong bo co HAI con so, chenh toi 1,3 diem (VPB 12,51
vs 13,81). vnstock dung HOP NHAT nen module nay lay hop nhat lam cot chinh.

FILE LA BANG CONG VIEC, KHONG CHI LA KET QUA CRAWL.
Khung day du 22 NH x 15 ky (2019-H1 -> 2026-H1) = 330 dong; o chua tim ra so thi
de TRONG chu khong bo dong. O trong noi ro "ky nay ton tai nhung chua co so",
khac han voi khong co dong nao -- nguoi doc khong phai tu doan.

Vi file co dong NHAP TAY nen write() KHONG BAO GIO GHI DE o da co so, dung
nguyen tac cua loan_rates.py:
    - o file cu co so, code khong co  -> giu nguyen file cu
    - o file cu trong, code co so     -> dien vao
    - ca hai co so va LECH nhau       -> BAO conflict, VAN GIU FILE CU
Chay lai crawler bao nhieu lan cung khong mat cong nhap tay. Chi `--rebuild` moi
dung lai tu dau tu code, va lenh do XOA moi o nhap tay.

Khi dien tay, nen dat nguon="nhap_tay" va dien kem source_url + note de sau con
truy lai duoc goc. Cot bat buoc: car_percent (hop nhat). Cac cot khac tuy chon.

Chay:
    python -m crawlers.car                 # dung + ghi CSV + validate (GIU o nhap tay)
    python -m crawlers.car --rebuild       # dung lai tu code, XOA o nhap tay
    python -m crawlers.car --validate      # doi chieu voi vnstock
    python -m crawlers.car --coverage      # tinh trang 22 NH
    python -m crawlers.car --as-of 2026-H1 # CAR dung duoc tai mot ky, kem tuoi du lieu
    python -m crawlers.car --fetch VIB     # tai + trich lai tu ban goc
    python -m crawlers.car --check-sources # kiem trich dan con song khong
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

OUT = Path("data/credit")
MASTER = OUT / "bank_car_halfyear.csv"
VNSTOCK = OUT / "bank_credit_quarterly.csv"

# Don vi ky la NUA NAM, khong phai quy. Ly do: 21/22 NH cong bo 6 thang/lan
# (30/06 va 31/12) nen schema theo quy se de trong hai o moi nam cho gan het bang,
# va o rong do KHONG phai thieu du lieu ma la ky khong ton tai. Chi VPBank cong bo
# theo quy; cac o Q1/Q3 cua rieng NH do duoc dung lam KY THAY THE, xem to_half().
COLUMNS = [
    "ticker", "period", "as_of_date", "ky_goc", "dung_ky_thay_the",
    "car_percent", "car_rieng_le_percent", "tier1_percent",
    "thong_tu", "co_so", "nguon", "do_tin_cay",
    "source_url", "note", "retrieved_at_utc",
]

QUARTER_END = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}
HALF_END = {"H1": "06-30", "H2": "12-31"}

# Quy nao roi vao nua nam nao, va thu tu uu tien trong cung mot nua.
# rank 0 = ky chuan (chot nua nam), rank 1 = ky thay the (dung khi thieu ky chuan).
QUARTER_TO_HALF = {1: ("H1", 1), 2: ("H1", 0), 3: ("H2", 1), 4: ("H2", 0)}

# ---------------------------------------------------------------------------
# So trich tay tu ban Tru cot 3 do chinh ngan hang cong bo.
# Moi dong: ticker, period, car_hop_nhat, car_rieng_le, tier1_hop_nhat,
#           thong_tu, do_tin_cay, source_url, note
#
# do_tin_cay:
#   cao   = bang co nhan cot ro rang, hoac van ban ghi thang bang chu
#   tb    = so doc dung nhung viec gan cot rieng_le/hop_nhat suy tu THU TU cot,
#           chua co cach doi chieu doc lap -> kiem lai truoc khi trich luan van
# ---------------------------------------------------------------------------
DISCLOSED: list[tuple] = [
    (
        "VIB", "2025-Q2", 12.15, 12.08, 10.67, "TT41", "cao",
        "https://www.vib.com.vn/wps/wcm/connect/a3ab69fb-bee6-4c51-9587-ee2d41f8dc1b/"
        "VIB+Pillar+3+Report.Final_VN+30.06.2026.pdf?MOD=AJPERES&CVID=pL4vXSN",
        "TEN FILE GHI 30.06.2026 NHUNG NOI DUNG LA 30/06/2025 - da doc ky tu trong file, "
        "khong lay tu URL. Bang trang 6 (hop nhat) / trang 7 (rieng le), co nhan cot ro. "
        "VIB ghi trong chinh bao cao: 'dang tai 6 thang mot lan'.",
    ),
    (
        "VIB", "2024-Q4", 11.97, 11.93, 10.49, "TT41", "cao",
        "https://www.vib.com.vn/wps/wcm/connect/a3ab69fb-bee6-4c51-9587-ee2d41f8dc1b/"
        "VIB+Pillar+3+Report.Final_VN+30.06.2026.pdf?MOD=AJPERES&CVID=pL4vXSN",
        "Ky so sanh in kem trong cung bao cao. vnstock KHONG co o Q4 nao - day la vi du "
        "cho thay moi ban cong bo cho khong mot ma HAI ky.",
    ),
    (
        "VPB", "2025-Q2", 13.81, 12.51, None, "TT41", "cao",
        "https://www.vpbank.com.vn/-/media/vpbank-latest/5nha-dau-tu/"
        "cong-bo-thong-tin-ty-le-an-toan-von/2025/cong-bo-thong-tin-ty-le-an-toan-von-quy-2-2025.pdf",
        "Van ban ghi THANG BANG CHU: 'tai thoi diem 30/06/2025, he so CAR tren co so rieng "
        "le va hop nhat ... dat 12.51% va 13.81%'. Khop tuyet doi voi vnstock 2025-Q2. "
        "VPBank cong bo THEO QUY (co ca Q1/Q3), la NH duy nhat tim duoc lam vay.",
    ),
    (
        "SHB", "2025-Q2", 12.46, 12.06, 9.37, "TT41", "tb",
        "https://www.shb.com.vn/wp-content/uploads/2025/10/CONG-BO-TY-LE-AN-TOAN-VON-30-06-2025.pdf",
        "Gan cot rieng_le/hop_nhat SUY TU THU TU COT trong bang (nhan cot va gia tri nam o "
        "hai khoi text roi nhau). vnstock chi co den 2024-Q2 = 12.61 nen chua doi chieu duoc. "
        "Kiem lai bang cach render trang 5 thanh anh truoc khi trich luan van.",
    ),
    (
        "BID", "2025-Q2", 9.57, 9.39, 6.75, "TT41", "tb",
        "https://bidv.com.vn/wps/wcm/connect/408c687f-055c-4e0c-88b9-0c1dba6710bd/"
        "Bao+cao+CBTT_+30.6.2025_VIE.pdf?MOD=AJPERES&CACHEID=ROOTWORKSPACE-408c687f-055c-4e0c-88b9-0c1dba6710bd-pACUd9K",
        "Gan cot suy tu thu tu cot, nhu SHB. Hop ly theo chieu: vnstock 2024-Q2 = 9.48 -> "
        "9.57 la buoc tang nho. BIDV da co ban 31/12/2025 tren trang IR, chua lay.",
    ),
    (
        "HDB", "2024-Q2", 13.94, 13.40, None, "TT41", "cao",
        "https://cdn.hdbank.com.vn/hdbank-file/investor/editor/"
        "bM0oFeFPUJyfnjkNnAjK20240904113105/HDBankCongbothongtinCARTT4130062024dau_1725437683266.pdf",
        "PDF SCAN, khong co lop text - doc bang cach render trang 5 thanh anh. Bang co nhan "
        "cot day du (31/12/2023 | 30/06/2024, moi ky x Rieng le | Hop nhat). Khop tuyet doi "
        "voi vnstock 2024-Q2 = 13.94.",
    ),
    (
        "HDB", "2023-Q4", 12.57, 12.21, None, "TT41", "cao",
        "https://cdn.hdbank.com.vn/hdbank-file/investor/editor/"
        "bM0oFeFPUJyfnjkNnAjK20240904113105/HDBankCongbothongtinCARTT4130062024dau_1725437683266.pdf",
        "Ky so sanh in kem trong cung bao cao scan.",
    ),
    (
        "TCB", "2025-Q4", 14.61, 11.97, 13.67, "TT41", "cao",
        "https://techcombank.com/content/dam/techcombank/public-site/documents/"
        "ty-le-an-toan-von-2h2025-final.pdf",
        "Bang 2 trang 6, co nhan cot day du. Kiem bang so hoc tu Bang 1: von tu co hop "
        "nhat 181,870 / tong TSCRR 1,244,531 = 14.614%. Luu y CAR RIENG LE (11.97) THAP "
        "HON ty le von cap 1 rieng le (12.74) - khong phai loi doc: khoan giam tru khi "
        "tinh von tu co o cap rieng le la 12,708 ty, lon hon von cap 2 (3,877 ty).",
    ),
    (
        "TCB", "2025-Q2", 14.97, 13.09, 14.25, "TT41", "cao",
        "https://techcombank.com/content/dam/techcombank/public-site/documents/"
        "ty-le-an-toan-von-2h2025-final.pdf",
        "Ky so sanh in kem trong ban 2H2025. Ban 1H2025 rieng cung ton tai: "
        "ty-le-an-toan-von-1h2025-final.pdf",
    ),
    (
        "TPB", "2024-Q2", 13.17, 13.14, None, "TT41", "cao",
        "https://tpb.vn/wps/wcm/connect/fc169b8a-2b23-4d8c-b676-7a3fd0ec12c3/"
        "BC+CBTT+CAR_TT41_T6.2024.pdf?MOD=AJPERES&CONVERT_TO=url&CACHEID=ROOTWORKSPACE-fc169b8a-2b23-4d8c-b676-7a3fd0ec12c3-paKBrns",
        "Khop tuyet doi voi vnstock 2024-Q2 = 13.17, va con so nay xac nhan THU TU COT la "
        "rieng le truoc, hop nhat sau (13.14 | 13.17) - co so de suy cot cho SHB/BID.",
    ),
    # Ky 30/06/2026, trich 07/10/2026 tu ban Vietstock luu lai (xem VIETSTOCK_CAR). Ca bon
    # bang deu co NHAN COT "Rieng le | Hop nhat" ngay tren dong so -> do_tin_cay cao.
    (
        "BID", "2026-Q2", 10.01, 9.84, 7.12, "TT41", "cao",
        "https://static2.vietstock.vn/data/HOSE/2026/BCTLATV/VN/QUY%202/BID_BaocaoTyleAnToanVon_6T_2026.pdf",
        "Bang 2 trang 6, nhan cot 'Rieng le 30/06/2026 | Hop nhat 30/06/2026'. Ghi chu cua "
        "bang: tinh theo TT41 va TT22/2023. Hop nhat 9.18 (2025-H2) -> 10.01.",
    ),
    (
        "EIB", "2026-Q2", 12.60, 12.55, 12.80, "TT41", "cao",
        "https://static2.vietstock.vn/data/HOSE/2026/BCTLATV/VN/QUY%202/EIB_BaocaoTyleAnToanVon_6T_2026.pdf",
        "Muc 5 'Cac ty le von' trang 3, nhan cot Rieng le | Hop nhat. Ty le von cap 1 (12.80) "
        "CAO HON CAR (12.60) dung nhu nguon in - cung hien tuong TCB 2025-Q4, khong phai loi doc.",
    ),
    (
        "SSB", "2026-Q2", 12.06, 12.02, 11.89, "TT41", "cao",
        "https://static2.vietstock.vn/data/HOSE/2026/BCTLATV/VN/QUY%202/SSB_BaocaoTyleAnToanVon_6T_2026.pdf",
        "Bang 1 trang 5 (doc tu anh: trich text lam lech dong nhan va so). Kiem so hoc: von tu "
        "co hop nhat 42,763,758 / TSCRR 354,736,711 = 12.055%. Giam 1.33 diem so voi 13.39 "
        "(2025-H2); ban cong bo khong in ky so sanh.",
    ),
    (
        "BAB", "2026-Q2", 8.95, 8.88, 7.06, "TT41", "cao",
        "https://static2.vietstock.vn/data/HNX/2026/BCTLATV/VN/QUY%202/BAB_BaocaoTyleAnToanVon_6T_2026.pdf",
        "PDF SCAN, khong co lop text - doc Bang 2 trang 6 bang cach render thanh anh. Giam 1.07 "
        "diem so voi 10.02 (2025-H2); ban cong bo khong in ky so sanh.",
    ),
]

# Vietstock luu lai ban cong bo CAR nua nam cua phan lon NH niem yet theo mot mau ten co dinh
# (tim ra 07/10/2026), on dinh hon trang IR cua tung NH:
#   https://static2.vietstock.vn/data/{HOSE|HNX}/{nam}/BCTLATV/VN/QUY%202/{MA}_BaocaoTyleAnToanVon_6T_{nam}.pdf
# Ngay 07/10/2026 da co ban 2026 cua ACB, BAB, BID, EIB, SSB, VPB; CTG, HDB, NAB, NVB, PGB, SHB,
# TPB chua co (nam truoc SHB, OCB dang cuoi thang 10).
VIETSTOCK_CAR = ("https://static2.vietstock.vn/data/{san}/{nam}/BCTLATV/VN/QUY%202/"
                 "{ma}_BaocaoTyleAnToanVon_6T_{nam}.pdf")

# ---------------------------------------------------------------------------
# MB Bank: 12 ban Tru cot 3, 30/06/2019 -> 31/12/2025, dung nhip 6 thang/lan.
#
# !!! CANH BAO QUAN TRONG NHAT CUA CA MODULE NAY !!!
# THU TU COT CUA MBB DAO GIUA CAC BAN. Ban 30/06/2020 tro ve truoc in
# "Rieng le | Hop nhat"; tu ban 31/12/2020 tro di in "Hop nhat | Rieng le".
# Doc theo VI TRI COT se lay nham phia o 3 ban dau, va sai lech dung bang muc
# chenh rieng_le - hop_nhat (0,3-0,4 diem) chu khong sai to den muc de nhan ra.
#
# Da chung minh bang vnstock, ba diem nam hai ben cho dao:
#   30/06/2019 (RL|HN): 9.23 | 9.58  -> vnstock 9.58  = cot THU HAI
#   30/06/2020 (RL|HN): 10.85| 11.27 -> vnstock 11.27 = cot THU HAI
#   30/06/2024 (HN|RL): 11.10| 11.17 -> vnstock 11.10 = cot THU NHAT
# Ca ba khop tuyet doi. Vi vay: LUON doc NHAN COT, khong bao gio doc vi tri.
#
# Day cung la ly do SHB va BID trong DISCLOSED van de do_tin_cay = "tb": voi hai
# NH do viec gan cot moi chi suy tu thu tu, chua co diem kiem cheo nao.
#
# Kiem chung noi bo them: o CA HAI phia cua cho dao, quan he van giu nguyen huong
# -- ty le von cap 1 RIENG LE luon cao hon hop nhat, con CAR hop nhat thi cao hon
# rieng le (tru 2024-2025 khi dao chieu nhe). Neu doc nham phia thi quan he nay se
# lat nguoc tai dung ban 31/12/2020.
#
# Moi dong: period, car_hop_nhat, car_rieng_le, tier1_hop_nhat, thu_tu_cot, url
# ---------------------------------------------------------------------------
_MBB = "https://mbbank.com.vn/resources/files/"
MBB_HALFYEAR: list[tuple] = [
    ("2019-Q2", 9.58, 9.23, 8.17, "RL|HN",
     _MBB + "NhaDauTu/thong-bao/1.2020/mbb.cbtt-bao-cao-cong-bo-thong-tin-ty-le-an-toan-von-30.6.2019.pdf"),
    ("2019-Q4", 10.12, 9.83, 9.04, "RL|HN",
     _MBB + "NhaDauTu/thong-bao/06.2020/bao-cao-cong-bo-thong-tin-car---31-12-2019-f.pdf"),
    ("2020-Q2", 11.27, 10.85, 9.98, "RL|HN",
     _MBB + "NhaDauTu/thong-bao/11.2020/mbb.cbtt-bao-cao-ty-le-an-toan-von-ngay-30.06.2020-(thong-tu-41).pdf"),
    ("2020-Q4", 10.42, 10.14, 9.47, "HN|RL",
     _MBB + "NhaDauTu/thong-bao/03.2021/mbb.cbtt-bao-cao-ty-le-an-toan-von-car-theo-thong-tu-41-ngay-31.12.2020.pdf"),
    ("2021-Q2", 10.66, 10.25, 9.71, "HN|RL",
     _MBB + "NhaDauTu/thong-bao/10.2021/mbb.cbtt-bao-cao-ty-le-an-toan-von-car-theo-thong-tu-41-ngay-30.06.2021.pdf"),
    ("2021-Q4", 11.28, 11.02, 9.75, "HN|RL",
     _MBB + "NhaDauTu/thong-bao/06.2022/mbb.cbtt-bao-cao-ty-le-an-toan-von-car-thong-tu-41-ngay-31.12.2021-final.pdf"),
    ("2022-Q4", 11.53, 11.37, 10.03, "HN|RL",
     _MBB + "NhaDauTu/thong-bao/02.2023/mbb.cbtt---bc-car41-31.12.2022-signed.pdf"),
    # DUY NHAT ban nay la trang SCAN: khong trang nao chua "10.75" trong lop text
    # (ca file co 21k ky tu text nhung trang co Bieu 2 la anh). So doc tu anh.
    # May man la hai cot BANG NHAU (10.75 / 10.75) nen thu tu cot khong anh huong.
    ("2023-Q4", 10.75, 10.75, 9.71, "HN|RL",
     _MBB + "NhaDauTu/2024/thang-02/mbb.cbtt-bao-cao-ty-le-an-toan-von-tai-31.12.2023.pdf"),
    ("2024-Q2", 11.10, 11.17, 9.75, "HN|RL",
     _MBB + "CBTT/2024/T11/20241107---mbb---cbtt-ty-le-an-toan-von-tai-ngay-30.06.2024-ky.pdf"),
    ("2024-Q4", 11.76, 11.74, 10.08, "HN|RL",
     _MBB + "NhaDauTu/2025/THANG-6.2025/20250602---mbb---cbtt-ty-le-an-toan-von-tai-ngay-31.12.2024..pdf"),
    ("2025-Q2", 11.60, 11.64, 9.65, "HN|RL",
     _MBB + "NhaDauTu/2025/20251106---mbb---cong-bo-thong-tin-ty-le-an-toan-von-tai-ngay-30.06.2025.pdf"),
    ("2025-Q4", 11.02, 11.11, 9.25, "HN|RL",
     _MBB + "NhaDauTu/2026/T05-2026/20260527---mbb---cbtt-ty-le-an-toan-von-tai-ngay-31122025-(vn-en).pdf"),
]


# ---------------------------------------------------------------------------
# Techcombank: bieu do "Ty le an toan von (CAR)" o trang 6 ban 2H2025 cho hai bien
# CAR HOP NHAT chay tu 12.2019 den 12.2025, dung nhip nua nam.
#
# Vi sao tin duoc bieu do nay trong khi da bac bieu do cua VNDIRECT: bieu do CUA
# NGAN HANG co NHAN SO in tren tung cot, con Hinh 15 cua VNDIRECT khong co nhan
# nao ca va phai uoc bang mat (+-0,2 diem). O day con so la do chinh nguon in ra.
# Doi lai, nguon tu ghi chu la "duoc lam tron 1 chu so" -> do_tin_cay = "tb", va
# KHONG duoc dung cac o nay de tinh chenh lech nho hon 0,1 diem.
#
# Kiem cheo hai diem voi vnstock, ca hai khop: 06.2020 bieu do 16.9 vs vnstock
# 16.87; 06.2022 bieu do 15.8 vs vnstock 15.83.
#
# CO Y BO 2020-Q2 va 2022-Q2 khoi danh sach nay: vnstock da co ban 2 chu so chinh
# xac hon, ma DISCLOSED thi ghi de len vnstock. Them vao day se lam MAT do chinh xac.
# ---------------------------------------------------------------------------
TCB_CHART: list[tuple[str, float]] = [
    ("2019-Q4", 15.5),
    ("2020-Q4", 16.1),
    ("2021-Q2", 15.2),
    ("2021-Q4", 15.0),
    ("2022-Q4", 15.2),
    ("2023-Q2", 15.1),
    ("2023-Q4", 14.4),
    ("2024-Q2", 14.5),
    ("2024-Q4", 15.4),
]
TCB_URL = ("https://techcombank.com/content/dam/techcombank/public-site/documents/"
           "ty-le-an-toan-von-2h2025-final.pdf")


# ---------------------------------------------------------------------------
# VPBank: nguon DUY NHAT tim duoc cong bo THEO QUY. 17 ban 2022-Q1 -> 2026-Q1,
# doi chieu voi 4 o cua vnstock thi 3/3 o trich duoc deu khop tuyet doi.
#
# URL sinh theo quy tac, nhung TEN FILE DOI 3 LAN qua cac nam nen phai giu ca ba
# bien the -- khong doan mot dang duy nhat:
#     2022:      /nam-2022/...-quy-{q}-2022.pdf
#     2023-2024: /nam-{y}/...-q{q}-{y}.pdf
#     2025-2026: /{y}/...-q{q}-{y}.pdf  hoac  ...-quy-{q}-{y}.pdf  (tron ca hai)
#
# Gia tri trich tu CAU VAN ban bao cao tu mo ta ("... dat 12.45% va 14.35%"),
# khong doc tu bang, vi bang bi vo bo cuc khi trich text. Doc duoc 12/17 ky;
# 5 ky con lai (2022-Q2, 2022-Q4, 2023-Q1, 2024-Q1, 2024-Q3) dung cach dien dat
# khac, CHUA lay - de trong chu khong suy.
#
# Kiem chung noi bo: cot ky truoc cua ban 2025-Q4 (14.01 / 15.50) trung khop voi
# gia tri trich doc lap tu ban 2024-Q4, va phep tru cua chinh nguon khop
# (14.01 - 1.56 = 12.45; 15.50 - 1.15 = 14.35).
#
# Moi dong: period, car_rieng_le, car_hop_nhat
# ---------------------------------------------------------------------------
VPB_QUARTERLY: list[tuple[str, float, float]] = [
    ("2022-Q1", 15.29, 15.33),
    ("2022-Q3", 13.57, 14.95),
    ("2023-Q2", 12.18, 13.85),
    ("2023-Q3", 12.05, 13.77),
    ("2023-Q4", 15.92, 17.07),
    ("2024-Q2", 14.15, 15.56),
    ("2024-Q4", 14.01, 15.50),
    ("2025-Q1", 13.29, 14.65),
    ("2025-Q2", 12.51, 13.81),
    ("2025-Q3", 12.45, 13.61),
    ("2025-Q4", 12.45, 14.35),
    ("2026-Q1", 12.03, 13.74),
    # Doc tu Bang 3 trang 5 (render anh), co nhan cot; cot 31/12/2025 in kem trong cung bang
    # (12.45 / 14.35) trung dong 2025-Q4 o tren -> thu tu cot da kiem.
    ("2026-Q2", 11.57, 13.29),
]

_VPB_BASE = ("https://www.vpbank.com.vn/-/media/vpbank-latest/5nha-dau-tu/"
             "cong-bo-thong-tin-ty-le-an-toan-von/{folder}/"
             "cong-bo-thong-tin-ty-le-an-toan-von-{name}.pdf")
# ten file that, da probe tung URL mot -- khong sinh bang quy tac vi ten khong deu
_VPB_FILES = {
    "2022-Q1": ("nam-2022", "quy-1-2022"), "2022-Q2": ("nam-2022", "quy-2-2022"),
    "2022-Q3": ("nam-2022", "quy-3-2022"), "2022-Q4": ("nam-2022", "quy-4-2022"),
    "2023-Q1": ("nam-2023", "q1-2023"), "2023-Q2": ("nam-2023", "q2-2023"),
    "2023-Q3": ("nam-2023", "q3-2023"), "2023-Q4": ("nam-2023", "q4-2023"),
    "2024-Q1": ("nam-2024", "q1-2024"), "2024-Q2": ("nam-2024", "q2-2024"),
    "2024-Q3": ("nam-2024", "q3-2024"), "2024-Q4": ("nam-2024", "q4-2024"),
    "2025-Q1": ("2025", "q1-2025"), "2025-Q2": ("2025", "quy-2-2025"),
    "2025-Q3": ("2025", "quy-3-2025"), "2025-Q4": ("2025", "quy-4-2025"),
    "2026-Q1": ("2026", "q1-2026"),
}


# Ky chua tim ra file tren vpbank.com.vn (cac bien the ten da probe 07/10/2026 deu khong ra PDF)
# -> dung ban Vietstock luu lai.
_VPB_OTHER = {
    "2026-Q2": VIETSTOCK_CAR.format(san="HOSE", nam=2026, ma="VPB"),
}


def vpb_url(period: str) -> str:
    if period in _VPB_OTHER:
        return _VPB_OTHER[period]
    folder, name = _VPB_FILES[period]
    return _VPB_BASE.format(folder=folder, name=name)


# ---------------------------------------------------------------------------
# Trang cong bo Tru cot 3 cua tung ngan hang, de chay lai --fetch.
# "" = chua tim duoc. Xem ghi chu trong coverage().
# ---------------------------------------------------------------------------
PILLAR3: dict[str, str] = {
    "ACB": "https://acb.com.vn/acbwebsite/files/12.2024_CONG%20BO%20THONG%20TIN%20THEO%20TT41_VN_10042025.pdf",
    "BAB": VIETSTOCK_CAR.format(san="HNX", nam=2026, ma="BAB"),
    "BID": "https://bidv.com.vn/bidv/quan-he-nha-dau-tu/thong-tin-co-dong/congbothongtin",
    "BVB": "https://bvbank.net.vn/wp-content/uploads/2022/01/BAOCAOCONGBOTHONGTINTYLEANTOANVON__1588563611354.pdf",
    "CTG": "",
    "EIB": VIETSTOCK_CAR.format(san="HOSE", nam=2026, ma="EIB"),
    "HDB": "https://cdn.hdbank.com.vn/hdbank-file/investor/editor/bM0oFeFPUJyfnjkNnAjK20240904113105/HDBankCongbothongtinCARTT4130062024dau_1725437683266.pdf",
    "LPB": "https://lpbank.com.vn/tin-tuc/3253-bao-cao-cong-bo-thong-tin-ty-le-an-toan-von-ky-31-12-2025",
    "MBB": "https://mbbank.com.vn/resources/files/NhaDauTu/2026/T05-2026/20260527---mbb---cbtt-ty-le-an-toan-von-tai-ngay-31122025-(vn-en).pdf",
    "MSB": "",
    "NAB": "https://namabank.com.vn/en-US/car-disclosure",
    "NVB": "",
    "OCB": "https://webocb-api.ocb.com.vn/Resources/Files/20251024132716_2.1.-ban-cong-bo-thong-tin-an-toan-von-30.06.2025vietnamese.pdf",
    "PGB": "",
    "SHB": "https://www.shb.com.vn/wp-content/uploads/2025/10/CONG-BO-TY-LE-AN-TOAN-VON-30-06-2025.pdf",
    "SSB": "https://www.seabank.com.vn/nha-dau-tu/ty-le-an-toan-von",
    "STB": "https://www.sacombank.com.vn/content/dam/sacombank/files/nhadautu/cong-bo-thong-tin/2025/Bao-cao-CBTT-ve-Ty-le-An-toan-von.pdf",
    "TCB": "https://techcombank.com/content/dam/techcombank/public-site/documents/ty-le-an-toan-von-2h2025-final.pdf",
    "TPB": "https://tpb.vn/wps/wcm/connect/fc169b8a-2b23-4d8c-b676-7a3fd0ec12c3/BC+CBTT+CAR_TT41_T6.2024.pdf?MOD=AJPERES&CONVERT_TO=url&CACHEID=ROOTWORKSPACE-fc169b8a-2b23-4d8c-b676-7a3fd0ec12c3-paKBrns",
    "VCB": "https://portal.vietcombank.com.vn/content/Investors/Investors",
    "VIB": "https://www.vib.com.vn/wps/wcm/connect/a3ab69fb-bee6-4c51-9587-ee2d41f8dc1b/VIB+Pillar+3+Report.Final_VN+30.06.2026.pdf?MOD=AJPERES&CVID=pL4vXSN",
    "VPB": "https://www.vpbank.com.vn/-/media/vpbank-latest/5nha-dau-tu/cong-bo-thong-tin-ty-le-an-toan-von/2025/cong-bo-thong-tin-ty-le-an-toan-von-quy-2-2025.pdf",
}

# NH da chuyen / dang ky chuyen sang Basel III (TT14) -- quyet dinh CO SO tinh CAR.
# Nguon: VNDIRECT, bao cao nganh 02/12/2025 + cong bo cua chinh NH.
# Day la METADATA de biet dong nao khong so truc tiep duoc voi dong nao, KHONG phai
# so lieu CAR. Bao cao CTCK khong dung lam nguon so - xem ghi chu cuoi file.
BASEL3_APPLYING = {"TPB", "LPB", "VIB", "SSB", "HDB", "NAB", "VCB", "BID"}
BASEL3_IRB_REGISTERED = {"TPB", "VPB", "VCB", "ACB"}
TT14_EFFECTIVE = "2025-09-15"


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
# mbbank.com.vn chan client tu dong bang mot phep thu cookie chay bang JavaScript:
# lan goi dau tra ve 177 byte HTML dat cookie "D1N" roi reload. Khong phai dang
# nhap hay tra phi - chi la buoc ma trinh duyet lam tu dong. Doc cookie tu chinh
# phan hoi roi goi lai la qua; khong lam vay thi moi URL cua MBB deu tra 0 byte.
_COOKIE_JS = re.compile(r'document\.cookie="([^"=]+)=([^"]+)"')


def _get(url: str, timeout: int = 90):
    """GET mot file, tu vuot phep thu cookie kieu JavaScript neu nguon dung."""
    import requests

    session = requests.Session()
    session.headers.update({"User-Agent": UA})
    r = session.get(url, timeout=timeout, verify=False)
    if b"%PDF" not in r.content[:16]:
        m = _COOKIE_JS.search(r.text[:800])
        if m:
            from urllib.parse import urlparse
            session.cookies.set(m.group(1), m.group(2), domain=urlparse(url).hostname)
            r = session.get(url, timeout=timeout, verify=False)
    return r


def period_end(period: str) -> str:
    """Ngay chot cua mot ky quy (dung cho ban ghi nguon, truoc khi gop nua nam)."""
    year, quarter = period.split("-Q")
    return f"{year}-{QUARTER_END[int(quarter)]}"


def to_half(period: str) -> tuple[str, int]:
    """'2025-Q2' -> ('2025-H1', 0). rank 0 = ky chuan, 1 = ky thay the."""
    year, quarter = period.split("-Q")
    half, rank = QUARTER_TO_HALF[int(quarter)]
    return f"{year}-{half}", rank


def half_end(period: str) -> str:
    year, half = period.split("-")
    return f"{year}-{HALF_END[half]}"


def collapse_to_half(df: pd.DataFrame) -> pd.DataFrame:
    """Gop ban ghi theo quy thanh ky nua nam.

    Trong mot nua nam, uu tien ky chot (Q2 cho H1, Q4 cho H2). Chi khi thieu ky do
    moi lay Q1/Q3 lam thay the, va khi do danh dau dung_ky_thay_the=True kem
    as_of_date THAT (31/03 hoac 30/09) -- khong gan nhan 30/06 cho mot con so chot
    ngay 31/03. Day la cho de sinh sai lech am tham nhat khi doi don vi ky.
    """
    out = df.copy()
    mapped = out["period"].map(to_half)
    out["ky_goc"] = out["period"]
    out["as_of_date"] = out["period"].map(period_end)
    out["period"] = [m[0] for m in mapped]
    out["_rank"] = [m[1] for m in mapped]
    out = out.sort_values(["ticker", "period", "_rank"])
    out = out.drop_duplicates(subset=["ticker", "period"], keep="first")
    out["dung_ky_thay_the"] = out["_rank"] == 1
    return out.drop(columns=["_rank"])


# ---------------------------------------------------------------------------
# Doc PDF ban cong bo
# ---------------------------------------------------------------------------
_DATE = re.compile(r"\b(\d{2})[/.](\d{2})[/.](20\d{2})\b")
_PCT = re.compile(r"(\d{1,2})[.,](\d{1,2})\s*%")


def parse(content: bytes) -> dict:
    """Trich ky bao cao + cac ung vien ty le tu PDF ban cong bo.

    KHONG doan gia tri nao la CAR: tra ve cac o tim duoc kem so trang de nguoi
    doc chot. Ly do giong lending_rates_bank.py -- module doc dung nhung gi
    nguon in ra, cho gi khong chac thi bao chu khong tu sua.
    """
    import fitz

    doc = fitz.open(stream=content, filetype="pdf")
    full = "\n".join(page.get_text() for page in doc)
    scanned = len(full.strip()) < 500

    hits = []
    for i, page in enumerate(doc):
        text = page.get_text()
        if not re.search(r"[Tt]ỷ lệ an toàn vốn", text) or not _PCT.search(text):
            continue
        hits.append({
            "trang": i + 1,
            "ky": ["/".join(d) for d in _DATE.findall(text)][:4],
            "ty_le": [f"{a}.{b}" for a, b in _PCT.findall(text)][:8],
        })

    # Co so tinh. Chi nhac ten Thong tu 14 la KHONG DU: gan nhu ban cong bo nao tu
    # 2025 cung dan TT14 o phan boi canh du van dang tinh theo TT41. Ban VIB ky
    # 30/06/2025 la vi du - heuristic chi dua vao ten van ban doc ra TT14, sai.
    # Chan bang ngay: TT14 hieu luc 15/09/2025 nen ky truoc do khong the la TT14.
    # Bo ngay TUONG LAI: ban VPBank co "01/01/2030" trong lo trinh Basel III, lay
    # max tho se day ky bao cao vuot moc TT14 va lam ca ban 2025 thanh "?".
    hom_nay = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ky_max = max(
        (f"{y}-{m}-{d}" for d, m, y in _DATE.findall(full) if f"{y}-{m}-{d}" <= hom_nay),
        default="",
    )
    nhac_14 = bool(re.search(r"Thông tư\s*(số\s*)?14(?:/2025)?", full))
    nhac_41 = bool(re.search(r"Thông tư\s*(số\s*)?41", full))
    if ky_max and ky_max < TT14_EFFECTIVE:
        thong_tu = "TT41"  # truoc ngay TT14 co hieu luc, khong the la TT14
    elif nhac_14 and not nhac_41:
        thong_tu = "TT14"
    elif nhac_14 and nhac_41:
        thong_tu = "?"  # nhac ca hai va ky sau 15/09/2025 -> phai doc tay
    elif nhac_41:
        thong_tu = "TT41"
    else:
        thong_tu = "?"

    return {
        "so_trang": len(doc),
        "scanned": scanned,
        "thong_tu": thong_tu,
        "ky_trong_file": sorted({"/".join(d) for d in _DATE.findall(full)}),
        "bang": hits,
    }


def fetch(ticker: str, url: str | None = None) -> dict:
    """Tai ban cong bo cua mot NH va trich thu. Khong ghi file."""
    import requests

    url = url or PILLAR3.get(ticker, "")
    if not url:
        return {"ticker": ticker, "loi": "chua co URL trong PILLAR3"}
    # portal WebSphere gan ?MOD=AJPERES... sau .pdf nen khong dung endswith duoc
    if ".pdf" not in url.split("?")[0].lower():
        return {"ticker": ticker, "url": url,
                "loi": "URL la TRANG danh sach, khong phai PDF - mo tay de lay link ban moi nhat"}

    try:
        r = _get(url)
    except Exception as exc:
        return {"ticker": ticker, "url": url, "loi": repr(exc)[:150]}
    if b"%PDF" not in r.content[:2048]:
        return {"ticker": ticker, "url": url,
                "loi": f"khong phai PDF (HTTP {r.status_code}, {len(r.content)} bytes)"}

    out = parse(r.content)
    out["ticker"] = ticker
    out["url"] = url
    return out


# ---------------------------------------------------------------------------
# Dung bang
# ---------------------------------------------------------------------------
def from_vnstock() -> pd.DataFrame:
    """88 o CAR co san trong bank_credit_quarterly.csv."""
    df = pd.read_csv(VNSTOCK, encoding="utf-8-sig")
    df = df[df["car_percent"].notna()][["ticker", "period", "car_percent"]].copy()
    # float chu khong phai pd.NA: giu cung dtype voi from_disclosed() nen concat
    # khong phai doan kieu du lieu
    df["car_rieng_le_percent"] = float("nan")
    df["tier1_percent"] = float("nan")
    df["thong_tu"] = df["period"].map(lambda p: "TT14?" if p >= "2025-Q4" else "TT41")
    df["co_so"] = "hop_nhat"
    df["nguon"] = "vnstock"
    df["do_tin_cay"] = "cao"
    df["source_url"] = ""
    df["note"] = ("Truong RT_BANK_CAR. Doi chieu voi ban NH tu cong bo cho ket qua "
                  "khop tuyet doi (5/5 o) -> day la ban HOP NHAT do NH cong bo.")
    return df


def from_disclosed() -> pd.DataFrame:
    rows = []
    for period, hop_nhat, rieng_le, tier1, thu_tu, url in MBB_HALFYEAR:
        rows.append({
            "ticker": "MBB",
            "period": period,
            "car_percent": hop_nhat,
            "car_rieng_le_percent": rieng_le,
            "tier1_percent": tier1,
            # ban 31/12/2025 van ghi ro "theo Thong tu 41/2016 va van ban sua doi"
            "thong_tu": "TT41",
            "co_so": "hop_nhat",
            "nguon": "ngan_hang_cong_bo",
            "do_tin_cay": "cao",
            "source_url": url,
            "note": f"Bieu 2, thu tu cot '{thu_tu}' doc tu NHAN COT chu khong tu vi tri "
                    f"- MBB DAO thu tu cot tu ban 31/12/2020. Xem MBB_HALFYEAR.",
        })
    for period, hop_nhat in TCB_CHART:
        rows.append({
            "ticker": "TCB",
            "period": period,
            "car_percent": hop_nhat,
            "car_rieng_le_percent": float("nan"),
            "tier1_percent": float("nan"),
            "thong_tu": "TT41",
            "co_so": "hop_nhat",
            "nguon": "ngan_hang_cong_bo",
            "do_tin_cay": "tb",
            "source_url": TCB_URL,
            "note": "Doc tu bieu do CAR trang 6 ban 2H2025 - bieu do CO NHAN SO, nhung "
                    "nguon tu ghi la lam tron 1 chu so. Dung dung de tinh chenh lech "
                    "duoi 0,1 diem. Xem TCB_CHART.",
        })
    for period, rieng_le, hop_nhat in VPB_QUARTERLY:
        rows.append({
            "ticker": "VPB",
            "period": period,
            "car_percent": hop_nhat,
            "car_rieng_le_percent": rieng_le,
            "tier1_percent": float("nan"),
            # TT14 hieu luc 15/09/2025 nhung VPBank chua tuyen bo ap dung trong cac
            # ban nay -> danh dau nghi van cho ky sau moc, khong tu ket luan
            "thong_tu": "TT41" if period < "2025-Q4" else "TT41?",
            "co_so": "hop_nhat",
            "nguon": "ngan_hang_cong_bo",
            "do_tin_cay": "cao",
            "source_url": vpb_url(period),
            "note": "Trich tu cau van ban bao cao tu mo ta. VPBank la NH duy nhat cong bo "
                    "THEO QUY (17 ban 2022-Q1 -> 2026-Q1). Xem VPB_QUARTERLY.",
        })
    for tic, period, car, rieng_le, tier1, tt, tin_cay, url, note in DISCLOSED:
        if tic == "VPB":
            continue  # da co trong VPB_QUARTERLY, tranh trung khoa
        rows.append({
            "ticker": tic,
            "period": period,
            "car_percent": car,
            "car_rieng_le_percent": rieng_le,
            "tier1_percent": tier1,
            "thong_tu": tt,
            "co_so": "hop_nhat",
            "nguon": "ngan_hang_cong_bo",
            "do_tin_cay": tin_cay,
            "source_url": url,
            "note": note,
        })
    return pd.DataFrame(rows)


def periods(start: str = "2019-H1", end: str = "2026-H1") -> list[str]:
    y0, h0 = int(start[:4]), int(start[-1])
    y1, h1 = int(end[:4]), int(end[-1])
    out = []
    y, h = y0, h0
    while (y, h) <= (y1, h1):
        out.append(f"{y}-H{h}")
        y, h = (y + 1, 1) if h == 2 else (y, 2)
    return out


def tickers() -> list[str]:
    return sorted(pd.read_csv(VNSTOCK, encoding="utf-8-sig")["ticker"].unique())


def full_grid() -> pd.DataFrame:
    """Khung DAY DU 22 NH x moi ky nua nam, o chua co so thi de TRONG.

    Muc dich: file la BANG CONG VIEC, khong chi la ket qua crawl. O trong noi ro
    "ky nay ton tai nhung chua tim ra so", khac han voi viec khong co dong nao -
    nguoi doc khong phai tu doan xem la thieu du lieu hay khong co ky do.
    """
    rows = [{"ticker": t, "period": p, "as_of_date": half_end(p),
             "ky_goc": "", "dung_ky_thay_the": False,
             "car_percent": float("nan"), "car_rieng_le_percent": float("nan"),
             "tier1_percent": float("nan"), "thong_tu": "", "co_so": "hop_nhat",
             "nguon": "", "do_tin_cay": "", "source_url": "", "note": ""}
            for t in tickers() for p in periods()]
    return pd.DataFrame(rows)


def build() -> pd.DataFrame:
    """Khung day du, dien nhung o code da biet.

    Thu tu quan trong: gop nguon TRUOC (ban NH tu cong bo thang vnstock o o quy
    trung nhau), roi moi collapse_to_half(). Lam nguoc lai thi mot ban vnstock ky
    Q2 co the dai dien cho ca nua nam va che mat ban goc cua chinh ngan hang.
    """
    known = pd.concat([from_vnstock(), from_disclosed()], ignore_index=True)
    # nguon sau thang nguon truoc o o trung khoa QUY
    known = known.drop_duplicates(subset=["ticker", "period"], keep="last")
    known = collapse_to_half(known).set_index(["ticker", "period"])

    grid = full_grid().set_index(["ticker", "period"])
    common = known.index.intersection(grid.index)
    for col in [c for c in COLUMNS if c not in ("ticker", "period", "retrieved_at_utc")]:
        grid.loc[common, col] = known.loc[common, col]

    grid["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
    return grid.reset_index()[COLUMNS].sort_values(["ticker", "period"]).reset_index(drop=True)


# cot nguoi dung co the sua tay; giu nguyen khi hop nhat lai
_VALUE_COLS = ["as_of_date", "ky_goc", "dung_ky_thay_the", "car_percent",
               "car_rieng_le_percent", "tier1_percent", "thong_tu", "co_so",
               "nguon", "do_tin_cay", "source_url", "note"]


def write(rebuild: bool = False) -> pd.DataFrame:
    """Ghi file, GIU NGUYEN nhung o da co so trong file cu.

    Cung nguyen tac voi loan_rates.py: module KHONG BAO GIO ghi de o da co so.
    File nay co dong nhap tay, nen chay lai crawler ma ghi de thi mat cong nhap.
    - o file cu co so, code khong co  -> giu nguyen file cu
    - o file cu trong, code co so     -> dien vao
    - ca hai cung co so va LECH nhau  -> BAO conflict, van giu file cu

    rebuild=True bo qua file cu, dung lai tu dau tu code (chi dung khi co y).
    """
    OUT.mkdir(parents=True, exist_ok=True)
    df = build()
    conflicts, replaced, kept = [], [], 0

    if MASTER.exists() and not rebuild:
        # Doc file cu NGUYEN VAN CHU: nguoi dung ghi "NA" (= NH khong cong bo ky do) o mot so o,
        # doc mac dinh thi pandas bien "NA" thanh o trong va lan ghi sau xoa mat dau danh dau.
        old = pd.read_csv(MASTER, encoding="utf-8-sig", keep_default_na=False,
                          na_values=[""]).set_index(["ticker", "period"])
        new = df.set_index(["ticker", "period"])
        new["car_percent"] = new["car_percent"].astype(object)
        keep_cols = _VALUE_COLS + ["retrieved_at_utc"]
        for key in old.index.intersection(new.index):
            o, n = old.loc[key], new.loc[key]
            if pd.isna(o["car_percent"]):
                # code cung chua co so -> giu nguyen dong cu (ky_goc, note nguoi dung da ghi)
                if pd.isna(n["car_percent"]):
                    for col in keep_cols:
                        new.loc[key, col] = o[col]
                continue
            if str(o["car_percent"]).strip().upper() == "NA":
                kept += 1
                if pd.notna(n["car_percent"]):
                    conflicts.append((key, "NA", float(n["car_percent"])))
                for col in keep_cols:
                    new.loc[key, col] = o[col]
                continue
            # Ky THAY THE (Q1/Q3 dung tam cho nua nam) chi giu den khi code co so cua KY CHOT.
            # Khong coi la conflict: day la thay so tam bang so dung ky, vi du VPB 2026-H1
            # mang so 31/03 cho toi khi ban 30/06/2026 duoc trich (07/10/2026).
            if (str(o["dung_ky_thay_the"]) == "True" and pd.notna(n["car_percent"])
                    and str(n["dung_ky_thay_the"]) != "True"):
                replaced.append((key, o["ky_goc"], n["ky_goc"]))
                continue
            kept += 1
            if pd.notna(n["car_percent"]) and abs(float(o["car_percent"]) - float(n["car_percent"])) > 1e-9:
                conflicts.append((key, float(o["car_percent"]), float(n["car_percent"])))
            for col in keep_cols:
                new.loc[key, col] = o[col]
        df = new.reset_index()[COLUMNS].sort_values(["ticker", "period"]).reset_index(drop=True)

    df.to_csv(MASTER, index=False, encoding="utf-8-sig")
    # doc lai theo cach mac dinh ("NA" -> NaN) de validate()/thong ke nhan cot so
    df = pd.read_csv(MASTER, encoding="utf-8-sig")
    n_filled = int(df["car_percent"].notna().sum())
    msg = (f"car: {len(df)} dong ({df['ticker'].nunique()} NH x {df['period'].nunique()} ky), "
           f"da co so={n_filled}, con trong={len(df) - n_filled}, giu tu file cu={kept}, "
           f"thay ky thay the={len(replaced)}, conflicts={len(conflicts)}")
    with open("crawl_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg} -> {MASTER}\n")
    print(f"ghi {MASTER}\n  {msg}")
    for (tic, per), ky_cu, ky_moi in replaced:
        print(f"  {tic} {per}: thay ky thay the {ky_cu} bang ky chot {ky_moi}")
    if conflicts:
        print("  !! O LECH giua file va code (GIU FILE, khong tu sua):")
        for (tic, per), o, n in conflicts:
            print(f"     {tic} {per}: file={o} vs code={n}")
    return df


# ---------------------------------------------------------------------------
# Kiem dinh
# ---------------------------------------------------------------------------
def validate(df: pd.DataFrame | None = None) -> None:
    if df is None:
        df = pd.read_csv(MASTER, encoding="utf-8-sig")

    print(f"{len(df)} dong, {df['ticker'].nunique()}/22 NH, "
          f"{df['period'].min()} -> {df['period'].max()}")

    # o trong la "chua tim ra so", khong phai "ky khong ton tai" -- moi thong ke
    # ben duoi deu tinh tren o DA CO SO, neu khong ty le se bi loang
    co = df[df["car_percent"].notna()]
    print(f"da co so: {len(co)}/{len(df)} o ({len(co) / len(df) * 100:.0f}%), "
          f"con trong {len(df) - len(co)}")
    halves = co["period"].str[-2:].value_counts()
    print(f"phan bo o DA CO SO theo nua nam: {halves.to_dict()}")

    print("\n=== BANG CONG VIEC: o con trong theo tung NH ===")
    ks = periods()
    piv = co.pivot_table(index="ticker", columns="period", values="car_percent",
                         aggfunc="first").reindex(index=tickers(), columns=ks)
    trong = piv.isna().sum(1).sort_values(ascending=False)
    for tic, n in trong.items():
        if n == 0:
            print(f"  {tic}: DU CA {len(ks)} KY")
        else:
            print(f"  {tic}: thieu {n}/{len(ks)} -> "
                  + ", ".join(k for k in ks if pd.isna(piv.loc[tic, k])))
    print(f"\nNH day du moi ky: {int((trong == 0).sum())}/22")
    print("ky trong nhieu nhat: "
          + str(piv.isna().sum().sort_values(ascending=False).head(4).to_dict()))

    thay_the = df[df["dung_ky_thay_the"]]
    print(f"\nky THAY THE (lay Q1/Q3 vi thieu ky chot 30/06 - 31/12): {len(thay_the)} dong")
    if len(thay_the):
        print("   " + ", ".join(f"{r.ticker} {r.period}<-{r.ky_goc}"
                                for r in thay_the.itertuples()))
        print("   as_of_date cua cac dong nay KHONG phai 30/06 hay 31/12 - doc cot do,")
        print("   dung gia dinh moi dong H1 deu chot cung mot ngay.")

    print(f"\nnguon: {df['nguon'].value_counts().to_dict()}")
    print(f"do tin cay: {df['do_tin_cay'].value_counts().to_dict()}")
    print(f"co so tinh: {df['thong_tu'].value_counts().to_dict()}")

    car = df["car_percent"]
    print(f"\nkhoang: {car.min():.2f}% - {car.max():.2f}%, trung vi {car.median():.2f}%")
    below = df[car < 8.0]
    print(f"duoi nguong toi thieu 8%: {len(below)} dong"
          + (f" -> {below['ticker'].tolist()}" if len(below) else " (dung ky vong)"))

    # doi chieu ban NH tu cong bo voi vnstock o cac o trung
    vn = from_vnstock().set_index(["ticker", "period"])["car_percent"]
    dis = from_disclosed().set_index(["ticker", "period"])["car_percent"]
    both = pd.concat([vn.rename("vnstock"), dis.rename("ngan_hang")], axis=1).dropna()
    print(f"\ndoi chieu ban NH tu cong bo voi vnstock: {len(both)} o trung")
    if len(both):
        both["lech"] = (both["ngan_hang"] - both["vnstock"]).round(4)
        print(both.to_string())
        exact = int((both["lech"].abs() < 1e-9).sum())
        print(f"  khop tuyet doi: {exact}/{len(both)}")
        if exact < len(both):
            print("  !! CO O LECH - kiem lai truoc khi dung, dung tu chon ben nao dung")

    news = dis.index.difference(vn.index)
    print(f"o MOI vnstock chua co: {len(news)} -> {[f'{t} {p}' for t, p in news]}")

    # canh bao dut gay co so
    # "TT41?" la CHUA XAC NHAN, khong phai co so khac -> bo dau ? truoc khi so sanh,
    # neu khong VPB bi bao nham la dang o hai co so
    # CHI xet cac o DA CO SO: o trong co thong_tu rong, neu tinh vao thi moi NH
    # deu thanh "hai co so" ({'TT41', ''}) va canh bao mat het y nghia
    tt = df["thong_tu"].fillna("")
    dat = df[(tt != "") & df["car_percent"].notna()].assign(_c=tt.str.rstrip("?"))
    mixed = dat.groupby("ticker")["_c"].nunique()
    if (mixed > 1).any():
        print(f"\n!! NH co CAR tren HAI CO SO KHAC NHAU: {mixed[mixed > 1].index.tolist()}")
        print("   KHONG so cac dong nay voi nhau nhu cung mot chuoi.")

    ngo = df[tt.str.endswith("?")]
    if len(ngo):
        print(f"\nco so CHUA XAC NHAN ({len(ngo)} dong, ky sau moc TT14 {TT14_EFFECTIVE}):")
        print("   " + ", ".join(f"{r.ticker} {r.period}" for r in ngo.itertuples()))
        print("   Doc ban goc de chot TT41 hay TT14 truoc khi dua vao xep hang.")


def coverage(df: pd.DataFrame | None = None, den_ky: str = "2026-H1") -> pd.DataFrame:
    """Tinh trang tung NH: quan sat cuoi cung, do cu, con thieu gi."""
    if df is None:
        df = pd.read_csv(MASTER, encoding="utf-8-sig")

    # file la khung day du nen phai LOC o da co so, neu khong moi NH deu "co 15
    # quan sat" ma car_moi_nhat lai NaN
    df = df[df["car_percent"].notna()]
    all_tickers = tickers()
    y_den, h_den = int(den_ky[:4]), int(den_ky[-1])

    rows = []
    for tic in all_tickers:
        g = df[df["ticker"] == tic].sort_values("period")
        if g.empty:
            rows.append({"ticker": tic, "so_quan_sat": 0, "ky_cuoi": None,
                         "car_moi_nhat": None, "nguon": None, "cu_may_nua_nam": None,
                         "co_url": bool(PILLAR3.get(tic))})
            continue
        last = g.iloc[-1]
        y, h = int(last["period"][:4]), int(last["period"][-1])
        rows.append({
            "ticker": tic,
            "so_quan_sat": len(g),
            "ky_cuoi": last["period"],
            "car_moi_nhat": last["car_percent"],
            "nguon": last["nguon"],
            "cu_may_nua_nam": (y_den - y) * 2 + (h_den - h),
            "co_url": bool(PILLAR3.get(tic)),
        })
    out = pd.DataFrame(rows)

    print(out.to_string(index=False))
    print(f"\nco it nhat 1 quan sat: {int((out['so_quan_sat'] > 0).sum())}/22")
    thieu = out[out["so_quan_sat"] == 0]["ticker"].tolist()
    print(f"KHONG co quan sat nao: {thieu or 'khong'}")
    cu = out[out["cu_may_nua_nam"] > 2].sort_values("cu_may_nua_nam", ascending=False)
    print(f"cu hon 1 nam (>2 nua nam) tinh den {den_ky}: {len(cu)} NH")
    if len(cu):
        print(cu[["ticker", "ky_cuoi", "car_moi_nhat", "cu_may_nua_nam"]].to_string(index=False))
    chua_co_url = out[~out["co_url"]]["ticker"].tolist()
    print(f"chua tim duoc trang cong bo: {chua_co_url or 'khong'}")
    return out


def as_of(period: str = "2026-H1", df: pd.DataFrame | None = None) -> pd.DataFrame:
    """CAR dung duoc tai mot ky, forward-fill tu quan sat gan nhat.

    Tra ve kem cot tuoi_quy va thong_tu de KHONG cho phep dung mu: mot NH mang so
    cu 4 nam khong duoc xep hang ngang voi NH co so moi 2 quy, va mot NH da chuyen
    sang TT14 khong so truc tiep duoc voi NH con o TT41. Xem muc do nhay trong
    README truoc khi dua vao ma tran quyet dinh.
    """
    if df is None:
        df = pd.read_csv(MASTER, encoding="utf-8-sig")
    y_den, h_den = int(period[:4]), int(period[-1])

    usable = df[(df["period"] <= period) & df["car_percent"].notna()].sort_values("period")
    last = usable.groupby("ticker").tail(1).set_index("ticker")
    out = last[["period", "as_of_date", "car_percent", "thong_tu", "nguon", "do_tin_cay"]].copy()
    out["tuoi_nua_nam"] = out["period"].map(
        lambda p: (y_den - int(p[:4])) * 2 + (h_den - int(p[-1])))
    return out.sort_values("car_percent", ascending=False)


def check_sources(pause: float = 0.5) -> bool:
    """Kiem cac trich dan trong DISCLOSED con song khong."""
    import time

    import requests

    ok = True
    seen = set()
    urls = [(t, p, u) for t, p, _c, *_r, u, _n in DISCLOSED]
    urls += [("MBB", p, u) for p, *_x, u in MBB_HALFYEAR]
    urls += [("VPB", p, vpb_url(p)) for p, *_x in VPB_QUARTERLY]
    for tic, period, url in urls:
        if url in seen:
            continue
        seen.add(url)
        try:
            r = _get(url, timeout=60)
        except Exception as exc:
            print(f"!! {tic:4s} {period}  KHONG TAI DUOC: {repr(exc)[:80]}")
            ok = False
            continue
        is_pdf = b"%PDF" in r.content[:2048]
        good = r.status_code == 200 and is_pdf
        ok &= good
        print(f"{'OK ' if good else '!! '}{tic:4s} {period}  {r.status_code}  "
              f"pdf={str(is_pdf):5s}  {len(r.content) // 1024} KB")
        time.sleep(pause)

    print("\ntat ca trich dan con song" if ok else "\nCO TRICH DAN HONG - sua DISCLOSED")
    return ok


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if "--rebuild" in sys.argv:
        # bo qua file cu, dung lai tu dau tu code -- XOA moi o nhap tay
        validate(write(rebuild=True))
    elif "--validate" in sys.argv:
        validate()
    elif "--coverage" in sys.argv:
        coverage()
    elif "--as-of" in sys.argv:
        i = sys.argv.index("--as-of")
        ky = sys.argv[i + 1] if len(sys.argv) > i + 1 else "2026-Q2"
        print(as_of(ky).to_string())
    elif "--fetch" in sys.argv:
        i = sys.argv.index("--fetch")
        tic = sys.argv[i + 1] if len(sys.argv) > i + 1 else ""
        result = fetch(tic.upper())
        for key, value in result.items():
            if key == "bang":
                for b in value:
                    print(f"  trang {b['trang']}: ky={b['ky']} -> {b['ty_le']}")
            else:
                print(f"{key}: {value}")
    elif "--check-sources" in sys.argv:
        raise SystemExit(0 if check_sources() else 1)
    else:
        validate(write())
