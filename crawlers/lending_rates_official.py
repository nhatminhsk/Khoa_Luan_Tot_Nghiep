"""Lai cho vay binh quan do chinh tung ngan hang cong bo tren website cua minh.

Can cu: Chi thi 01/CT-NHNN (15/01/2024) yeu cau moi TCTD dang tren website: lai cho vay binh quan,
chenh lech lai cho vay binh quan - huy dong binh quan, lai suat co so (neu co). Nguon nay de thay
bang tong hop cua VietnamNet (crawlers/lending_rates_bank.py), vi bang do moi thang chi co 1-19 NH.

Moi ngan hang cong bo mot kieu khac nhau, nen file giu nguyen chi tieu ngan hang ghi, KHONG quy doi:
  segment: all | individual | business | short_term | medium_long_term | consumer_short_term
           | individual_short_term | individual_medium_long_term
  measure: avg_lending (lai cho vay binh quan) | spread (tru lai huy dong binh quan)
           | spread_net (spread sau khi tru chi phi huy dong, su dung von)
  basis:   new_loans (khoan vay moi giai ngan trong ky) | all_loans | unknown
So sanh giua ngan hang chi hop le khi cung segment + measure (+ basis).

period la ky ngan hang ghi (cung cach VietnamNet ghi thang). BIDV ghi "ky thang 05/2026 (du lieu tinh
den 30/4/2026)" -> period 2026-05, as_of 30/4/2026. MB khong ghi ky -> period = thang thu thap, note ghi ro.
HDBank cong bo theo "ap dung tu ngay" -> period = thang ap dung.

Ngan hang chua doc duoc nam trong GAPS (kem ly do); voi cac ngan hang nay van dung VietnamNet.

Trang dung bang JavaScript (VIB, SHB, MB, HDBank, PGBank, BVBank, NCB) duoc dung bang Edge headless
(--dump-dom), khong can cai Playwright. OCB chi mo duoc khi bam menu nen dieu khien Edge qua DevTools
(_render_click, dung thu vien websockets co san). Duong dan Edge doc tu bien EDGE_PATH neu co.

Nguon chi co anh (Nam A, Sacombank, VCB 2024-01/2026, BVBank vai thang): so nhap tay vao
lending_rates_official_manual.csv (cung cot, source_kind = image_manual, source_url = anh goc) va duoc
gop vao file chinh moi lan chay. Crawler in "la ANH, chua nhap tay" khi ngan hang dang anh moi.

Chay:
  python -m crawlers.lending_rates_official             # thang moi nhat, bo qua NH da co so thang truoc
  python -m crawlers.lending_rates_official --force     # doc lai tat ca
  python -m crawlers.lending_rates_official --backfill  # them lich su: trang theo nam, mau ten file, Wayback
"""
from __future__ import annotations

import io
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests

OUT = Path("data/interest_rates")
MASTER = OUT / "lending_rates_official.csv"

COLUMNS = ["ticker", "period", "segment", "measure", "value_percent", "basis", "as_of", "published_date",
           "source_kind", "source_url", "note", "retrieved_at_utc"]
KEY = ["ticker", "period", "segment", "measure"]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "vi,en;q=0.9"}

EDGE_CANDIDATES = [os.environ.get("EDGE_PATH"),
                   r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                   r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]

# Lai cho vay binh quan / chenh lech ngoai khoang nay la doc sai (vd nam, so trang).
RANGE = {"avg_lending": (3.0, 25.0), "spread": (0.3, 10.0), "spread_net": (0.0, 8.0)}

NUM = r"(\d{1,2}(?:[.,]\d{1,3})?)"
# So lai suat luon co phan thap phan; bat buoc co de khong lay nham "5" trong "ky thang 5/2026"
# hay "05.202" trong "05.2026".
DEC = r"(?<![\d.,])(\d{1,2}[.,] ?\d{1,3})(?![\d])"  # BIDV chen khoang trang: "6, 61"

# Ngan hang chua tu dong doc duoc o phien ban nay, va ly do (kiem 08/10/2026).
GAPS = {
    # Ca 4 ngan hang deu co trong bang VietnamNet (nen co cong bo o dau do), nhung tim tren web ngan hang,
    # tim kiem theo ten mien va chi muc Wayback deu khong ra trang. Van dung VietnamNet cho 4 ngan hang nay.
    "CTG": "chua tim thay trang cong bo tren vietinbank.vn (chi co lai tham chieu); dung VietnamNet",
    "VPB": "chua tim thay trang cong bo (chi thay bieu lai tham chieu); dung VietnamNet",
    "LPB": "chua tim thay trang cong bo (chi thay lai co so); dung VietnamNet",
    "BAB": "chua tim thay trang cong bo tren baca-bank.vn; dung VietnamNet",
}


# ---------------------------------------------------------------------------
# tai trang

def _get(url: str, timeout: int = 40) -> requests.Response:
    try:
        return requests.get(url, headers=HEADERS, timeout=timeout)
    except requests.exceptions.SSLError:
        # Vai CDN ngan hang thieu chung chi trung gian; chi doc so cong khai nen bo kiem tra o day.
        import urllib3
        urllib3.disable_warnings()
        return requests.get(url, headers=HEADERS, timeout=timeout, verify=False)


def _render(url: str, budget_ms: int = 12000) -> str:
    exe = next((p for p in EDGE_CANDIDATES if p and Path(p).exists()), None)
    if exe is None:
        raise RuntimeError("khong tim thay Microsoft Edge de dung trang JavaScript (dat EDGE_PATH)")
    profile = Path(tempfile.gettempdir()) / "kltn_edge_headless"
    cmd = [exe, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
           f"--user-data-dir={profile}", f"--virtual-time-budget={budget_ms}", f"--user-agent={UA}",
           "--dump-dom", url]
    out = subprocess.run(cmd, capture_output=True, timeout=180)
    return out.stdout.decode("utf-8", "ignore")


def _render_click(url: str, click_js: str, wait_s: float = 6.0) -> str:
    """Mo url bang Edge headless qua DevTools, chay click_js (bam menu), cho, tra ve HTML.

    Dung cho trang ung dung mot trang ma duong dan chi chay khi vao bang menu (OCB: mo thang
    /vi/cong-cu/lai-suat tra 404, va API cua ho can ma xac thuc do chinh trang tao)."""
    import asyncio
    import json
    import socket
    import urllib.request

    import websockets

    exe = next((p for p in EDGE_CANDIDATES if p and Path(p).exists()), None)
    if exe is None:
        raise RuntimeError("khong tim thay Microsoft Edge (dat EDGE_PATH)")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    profile = Path(tempfile.gettempdir()) / "kltn_edge_cdp"
    proc = subprocess.Popen([exe, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                             f"--remote-debugging-port={port}", f"--user-data-dir={profile}", f"--user-agent={UA}",
                             "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        tabs = None
        for _ in range(100):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2))
                break
            except OSError:
                time.sleep(0.2)
        ws_url = next(t["webSocketDebuggerUrl"] for t in tabs or [] if t.get("type") == "page")

        async def go() -> str:
            async with websockets.connect(ws_url, max_size=100_000_000) as ws:
                seq = 0

                async def call(method: str, params: dict | None = None) -> dict:
                    nonlocal seq
                    seq += 1
                    await ws.send(json.dumps({"id": seq, "method": method, "params": params or {}}))
                    while True:
                        msg = json.loads(await ws.recv())
                        if msg.get("id") == seq:
                            return msg.get("result", {})

                await call("Page.enable")
                await call("Page.navigate", {"url": url})
                await asyncio.sleep(wait_s)
                await call("Runtime.evaluate", {"expression": click_js})
                await asyncio.sleep(wait_s)
                r = await call("Runtime.evaluate", {"expression": "document.documentElement.outerHTML",
                                                    "returnByValue": True})
                return r.get("result", {}).get("value", "")

        return asyncio.run(go())
    finally:
        proc.terminate()


def _plain(raw: str) -> str:
    t = unescape(re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S))
    t = re.sub(r"<(td|th)[^>]*>", " | ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)


def _pdf_text(content: bytes) -> str:
    import pdfplumber
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        return re.sub(r"\s+", " ", " ".join((p.extract_text() or "") for p in pdf.pages))


def _links(raw: str, base: str) -> list[tuple[str, str]]:
    out = []
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', raw, re.S):
        text = re.sub(r"<[^>]+>|\s+", " ", unescape(m.group(2))).strip()
        out.append((text, urljoin(base, unescape(m.group(1)))))
    return out


def _wayback(url_key: str, since: str = "20240301") -> list[tuple[str, str]]:
    """(url ban luu nguyen goc, ngay luu) cho moi thang co ban chup cua url_key."""
    cdx = ("http://web.archive.org/cdx/search/cdx?url=" + url_key +
           f"&output=json&fl=timestamp,original&filter=statuscode:200&collapse=timestamp:6&from={since}")
    try:
        rows = requests.get(cdx, timeout=150).json()[1:]
    except Exception as e:  # Wayback hay qua tai; thieu lich su khong lam hong ky moi nhat
        print(f"    wayback {url_key}: {e}")
        return []
    return [(f"https://web.archive.org/web/{ts}id_/{orig}", ts[:8]) for ts, orig in rows]


# ---------------------------------------------------------------------------
# doc so

def _num(s: str) -> float:
    return float(s.replace(" ", "").replace(",", "."))


def _after(text: str, label: str, window: int = 40) -> float | None:
    """So dau tien dung ngay sau nhan. Duyet moi lan nhan xuat hien: nhan hay lap lai trong tieu de muc
    ("Lai suat cho vay binh quan va chenh lech ...") ma ngay sau tieu de khong co so."""
    for m in re.finditer(label, text, re.I):
        n = re.search(DEC, text[m.end(): m.end() + window])
        if n:
            return _num(n.group(1))
    return None


def _period(text: str) -> str | None:
    for pat in (r"th[áa]ng\s*(\d{1,2})\s*n[ăa]m\s*(20\d{2})",
                r"th[áa]ng\s*(\d{1,2})\s*[/.\-]\s*(20\d{2})",
                r"month of\s*(\d{1,2})\s*-\s*(20\d{2})"):
        m = re.search(pat, text, re.I)
        if m and 1 <= int(m.group(1)) <= 12:
            return f"{m.group(2)}-{int(m.group(1)):02d}"
    return None


def _ym(d: str) -> str | None:
    """'30/4/2026' -> '2026-04'."""
    m = re.match(r"(\d{1,2})/(\d{1,2})/(20\d{2})", d or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}" if m else None


def _months_back(n: int, today: date | None = None) -> list[tuple[int, int]]:
    d = today or date.today()
    y, m = d.year, d.month
    out = []
    for _ in range(n):
        out.append((y, m))
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return out


def _rows(tk: str, period: str | None, values: dict, url: str, kind: str, basis: str = "unknown",
          as_of: str = "", published: str = "", note: str = "") -> list[dict]:
    if not period:
        return []
    now = datetime.now(timezone.utc).isoformat()
    out = []
    for (segment, measure), v in values.items():
        if v is None:
            continue
        lo, hi = RANGE[measure]
        if not lo <= v <= hi:
            print(f"    {tk} {period} {segment}/{measure} = {v} ngoai khoang {lo}-{hi}, bo")
            continue
        out.append(dict(ticker=tk, period=period, segment=segment, measure=measure, value_percent=v,
                        basis=basis, as_of=as_of, published_date=published, source_kind=kind,
                        source_url=url, note=note, retrieved_at_utc=now))
    return out


# ---------------------------------------------------------------------------
# tung ngan hang. Moi ham tra list[dict]; backfill=True thi them lich su neu nguon co.

def _acb(backfill: bool) -> list[dict]:
    pages = [("https://acb.com.vn/lai-suat-cho-vay", "")]
    if backfill:
        pages += _wayback("acb.com.vn/lai-suat-cho-vay")
    out = []
    for url, snap in pages:
        r = _get(url, timeout=60)
        if r.status_code != 200:
            continue
        t = _plain(r.text)
        m = re.search(r"K[ỳy]\s*th[áa]ng\s*(\d{1,2})/(20\d{2})", t, re.I)
        period = f"{m.group(2)}-{int(m.group(1)):02d}" if m else None
        out += _rows("ACB", period, {
            ("all", "avg_lending"): _after(t, r"Lãi suất cho vay bình quân\s*\(\*\)"),
            ("all", "spread"): _after(t, r"Chênh lệch lãi suất tiền gửi và cho vay bình quân\s*\(\*\*\)"),
        }, url, "html" if not snap else "wayback", basis="new_loans")
    return out


BID_POST = ("https://bidv.com.vn/bidv/tin-tuc/congbothongtinlaisuat_vi/congbolaisuatchovay_vi/"
            "bidv-cong-bo-lai-suat-cho-vay-binh-quan-ky-thang-{m:02d}-{y}")


def _bid(backfill: bool) -> list[dict]:
    out = []
    for y, m in _months_back(30 if backfill else 3):
        url = BID_POST.format(m=m, y=y)
        r = _get(url)
        if r.status_code != 200 or "bình quân" not in r.text:
            continue
        t = re.sub(r"\s*/\s*", "/", _plain(r.text))  # "ky thang 04 /2026", "31 / 03 /2026"
        if not re.search(rf"k[ỳy]\s*th[áa]ng\s*0?{m}/{y}", t, re.I):
            continue
        a = re.search(r"tính đến ngày\s*(\d{1,2}/\d{1,2}/20\d{2})", t)
        pub = re.search(r"Đăng tải ngày\s*(\d{1,2}/\d{1,2}/20\d{2})", t)
        # period = ky BIDV ghi. Tu ky 05/2026 BIDV ghi them "du lieu tinh den cuoi thang truoc"; cac ky truoc
        # khong ghi. Doi period theo ngay so lieu se lam ky 04 va ky 05/2026 trung khoa (da gap 08/10/2026).
        out += _rows("BID", f"{y}-{m:02d}", {
            ("all", "avg_lending"): _after(t, r"\|\s*Lãi suất cho vay bình quân"),
            ("all", "spread"): _after(t, r"Chênh lệch lãi suất \(cho vay bình quân[^)]*\)"),
            ("all", "spread_net"): _after(t, r"Chênh lệch lãi suất sau khi trừ[^|]*?sử dụng vốn"),
        }, url, "html", as_of=a.group(1) if a else "", published=pub.group(1) if pub else "",
            note="period = ky BIDV cong bo; so lieu tinh den cuoi thang truoc (BIDV ghi ro tu ky 05/2026)")
    return out


def _eib(backfill: bool) -> list[dict]:
    years = range(2024, date.today().year + 1) if backfill else [date.today().year]
    out = []
    for y in years:
        for url in (f"https://eximbank.com.vn/tin-tuc/lai-suat-binh-quan-thang-trong-nam-{y}",
                    f"https://eximbank.com.vn/tin-tuc/lai-suat-cho-vay-binh-quan-thang-trong-nam-{y}",
                    f"https://eximbank.com.vn/en/news/lai-suat-cho-vay-binh-quan-thang-trong-nam-{y}"):
            r = _get(url, timeout=60)
            if r.status_code == 200 and "BÌNH QUÂN THÁNG" in r.text.upper():
                break
        else:
            continue
        t = _plain(r.text)
        heads = list(re.finditer(r"LÃI SUẤT CHO VAY BÌNH QUÂN THÁNG\s*(\d{1,2})\s*NĂM\s*(20\d{2})", t, re.I))
        for i, h in enumerate(heads):
            block = t[h.end(): heads[i + 1].start() if i + 1 < len(heads) else h.end() + 1500]
            a = re.search(r"kỳ báo cáo:\s*(\d{1,2}/\d{1,2}/20\d{2})", block)
            out += _rows("EIB", f"{h.group(2)}-{int(h.group(1)):02d}", {
                ("all", "avg_lending"): _after(block, r"\|\s*Lãi suất cho vay bình quân\s*\|"),
                ("individual", "avg_lending"): _after(block, r"khách hàng cá nhân"),
                ("business", "avg_lending"): _after(block, r"khách hàng doanh nghiệp"),
                ("all", "spread"): _after(block, r"Chênh lệch lãi suất tiền gửi và cho vay bình quân"),
            }, url, "html", basis="all_loans", as_of=a.group(1) if a else "")
    return out


TCB_PDF = ("https://techcombank.com/content/dam/techcombank/public-site/documents/"
           "lai-suat-cho-vay-binh-quan-{seg}-techcombank-thang-{m:02d}-{y}.pdf")


def _tcb(backfill: bool) -> list[dict]:
    out = []
    for y, m in _months_back(30 if backfill else 4):
        for seg, segment in (("khcn", "individual"), ("khdn", "business")):
            url = TCB_PDF.format(seg=seg, m=m, y=y)
            r = _get(url)
            if r.status_code != 200 or not r.content.startswith(b"%PDF"):
                continue
            t = _pdf_text(r.content)
            # PDF tach tung chu so: "0 6 - 2 0 2 6"
            t = re.sub(r"(?<=\d) (?=\d)", "", t)
            out += _rows("TCB", _period(t) or f"{y}-{m:02d}", {
                (segment, "avg_lending"): _after(t, r"Average Lending Rate \(\*\)"),
                # so chenh lech nam giua "Difference between" va "Average Lending & Average Deposit Rate"
                (segment, "spread"): _after(t, r"Difference between", 40),
            }, url, "pdf", basis="new_loans")
    return out


def _hdb(backfill: bool) -> list[dict]:
    page = "https://hdbank.com.vn/vi/personal/cong-cu/interest-rate"
    raw = _render(page)
    pdfs = [u for text, u in _links(raw, page) if "BÌNH QUÂN" in text.upper() and u.lower().endswith(".pdf")]
    out = []
    for url in pdfs[:1]:
        r = _get(url)
        if not r.content.startswith(b"%PDF"):
            continue
        t = _pdf_text(r.content)
        a = re.search(r"Áp dụng từ ngày\s*(\d{1,2}/\d{1,2}/20\d{2})", t)
        m = re.search(r"Ngắn hạn\s*Trung dài hạn\s*" + NUM + r"\s*%\s*" + NUM + r"\s*%", t)
        out += _rows("HDB", _ym(a.group(1)) if a else None, {
            ("short_term", "avg_lending"): _num(m.group(1)) if m else None,
            ("medium_long_term", "avg_lending"): _num(m.group(2)) if m else None,
            ("all", "spread"): _after(t, r"Chênh lệch lãi suất tiền gửi và cho vay bình quân là"),
        }, url, "pdf", as_of=a.group(1) if a else "", note="HDBank cong bo theo 'ap dung tu ngay', khong theo thang")
    return out


def _vib(backfill: bool) -> list[dict]:
    url = "https://www.vib.com.vn/vn/lai-suat-vay-binh-quan/"
    t = _plain(_render(url))
    m = re.search(r"Thời gian:\s*Tháng\s*(\d{1,2})/(20\d{2})", t)
    t = t[m.end():] if m else ""  # chu "Ca nhan", "Doanh nghiep" con nam o menu phia tren
    return _rows("VIB", f"{m.group(2)}-{int(m.group(1)):02d}" if m else None, {
        ("individual", "avg_lending"): _after(t, r"\bCá nhân\b"),
        ("business", "avg_lending"): _after(t, r"\bDoanh nghiệp\b"),
        ("all", "spread"): _after(t, r"Chênh lệch lãi suất tiền gửi và cho vay bình quân"),
    }, url, "html_render")


def _shb(backfill: bool) -> list[dict]:
    url = "https://www.shb.com.vn/cong-bo-lai-suat-binh-quan/"
    t = _plain(_render(url))
    i = t.find("công bố lãi suất bình quân phát sinh")
    t = t[i:] if i >= 0 else ""
    return _rows("SHB", _period(re.sub(r"(\d{1,2})\.(20\d{2})", r"\1/\2", t[:200])), {
        ("consumer_short_term", "avg_lending"): _after(t, r"LSBQ cho vay ngắn hạn[^:]*:"),
        ("all", "spread"): _after(t, r"Chênh lệch lãi suất \(cho vay bình quân[^)]*\):"),
    }, url, "html_render", note="SHB chi cong bo LSBQ cho vay ngan han phuc vu doi song, tieu dung")


def _mbb(backfill: bool) -> list[dict]:
    url = "https://www.mbbank.com.vn/Fee"
    t = _plain(_render(url, budget_ms=15000))
    # MB khong ghi ky cua so binh quan; so nam o muc II cua bieu lai KHCN "ap dung tu ngay dd/mm/yyyy"
    # -> period = thang ap dung (cung quy uoc HDBank). Khong thay ngay thi moi lay thang thu thap.
    a = re.search(r"áp dụng (?:kể )?từ (?:ngày )?(\d{1,2}/\d{1,2}/20\d{2})", t)
    today = date.today()
    period = _ym(a.group(1)) if a else f"{today.year}-{today.month:02d}"
    note = ("MB khong ghi ky so lieu; period = thang 'ap dung tu ngay' cua bieu lai KHCN chua so nay" if a
            else "MB khong ghi ky so lieu; period = thang thu thap")
    return _rows("MBB", period, {
        ("individual", "avg_lending"): _after(t, r"Lãi suất cho vay bình quân khách hàng cá nhân"),
        ("business", "avg_lending"): _after(t, r"Lãi suất cho vay bình quân khách hàng doanh nghiệp"),
        # lan dau xuat hien la muc KHCN; muc SME phia duoi nhac lai cung chi tieu
        ("all", "spread"): _after(t, r"Chênh lệch lãi suất cho vay và huy động của Ngân hàng"),
    }, url, "html_render", as_of=a.group(1) if a else "", note=note)


def _pgb(backfill: bool) -> list[dict]:
    page = "https://www.pgbank.com.vn/tin-tuc?page=1&q=lai-suat-cho-vay-binh-quan-12"
    raw = _render(page)
    pdfs = list(dict.fromkeys(u for text, u in _links(raw, page)
                              if "bình quân" in text.lower() and u.lower().endswith(".pdf")))
    out = []
    for url in pdfs[: (24 if backfill else 2)]:
        r = _get(url)
        if not r.content.startswith(b"%PDF"):
            continue
        t = _pdf_text(r.content)
        out += _rows("PGB", _period(t), {
            ("all", "avg_lending"): _after(t, r"Lãi suất cho vay bình quân"),
            ("all", "spread"): _after(t, r"Chênh lệch LSCV bình quân và Lãi suất tiền gửi bình quân"),
        }, url, "pdf")
    return out


def _bvb(backfill: bool) -> list[dict]:
    years = range(2024, date.today().year + 1) if backfill else [date.today().year]
    out = []
    for y in years:
        page = f"https://bvbank.net.vn/thong-bao/lai-suat-cho-vay-binh-quan-thang-nam-{y}/"
        raw = _render(page)
        for text, url in _links(raw, page):
            m = re.search(r"T(\d{2})\.(20\d{2})\.(pdf|png|jpe?g)$", url, re.I)
            if not m:
                continue
            period = f"{m.group(2)}-{m.group(1)}"
            if m.group(3).lower() != "pdf":
                _need_manual("BVB", url, f"ky {period}")
                continue
            r = _get(url)
            if not r.content.startswith(b"%PDF"):
                continue
            t = _pdf_text(r.content)
            out += _rows("BVB", _period(t) or period, {
                ("all", "avg_lending"): _after(t, r"Lãi suất cho vay bình quân\s*\(\*\)"),
                ("individual", "avg_lending"): _after(t, r"đối với Khách hàng Cá nhân"),
                ("business", "avg_lending"): _after(t, r"đối với Khách hàng Doanh nghiệp"),
                ("all", "spread"): _after(t, r"Chênh lệch lãi suất tiền gửi và cho vay bình quân"),
            }, url, "pdf", basis="all_loans")
    return out


# MSB doi duong dan gan nhu moi thang (da gap ca 4 kieu duoi day, 2025-2026); xac nhan bang thang trong tieu de.
MSB_SLUGS = ("bao-cao-tinh-hinh-cong-bo-lai-suat-thang-{mm}-{y}/", "cong-bo-lai-suat-thang-{mm}-{y}/",
             "bao-cao-1117-nhnn-bao-cao-tinh-hinh-cong-bo-lai-suat-t{m}-{y}/", "cong-bo-lai-suat-binh-quan-thang-{m}/")


def _msb(backfill: bool) -> list[dict]:
    out = []
    base = "https://www.msb.com.vn/ve-chung-toi/tin-tuc-va-su-kien/"
    for y, m in _months_back(24 if backfill else 3):
        urls = [base + pre + s.format(m=m, mm=f"{m:02d}", y=y) for s in MSB_SLUGS for pre in ("ve-msb/", "")]
        for url in urls:
            r = _get(url)
            if r.status_code != 200:
                continue
            t = _plain(r.text)
            if not re.search(rf"tháng\s*0?{m}\.{y}", t, re.I):
                continue
            out += _rows("MSB", f"{y}-{m:02d}", {
                ("all", "avg_lending"): _after(t, r"\|\s*Lãi suất cho vay bình quân\s*\|"),
                ("all", "spread"): _after(t, r"Chênh lệch lãi suất tiền gửi và cho vay bình quân\s*\(\*\)\s*\|"),
            }, url, "html", basis="new_loans")
            break
    return out


def _ssb(backfill: bool) -> list[dict]:
    """Hai loai bai: 'lai suat cho vay KHCN thang MM' (so trong PDF dinh kem, tach ngan / trung dai han,
    khoan vay phat sinh moi) va 'chenh lech ... ngay DD/MM/YYYY' (so nam ngay trong bai)."""
    page = "https://www.seabank.com.vn/tin-tuc/cong-bo-lai-suat-cho-vay/khach-hang-ca-nhan"
    r = _get(page, timeout=60)
    posts = sorted(set(u for _, u in _links(r.text, page)
                       if re.search(r"khcn-thang-\d{6}$|chenh-lech.*ngay-\d{8}$", u)))
    out = []
    for post in posts:
        pr = _get(post, timeout=60)
        d = re.search(r"ngay-(\d{2})(\d{2})(20\d{2})$", post)
        if d:
            t = _plain(pr.text)
            out += _rows("SSB", f"{d.group(3)}-{d.group(2)}", {
                ("all", "spread"): _after(t, r"cho vay bình quân toàn hàng của SeABank thời điểm\s*[\d/]+\s*là"),
            }, post, "html", as_of=f"{d.group(1)}/{d.group(2)}/{d.group(3)}")
            continue
        files = [u for text, u in _links(pr.text, post) if "tại đây" in text.lower()]
        if not files:
            continue
        url = files[0]
        if not url.lower().split("?")[0].endswith(".pdf"):
            _need_manual("SSB", url, f"bai {post.rsplit('/', 1)[-1]}")
            continue
        fr = _get(url)
        if not fr.content.startswith(b"%PDF"):
            continue
        t = _pdf_text(fr.content)
        m = re.search(r"khcn-thang-(\d{2})(20\d{2})$", post)
        out += _rows("SSB", _period(t) or (f"{m.group(2)}-{m.group(1)}" if m else None), {
            ("individual_short_term", "avg_lending"): _after(t, r"Ngắn hạn"),
            ("individual_medium_long_term", "avg_lending"): _after(t, r"Trung dài hạn"),
        }, url, "pdf", basis="new_loans")
    return out


def _tpb(backfill: bool) -> list[dict]:
    url = "https://tpb.vn/tin-tuc/cong-bo-lai-suat-binh-quan/bang-lai-suat-cho-vay-binh-quan"
    pages = [(url, "html")] + ([(u, "wayback") for u, _ in _wayback("tpb.vn/tin-tuc/cong-bo-lai-suat-binh-quan/"
                                                                       "bang-lai-suat-cho-vay-binh-quan")] if backfill else [])
    out = []
    for u, kind in pages:
        r = _get(u, timeout=60)
        if r.status_code != 200:
            continue
        t = _plain(r.text)
        m = re.search(r"kỳ số liệu tháng\s*(\d{1,2})\s*năm\s*(20\d{2})", t, re.I)
        out += _rows("TPB", f"{m.group(2)}-{int(m.group(1)):02d}" if m else None, {
            ("all", "avg_lending"): _after(t, r"Lãi suất cho vay bình quân chung\s*\|"),
            ("individual", "avg_lending"): _after(t, r"bình quân đối với Khách hàng Cá nhân\s*\|"),
            ("business", "avg_lending"): _after(t, r"bình quân đối với Khách hàng Doanh nghiệp\s*\|"),
            ("all", "spread"): _after(t, r"Chênh lệch lãi suất bình quân thực tế\s*\|"),
        }, u, kind)
    return out


def _nvb(backfill: bool) -> list[dict]:
    """NCB sua lai cung mot bai moi ky; bai ghi ngay dang, khong ghi ky so lieu."""
    url = ("https://www.ncb-bank.vn/vi/tin-tuc/"
           "ncb-cong-bo-lai-suat-cho-vay-binh-quan-va-chenh-lech-lai-suat-binh-quan-n104492")
    t = _plain(_render(url))
    i = t.find("Nội dung")
    head = t[max(0, i - 120): i]
    d = re.search(r"(\d{2})/(\d{2})/(20\d{2})", head)
    return _rows("NVB", f"{d.group(3)}-{d.group(2)}" if d else None, {
        ("all", "avg_lending"): _after(t, r"Lãi suất bình quân Cho vay\s*\(\*\)"),
        ("individual_project_housing", "avg_lending"): _after(t, r"KHCN\s*\(Nhà dự án\)"),
        ("business_working_capital", "avg_lending"): _after(t, r"KHDN\s*\(Bổ sung Vốn lưu động\)"),
        ("all", "spread"): _after(t, r"Huy động bình quân\)\s*\(\*\*\)"),
    }, url, "html_render", as_of=f"{d.group(1)}/{d.group(2)}/{d.group(3)}" if d else "",
        note="NCB khong ghi ky; period = thang cua ngay dang bai")


def _ocb(backfill: bool) -> list[dict]:
    url = "https://ocb.com.vn/vi/cong-cu/lai-suat"
    raw = _render_click("https://ocb.com.vn/vi",
                        "[...document.querySelectorAll('a')].find(a=>a.href.endsWith('/vi/cong-cu/lai-suat'))?.click()",
                        wait_s=7)
    t = _plain(raw)
    m = re.search(r"Kỳ tháng\s*(\d{1,2})/(20\d{2})", t)
    return _rows("OCB", f"{m.group(2)}-{int(m.group(1)):02d}" if m else None, {
        ("individual", "avg_lending"): _after(t, r"Lãi suất cho vay bình quân đối với khách hàng cá nhân"),
        ("all", "spread"): _after(t, r"Chênh lệch lãi suất cho vay bình quân và lãi suất tiền gửi bình quân"),
    }, url, "html_render")


# ---------------------------------------------------------------------------
# Nguon chi co anh: so do nguoi nhap tay vao MANUAL (cung cot, source_kind = image_manual, source_url = anh).
# Crawler chi tim anh moi nhat va bao khi anh do chua co trong MANUAL.

MANUAL = OUT / "lending_rates_official_manual.csv"


def _manual_urls() -> set[str]:
    # So khop bo query: VCB doi ?ts=... moi khi sua trang ma anh khong doi.
    if not MANUAL.exists():
        return set()
    return {u.split("?")[0] for u in pd.read_csv(MANUAL, dtype=str).source_url}


def _need_manual(tk: str, url: str, what: str) -> None:
    if url.split("?")[0] not in _manual_urls():
        print(f"    {tk}: {what} la ANH, chua nhap tay -> {MANUAL.name}: {url}")


def _nab(backfill: bool) -> list[dict]:
    page = "https://www.namabank.com.vn/lai-suat-cho-vay-binh-quan"
    r = _get(page)
    for src in re.findall(r'<img[^>]+src="([^"]*laisuatbinhquan[^"]*)"', r.text, re.I):
        _need_manual("NAB", urljoin(page, src), "lai cho vay binh quan")
    return []


def _stb(backfill: bool) -> list[dict]:
    """Sacombank ghi de cung mot anh moi ky; ky doc tu tieu de trang."""
    page = f"https://www.sacombank.com.vn/trang-chu/tin-tuc/thong-bao/{date.today().year}/lai-suat-binh-quan.html"
    r = _get(page)
    m = re.search(r"Lãi suất cho vay bình quân tháng\s*(\d{1,2})\.(20\d{2})", _plain(r.text))
    img = re.search(r'src="([^"]*cong-bo-lai-suat-binh-quan[^"]*\.(?:jpe?g|png))"', r.text, re.I)
    if m and img:
        period = f"{m.group(2)}-{int(m.group(1)):02d}"
        man = pd.read_csv(MANUAL, dtype=str) if MANUAL.exists() else pd.DataFrame(columns=COLUMNS)
        if not ((man.ticker == "STB") & (man.period == period)).any():
            print(f"    STB: ky {period} la ANH, chua nhap tay -> {urljoin(page, img.group(1))}")
    return []


VCB_SEARCH = ("https://www.vietcombank.com.vn/vi-VN/sxa/search/results/?l=vi-VN&q={q}&p=100"
              "&v=%7B5E30B19D-3205-453A-97DA-2EC52C3B1DC1%7D&s=%7B96F6D836-0056-44EC-825D-6EC2A1CB2532%7D"
              "&itemid=%7B7FFD0BD8-62BB-4848-AAD9-98D4D9442890%7D")


def _vcb(backfill: bool) -> list[dict]:
    """Danh sach bai lay tu API tim kiem cua chinh VCB (moi thang mot bai 'Thong tin lai suat ...').
    So nam trong anh (da so) hoac PDF dinh kem."""
    from urllib.parse import quote
    arts = set()
    for q in ("lãi suất cho vay bình quân", "Thông tin lãi suất"):
        try:
            res = _get(VCB_SEARCH.format(q=quote(q)), timeout=60).json().get("Results", [])
        except ValueError:
            continue
        for x in res:
            u = x.get("Url", "")
            if (re.search(r"/Trang-thong-tin-dien-tu/Articles/20\d{2}/", u)
                    and re.search(r"(?i)thong-tin-lai-suat|lai-suat-binh-quan|lai-suat-cho-vay-binh-quan"
                                  r"|cong-bo-lai-suat-cho-vay|cong-bo-thong-tin-lai-suat", u)):
                arts.add(urljoin("https://www.vietcombank.com.vn", u))
    def parse(t: str) -> dict:
        return {("all", "avg_lending"): _after(t, r"Lãi suất cho vay bình quân(?: kỳ tháng\s*\d{1,2}/20\d{2})?\s*:?"),
                ("all", "spread"): _after(t, r"lãi suất tiền gửi bình quân(?!\s*sau)\s*:?", 15),
                ("all", "spread_net"): _after(t, r"sau khi trừ[^%]{0,120}?sử dụng vốn\s*:?", 15)}

    def parse_pdf(t: str) -> dict:
        # PDF cua VCB tach chu thanh cot: so dung TRUOC nhan ("7,4% Lai suat cho vay binh quan ky thang 08/2026:
        # /nam ..."), nhung thu tu luon la: lai binh quan, chenh lech, chenh lech sau chi phi.
        nums = [_num(x) for x in re.findall(DEC + r"\s*%", t)]
        keys = [("all", "avg_lending"), ("all", "spread"), ("all", "spread_net")]
        return dict(zip(keys, nums[:3]))

    out = []
    # URL bai bat dau bang /Articles/YYYY/MM/DD/ nen sap xep chuoi la sap xep theo ngay dang.
    for art in sorted(arts, reverse=True)[: (60 if backfill else 3)]:
        r = _get(art, timeout=60)
        t = _plain(r.text)
        m = re.search(r"kỳ tháng\s*(\d{1,2})/(20\d{2})", t)
        if m and parse(t)[("all", "avg_lending")] is not None:  # 2026: so nam ngay trong bai
            out += _rows("VCB", f"{m.group(2)}-{int(m.group(1)):02d}", parse(t), art, "html")
            continue
        # Con lai: PDF hoac anh dinh kem. Bo anh nen (_bg), anh thu nho tin lien quan (h=32/h=160).
        media = [urljoin(art, x) for x in re.findall(r'(?:src|href)="([^"]*/-/media/Project/VCB-Sites/VCB/[^"]+)"', r.text)]
        media = [x for x in media if re.search(r"(?i)lai-suat", x) and re.search(r"(?i)\.(pdf|jpe?g|png)(\?|$)", x)
                 and not re.search(r"(?i)_bg\.|[?&]h=\d", x)]
        for mu in media[:1]:
            if re.search(r"(?i)\.pdf(\?|$)", mu):
                fr = _get(mu)
                if fr.content.startswith(b"%PDF"):
                    pt = _pdf_text(fr.content)
                    km = re.search(r"kỳ tháng\s*(\d{1,2})/(20\d{2})", pt)
                    out += _rows("VCB", f"{km.group(2)}-{int(km.group(1)):02d}" if km else _period(pt),
                                 parse_pdf(pt), mu, "pdf")
            else:
                _need_manual("VCB", mu, f"bai {art.rsplit('/', 1)[-1]}")
    return out


BANKS = {"ACB": _acb, "BID": _bid, "EIB": _eib, "TCB": _tcb, "HDB": _hdb, "VIB": _vib, "SHB": _shb,
         "MBB": _mbb, "PGB": _pgb, "BVB": _bvb, "MSB": _msb, "SSB": _ssb, "TPB": _tpb, "NVB": _nvb,
         "OCB": _ocb, "NAB": _nab, "STB": _stb, "VCB": _vcb}


# ---------------------------------------------------------------------------

def _load() -> pd.DataFrame:
    if MASTER.exists():
        return pd.read_csv(MASTER, dtype=str)
    return pd.DataFrame(columns=COLUMNS)


def _expected_period(today: date | None = None) -> str:
    """Ky ngan hang le ra da cong bo: thang truoc."""
    y, m = _months_back(2, today)[1]
    return f"{y}-{m:02d}"


def run(backfill: bool = False, force: bool = False, only: list[str] | None = None) -> pd.DataFrame:
    OUT.mkdir(parents=True, exist_ok=True)
    old = _load()
    latest = old.groupby("ticker").period.max().to_dict() if len(old) else {}
    want = _expected_period()
    new_rows, status = [], {}
    for tk, fn in BANKS.items():
        if only and tk not in only:
            continue
        if not (backfill or force) and latest.get(tk, "") >= want:
            status[tk] = f"da co {latest[tk]}, bo qua"
            continue
        t0 = time.time()
        try:
            rows = fn(backfill)
            new_rows += rows
            periods = sorted({r["period"] for r in rows})
            if rows:
                status[tk] = f"{len(rows)} dong, ky {periods[0]}..{periods[-1]}"
            elif fn in (_nab, _stb):
                status[tk] = "nguon la anh: so lay tu file nhap tay, chi kiem anh moi"
            else:
                status[tk] = "KHONG DOC DUOC so nao"
        except Exception as e:  # mot ngan hang hong khong chan ngan hang khac
            status[tk] = f"LOI {type(e).__name__}: {str(e)[:120]}"
        print(f"  {tk}: {status[tk]} ({time.time() - t0:.0f}s)")
    for tk, why in GAPS.items():
        status[tk] = "CHUA DOC: " + why
    new = pd.DataFrame(new_rows, columns=COLUMNS).astype(str)
    manual = pd.read_csv(MANUAL, dtype=str) if MANUAL.exists() else pd.DataFrame(columns=COLUMNS)
    merged = pd.concat([old, new, manual], ignore_index=True)
    # Cung khoa: giu ban doc sau cung (ban nhap tay tu anh dung cuoi), bao neu so bi sua lai.
    dup = merged[merged.duplicated(KEY, keep=False)]
    for k, g in dup.groupby(KEY):
        if pd.to_numeric(g.value_percent).nunique() > 1:
            print(f"  SO BI SUA {k}: {list(g.value_percent)}")
    merged = merged.drop_duplicates(KEY, keep="last").sort_values(KEY)
    merged.to_csv(MASTER, index=False, encoding="utf-8")
    print(f"  -> {MASTER}: {len(merged)} dong, {merged.ticker.nunique()} ngan hang "
          f"(+{len(merged) - len(old)} dong moi, {len(manual)} dong nhap tay tu anh)")
    return pd.DataFrame(sorted(status.items()), columns=["ticker", "status"])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    only = [a.upper() for a in args if not a.startswith("--")] or None
    print(run(backfill="--backfill" in args, force="--force" in args, only=only).to_string(index=False))
