from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd

PDF_DIR = "data/bctc_pdf"
CACHE = f"{PDF_DIR}/_ocr"
INVENTORY = f"{PDF_DIR}/inventory.csv"
OUT = "data/credit/ocr_asset_quality_quarterly.csv"  # thi diem
OUT_ALL = "data/credit/ocr_asset_quality_2012_2017.csv"
VND = "data/credit/bank_balance_vndirect_quarterly.csv"
PANEL = "data/model/bank_panel_quarterly.csv"
LOW_DPI, HIGH_DPI, RETRY_DPI, THREADS, WORKERS = 90, 200, 300, 4, 4
# Tong 5 nhom so voi du no gop VNDirect: bang phan loai co the kem dong ngoai (repo cua MBS ~1,2%) nen de 2%;
# phep kiem chat la dong tong in ngay trong bang (0,1%). Tong tien gui khop tien gui KH tren CDKT gan nhu tuyet doi.
TOL_LOANS, EXACT = 0.02, 3
UNITS = (1.0, 1e3, 1e4, 1e6)
LOANS_EXACT = ("tong_bang", "khop_cdkt")  # hai phep kiem BANG DUNG cho bang no
PRIOR_TOL = 2e-5  # "khop dung" so ky truoc tren CDKT VNDirect (dong): lam tron trieu dong cua bang lech < 1e-6
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
EXCHANGES = {"ACB": ["HNX", "HOSE"], "SHB": ["HNX", "HOSE"], "NVB": ["HNX", "UPCOM", "OTC"], "BAB": ["HNX", "UPCOM", "OTC"],
             "PGB": ["UPCOM", "HOSE", "OTC"]}
DEFAULT_EX = ["HOSE", "HNX", "UPCOM", "OTC"]  # NH chua niem yet truoc 2017: Vietstock co the luu o UPCOM/OTC
# Truoc khi niem yet, Vietstock luu BCTC quy o thu muc OTC theo TEN THUONG HIEU thay vi ma (do 13/10/2026):
# OTC/2015/BCTC/VN/QUY 2/Techcombank_Baocaotaichinh_Q2_2015_Hopnhat.pdf, VPBank_..., NamABank_..., PGBank_..., SeABank_...
BRAND = {"TCB": ["Techcombank"], "VPB": ["VPBank"], "TPB": ["TPBank", "Tienphongbank"], "HDB": ["HDBank"],
         "MSB": ["Maritimebank"], "OCB": ["Phuongdongbank"], "SSB": ["SeABank"], "NAB": ["NamABank"], "PGB": ["PGBank"],
         "BVB": ["VietCapitalBank", "BanVietBank"], "BAB": ["BacABank"], "LPB": ["LienVietPostBank"]}
ALL_BANKS = "ACB BAB BID BVB CTG EIB HDB LPB MBB MSB NAB NVB OCB PGB SHB SSB STB TCB TPB VCB VIB VPB".split()
ALL_QUARTERS = [(y, q) for y in range(2012, 2018) for q in (1, 2, 3, 4)]
INVENTORY_ALL = f"{PDF_DIR}/inventory_all.csv"
# Nguon bo sung cho quy Vietstock khong co (13/10/2026): BCTC quy tren web NH (TPBank), ban luu Wayback (Bac A Bank),
# BCTC nam kiem toan tren Vietstock (.../BCTC/VN/NAM/{MA}_Baocaotaichinh_{nam}_Kiemtoan_Hopnhat.pdf) cho quy 4.
EXTRA = f"{PDF_DIR}/extra_sources.csv"
# Danh muc that cua Vietstock (14/10/2026): do URL theo mau ten bo sot file .rar/.zip/.docx, thu muc KHAC, BCTC soat
# xet 6 thang (_6T_{nam}_Soatxet), ten cu (BIDV_, NASB_ cho Bac A) va NH luu o san khac (VIB 2012-2014).
CATALOG = f"{PDF_DIR}/vietstock_documents.csv"
ALT_DIR = f"{PDF_DIR}/_alt"
SEVENZIP = r"C:\Program Files\7-Zip\7z.exe"
VS = "https://finance.vietstock.vn"
# So doc bang mat tu anh trang (o OCR khong qua phep kiem): cung phai qua phep cong DUNG nhu OCR -- tong cac nhom/loai
# bang dong tong in trong bang, hoac bang so tren CDKT VNDirect. Don vi: so in trong bang; unit = he so ra dong.
# lech_nguon: chinh bao cao cong sai (LPB 2015-Q3: 5 nhom cong 54.611.751, dong tong in 54.609.751 = CDKT) -> chi nhan
# khi dong tong in BANG DUNG CDKT va muc lech dung bang so ghi; trang thai rieng "ok_lech_nguon".
MANUAL = "data/credit/ocr_doc_tay.csv"
VARIANTS = ["Hopnhat", "Congtyme", "Rieng", None]
PILOT_BANKS = ["ACB", "MBB", "CTG", "SHB", "EIB"]
PILOT_QUARTERS = [(2012, 4), (2013, 2), (2014, 3), (2015, 1), (2016, 2), (2017, 3), (2018, 2)]
QEND = {1: (31, 3), 2: (30, 6), 3: (30, 9), 4: (31, 12)}
LOAN_KEYS = ["tieuchuan", "canchuy", "nghingo", "matvon", "khanang"]
DEP_KEYS = ["khongkyhan", "cokyhan", "chuyendung", "kyquy"]

_OCR = None


def fold(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s).replace("đ", "d").replace("Đ", "D"))
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if not unicodedata.combining(c)).lower())


# --------------------------------------------------------------------------- tai PDF
def _exists(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-200"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status in (200, 206)
    except Exception:
        return False


def inventory(banks, quarters, path: str = INVENTORY, reprobe_missing: bool = False) -> pd.DataFrame:
    rows = pd.read_csv(path, encoding="utf-8-sig").fillna("").to_dict("records") if os.path.exists(path) else []
    if reprobe_missing:  # do lai cac o chua co URL (vd sau khi them ten thuong hieu)
        rows = [r for r in rows if r["url"]]
    done = {(r["ticker"], int(r["year"]), int(r["quarter"])) for r in rows}
    for t in banks:
        names = [t] + BRAND.get(t, [])
        memo = None
        pat = re.compile(r"/data/(\w+)/\d{4}/BCTC/VN/QUY%20\d/(\w+?)_Baocaotaichinh_Q\d_\d{4}(?:_(\w+))?\.pdf")
        for r in rows:
            if r["ticker"] == t and r["url"]:
                memo = pat.search(r["url"]).groups()
        for y, q in quarters:
            if (t, y, q) in done:
                continue
            combos = [(ex, n, v) for ex in list(dict.fromkeys(EXCHANGES.get(t, DEFAULT_EX) + ["OTC"])) for n in names for v in VARIANTS]
            if memo:
                combos.insert(0, memo)
            hit = ""
            for ex, n, v in combos:
                url = (f"https://static2.vietstock.vn/data/{ex}/{y}/BCTC/VN/QUY%20{q}/{n}_Baocaotaichinh_Q{q}_{y}"
                       + (f"_{v}" if v else "") + ".pdf")
                time.sleep(0.2)
                if _exists(url):
                    hit, memo = url, (ex, n, v)
                    break
            rows.append(dict(ticker=t, year=y, quarter=q, url=hit))
        pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
        n = sum(1 for r in rows if r["ticker"] == t and r["url"])
        print(f"  kiem ke {t}: {n}/{len(quarters)} quy co PDF", flush=True)
    return pd.DataFrame(rows)


def pdf_path(t, y, q) -> str:
    return f"{PDF_DIR}/{t}_{y}Q{q}.pdf"


def _download_one(url: str, path: str):
    os.makedirs(PDF_DIR, exist_ok=True)
    for attempt in range(5):  # Wayback tra 429 khi goi day; nghi tang dan
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = resp.read()
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 4:
                raise
            time.sleep(30 * (attempt + 1))
    if not data.startswith(b"%PDF"):
        raise ValueError(f"khong phai PDF: {url}")
    with open(path + ".part", "wb") as fh:
        fh.write(data)
    os.replace(path + ".part", path)


def download(inv: pd.DataFrame):
    os.makedirs(PDF_DIR, exist_ok=True)
    for r in inv[inv.url != ""].itertuples():
        p = pdf_path(r.ticker, r.year, r.quarter)
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            continue
        req = urllib.request.Request(r.url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=180) as resp, open(p, "wb") as fh:
            fh.write(resp.read())
        time.sleep(1)


# --------------------------------------------------------------------------- OCR
def _engine():
    global _OCR
    if _OCR is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR = RapidOCR(intra_op_num_threads=THREADS, inter_op_num_threads=1)
    return _OCR


def ocr_page(path: str, page: int, dpi: int) -> list:
    os.makedirs(CACHE, exist_ok=True)
    cp = f"{CACHE}/{os.path.basename(path)[:-4]}_p{page}_{dpi}.json"
    if os.path.exists(cp):
        return json.load(open(cp, encoding="utf-8"))
    import pymupdf
    doc = pymupdf.open(path)
    pix = doc[page].get_pixmap(dpi=dpi)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]
    res, _ = _engine()(np.ascontiguousarray(img))
    out = [[float(min(p[0] for p in b)), float(min(p[1] for p in b)), float(max(p[0] for p in b)), float(max(p[1] for p in b)),
            txt, float(sc)] for b, txt, sc in (res or [])]
    json.dump(out, open(cp, "w", encoding="utf-8"), ensure_ascii=False)
    return out


def _layer_ok(path: str) -> bool:
    import pymupdf
    raw = "".join(p.get_text() for p in pymupdf.open(path))
    letters = [c for c in raw if c.isalpha()]
    marked = sum(1 for c in letters if c in "đĐ" or unicodedata.normalize("NFD", c) != c)
    return len(letters) > 2000 and marked / len(letters) >= 0.10


def _score(text: str, keys) -> int:
    return sum(k in text for k in keys) + (1 if re.search(r"\d{1,3}(\d{3}){2,}", text) else 0)


# --------------------------------------------------------------------------- tach bang
NUM = re.compile(r"^\(?-?\d{1,3}([.,\s]\d{3})+\)?$|^\(?-?\d{4,}\)?$|^-$")
DATE = re.compile(r"(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4})")
INLINE = re.compile(r"\(?-?\d[\d.,]*\d\)?")


def _num(tok: str):
    t = tok.replace(" ", "")
    if t == "-":
        return 0
    if not NUM.match(t):
        return None
    neg = t.startswith("(") or t.startswith("-")
    v = int(re.sub(r"[^\d]", "", t))
    return -v if neg else v


def _box_dates(b) -> list:
    w = (b[2] - b[0]) / max(len(b[4]), 1)
    return [(m.groups(), b[0] + w * (m.start() + m.end()) / 2) for m in DATE.finditer(b[4])]


def _rows(boxes: list) -> list[dict]:
    if not boxes:
        return []
    h = np.median([b[3] - b[1] for b in boxes])
    items = sorted(boxes, key=lambda b: (b[1] + b[3]) / 2)
    rows, cur = [], [items[0]]
    for b in items[1:]:
        if abs((b[1] + b[3]) / 2 - np.mean([(c[1] + c[3]) / 2 for c in cur])) <= 0.5 * h:
            cur.append(b)
        else:
            rows.append(cur)
            cur = [b]
    rows.append(cur)
    # so 1-3 chu so khong co dau ngan cach (LPB 2015-Q3 "Tien gui von chuyen dung 626" trieu) chi tinh la so khi o
    # nam o nua phai trang (vung cot so); ben trai la danh so muc "1", "2" trong nhan
    xr = 0.5 * max(b[2] for b in boxes)
    out = []
    for r in rows:
        r = sorted(r, key=lambda b: b[0])
        nums, parts = [], []
        for b in r:
            v = _num(b[4])
            if v is None and re.fullmatch(r"\(?\d{1,3}\)?", b[4].strip()) and (b[0] + b[2]) / 2 > xr:
                v = int(re.sub(r"\D", "", b[4]))
                v = -v if b[4].strip().startswith("(") else v
            if v is not None:
                nums.append((v, (b[0] + b[2]) / 2))
                continue
            # OCR dinh so vao nhan ("No du tieu chuan 69511.713.622.359"): boc day so >= 5 chu so, bo ngay thang
            txt = DATE.sub(" ", b[4])
            found = [m for m in INLINE.finditer(txt) if len(re.sub(r"\D", "", m.group())) >= 5]
            w = (b[2] - b[0]) / max(len(b[4]), 1)
            for m in found:
                d = int(re.sub(r"\D", "", m.group()))
                nums.append((-d if m.group().startswith("(") else d, b[0] + w * (m.start() + m.end()) / 2))
            parts.append(INLINE.sub(" ", txt) if found else b[4])
        nums.sort(key=lambda n: n[1])
        label = " ".join(parts)
        out.append(dict(y=float(np.mean([(b[1] + b[3]) / 2 for b in r])), label=label, f=fold(label), nums=nums,
                        dates=[d for b in r for d in _box_dates(b)]))
    return out


def _loan_class(f: str):
    m = re.search(r"nh[o0]m0?([1-5])|loai([1-5])", f)
    if m:
        return int(m.group(1) or m.group(2))
    m = re.search(r"t[il1][ec]u\w?ch", f)  # "tieu chuan", OCR "ticu chuan" (SHB 2016-Q3)
    if m:
        # nhom 1 "No du tieu chuan" / nhom 3 "No duoi tieu chuan": phan chu giua "No" va "tieu" dai <= 2 ("du"; OCR
        # "di", "au", "dt") hay >= 3 ("duoi"; OCR "dudi", "durdi", "dubi"). Truoc 14/10 bat buoc "du" -> mat nhom 1
        # khi OCR doc "au"/"di" (BAB 2016-Q2, BID 2015-Q4, CTG 2015-Q2) hoac "tieujchuan" (PGB 2015-Q1)
        pre = f[:m.start()]
        tok = list(re.finditer(r"n[oagpqyiu0]i?", pre))  # chu "No" cuoi ("Nhomi - Ng du", "Ny du", "Noi du")
        pre = pre[tok[-1].end():] if tok else pre
        if len(pre) <= 2:
            return 1
        if len(pre) <= 6 and pre[0] == "d":
            return 3
        return None
    if "canch" in f or re.search(r"chuy(?!en)", f):  # "chu y" -- khong lay "chuyen nhuong", "chuyen dung"
        return 2
    if re.search(r"ngh[i1l]ng", f):
        return 4
    if "matvon" in f or "khanang" in f:
        return 5
    return None


def _dep_class(f: str, raw: str = ""):
    # dong con: "bang VND", "bang ngoai te", "bang dong Viet Nam" (OCR "bing"), hoac nhan goc bat dau bang "-";
    # dong tong "Tien, vang gui khong ky han" co chu "vang" nhung KHONG la dong con
    sub = (bool(re.search(r"b\w{1,2}ng(vnd|vne|ngoai|vang|usd|dola|eur|dong|viet)", f)) or f.startswith("bang")
           or raw.lstrip().startswith(("-", "–", "+", "·", "•")))
    # nhan OCR meo (14/10): "khong ky hgn", "khng kyhan", "c6kyhn", "eo ky han", "c ky han", "ky" -> "xy" (ACB 2015-Q2)
    # HDB viet tat "KKH" / "CKH" (chu in hoa dung rieng -- "cac khoan" bo dau cung chua "ckh")
    # (OCR dinh chu: "Tien guiKKHbangVND" -> khong dung , chi can khong nam trong cum in hoa dai hon)
    # bat buoc "y/i" sau "k": khong nham "co kha nang" (no co kha nang mat von), "khong kha nang"
    if re.search(r"kh\w{0,2}ngk[yi]\w?h\w{0,2}n|kh[o06]ngxyh[ae]n", f) or re.search(r"(?<![A-Z])KKH(?![A-Z])", raw):
        return ("demand", sub)
    if re.search(r"[ce][o06]?[kx][yi]\w?h\w?n", f) or re.search(r"(?<![A-Z])CKH(?![A-Z])", raw):
        return ("term", sub)
    if re.search(r"chuy\w{0,2}nd\w{0,2}ng", f):  # "chuyen dung", OCR "chuyen dang", "diung", "ding"
        return ("special", sub)
    if "kyquy" in f:
        return ("margin", sub)
    if "tietkiem" in f:  # ACB tach "Tien gui tiet kiem" thanh dong rieng ngang hang co ky han
        return ("savings", sub)
    return (None, sub)


def _col_x(rows, year, quarter):
    d, m = QEND[quarter]
    for r in rows:
        for (dd, mm, yy), x in r["dates"]:
            if int(yy) == year and int(mm) == m and int(dd) == d:
                return x
    return None


def _cols(rows, year, quarter) -> list:
    d, m = QEND[quarter]
    xs = [x for r in rows for _, x in r["nums"]]
    xmin = 0.4 * max(xs) if xs else 0
    out, cur = [], None
    for i, r in enumerate(rows):
        heads = sorted(((dt, x) for dt, x in r["dates"] if x >= xmin), key=lambda h: h[1])
        # nhan con lai sau khi bo ngay phai ngan ("(so soat xet)", "tai ngay"); chu thich OCB 2017-Q3 "ngay 31/12/2014
        # cua Ngan hang Nha nuoc VN)" xuong dong nen ngay roi vao vung cot so
        if heads and not r["nums"] and len(fold(DATE.sub("", r["label"]))) <= 15:
            hit = [k for k, ((dd, mm, yy), _) in enumerate(heads) if int(yy) == year and int(mm) == m and int(dd) == d]
            if not hit:
                cur = float("nan")
            else:
                # tam cot so THAT: trung vi toa do cac dong ben duoi co dung len(heads) so, ghep theo thu tu trai->phai
                # (toa do o tieu de lech cot so tới 300 px o TCB 2013-Q3 vi o chu tieu de dai)
                seg = []
                for rr in rows[i + 1:i + 25]:  # chi cac dong cua CHINH bang nay: dung o tieu de ngay ke tiep (BAB 2013-Q4)
                    if rr["dates"] and not rr["nums"]:
                        break
                    seg.append(rr)
                below = [sorted(x for _, x in rr["nums"]) for rr in seg if len(rr["nums"]) == len(heads)]
                centers = ([float(np.median([b[j] for b in below])) for j in range(len(heads))] if len(below) >= 2
                           else [x for _, x in heads])
                k = hit[0]
                gap = min((abs(c - centers[k]) for j, c in enumerate(centers) if j != k), default=None)
                # nua khoang cach cot: so duy nhat con lai trong dong ma xa hon muc nay la so cua ky khac (OCR lam mat
                # o ky nay: BID 2017-Q1 "co ky han [596.173.612]" la so 31/12/2016)
                cur = (centers[k], gap / 2 if gap else None)
        out.append(cur)
    return out


def _pick(nums, col):
    if not nums:
        return None
    if col is not None and not isinstance(col, tuple):  # NaN: bang cua ky khac
        return None
    col_x, half = col if isinstance(col, tuple) else (None, None)
    # cot ty le "100%" OCR thanh 10000 nam giua hai cot so tien (BAB 2013-Q4): bo so nho bat thuong so voi so lon nhat
    # cung dong (cung mot khoan muc o hai ky khong chenh 10^5 lan); giu so 0 ("-")
    mx = max(abs(n) for n, _ in nums)
    nums = [(n, x) for n, x in nums if n == 0 or abs(n) >= 1e-5 * mx]
    v = [n for n, _ in nums]
    # bang chia cot theo tien te (VND | ngoai te | tong), vd ACB: lay cot tong
    if len(v) >= 3 and v[-1] > 0 and abs(v[-1] - v[-2] - v[-3]) <= 0.005 * v[-1]:
        return v[-1]
    if col_x is None:
        return nums[0][0]
    best = min(nums, key=lambda n: abs(n[1] - col_x))
    if half and abs(best[1] - col_x) > half:
        return None
    return best[0]


def extract_loans(rows, year, quarter) -> list[dict]:
    cls = [_loan_class(r["f"]) for r in rows]
    vals = [_pick(r["nums"], col) for r, col in zip(rows, _cols(rows, year, quarter))]
    # mot dong mat nhan nam giua nhom k va nhom k+2 -> nhom k+1 (BID 2016-Q3: nhan "No can chu y" OCR lech dong)
    for i, r in enumerate(rows):
        if cls[i] is None and vals[i] is not None and len(r["f"]) <= 12:
            a = next((cls[j] for j in range(i - 1, -1, -1) if cls[j] is not None), None)
            b = next((cls[j] for j in range(i + 1, len(rows)) if cls[j] is not None), None)
            if a is not None and b == a + 2:
                cls[i] = a + 1
    blocks, cur = [], {}
    for r, c, v in zip(rows, cls, vals):
        if c is None and v is not None and 5 in cur and "trongdo" not in r["f"] and len(cur.get("tail", [])) < 4:
            # cac dong khong nhan duoi nhom 5: dong tong, dong cong them (repo cua MBS, "No cho xu ly" NAB) -- cach hieu
            # chon trong _loan_cand bang phep cong dung
            cur.setdefault("tail", []).append((v, len(r["f"]) <= 12 or r["f"].startswith(("tong", "cong"))))
            continue
        if c is None or v is None:
            continue
        if c in cur:
            blocks.append(cur)
            cur = {}
        cur[c] = v
    blocks.append(cur)
    return [b for b in blocks if len([k for k in b if k in range(1, 6)]) >= 4]


def extract_deposits(rows, year, quarter) -> list[dict]:
    cols = _cols(rows, year, quarter)
    blocks, cur = [], {}
    head = None  # loai cua dong tieu de MUC khong co so ngay tren (HDB: "Tien gui von chuyen dung" roi "Bang VND", ...)
    for r, col in zip(rows, cols):
        c, sub = _dep_class(r["f"], r["label"])
        v = _pick(r["nums"], col)
        if c is None and sub and head and v is not None:
            c = head
        elif c is not None and not sub:
            head = c if v is None else None
        elif c is None and v is not None:
            head = None
        # bang moi: dong tieu de ngay, hoac dong "khong ky han" (ke ca dong con) xuat hien lai sau cac loai khac -- TCB
        # chi in dong con "bang VND / ngoai te", khong co dong cap tren -> truoc 14/10 bang tien gui cua TCTD khac phia
        # tren bi cong vao tien gui khach hang
        if cur and ((r["dates"] and not r["nums"])
                    or (c == "demand" and any(k[0] in ("term", "savings", "special", "margin") for k in cur if k != "total"))):
            blocks.append(cur)
            cur = {}
        if c is None and v is not None and cur and "total" not in cur and (len(r["f"]) <= 12 or r["f"].startswith(("tong", "cong"))):
            if any(k[0] in ("special", "margin") for k in cur if k != "total"):
                cur["total"] = v  # dong "Tong" in ngay sau cac loai tien gui
            continue
        if c is None or v is None:
            continue
        key = (c, sub)
        if (c, False) in cur and key == (c, False) or (c == "demand" and not sub and cur):
            if cur:
                blocks.append(cur)
            cur = {}
        cur.setdefault(key, []).append(v)
    blocks.append(cur)
    out = []
    for b in blocks:
        top = {}
        for c in ("demand", "term", "savings", "special", "margin"):
            if (c, False) in b:
                top[c] = b[(c, False)][0]
            elif (c, True) in b:
                top[c] = sum(b[(c, True)])
        if "demand" in top and "term" in top:
            if "total" in b:
                top["_total"] = b["total"]
            out.append(top)
            # dong cap tren va tong dong con lech nhau (loi in cua chinh bao cao: LPB 2015-Q3 "khong ky han 17.889.904"
            # trong khi hai dong con cong 17.888.904) -> them ung vien tinh tu dong con; phep cong dung se chon
            alt = {c: (sum(b[(c, True)]) if (c, True) in b and (c, False) in b else v) for c, v in top.items()}
            if alt != top:
                out.append(alt)
    return out


def _decompose(vals: list[int]) -> list[int]:
    top, i = [], 0
    while i < len(vals):
        acc, k, nxt = 0, i + 1, i + 1
        while k < len(vals) and acc < vals[i]:
            acc += vals[k]
            k += 1
            if abs(acc - vals[i]) <= EXACT:
                nxt = k
                break
        top.append(vals[i])
        i = nxt
    return top


def extract_deposits_numeric(rows, year, quarter, ref_vnd) -> list[dict]:
    if not ref_vnd or ref_vnd != ref_vnd:
        return []
    vals = [(_pick(r["nums"], col), r["f"]) for r, col in zip(rows, _cols(rows, year, quarter))]
    out = []
    for t, (v, _) in enumerate(vals):
        if v is None or v <= 0:
            continue
        sc = min(UNITS, key=lambda x: abs(v * x - ref_vnd))
        if abs(v * sc / ref_vnd - 1) > 0.05:  # dong tong phai gan tien gui CDKT; su chinh xac den tu phep tach DUNG
            continue
        for start in range(max(0, t - 16), t):
            seg = vals[start:t]
            if any(x is None for x, _ in seg) or not re.search(r"kh.?.?ng|kyhan|k.han", seg[0][1]):
                continue
            top = _decompose([x for x, _ in seg])
            if len(top) >= 2 and abs(sum(top) - v) <= EXACT:
                out.append({"demand": top[0], "other": sum(top[1:]), "_total": v})
                break
    return out


# --------------------------------------------------------------------------- mot bao cao
def _scale(total, ref):
    if not total or total <= 0 or not ref or ref != ref:
        return 1e6, np.nan
    # chi cac don vi co that: dong, nghin dong, trieu dong, va 10.000 dong (TCB in "trieu dong" co 2 chu so thap phan
    # 99.560.159,23 -> bo dau). Truoc 14/10 cho moi luy thua 10 -> bang khac nhan 10, 100, 10^7 lot vao (HDB 2012-Q4
    # CASA 0,06%, SHB 2016-Q3 CASA 63%, STB 2014-Q3, BAB 2017-Q1).
    best = min(UNITS, key=lambda s: abs(np.log(total * s / ref)))
    return best, total * best / ref - 1


def _prior(total: float, sc: float, refs: list) -> bool:
    return any(r == r and r and abs(total * sc / r - 1) < PRIOR_TOL for r in refs)


def process(t: str, y: int, q: int, ref: dict, url: str = "", path: str | None = None) -> dict:
    path = path or pdf_path(t, y, q)
    out = dict(ticker=t, period=f"{y}-Q{q}", pdf=os.path.basename(path))
    if not os.path.exists(path) and url:
        _download_one(url, path)
    if not os.path.exists(path):
        return {**out, "status": "khong_co_pdf"}
    if path.lower().endswith(".docx"):
        use_layer, src = True, "docx"
        best_l, best_d, lp, dp = _scan_docx(path, y, q, ref)
    else:
        use_layer = _layer_ok(path)
        src = "lop_chu" if use_layer else "ocr"
        best_l, best_d, lp, dp = _scan(path, y, q, ref, use_layer)
    if src != "docx" and use_layer and not (_loans_ok(best_l) and _dep_ok(best_d)):
        src = "ocr"
        l2, d2, lp2, dp2 = _scan(path, y, q, ref, False)
        if not _loans_ok(best_l) and l2 is not None and (best_l is None or _loan_rank(l2) < _loan_rank(best_l)):
            best_l, lp = l2, lp2
        if not _dep_ok(best_d) and d2 is not None and (best_d is None or _dep_rank(d2) < _dep_rank(best_d)):
            best_d, dp = d2, dp2
    out["locate"] = src
    if best_l:
        out.update(best_l)
        g = [best_l.get(f"g{k}") for k in range(1, 6)]
        if all(v is not None for v in g) and sum(g) > 0:
            out["npl_percent"] = round(sum(g[2:]) / sum(g) * 100, 4)
            out["loans_g2_percent"] = round(g[1] / sum(g) * 100, 4)
    if best_d:
        out.update(best_d)
        tot = sum(best_d.get(k) or 0 for k in ("dep_demand", "dep_term", "dep_savings", "dep_special", "dep_margin", "dep_other"))
        if tot and best_d.get("dep_demand") is not None:
            out["casa_percent"] = round(best_d["dep_demand"] / tot * 100, 4)
    out["loans_status"] = ("khong_thay_bang" if best_l is None else "ok" if best_l["loans_check"] in LOANS_EXACT
                           else "can_kiem_mat" if best_l["loans_check"] == "vndirect" else best_l["loans_check"])
    out["dep_status"] = ("khong_thay_bang" if best_d is None else "ok" if best_d["dep_check"] == "khop_cdkt"
                         else "ok_tong_bang" if best_d["dep_check"] == "tong_bang"
                         else "ky_truoc" if best_d["dep_check"] == "ky_truoc" else "lech_tong")
    out["candidates"] = json.dumps({"loans": [i + 1 for i in lp], "dep": [i + 1 for i in dp]})
    return out


def _loan_cand(b: dict, page: int, ref: dict, dpi: int = HIGH_DPI) -> dict:
    g = [b.get(k) for k in range(1, 6)]
    full = all(v is not None and v >= 0 for v in g)
    tot = sum(v for v in g if v)
    sc, rel = _scale(tot, ref.get("loans_gross_vnd"))
    tail = b.get("tail", [])
    # dong tong o vi tri j duoi nhom 5; cac dong truoc no hoac cong vao tong (repo MBS, "No cho xu ly" NAB 2015) hoac
    # nam ngoai tong (repo NAB 2013-Q4) -> lay cach hieu cong DUNG; khong co thi nhu cu (dong nhan ngan dau tien la tong)
    opts = [(tail[j][0], e) for j in range(len(tail)) for e in dict.fromkeys((sum(v for v, _ in tail[:j]), 0))]
    hit = next(((t_, e) for t_, e in opts if full and abs(tot + e - t_) <= EXACT), None)
    if hit:
        t, extra = hit
    else:
        j = next((j for j, (_, short) in enumerate(tail) if short), None)
        t, extra = (tail[j][0], sum(v for v, _ in tail[:j])) if j is not None else (None, sum(v for v, _ in tail))
    b = {**b, "total": t, "extra": extra}
    # tong 5 nhom (+ dong cong them) BANG DUNG du no gop tren CDKT: phep kiem doc lap ngang dong tong in trong bang
    # (dong tong OCR hong: NVB 2012-Q2 "1323112208", LPB 2015-Q3)
    cdkt = (full and rel == rel and ref.get("loans_gross_vnd")
            and min(abs(tot + e - ref["loans_gross_vnd"] / sc) for e in {extra, 0}) <= EXACT)
    # bang khac cung co du 5 nhom va dong tong khop dung (phan loai cam ket ngoai bang, du phong theo nhom): HDB 2014-Q4
    # lay nham bang tong 722 ty trong khi du no ~50 nghin ty -> them dieu kien hop ly
    # 258/263 o dat lech CDKT <= 5% (bang cong ty me: STB -2,7%, MBB -1%); BVB 2013-Q4/2016-Q4 lech +26/+36% (bang phan
    # loai toan bo cap tin dung, khong chi cho vay -> NPL khac dinh nghia panel); MSB 2015-Q2 -44% (bang khac, nhom 2-4
    # bang 0) -> nguong 10% (14/10/2026; truoc la 50%)
    if rel == rel:
        plausible = abs(rel) <= 0.10
    else:
        plausible = full and tot > 0 and sum(g[2:]) / tot <= 0.20 and g[0] / tot >= 0.60
    plausible = plausible and full and any(g[1:4])
    prior = full and rel == rel and abs(rel) > PRIOR_TOL and _prior(tot + b.get("extra", 0), sc, ref.get("prev_loans", []))
    if not full:
        check = "thieu_nhom"
    elif prior:
        check = "ky_truoc"
    elif t and abs(tot + b.get("extra", 0) - t) <= EXACT and plausible:
        check = "tong_bang"
    elif t and abs(tot + b.get("extra", 0) - t) <= EXACT and rel == rel and abs(rel) <= 0.5 and any(g[1:4]):
        check = "pham_vi_khac"  # cong dung nhung lech du no cho vay 10-50%: bang cua pham vi khac (cap tin dung)
    elif cdkt:
        check = "khop_cdkt"
    elif rel == rel and abs(rel) <= TOL_LOANS:
        check = "vndirect"
    else:
        check = "lech_tong"
    return dict(page_loans=page, **{f"g{k}": b.get(k) for k in range(1, 6)}, loans_extra=b.get("extra"), loans_table_total=t,
                loans_scale=sc, loans_rel=rel, loans_check=check, loans_dpi=dpi)


def _loan_rank(c):
    order = {"tong_bang": 0, "khop_cdkt": 0, "vndirect": 1, "pham_vi_khac": 2, "lech_tong": 2, "ky_truoc": 2, "thieu_nhom": 3}
    return (order[c["loans_check"]], abs(c["loans_rel"]) if c["loans_rel"] == c["loans_rel"] else 9)


def _dep_cand(b: dict, page: int, ref: dict, dpi: int = HIGH_DPI, method: str = "nhan") -> dict:
    b = dict(b)
    t = b.pop("_total", None)
    tot = sum(v for v in b.values() if v)
    sc, rel = _scale(tot, ref.get("deposits_vnd"))
    exact = rel == rel and abs(tot - ref["deposits_vnd"] / sc) <= EXACT
    # khong co so CDKT (BAB 2012-2015 VNDirect trong) thi chi con phep cong dung theo dong tong cua bang
    inner = (t is not None and abs(tot - t) <= EXACT and bool(b.get("special") or b.get("margin") or method == "so")
             and (rel != rel or abs(rel) <= 0.05) and 0 < (b.get("demand") or 0) < tot)
    prior = not exact and rel == rel and _prior(tot, sc, ref.get("prev_dep", []))
    check = "khop_cdkt" if exact else "ky_truoc" if prior else "tong_bang" if inner else "lech"
    return dict(dep_table_total=t, page_dep=page, dep_demand=b.get("demand"), dep_term=b.get("term"), dep_savings=b.get("savings"),
                dep_special=b.get("special"), dep_margin=b.get("margin"), dep_other=b.get("other"), dep_scale=sc, dep_rel=rel,
                dep_check=check, dep_dpi=dpi, dep_method=method)


def _dep_rank(c):
    return ({"khop_cdkt": 0, "tong_bang": 1}.get(c["dep_check"], 2), abs(c["dep_rel"]) if c["dep_rel"] == c["dep_rel"] else 9)


def _dep_ok(c) -> bool:
    return c is not None and c["dep_check"] in ("khop_cdkt", "tong_bang")


def _loans_ok(c) -> bool:
    return c is not None and c["loans_check"] in ("tong_bang", "khop_cdkt", "vndirect")


def _ok(c, key, tol) -> bool:
    return c is not None and c[key] == c[key] and abs(c[key]) <= tol


def _better(a, b, key) -> bool:
    err = lambda c: abs(c[key]) if c is not None and c[key] == c[key] else 9  # noqa: E731
    return err(a) < err(b)


def _scan(path, y, q, ref, use_layer):
    import pymupdf
    doc = pymupdf.open(path)
    n = doc.page_count
    order = list(range(min(4, n), n)) + list(range(min(4, n)))
    if n > 30:  # bao cao dai (soat xet, kiem toan 40-100 trang): 252 bang no da doc nam o 0,50 +- 0,07 do dai, bang
        # tien gui o 0,63 +- 0,05 -> quet tu hai diem do ra ngoai thay vi tu dau (14/10/2026)
        order = sorted(range(min(4, n), n), key=lambda i: min(abs(i / n - 0.50), abs(i / n - 0.63))) + list(range(min(4, n)))
    best_l = best_d = None
    lp, dp = [], []
    for i in order:
        text = fold(doc[i].get_text()) if use_layer else fold(" ".join(b[4] for b in ocr_page(path, i, LOW_DPI)))
        if not (best_l is not None and best_l["loans_check"] in LOANS_EXACT) and _score(text, LOAN_KEYS) >= 3:
            lp.append(i)
            blocks = extract_loans(_rows(ocr_page(path, i, HIGH_DPI)), y, q)
            cands = [_loan_cand(b, i + 1, ref) for b in blocks]
            if cands and not any(c["loans_check"] in LOANS_EXACT for c in cands):
                # thieu nhom hoac tong khong khop DUNG: OCR lai net hon roi cham lai
                cands += [_loan_cand(b, i + 1, ref, RETRY_DPI) for b in extract_loans(_rows(ocr_page(path, i, RETRY_DPI)), y, q)]
            # bang tran trang: nhom 5 / dong tong o dau trang sau, hoac nhom 1 o cuoi trang truoc (TCB 2013-Q1)
            for a, b_ in ((i, i + 1), (i - 1, i)):
                if any(c["loans_check"] in LOANS_EXACT for c in cands) or a < 0 or b_ >= n:
                    continue
                rows2 = _rows(ocr_page(path, a, HIGH_DPI)) + _rows(ocr_page(path, b_, HIGH_DPI))
                cands += [_loan_cand(b, i + 1, ref) for b in extract_loans(rows2, y, q)]
            for cand in cands:
                if best_l is None or _loan_rank(cand) < _loan_rank(best_l):
                    best_l = cand
        if not _dep_ok(best_d) and _score(text, DEP_KEYS) >= 3:
            dp.append(i)
            rows = _rows(ocr_page(path, i, HIGH_DPI))
            cands = [_dep_cand(b, i + 1, ref) for b in extract_deposits(rows, y, q)]
            if not any(_dep_ok(c) for c in cands):  # nhan bi OCR hong: tach theo so
                cands += [_dep_cand(b, i + 1, ref, method="so") for b in extract_deposits_numeric(rows, y, q, ref.get("deposits_vnd"))]
            if cands and not any(_dep_ok(c) for c in cands):
                rows = _rows(ocr_page(path, i, RETRY_DPI))
                cands += [_dep_cand(b, i + 1, ref, RETRY_DPI) for b in extract_deposits(rows, y, q)]
                cands += [_dep_cand(b, i + 1, ref, RETRY_DPI, "so") for b in extract_deposits_numeric(rows, y, q, ref.get("deposits_vnd"))]
            if not any(_dep_ok(c) for c in cands) and i + 1 < n:
                # bang tran sang trang sau (MBB 2013-Q1: von chuyen dung, ky quy, dong tong o dau trang 37)
                rows2 = _rows(ocr_page(path, i, HIGH_DPI)) + _rows(ocr_page(path, i + 1, HIGH_DPI))
                cands += [_dep_cand(b, i + 1, ref) for b in extract_deposits(rows2, y, q)]
            for cand in cands:
                if best_d is None or _dep_rank(cand) < _dep_rank(best_d):
                    best_d = cand
        if (best_l is not None and best_l["loans_check"] in LOANS_EXACT
                and _dep_ok(best_d)):
            break
    return best_l, best_d, lp, dp


def _docx_rows(path: str) -> list[list[dict]]:
    import zipfile
    from xml.etree import ElementTree as ET
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    root = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    tables = []
    for tbl in root.iter(f"{w}tbl"):
        rows = []
        for i, tr in enumerate(tbl.iter(f"{w}tr")):
            col, cells = 0, []
            for tc in tr.findall(f"{w}tc"):
                span = tc.find(f"{w}tcPr/{w}gridSpan")
                n = int(span.get(f"{w}val")) if span is not None else 1
                cells.append(("".join(t.text or "" for t in tc.iter(f"{w}t")).strip(), (col + n / 2) * 100))
                col += n
            nums, parts = [], []
            for txt, x in cells:
                v = _num(txt.replace(" ", ""))
                if v is not None and txt:
                    nums.append((v, x))
                elif txt:
                    parts.append(txt)
            label = " ".join(parts)
            rows.append(dict(y=float(i), label=label, f=fold(label), nums=nums,
                             dates=[(DATE.search(t).groups(), x) for t, x in cells if DATE.search(t)]))
        tables.append(rows)
    return tables


def _scan_docx(path, y, q, ref):
    best_l = best_d = None
    lp, dp = [], []
    for i, rows in enumerate(_docx_rows(path)):
        for c in [_loan_cand(b, i + 1, ref, 0) for b in extract_loans(rows, y, q)]:
            if best_l is None or _loan_rank(c) < _loan_rank(best_l):
                best_l, lp = c, [i]
        cands = [_dep_cand(b, i + 1, ref, 0) for b in extract_deposits(rows, y, q)]
        cands += [_dep_cand(b, i + 1, ref, 0, "so") for b in extract_deposits_numeric(rows, y, q, ref.get("deposits_vnd"))]
        for c in cands:
            if best_d is None or _dep_rank(c) < _dep_rank(best_d):
                best_d, dp = c, [i]
    return best_l, best_d, lp, dp


def _job(args):
    t, y, q, ref, url = args
    t0 = time.time()
    try:
        r = process(t, y, q, ref, url)
    except Exception as e:  # mot bao cao loi khong lam dung ca lo
        r = dict(ticker=t, period=f"{y}-Q{q}", status=f"loi: {type(e).__name__}: {e}"[:200])
    r["seconds"] = round(time.time() - t0)
    return r


def _save(df: pd.DataFrame, path: str):
    for attempt in range(10):
        try:
            df.to_csv(path + ".tmp", index=False, encoding="utf-8-sig")
            os.replace(path + ".tmp", path)
            return
        except OSError:
            time.sleep(2 * (attempt + 1))
    df.to_csv(path, index=False, encoding="utf-8-sig")


def _ref(vnd: pd.DataFrame, t: str, period: str) -> dict:
    if (t, period) not in vnd.index:
        return {}
    ref = vnd.loc[(t, period), ["loans_gross_vnd", "deposits_vnd"]].to_dict()
    y, q = int(period[:4]), int(period[-1])
    i = y * 4 + q - 1
    prev = {f"{j // 4}-Q{j % 4 + 1}" for j in (i - 1, i - 4)} | {f"{y - 1}-Q4"}
    rows = [vnd.loc[(t, p)] for p in sorted(prev) if (t, p) in vnd.index]
    ref["prev_loans"] = [float(r.loans_gross_vnd) for r in rows]
    ref["prev_dep"] = [float(r.deposits_vnd) for r in rows]
    return ref


def run(inv: pd.DataFrame, out_path: str = OUT, resume: bool = False) -> pd.DataFrame:
    vnd = pd.read_csv(VND, encoding="utf-8-sig").set_index(["ticker", "period"])
    res = []
    if resume and os.path.exists(out_path):
        old = pd.read_csv(out_path, encoding="utf-8-sig")
        if "status" in old:
            old = old[~old.status.fillna("").str.startswith("loi")]
        res = old.to_dict("records")
    done = {(r["ticker"], r["period"]) for r in res}
    jobs = []
    for r in inv.itertuples():
        key = (r.ticker, f"{r.year}-Q{r.quarter}")
        if key in done:
            continue
        ref = _ref(vnd, *key)
        jobs.append((r.ticker, int(r.year), int(r.quarter), ref, getattr(r, "url", "")))
    print(f"  {len(jobs)} bao cao can chay, {len(done)} da co", flush=True)
    # luot 2: bao cao loi (MemoryError / ONNXRuntimeError khi may thieu RAM, 14/10/2026: 22/380) chay lai voi it
    # tien trinh hon
    for attempt, workers in enumerate((WORKERS, 1)):
        if not jobs:
            break
        failed = []
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_job, j): j for j in jobs}
            for f in as_completed(futs):
                r = f.result()
                if str(r.get("status", "")).startswith("loi") and attempt == 0:
                    failed.append(futs[f])
                    print(f"  {r['ticker']} {r['period']}: {str(r['status'])[:60]} -> chay lai sau", flush=True)
                    continue
                res.append(r)
                _save(pd.DataFrame(res).sort_values(["ticker", "period"]), out_path)
                print(f"  [{len(res) - len(done)}/{len(jobs) + len(done) - len(done)}] {r['ticker']} {r['period']}: no "
                      f"{r.get('loans_status', r.get('status'))} (NPL {r.get('npl_percent')}), tien gui {r.get('dep_status', '')} "
                      f"(CASA {r.get('casa_percent')}), {r['seconds']}s", flush=True)
        jobs = failed
    return pd.DataFrame(res).sort_values(["ticker", "period"])


# --------------------------------------------------------------------------- danh muc Vietstock + ban thay the
def _classify(url: str) -> dict:
    u = urllib.parse.unquote(url)
    f = u.rsplit("/", 1)[1]
    folder = u.split("/BCTC/VN/")[1].split("/")[0] if "/BCTC/VN/" in u else "KHAC"
    m, m6, m9 = re.search(r"_Q([1-4])_(\d{4})", f), re.search(r"_6T_(\d{4})", f), re.search(r"_9T_(\d{4})", f)
    my = re.search(r"_(\d{4})", f)
    if m:
        kind, y, q = "quy", int(m.group(2)), int(m.group(1))
    elif m6:
        kind, y, q = "6T", int(m6.group(1)), 2
    elif m9:
        kind, y, q = "9T", int(m9.group(1)), 3
    elif my:
        kind, y, q = "nam", int(my.group(1)), 4
    else:
        kind, y, q = "?", None, None
    low = f.lower()
    scope = "Hopnhat" if "hopnhat" in low else "Congtyme" if "congtyme" in low else "Rieng" if "rieng" in low else ""
    return dict(file=f, folder=folder, ext=f.rsplit(".", 1)[-1].lower(), kind=kind, scope=scope,
                period=f"{y}-Q{q}" if y else "", tags=",".join(t for t in ("Soatxet", "Kiemtoan", "DieuChinh", "TMBCTC", "KQKD")
                                                            if t.lower() in low))


def catalog(banks=ALL_BANKS, years=range(2012, 2019)) -> pd.DataFrame:
    import http.cookiejar
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    op.addheaders = [("User-Agent", UA)]
    html = op.open(f"{VS}/BID/tai-tai-lieu.htm?doctype=1", timeout=90).read().decode("utf-8", "replace")
    tok = re.search(r"__CHART_AjaxAntiForgeryForm method=post><input name=__RequestVerificationToken type=hidden value=([^>\s]+)>",
                    html).group(1)
    rows = []
    for t in banks:
        for y in years:
            page = 1
            while True:
                body = urllib.parse.urlencode(dict(code=t, page=page, year=y, type=1, __RequestVerificationToken=tok)).encode()
                req = urllib.request.Request(f"{VS}/data/getdocument", data=body, headers={"X-Requested-With": "XMLHttpRequest"})
                txt = op.open(req, timeout=90).read().decode("utf-8", "replace").strip()
                j = json.loads(txt) if txt.startswith("[") else []
                if not j:
                    break
                for d in j:
                    url = d["Url"].replace("http://", "https://").split("?ver=")[0]
                    # LastUpdate "/Date(ms)/" = luc Vietstock dang file -> do tre cong bo (audit_npl_bctc)
                    rows.append(dict(ticker=t, url=url, name=d["FullName"].strip(), file_id=d["FileInfoID"],
                                     last_update=d.get("LastUpdate"), update_time=d.get("UpdateTime"), **_classify(url)))
                if page * 20 >= j[0]["TotalRow"]:
                    break
                page += 1
                time.sleep(0.2)
        print(f"  danh muc {t}: {sum(r['ticker'] == t for r in rows)} file", flush=True)
    cat = pd.DataFrame(rows)
    cat.to_csv(CATALOG, index=False, encoding="utf-8-sig")
    return cat


def _fetch_doc(url: str, stem: str) -> str | None:
    import pymupdf
    os.makedirs(ALT_DIR, exist_ok=True)
    ext = url.rsplit(".", 1)[-1].lower()
    out = f"{ALT_DIR}/{stem}.{'docx' if ext == 'docx' else 'pdf'}"
    if os.path.exists(out):
        return out
    raw = f"{ALT_DIR}/{stem}.{ext}"
    if not os.path.exists(raw):
        req = urllib.request.Request(urllib.parse.quote(url, safe=":/"), headers={"User-Agent": UA})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=300) as resp:
                    data = resp.read()
                break
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504) or attempt == 3:
                    raise
                time.sleep(20 * (attempt + 1))
        with open(raw + ".part", "wb") as fh:
            fh.write(data)
        os.replace(raw + ".part", raw)
    if ext in ("pdf", "docx"):
        if ext == "pdf" and not open(raw, "rb").read(5).startswith(b"%PDF"):
            return None
        return raw
    if ext not in ("rar", "zip"):
        return None
    tmp = f"{ALT_DIR}/{stem}_x"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    subprocess.run([SEVENZIP, "x", "-y", f"-o{tmp}", raw], capture_output=True, check=False)
    files = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(tmp) for f in fs)
    pdfs = [f for f in files if f.lower().endswith(".pdf")]
    docx = [f for f in files if f.lower().endswith(".docx")]
    if pdfs:
        doc = pymupdf.open()
        for f in pdfs:
            try:
                doc.insert_pdf(pymupdf.open(f))
            except Exception:  # file hong trong goi: bo qua, giu cac file con lai
                pass
        if doc.page_count:
            doc.save(out)
    elif docx:
        out = f"{ALT_DIR}/{stem}.docx"
        shutil.copy(docx[0], out)
    shutil.rmtree(tmp, ignore_errors=True)
    return out if os.path.exists(out) else None


SCOPE_RANK = {"Hopnhat": 0, "": 0, "Congtyme": 1, "Rieng": 1}
LOAN_FIELDS = ["page_loans", "g1", "g2", "g3", "g4", "g5", "loans_extra", "loans_table_total", "loans_scale", "loans_rel",
               "loans_check", "loans_dpi", "npl_percent", "loans_g2_percent", "loans_status"]
DEP_FIELDS = ["page_dep", "dep_demand", "dep_term", "dep_savings", "dep_special", "dep_margin", "dep_other", "dep_scale",
              "dep_rel", "dep_check", "dep_dpi", "dep_method", "casa_percent", "dep_status", "dep_table_total"]
L_RANK = {"ok": 0, "ok_lech_nguon": 1, "can_kiem_mat": 1, "pham_vi_khac": 2, "lech_tong": 2, "ky_truoc": 2, "thieu_nhom": 3,
          "khong_thay_bang": 4}
D_RANK = {"ok": 0, "ok_tong_bang": 0, "ok_lech_nguon": 1, "lech_tong": 2, "ky_truoc": 2, "khong_thay_bang": 4}


def _scope_of(url: str) -> str:
    low = str(url).lower()
    return "Hopnhat" if "hopnhat" in low else "Congtyme" if "congtyme" in low else "Rieng" if "rieng" in low else ""


def _merge(best: dict | None, new: dict, src: str, scope: str) -> dict:
    best = dict(best or {})
    for part, fields, rank in (("loans", LOAN_FIELDS, L_RANK), ("dep", DEP_FIELDS, D_RANK)):
        key = lambda r, s: (rank.get(r.get(f"{part}_status"), 5), SCOPE_RANK.get(s, 1))  # noqa: E731
        if key(new, scope) < key(best, best.get(f"scope_{part}", "")):
            for f in fields:
                best[f] = new.get(f)
            best[f"src_{part}"], best[f"scope_{part}"] = src, scope
    return best


def _done(r: dict) -> bool:
    return (r.get("loans_status") == "ok" and r.get("dep_status") in ("ok", "ok_tong_bang")
            and SCOPE_RANK.get(r.get("scope_loans"), 1) == 0 and SCOPE_RANK.get(r.get("scope_dep"), 1) == 0)


def _alt_job(args):
    t, y, q, ref, base, cands = args
    t0 = time.time()
    best, tried = dict(base), []
    for c in cands:
        if _done(best):
            break
        stem = f"{t}_{y}Q{q}_{c['file_id']}"
        try:
            path = _fetch_doc(c["url"], stem)
            if path is None:
                tried.append(f"{c['file']}: khong doc duoc")
                continue
            r = process(t, y, q, ref, path=path)
            best = _merge(best, r, os.path.basename(path), c["scope"])
            tried.append(f"{c['file']}: no {r.get('loans_status')}, tien gui {r.get('dep_status')}")
        except Exception as e:  # mot file hong khong lam dung o
            tried.append(f"{c['file']}: loi {type(e).__name__}: {e}"[:160])
    best.update(ticker=t, period=f"{y}-Q{q}", alt_tried=" | ".join(tried), seconds=round(time.time() - t0))
    best.pop("status", None)
    return best


def _candidates(cat: pd.DataFrame, t: str, period: str, used: set) -> list[dict]:
    q = int(period[-1])
    kind_rank = {1: {"quy": 0}, 2: {"6T": 0, "quy": 1}, 3: {"quy": 0, "9T": 1}, 4: {"quy": 0, "nam": 1}}[q]
    c = cat[(cat.ticker == t) & (cat.period == period) & cat.kind.isin(list(kind_rank))
            & ~cat.tags.fillna("").str.contains("KQKD") & cat.ext.isin(["pdf", "docx", "rar", "zip"])]
    c = c.loc[[urllib.parse.unquote(u) not in used for u in c.url]].copy()
    if c.empty:
        return []
    c["scope"] = c.scope.fillna("")
    c["_k"] = list(zip(c.scope.map(lambda s: SCOPE_RANK.get(s, 1)), c.kind.map(kind_rank),
                       c.ext.map({"pdf": 0, "docx": 0, "zip": 1, "rar": 1}), c.tags.fillna("").str.contains("DieuChinh").map(int) * -1))
    return c.sort_values("_k").drop(columns="_k").to_dict("records")


def run_alt(out_path: str = OUT_ALL, recheck_scope: tuple = ("MBB", "STB", "VCB", "SSB"), max_prio: int = 3):
    cat = pd.read_csv(CATALOG, encoding="utf-8-sig") if os.path.exists(CATALOG) else catalog()
    cat["period"] = cat.period.fillna("")
    vnd = pd.read_csv(VND, encoding="utf-8-sig").set_index(["ticker", "period"])
    res = pd.read_csv(out_path, encoding="utf-8-sig")
    inv = pd.read_csv(INVENTORY_ALL, encoding="utf-8-sig").fillna("")
    ex = pd.read_csv(EXTRA, encoding="utf-8-sig") if os.path.exists(EXTRA) else pd.DataFrame(columns=["ticker", "year", "quarter", "url"])
    src_url = {}
    for r in pd.concat([inv[inv.url != ""], ex.sort_values("priority", ascending=False)]).itertuples():
        src_url.setdefault((r.ticker, f"{int(r.year)}-Q{int(r.quarter)}"), r.url)
    used = {urllib.parse.unquote(u) for u in src_url.values()}
    # ket qua cu: ghi nguon + pham vi (hop nhat / cong ty me) cho tung phan neu chua co
    for part in ("loans", "dep"):
        if f"src_{part}" not in res:
            res[f"src_{part}"] = res.pdf
            res[f"scope_{part}"] = [_scope_of(src_url.get((t, p), "")) for t, p in zip(res.ticker, res.period)]
    res = res[~res.status.fillna("").str.startswith("loi")] if "status" in res else res
    have = {(t, p): r for (t, p), r in zip(zip(res.ticker, res.period), res.to_dict("records"))}
    jobs = []
    for t in ALL_BANKS:
        for y, q in ALL_QUARTERS:
            p = f"{y}-Q{q}"
            base = have.get((t, p), {})
            need = not (base.get("loans_status") == "ok" and base.get("dep_status") in ("ok", "ok_tong_bang"))
            if not need and t in recheck_scope and SCOPE_RANK.get(base.get("scope_loans"), 1) > 0:
                need = True
            if not need or (base.get("alt_tried") == base.get("alt_tried") and base.get("alt_tried")):
                continue  # da thu ban thay the o lan chay truoc
            cands = _candidates(cat, t, p, used)
            if not cands:
                continue
            ref = _ref(vnd, t, p)
            jobs.append((t, y, q, ref, base, cands))
    # uu tien: o chua co so nao -> khong thay bang -> chua dat -> chi doi cong ty me sang hop nhat
    def prio(j):
        base = j[4]
        if not base:
            return 0
        if base.get("loans_status") == "khong_thay_bang" or base.get("dep_status") == "khong_thay_bang":
            return 1
        if not (base.get("loans_status") == "ok" and base.get("dep_status") in ("ok", "ok_tong_bang")):
            return 2
        return 3
    jobs.sort(key=prio)
    print(f"  {len(jobs)} o co ban thay the ({sum(len(j[5]) for j in jobs)} file); theo uu tien:",
          {k: sum(prio(j) == k for j in jobs) for k in range(4)}, f"-> chay muc <= {max_prio}", flush=True)
    jobs = [j for j in jobs if prio(j) <= max_prio]
    done = 0
    with ProcessPoolExecutor(max_workers=WORKERS) as ex_:
        futs = [ex_.submit(_alt_job, j) for j in jobs]
        for f in as_completed(futs):
            r = f.result()
            have[(r["ticker"], r["period"])] = r
            done += 1
            _save(pd.DataFrame(list(have.values())).sort_values(["ticker", "period"]), out_path)
            print(f"  [{done}/{len(jobs)}] {r['ticker']} {r['period']}: no {r.get('loans_status')} ({r.get('scope_loans')}, "
                  f"NPL {r.get('npl_percent')}), tien gui {r.get('dep_status')} (CASA {r.get('casa_percent')}), {r['seconds']}s",
                  flush=True)
    out = pd.DataFrame(list(have.values())).sort_values(["ticker", "period"])
    _save(out, out_path)
    return out


def apply_manual(res: pd.DataFrame, path: str = MANUAL) -> pd.DataFrame:
    if not os.path.exists(path):
        return res
    man = pd.read_csv(path, encoding="utf-8-sig", dtype={"note": str})
    vnd = pd.read_csv(VND, encoding="utf-8-sig").set_index(["ticker", "period"])
    res = res.copy()
    for m in man.itertuples():
        key = (res.ticker == m.ticker) & (res.period == m.period)
        if not key.any():
            res = pd.concat([res, pd.DataFrame([dict(ticker=m.ticker, period=m.period)])], ignore_index=True)
            key = (res.ticker == m.ticker) & (res.period == m.period)
        val = lambda c: (0 if getattr(m, c) != getattr(m, c) else int(getattr(m, c)))  # noqa: E731
        ref = vnd.loc[(m.ticker, m.period)] if (m.ticker, m.period) in vnd.index else None
        if m.part == "no":
            g = [val(f"g{k}") for k in range(1, 6)]
            s, extra = sum(g), val("extra")
            cdkt = ref is not None and abs((s + extra) * m.unit - ref.loans_gross_vnd) <= EXACT * m.unit
            gap = val("lech_nguon")
            src_gap = (gap and m.total == m.total and ref is not None and abs(abs(s + extra - m.total) - gap) <= EXACT
                       and abs(m.total * m.unit - ref.loans_gross_vnd) <= EXACT * m.unit)
            if not (m.total == m.total and abs(s + extra - m.total) <= EXACT) and not cdkt and not src_gap:
                print(f"  doc tay {m.ticker} {m.period} no: tong {s + extra} != {m.total} -- bo qua", flush=True)
                continue
            upd = {**{f"g{k}": g[k - 1] * m.unit for k in range(1, 6)}, "loans_extra": extra * m.unit,
                   "loans_table_total": m.total * m.unit if m.total == m.total else np.nan, "loans_scale": 1.0,
                   "loans_rel": (s * m.unit / ref.loans_gross_vnd - 1) if ref is not None else np.nan,
                   "loans_check": "doc_tay", "loans_status": "ok_lech_nguon" if src_gap and not cdkt else "ok",
                   "page_loans": m.page,
                   "npl_percent": round(sum(g[2:]) / s * 100, 4), "loans_g2_percent": round(g[1] / s * 100, 4),
                   "src_loans": m.file, "scope_loans": _scope_of(m.file)}
        else:
            parts = {c: val(c) for c in ("demand", "term", "savings", "special", "margin", "other")}
            s = sum(parts.values())
            cdkt = ref is not None and abs(s * m.unit - ref.deposits_vnd) <= EXACT * m.unit
            gap = val("lech_nguon")
            src_gap = (gap and m.total == m.total and ref is not None and abs(abs(s - m.total) - gap) <= EXACT
                       and abs(m.total * m.unit - ref.deposits_vnd) <= EXACT * m.unit)
            if not (m.total == m.total and abs(s - m.total) <= EXACT) and not cdkt and not src_gap:
                print(f"  doc tay {m.ticker} {m.period} tien gui: tong {s} != {m.total} -- bo qua", flush=True)
                continue
            upd = {**{f"dep_{c}": v * m.unit for c, v in parts.items()}, "dep_scale": 1.0,
                   "dep_table_total": m.total * m.unit if m.total == m.total else np.nan,
                   "dep_rel": (s * m.unit / ref.deposits_vnd - 1) if ref is not None else np.nan,
                   "dep_check": "doc_tay", "dep_status": "ok_lech_nguon" if src_gap and not cdkt else "ok",
                   "dep_method": "doc_tay", "page_dep": m.page,
                   "casa_percent": round(parts["demand"] / s * 100, 4), "src_dep": m.file, "scope_dep": _scope_of(m.file)}
        for c, v in upd.items():
            if c not in res:
                res[c] = np.nan
            res[c] = res[c].astype(object)
            res.loc[key, c] = v
    return res.sort_values(["ticker", "period"])


def _src_path(r) -> str:
    for d in (ALT_DIR, PDF_DIR):
        p = f"{d}/{r}"
        if os.path.exists(p):
            return p
    return ""


def render(t, y, q, dpi=110):
    import pymupdf
    o = pd.read_csv(OUT_ALL, encoding="utf-8-sig")
    r = o[(o.ticker == t) & (o.period == f"{y}-Q{q}")].iloc[0]
    for part, col in (("loans", "page_loans"), ("dep", "page_dep")):
        src = r.get(f"src_{part}", r.get("pdf"))
        path = _src_path(src) if src == src else ""
        if r.get(col) == r.get(col) and path.endswith(".pdf"):
            p = int(r[col])
            f = f"{CACHE}/{t}_{y}Q{q}_{part}_trang{p}.png"
            pymupdf.open(path)[p - 1].get_pixmap(dpi=dpi).save(f)
            print(f)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--all", action="store_true", help="22 NH x 2012-Q1..2017-Q4, chay tiep neu bi ngat")
    ap.add_argument("--recheck", action="store_true", help="cham lai cac o chua dat cua --all bang code moi (dung cache OCR)")
    ap.add_argument("--render", nargs=3)
    ap.add_argument("--catalog", action="store_true", help="tai lai danh muc tai lieu Vietstock 22 NH 2012-2018")
    ap.add_argument("--alt", action="store_true", help="o chua dat / chua co PDF: thu ban thay the trong danh muc")
    ap.add_argument("--fresh", action="store_true", help="voi --all: cham lai MOI o bang code hien tai (dung cache OCR)")
    ap.add_argument("--manual", action="store_true", help="ghi so doc bang mat (ocr_doc_tay.csv) vao ket qua")
    ap.add_argument("--alt-prio", type=int, default=3, help="--alt chi chay o co muc uu tien <= N (0 chua co so, 1 khong "
                    "thay bang, 2 chua dat, 3 doi cong ty me sang hop nhat)")
    a = ap.parse_args()
    if a.render:
        render(a.render[0], int(a.render[1]), int(a.render[2]))
        return
    if a.catalog:
        cat = catalog()
        print(f"{len(cat)} file -> {CATALOG}")
        return
    if a.manual and not (a.all or a.alt):
        res = apply_manual(pd.read_csv(OUT_ALL, encoding="utf-8-sig"))
        _save(res, OUT_ALL)
        print("Doc tay:", res.loans_status.value_counts().to_dict(), "|", res.dep_status.value_counts().to_dict())
        return
    if a.alt and not a.all:
        res = apply_manual(run_alt(max_prio=a.alt_prio))
        _save(res, OUT_ALL)
        print("\nTrang thai:", res.loans_status.value_counts().to_dict(), "|", res.dep_status.value_counts().to_dict(), "->", OUT_ALL)
        return
    if a.recheck:
        res = pd.read_csv(OUT_ALL, encoding="utf-8-sig")
        bad = ~(res.loans_status.isin(["ok"]) & res.dep_status.isin(["ok", "ok_tong_bang"]))
        inv = pd.read_csv(INVENTORY_ALL, encoding="utf-8-sig").fillna("")
        if os.path.exists(EXTRA):
            inv = pd.concat([inv[inv.url != ""], pd.read_csv(EXTRA, encoding="utf-8-sig").sort_values("priority")[
                ["ticker", "year", "quarter", "url"]]]).drop_duplicates(["ticker", "year", "quarter"])
        inv["period"] = inv.year.astype(int).astype(str) + "-Q" + inv.quarter.astype(int).astype(str)
        redo = inv.merge(res.loc[bad, ["ticker", "period"]], on=["ticker", "period"])
        print(f"Cham lai {len(redo)} bao cao chua dat", flush=True)
        keep = res[~bad]
        keep.to_csv(OUT_ALL, index=False, encoding="utf-8-sig")
        res = run(redo, OUT_ALL, resume=True)
        print("\nTrang thai:", res.loans_status.value_counts().to_dict(), "|", res.dep_status.value_counts().to_dict(), "->", OUT_ALL)
        return
    if a.all:
        print("Kiem ke 22 NH x 24 quy ...", flush=True)
        inv = inventory(ALL_BANKS, ALL_QUARTERS, INVENTORY_ALL)
        if os.path.exists(EXTRA):  # lap quy con thieu bang nguon bo sung (uu tien quy that, roi BCTC nam cho Q4)
            ex = pd.read_csv(EXTRA, encoding="utf-8-sig").sort_values("priority")
            have = {(r.ticker, int(r.year), int(r.quarter)) for r in inv[inv.url != ""].itertuples()}
            add = ex[[(t, int(y), int(q)) not in have for t, y, q in zip(ex.ticker, ex.year, ex.quarter)]]
            add = add.drop_duplicates(["ticker", "year", "quarter"])
            print(f"Nguon bo sung: them {len(add)} bao cao", flush=True)
            inv = pd.concat([inv[inv.url != ""], add[["ticker", "year", "quarter", "url"]]], ignore_index=True)
        inv = inv[inv.url != ""]
        print(f"Kiem ke: {len(inv)}/{len(ALL_BANKS) * len(ALL_QUARTERS)} bao cao co PDF", flush=True)
        bak = OUT_ALL.replace(".csv", "_truoc_cham_lai.csv")
        if a.fresh and os.path.exists(OUT_ALL) and not os.path.exists(bak):  # giu ban cua lan chay goc, khong ghi de
            os.replace(OUT_ALL, bak)
        res = run(inv, OUT_ALL, resume=not a.fresh)
        print("\nTrang thai:", res.loans_status.value_counts().to_dict(), "|", res.dep_status.value_counts().to_dict(), "->", OUT_ALL)
        if a.alt:
            res = run_alt(max_prio=a.alt_prio)
            print("\nSau ban thay the:", res.loans_status.value_counts().to_dict(), "|", res.dep_status.value_counts().to_dict())
        res = apply_manual(res)
        _save(res, OUT_ALL)
        print("Sau doc tay:", res.loans_status.value_counts().to_dict(), "|", res.dep_status.value_counts().to_dict())
        return
    if a.pilot:
        os.makedirs(PDF_DIR, exist_ok=True)
        if os.path.exists(INVENTORY):
            inv = pd.read_csv(INVENTORY, encoding="utf-8-sig").fillna("")
        else:
            inv = inventory(PILOT_BANKS, PILOT_QUARTERS)
            inv.to_csv(INVENTORY, index=False, encoding="utf-8-sig")
        print(f"Kiem ke: {int((inv.url != '').sum())}/{len(inv)} bao cao co PDF", flush=True)
        res = run(inv[inv.url != ""])
        res.to_csv(OUT, index=False, encoding="utf-8-sig")
        pan = pd.read_csv(PANEL, encoding="utf-8-sig")[["ticker", "period", "npl_percent", "casa_percent", "loans_g2_percent"]]
        chk = res.merge(pan, on=["ticker", "period"], suffixes=("", "_panel"))
        if len(chk):
            print("\nDoi chieu voi panel (2018+):")
            print(chk[["ticker", "period", "npl_percent", "npl_percent_panel", "casa_percent", "casa_percent_panel"]].to_string(index=False))
        print("\nTrang thai:", res.loans_status.value_counts().to_dict(), "|", res.dep_status.value_counts().to_dict(), "->", OUT)


if __name__ == "__main__":
    main()
