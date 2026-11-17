from __future__ import annotations

import csv
import io
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

OUT = Path("data/interest_rates")
MASTER = OUT / "deposit_official_daily.csv"
SOURCE_NAME = "bieu_ngan_hang"
COLUMNS = ["date", "effective_date", "ticker", "term_months", "channel", "rate_percent", "tier", "product",
           "source", "source_url", "source_updated_at", "retrieved_at_utc"]

# Cung bo ky han 24hmoney theo doi (web, xep hang va lich su deu dung bo nay).
TERMS = (1, 3, 6, 12, 18, 24, 36)
VN_TZ = timezone(timedelta(hours=7))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "vi,en;q=0.9"}
TIMEOUT = 60
# Tran NHNN cho ky 1 den duoi 6 thang (QD 2411/QD-NHNN, hieu luc 20/11/2024). Bieu chinh thuc khong duoc vuot,
# nen o nao vuot la doc nham cot/bang -> loai ca bang cua NH do.
CAP_1_5M = 4.75


@dataclass
class Board:
    ticker: str
    url: str
    cells: dict = field(default_factory=dict)          # (channel, term) -> rate
    effective: str = ""                                 # YYYY-MM-DD in tren bieu
    tier: dict = field(default_factory=dict)            # channel -> mo ta bac tien
    product: dict = field(default_factory=dict)         # channel -> san pham / cot
    updated: str = ""                                   # moc cap nhat cua trang (neu co)

    def put(self, channel: str, term, rate) -> None:
        if term in TERMS and rate is not None:
            self.cells[(channel, int(term))] = float(rate)


# ---------------------------------------------------------------------------
# tien ich

_SESSION = None


def _s() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()
        _SESSION.headers.update(HEADERS)
    return _SESSION


class _CurlResponse:
    def __init__(self, content: bytes):
        self.content = content
        self.encoding = "utf-8"

    @property
    def text(self) -> str:
        return self.content.decode(self.encoding, "replace")

    def json(self):
        return json.loads(self.content)


def _curl(url: str) -> _CurlResponse:
    import subprocess
    out = subprocess.run(["curl.exe", "-sSfL", "--max-time", str(TIMEOUT), "-A", UA, url],
                         capture_output=True, timeout=TIMEOUT + 30)
    if out.returncode != 0:
        raise RuntimeError(f"curl {url}: {out.stderr.decode('utf-8', 'replace')[:200]}")
    return _CurlResponse(out.stdout)


def _get(url: str, **kw):
    last = None
    for attempt in range(3):
        try:
            r = _s().get(url, timeout=TIMEOUT, **kw)
            r.raise_for_status()
            return r
        except requests.exceptions.SSLError as exc:
            if kw:
                raise
            try:
                return _curl(url)
            except Exception as exc2:
                last = exc2
        except Exception as exc:  # mang chap chon: thu lai 2 lan
            last = exc
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"GET {url}: {type(last).__name__}: {last}")


def _html(url: str) -> str:
    r = _get(url)
    r.encoding = "utf-8"
    return r.text


def _render(url: str, budget_ms: int = 15000) -> str:
    from crawlers.lending_rates_official import _render as render
    html = render(url, budget_ms)
    if len(html) < 2000:
        raise RuntimeError(f"Edge headless tra ve trang rong cho {url}")
    return html


def _rate(text) -> float | None:
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    m = re.search(r"(?<![\d.,])(\d{1,2}(?:[.,]\d{1,3})?)(?![\d])", str(text))
    return float(m.group(1).replace(",", ".")) if m else None


_TERM_RE = re.compile(r"(\d{1,2})\s*(?:-\s*)?(tháng|thang|months?|M\b|T\b|th\b)", re.IGNORECASE)


def _term(label) -> int | None:
    text = _nfc(unescape(str(label))).strip()
    if re.match(r"^\s*(trên|tren|dưới|duoi)\b", text, re.IGNORECASE):
        return None
    m = _TERM_RE.search(text)
    if not m or text.lower().find("tuần") != -1 and text.lower().find("tuần") < m.start():
        return None
    return int(m.group(1))


def _nfc(text: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFC", text).replace("\xa0", " ")


def _date(text: str) -> str:
    m = re.search(r"(?<!\d)(\d{1,2})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(20\d\d)", text or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else ""


def _effective(text: str) -> str:
    m = re.search(r"(hiệu lực|áp dụng|cập nhật|có hiệu lực)[^0-9]{0,40}(\d{1,2}\s*[./-]\s*\d{1,2}\s*[./-]\s*20\d\d)",
                  text or "", re.IGNORECASE)
    return _date(m.group(2)) if m else _date(text)


def _grid(table) -> list[list[str]]:
    grid: list[list[str]] = []
    pending: dict[tuple[int, int], str] = {}
    for r, tr in enumerate(table.find_all("tr")):
        row: list[str] = []
        c = 0
        cells = tr.find_all(["td", "th"])
        k = 0
        while k < len(cells) or (r, c) in pending:
            if (r, c) in pending:
                row.append(pending.pop((r, c)))
                c += 1
                continue
            cell = cells[k]
            k += 1
            text = _nfc(cell.get_text(" ", strip=True))
            rs, cs = int(cell.get("rowspan", 1) or 1), int(cell.get("colspan", 1) or 1)
            for dc in range(cs):
                row.append(text)
                for dr in range(1, rs):
                    pending[(r + dr, c + dc)] = text
                c += 1
        grid.append(row)
    return grid


def _pdf_lines(content: bytes, engine: str = "pdfplumber") -> list[str]:
    if not _is_pdf(content):
        raise RuntimeError("tai ve khong phai PDF")
    lines: list[str] = []
    if engine == "pymupdf":
        import pymupdf
        with pymupdf.open(stream=content, filetype="pdf") as doc:
            for page in doc:
                lines.extend(page.get_text().splitlines())
    else:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                lines.extend((page.extract_text() or "").splitlines())
    return [_nfc(re.sub(r"\s+", " ", ln)).strip() for ln in lines]


def _pdf_text(content: bytes) -> str:
    return "\n".join(_pdf_lines(content))


def _is_pdf(content: bytes) -> bool:
    return content[:5] == b"%PDF-"


_ROW_RE = re.compile(r"^(\d{1,2})\s*(?:tháng|Tháng|THÁNG|T)\b\s*(.*)$")
_TOKEN_RE = re.compile(r"^(?:\d{1,2}[.,]\d{1,3}|-)$")


def _term_rows(lines, start: int = 0, stop: int | None = None, widths=None) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for ln in lines[start:stop]:
        m = _ROW_RE.match(ln)
        if not m:
            continue
        toks = []
        for tok in m.group(2).split():
            if not _TOKEN_RE.match(tok):
                break
            toks.append(tok)
        if not toks or (widths and len(toks) not in widths):
            continue
        out.setdefault(int(m.group(1)), toks)
    return out


def _find(lines, pattern: str, start: int = 0) -> int:
    rx = re.compile(pattern, re.IGNORECASE)
    for i in range(start, len(lines)):
        if rx.search(lines[i]):
            return i
    raise RuntimeError(f"khong thay muc /{pattern}/ trong bieu")


# ---------------------------------------------------------------------------
# tung ngan hang. Moi ham tra ve Board; ghi ro nguon, muc, cot da doc trong docstring.

def _vcb() -> Board:
    url = "https://www.vietcombank.com.vn/vi-VN/KHCN/Cong-cu-Tien-ich/KHCN---Lai-suat"
    soup = BeautifulSoup(_html(url), "lxml")
    node = soup.find("input", id="currentDataInterestRate")
    if node is None:
        raise RuntimeError("khong thay currentDataInterestRate")
    data = json.loads(node["value"])
    b = Board("VCB", url, updated=data.get("UpdatedDate", ""), effective=_date_iso(data.get("UpdatedDate", "")))
    for d in data["Data"]:
        if d.get("currencyCode") != "VND":
            continue
        channel = {"Savings": "quay", "Online": "online"}.get(d.get("tenorType"))
        m = re.match(r"(\d+)-months?$", d.get("tenor", ""))
        if channel and m and d.get("rates") is not None:
            b.put(channel, int(m.group(1)), round(float(d["rates"]) * 100, 4))
    b.product = {"quay": "Tiet kiem tai quay", "online": "Tien gui truc tuyen"}
    return b


def _date_iso(text: str) -> str:
    m = re.match(r"(20\d\d-\d\d-\d\d)", text or "")
    return m.group(1) if m else ""


def _ctg() -> Board:
    url = "https://www.vietinbank.vn/ca-nhan/cong-cu-tien-ich/lai-suat-khcn"
    soup = BeautifulSoup(_html(url), "lxml")
    b = Board("CTG", url, product={"quay": "Lai suat huy dong VND"})
    for table in soup.find_all("table"):
        grid = _grid(table)
        if not grid or "VND" not in " ".join(grid[0]):
            continue
        col = next(i for i, h in enumerate(grid[0]) if "VND" in h)
        for row in grid[1:]:
            label = row[0].lower()
            # "Tu 1 thang den duoi 2 thang" -> 1; "12 thang"; "36 thang"; bo "Tren 12 thang den 13 thang"
            term = _term(row[0]) if (label.startswith("từ") or re.match(r"^\d", label)) else None
            if term is not None and col < len(row):
                b.put("quay", term, _rate(row[col]))
    return b


def _bid() -> Board:
    url = "https://bidv.com.vn/vn/tra-cuu-lai-suat"
    soup = BeautifulSoup(_render(url), "lxml")
    b = Board("BID", url, product={"quay": "Lai suat tien gui KHCN, VND"})
    for table in soup.find_all("table"):
        grid = _grid(table)
        if not grid or "VND" not in grid[0]:
            continue
        col = grid[0].index("VND")
        for row in grid[1:]:
            if col < len(row):
                b.put("quay", _term(row[0]), _rate(row[col]))
    return b


def _acb() -> Board:
    url = "https://acb.com.vn/lai-suat-tien-gui"
    soup = BeautifulSoup(_html(url), "lxml")
    b = Board("ACB", url, tier={"quay": "moi muc (thuong bac thang khong tinh)", "online": "< 200 trieu"},
              product={"quay": "TK Truyen thong, lai cuoi ky", "online": "Tien gui Online LCK"})
    for table in soup.find_all("table"):
        grid = _grid(table)
        head = " ".join(" ".join(r) for r in grid[:3])
        if "TK Truyền Thống" in head and "Lãi cuối kỳ" in head:
            # hang 3 la tieu de lai; cot dau tien "Lai cuoi ky" ben phai cot USD la VND / Truyen thong / cuoi ky
            sub = grid[2]
            col = sub.index("Lãi cuối kỳ", 1) if sub.count("Lãi cuối kỳ") > 1 else None
            if col is None:
                raise RuntimeError("ACB: khong xac dinh duoc cot VND lai cuoi ky")
            for row in grid[3:]:
                if col < len(row):
                    b.put("quay", _term(row[0]), _rate(row[col]))
        elif grid and "Tiền gửi Online (LCK)" in " ".join(grid[0]):
            terms = [_term(h) for h in grid[1]]
            low = next(r for r in grid[2:] if r and r[0].strip().startswith("<"))
            # dong < 200 co them o "1 - 3 tuan" o dau, cac dong khac khong: canh theo cuoi dong
            values = low[1:]
            heads = grid[1][1:]
            for h, v in zip(heads[-len(values):], values) if len(values) <= len(heads) else zip(heads, values):
                b.put("online", _term(h), _rate(v))
    return b


def _msb() -> Board:
    url = "https://www.msb.com.vn/khach-hang-ca-nhan/lai-suat-tiet-kiem/"
    soup = BeautifulSoup(_html(url), "lxml")
    b = Board("MSB", url, product={"quay": "Lai suat cao nhat", "online": "Lai suat cao nhat"})
    for node in soup.find_all(attrs={"data-config": True}):
        cfg = json.loads(node["data-config"])
        table = cfg.get("ratesTableVND")
        if not isinstance(table, dict):
            continue
        for key, channel in (("tai_quay", "quay"), ("truc_tuyen", "online")):
            for row in table.get(key, []):
                m = re.match(r"(\d+)M$", row.get("ky_han", ""))
                if m:
                    b.put(channel, int(m.group(1)), row.get("LAI_SUAT_CAO_NHAT"))
        break
    return b


def _pgb() -> Board:
    url = "https://www.pgbank.com.vn/lai-suat-tiet-kiem/ca-nhan-vnd"
    html = _render(url)
    soup = BeautifulSoup(html, "lxml")
    b = Board("PGB", url, effective=_effective(soup.get_text(" ", strip=True)),
              product={"quay": "TK thong thuong, cuoi ky", "online": "TK Online, cuoi ky"})
    for table in soup.find_all("table"):
        grid = _grid(table)
        if len(grid) < 3 or "Online" not in " ".join(grid[0]):
            continue
        top, sub = grid[0], grid[1]
        cols = {}
        for i, (group, kind) in enumerate(zip(top, sub)):
            if kind.strip() != "Trả lãi cuối kỳ":
                continue
            if "thông thường" in group and "quay" not in cols:
                cols["quay"] = i
            elif "Online" in group and "rút" not in group and "online" not in cols:
                cols["online"] = i
        if set(cols) != {"quay", "online"}:
            raise RuntimeError(f"PGB: khong xac dinh duoc cot: {top} / {sub}")
        for row in grid[2:]:
            for channel, col in cols.items():
                if col < len(row):
                    b.put(channel, _term(row[0]), _rate(row[col]))
    return b


def _nab() -> Board:
    index = "https://www.namabank.com.vn/lai-suat"
    soup = BeautifulSoup(_html(index), "lxml")
    links = {}
    for el in soup.find_all(attrs={"data-news-href": True}):
        title = el.get_text(" ", strip=True)
        href = urljoin(index, el["data-news-href"])
        if title.startswith("Lãi suất Tiền gửi VND") and "KHTC" not in title:
            links.setdefault("quay", (href, title))
        elif title.startswith("Lãi suất Tiết kiệm Trực tuyến") and "KHTC" not in title:
            links.setdefault("online", (href, title))
    if set(links) != {"quay", "online"}:
        raise RuntimeError(f"NAB: khong thay du 2 bieu tren trang lai-suat: {links}")
    b = Board("NAB", links["quay"][0], product={"quay": "Tiet kiem thong thuong, lai cuoi ky",
                                                "online": "Tiet kiem truc tuyen, lai cuoi ky"})
    dates = []
    for channel, (href, title) in links.items():
        dates.append(_date(title))
        page = BeautifulSoup(_html(href), "lxml")
        table = page.find("table")
        grid = _grid(table)
        head = grid[0]
        col = next((i for i, h in enumerate(head) if "cuối kỳ" in h.lower()), None)
        if col is None:
            raise RuntimeError(f"NAB {channel}: khong thay cot lai cuoi ky: {head}")
        by_term = {}
        for row in grid[1:]:
            term = _term(row[0].split(",")[0])
            if term is not None and col < len(row) and term not in by_term:
                by_term[term] = _rate(row[col])
        # Ky 24/36T lai cuoi ky ghi '-' kem chu thich "(**) ... ky han 24 thang lai cuoi ky, so tien gui duoi 500 ty
        # dong: ap dung lai suat ky han 23 thang lai cuoi ky" -> lay so cua ky han duoc chi dinh.
        note = _nfc(page.get_text(" ", strip=True))
        # (24T: "..., so tien gui duoi 500 ty dong: ap dung ... 23 thang"; 36T: "... voi khoan tien gui duoi 500 ty ...")
        for m in re.finditer(r"kỳ hạn (\d+) tháng lãi cuối kỳ[^:]{0,60}dưới 500 tỷ đồng:? áp dụng lãi suất kỳ hạn "
                             r"(\d+) tháng", note):
            asked, used = int(m.group(1)), int(m.group(2))
            if by_term.get(asked) is None and by_term.get(used) is not None:
                by_term[asked] = by_term[used]
        for term, rate in by_term.items():
            b.put(channel, term, rate)
    b.effective = max(d for d in dates if d) if any(dates) else ""
    b.url = links["quay"][0] + " ; " + links["online"][0]
    return b


def _ocb() -> Board:
    api = "https://webocb-api.ocb.com.vn"
    token = _get(f"{api}/api/Public/GetAccessTokenPublic").text.strip().strip('"')
    items = _get(f"{api}/api/interest-rate-header/get-all?language=vi&navigationCode=20211023010215008",
                 headers={"Authorization": "Bearer " + token}).json()["items"]
    vnd = [i for i in items if i.get("type") == "VND" and i.get("fileName")]
    if not vnd:
        raise RuntimeError("OCB: API khong tra bieu VND nao")
    latest = max(vnd, key=lambda i: i["publishDate"])
    url = f"{api}/Resources/Files/{latest['fileName']}"
    content = _get(url).content
    lines = _pdf_lines(content)
    start = _find(lines, r"^II\. TIẾT KIỆM THÔNG THƯỜNG")
    stop = _find(lines, r"^III\.", start)
    rows = _term_rows(lines, start, stop)
    b = Board("OCB", url, effective=_effective(" ".join(lines[:3])) or latest["publishDate"][:10],
              tier={"online": "< 100 trieu"}, product={"quay": "TK thong thuong, cuoi ky", "online": "TK truc tuyen, cuoi ky"})
    for term, toks in rows.items():
        if len(toks) != 8:
            raise RuntimeError(f"OCB {term}T: can 8 cot, doc duoc {toks}")
        b.put("quay", term, _rate(toks[4]))
        b.put("online", term, _rate(toks[5]))
    return b


def _vpb() -> Board:
    year = datetime.now(VN_TZ).year
    docs = []
    for y in (year, year - 1):
        api = ("https://www.vpbank.com.vn/uiux-api/api/document?categoryPath="
               f"/tai-lieu-bieu-mau/lai-suat-huy-dong/khach-hang-ca-nhan/{y}")
        docs = _walk_docs(_get(api).json())
        if docs:
            break
    docs = [d for d in docs if d[1].lower().endswith(".pdf")]
    if not docs:
        raise RuntimeError("VPB: API khong tra PDF nao")
    # Ten file mang ngay hieu luc: ".../2.-20261102-Phu-luc-BLS-niem-yet.pdf"
    dated = [(re.search(r"(20\d{6})", p).group(1), t, p) for t, p in docs if re.search(r"(20\d{6})", p)]
    if not dated:
        raise RuntimeError(f"VPB: ten PDF khong mang ngay: {docs[:3]}")
    _, title, path = max(dated)
    url = urljoin("https://www.vpbank.com.vn", path)
    lines = _pdf_lines(_get(url).content, engine="pymupdf")
    b = Board("VPB", url, effective=_effective(title), tier={"quay": "< 1 ty", "online": "< 1 ty"},
              product={"quay": "Tiet kiem thuong, cuoi ky, tai quay", "online": "Tiet kiem thuong, cuoi ky, Online"})
    # Chu PDF bi cat dong ('< 1 t' / 'ỷ', 'K' / 'ênh'), nen gop lai thanh mot chuoi roi doc theo moc.
    text = " ".join(lines)
    first = re.search(r"Tại quầy(.*?)K ?ênh Online(.*?)(?:2\.\s*Ti|$)", text, re.S)
    if not first:
        raise RuntimeError("VPB: khong thay phan Tai quay / Kenh Online")
    for channel, part in (("quay", first.group(1)), ("online", first.group(2))):
        head = re.search(r"1 - 3 tu ?ần(.*?)< ?1 t ?ỷ", part)
        low = re.search(r"< ?1 t ?ỷ(.*?)1 t ?ỷ ?- ?< ?3", part)
        if not head or not low:
            raise RuntimeError(f"VPB {channel}: khong doc duoc hang tieu de / dong < 1 ty")
        terms = re.findall(r"(\d{1,2})T", head.group(1))
        values = re.findall(r"\d{1,2}\.\d{2}", low.group(1))
        # dong < 1 ty co them o '1 - 3 tuan' (0.40) dung truoc cac ky han thang
        if len(values) == len(terms) + 1:
            values = values[1:]
        if len(values) != len(terms):
            raise RuntimeError(f"VPB {channel}: {len(terms)} ky han nhung {len(values)} so")
        for t, v in zip(terms, values):
            b.put(channel, int(t), float(v))
    return b


def _walk_docs(node, out=None) -> list[tuple[str, str]]:
    out = [] if out is None else out
    if isinstance(node, dict):
        title = node.get("title") or node.get("name") or ""
        for key in ("url", "filePath", "link", "fileUrl", "path"):
            val = node.get(key)
            if isinstance(val, str) and val.lower().endswith(".pdf"):
                out.append((title, val))
        for v in node.values():
            _walk_docs(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk_docs(v, out)
    return out


def _bvb() -> Board:
    page = "https://bvbank.net.vn/khach-hang-ca-nhan/lai-suat/"
    html = _render(page)
    pdfs = sorted(set(re.findall(r'https?://bvbank\.net\.vn/wp-content/uploads/\d{4}/\d{2}/Bieu-LSNY_Web_[\d.]+\.pdf',
                                 html)), key=lambda u: _date(u.rsplit("_", 1)[-1]))
    if not pdfs:
        raise RuntimeError("BVB: khong thay link Bieu-LSNY_Web_*.pdf")
    url = pdfs[-1]
    lines = _pdf_lines(_get(url).content)
    i_online = _find(lines, r"^A\. TIỀN GỬI VND")
    i_quay = _find(lines, r"^V Tiền gửi, tiết kiệm thông thường")
    # Tieu de "VII Tich luy Dong Hanh" (cot phai) chen giua bang V, nen dung o muc B (ngoai te), loc bang so cot.
    i_end = _find(lines, r"^B\. TIỀN GỬI", i_quay)
    b = Board("BVB", url, effective=_effective(" ".join(lines[:3])),
              product={"quay": "Tien gui, tiet kiem thong thuong, lai cuoi ky", "online": "Tien gui truc tuyen, lai cuoi ky"})
    # Muc I: 3 cot (cuoi ky, thang, truoc); muc V: 4 cot (cuoi ky, quy, thang, truoc); muc VI ben phai: 2 cot.
    for channel, (lo, hi), width in (("online", (i_online, i_quay), {3}), ("quay", (i_quay, i_end), {4})):
        for term, toks in _term_rows(lines, lo, hi, widths=width).items():
            b.put(channel, term, _rate(toks[0]))
    return b


def _links(html: str, base: str, pattern: str) -> list[str]:
    out = []
    for href in re.findall(r'href="([^"]+)"', html):
        url = urljoin(base, unescape(href))
        if re.search(pattern, url, re.IGNORECASE) and url not in out:
            out.append(url)
    return out


def _groups(line: str) -> list[tuple[int, list[float]]]:
    return [(int(m.group(1)), [float(x) for x in m.group(2).split()])
            for m in re.finditer(r"(\d{1,2}) ?tháng((?: \d{1,2}\.\d{2})+)", line)]


def _hdb() -> Board:
    page = "https://hdbank.com.vn/vi/personal/cong-cu/interest-rate"
    links = _links(_render(page), page, r"/document/\d{8}BIEULAISUATTIENGUIKHACHHANGCANHAN.*\.pdf$")
    if not links:
        raise RuntimeError("HDB: khong thay link bieu lai suat tien gui KHCN")

    def stamp(u):  # 20261910 = 19/10/2026 (YYYYDDMM), 20261004 = 10/04/2026
        y, a, b = re.search(r"/(\d{4})(\d{2})(\d{2})BIEU", u).groups()
        return f"{y}-{b}-{a}" if int(b) <= 12 else f"{y}-{a}-{b}"
    url = max(links, key=stamp)
    lines = _pdf_lines(_get(url).content)
    b = Board("HDB", url, effective=stamp(url),
              product={"quay": "TK co ky han thong thuong, cuoi ky", "online": "Tiet kiem Online VND, cuoi ky"})
    q0 = _find(lines, r"^a\. Tiết kiệm có kỳ hạn thông thường")
    q1 = _find(lines, r"^b\. Tiết kiệm không kỳ hạn", q0)
    for term, toks in _term_rows(lines, q0, q1).items():
        b.put("quay", term, _rate(toks[0]))
    i12 = _find(lines, r"^12 tháng loại 1", q0)
    loai2 = next(ln for ln in lines[i12 + 1:q1] if ln.startswith("loại 2"))
    b.put("quay", 12, _rate(loai2.split()[2]))
    o0 = _find(lines, r"^c\. Tiết kiệm Online VNĐ")
    o1 = _find(lines, r"^d\. ", o0)
    for term, toks in _term_rows(lines, o0, o1).items():
        b.put("online", term, _rate(toks[0]))
    return b


def _shb() -> Board:
    page = "https://www.shb.com.vn/category/lien-ket-nhanh/lai-suat/"
    links = _links(_render(page), page, r"BIEU-LS-HDV-VND-KHCN.*\.pdf$")
    if not links:
        raise RuntimeError("SHB: khong thay link BIEU-LS-HDV-VND-KHCN")
    url = links[0]
    lines = _pdf_lines(_get(url).content)
    b = Board("SHB", url, tier={"quay": "< 2 ty"},
              product={"quay": "Tiet kiem bac thang, cuoi ky", "online": "Tien gui tiet kiem online, cuoi ky"})
    s1 = _find(lines, r"^1\. Biểu lãi suất tiết kiệm bậc thang")
    s4 = _find(lines, r"^4\. Biểu lãi suất Tiền gửi tiết kiệm online", s1)
    b.effective = _effective(lines[s1])
    for channel, start, row_rx in (("quay", s1, r"^Cuối tỷ "), ("online", s4, r"^Cuối kỳ ")):
        head = next(ln for ln in lines[start:start + 8] if re.search(r"1 ?T 2 ?T 3 ?T", ln))
        terms = [int(t) for t in re.findall(r"(\d{1,2}) ?T\b", head)]
        row = lines[_find(lines, row_rx, start)]
        values = re.findall(r"\d{1,2}\.\d{2}", row)[-len(terms):]   # quay: bo KKH, 1-3 tuan o dau dong
        if len(values) != len(terms):
            raise RuntimeError(f"SHB {channel}: {len(terms)} ky han, {len(values)} so")
        for t, v in zip(terms, values):
            b.put(channel, t, float(v))
    return b


def _nvb() -> Board:
    page = "https://www.ncb-bank.vn/vi/lai-suat-tien-gui"
    links = _links(_render(page), page, r"/InterestRates/.*Bieu.*lai.*suat.*niem.*yet.*\.pdf$")
    if not links:
        raise RuntimeError("NVB: khong thay link bieu lai suat niem yet")
    url = max(links, key=lambda u: _date(u.split("hieu")[-1]))
    lines = _pdf_lines(_get(url).content)
    b = Board("NVB", url, effective=_effective(" ".join(lines[:3])),
              product={"quay": "Tiet kiem truyen thong, cuoi ky", "online": "Tiet kiem truyen thong online, cuoi ky"})
    q0 = _find(lines, r"^Tiếtkiệmtruyềnthống")
    q1 = _find(lines, r"^TiếtkiệmAn Phát", q0)
    for ln in lines[q0:q1]:
        for term, nums in _groups(ln):
            b.cells.setdefault(("quay", term), nums[0]) if term in TERMS else None
    o0 = _find(lines, r"tiếtkiệmOnline", q1)
    o0 = _find(lines, r"TIẾTKIỆM TRUYỀN THỐNG", o0)
    for ln in lines[o0:o0 + 40]:
        g = _groups(ln)
        if len(g) == 2:                 # cot trai An Phu, cot phai truyen thong
            term, nums = g[1]
        elif len(g) == 1 and re.match(r"^\d{1,2} ?tháng \d{1,2} ?tháng", ln):
            term, nums = g[0]           # An Phu trong o, chi con truyen thong
        else:
            continue
        if term in TERMS:
            b.cells.setdefault(("online", term), nums[0])
    return b


def _stb() -> Board:
    url = ("https://www.sacombank.com.vn/content/dam/sacombank/files/cong-cu/lai-suat/tien-gui/khcn/"
           "SACOMBANK_LAISUATNIEMYETTAIQUAY_KHCN_VIE.pdf")
    lines = _pdf_lines(_get(url).content)
    b = Board("STB", url, effective=_effective(" ".join(lines[:4])), tier={"quay": "< 500 trieu", "online": "< 50 trieu"},
              product={"quay": "TK truyen thong, lai cuoi ky", "online": "Tien gui truc tuyen, lai cuoi ky"})
    a = _find(lines, r"^I\. TIẾT KIỆM CÓ KỲ HẠN TRUYỀN THỐNG")
    a_end = _find(lines, r"^I ?I", a + 1)
    bb = _find(lines, r"^B\. ÁP DỤNG CHO TÀI KHOẢN MỞ TRỰC TUYẾN")
    bb_end = _find(lines, r"^G ?h ?i c ?h ?ú", bb)
    for channel, lo, hi in (("quay", a, a_end), ("online", bb, bb_end)):
        for i in range(lo, hi):
            ln = lines[i]
            m = re.match(r"^(\d{1,2}) tháng (\d{1,2}\.\d{2})%", ln)
            if m:
                b.cells.setdefault((channel, int(m.group(1))), float(m.group(2)))
                continue
            m = re.match(r"^Từ (\d{1,2}) đến$", ln)
            if m and i + 1 < hi:
                first = re.match(r"^(\d{1,2}\.\d{2})%", lines[i + 1])
                if first:
                    b.cells.setdefault((channel, int(m.group(1))), float(first.group(1)))
    b.cells = {k: v for k, v in b.cells.items() if k[1] in TERMS}
    return b


def _tpb() -> Board:
    page = "https://tpb.vn/cong-cu-tinh-toan/lai-suat"
    links = [u for u in _links(_render(page), page, r"BieuLaiSuat.*\.pdf") if "LSCS" not in u]
    if not links:
        raise RuntimeError("TPB: khong thay link BieuLaiSuat*.pdf")
    url = links[0].split("&CVID")[0]
    content = _get(url).content
    lines = _pdf_lines(content)
    b = Board("TPB", url, effective=_effective(" ".join(lines[:4])),
              product={"quay": "TK thuong linh lai cuoi ky (12T, 24T: Bao An Loc cuoi ky)", "online": "TK Dien tu"})
    import pdfplumber
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        table = max(pdf.pages[0].extract_tables(), key=len)
    sub = [(c or "").replace("\n", " ") for c in table[1]]
    c_thuong = sub.index("TK thường")
    c_baoan = sub.index("Cuối kỳ")
    for row in table[2:]:
        row = [(c or "").replace("\n", " ").strip() for c in row]
        lab = next((i for i, c in enumerate(row) if c), None)
        if lab is None or lab > 1:
            continue
        term = _term(row[lab]) if re.fullmatch(r"\d{1,2} tháng", row[lab]) else None
        if term not in TERMS:
            continue
        shift = lab                      # nua so dong bi lech mot o sang phai (nhan o cot 1)
        value = _rate(row[c_thuong + shift]) if c_thuong + shift < len(row) else None
        if value is None and term in (12, 24):
            value = _rate(row[c_baoan + shift]) if c_baoan + shift < len(row) else None
        b.put("quay", term, value)
    s = _find(lines, r"^1\.1\. Tiết kiệm Điện tử")
    head = next(ln for ln in lines[s:s + 4] if ln.startswith("KỲ HẠN"))
    row = next(ln for ln in lines[s:s + 6] if ln.startswith("TK Điện tử"))
    labels = re.findall(r"(\d{1,2}) (tuần|tháng)", head)
    values = re.findall(r"\d{1,2}\.\d{2}", row)
    if len(labels) != len(values):
        raise RuntimeError(f"TPB online: {len(labels)} ky han, {len(values)} so")
    for (n, unit), v in zip(labels, values):
        if unit == "tháng":
            b.put("online", int(n), float(v))
    return b


def _tcb() -> Board:
    base = ("https://techcombank.com/content/dam/techcombank/public-site/documents/"
            "tcb-bieu-lai-suat-tien-gui-tiet-kiem-tien-gui-co-ky-han-{}.pdf")
    today = datetime.now(VN_TZ).date()
    url = None
    for back in range(0, 121):
        candidate = base.format((today - timedelta(days=back)).strftime("%Y%m%d"))
        r = _s().head(candidate, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code == 200 and "pdf" in r.headers.get("content-type", ""):
            url = candidate
            break
    if url is None:
        raise RuntimeError("TCB: khong thay bieu nao trong 120 ngay")
    lines = _pdf_lines(_get(url).content)
    stamp = url[-12:-4]
    b = Board("TCB", url, effective=f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:]}",
              tier={"quay": "KH thuong < 1 ty", "online": "KH thuong < 1 ty"},
              product={"quay": "Tiet kiem Phat Loc tai quay", "online": "Tien gui Phat Loc Online"})
    q = _find(lines, r"^TIẾT KIỆM PHÁT LỘC TẠI QUẦY")
    o = _find(lines, r"^TIỀN GỬI PHÁT LỘC ONLINE", q)
    end = _find(lines, r"^TIỀN GỬI RÚT GỐC LINH HOẠT", o)
    for channel, lo, hi in (("quay", q, o), ("online", o, end)):
        for ln in lines[lo:hi]:
            m = re.match(r"^(\d{1,2})M((?: \d{1,2}\.\d{2}){12})$", ln)
            if m:
                b.put(channel, int(m.group(1)), float(m.group(2).split()[-1]))
    return b


def _lpb() -> Board:
    api = "https://lpbank.com.vn/api/content-service/public/interest-rate/findAll"
    b = Board("LPB", "https://lpbank.com.vn/ca-nhan/lai-suat",
              product={"quay": "Tiet kiem thong thuong tai quay (TK_TTQ_KHCN)", "online": "Tiet kiem Online (TK_ONLINE)"})
    dates = []
    for category, channel in (("TK_TTQ_KHCN", "quay"), ("TK_ONLINE", "online")):
        r = _s().post(api, json={"category": category}, timeout=TIMEOUT,
                      headers={"Accept": "application/json", "Referer": b.url})
        r.raise_for_status()
        data = r.json().get("data") or []
        for row in data:
            if row.get("recordType") == "DATA" and row.get("groupInterest") == "LSHD_VND":
                b.put(channel, _term(row.get("term", "")), row.get("endValue"))
                if row.get("effectiveDate"):
                    dates.append(row["effectiveDate"])
    if dates:   # '2026-10-18T17:00:00.000+00:00' = 00:00 ngay 19/10 gio Viet Nam
        stamp = datetime.fromisoformat(max(dates).replace("Z", "+00:00")).astimezone(VN_TZ)
        b.effective = stamp.strftime("%Y-%m-%d")
    return b


def _vib() -> Board:
    url = "https://www.vib.com.vn/vn/tiet-kiem"
    soup = BeautifulSoup(_render(url, 20000), "lxml")
    b = Board("VIB", url, tier={"quay": "10 - 300 trieu", "online": "2 - 300 trieu"},
              product={"quay": "Tien gui tai quay (TDE)", "online": "Tien gui truc tuyen"})
    for div_id, channel in (("saving-table-TDE", "quay"), ("saving-table-term", "online")):
        node = soup.find(id=div_id)
        if node is None:
            raise RuntimeError(f"VIB: khong thay {div_id}")
        text = node.get_text(" ", strip=True)
        body = text[text.find("trở lên"):]        # bo hang tieu de (danh sach ky han, cac bac tien)
        for m in re.finditer(r"(?<![<\d])(\d{1,2}) tháng(?: Nổi bật)? (\d{1,2}\.\d{2})%", body):
            if (channel, int(m.group(1))) not in b.cells:
                b.put(channel, int(m.group(1)), float(m.group(2)))
    return b


def _bab() -> Board:
    url = "https://www.baca-bank.vn/SitePages/website/lai-xuat.aspx?ac=L%25u00e3i%252520su%25u1ea5t&s=LX"
    soup = BeautifulSoup(_html(url), "lxml")
    data = {i.get("name"): i.get("value", "") for i in soup.find_all("input", type="hidden") if i.get("name")}
    select = next(s for s in soup.find_all("select") if s.get("name", "").endswith("DDL_LS"))
    data[select["name"]] = "VND|VNĐ"
    data["__EVENTTARGET"] = select["name"]
    r = _s().post(url, data=data, timeout=TIMEOUT)
    r.raise_for_status()
    page = BeautifulSoup(r.text, "lxml")
    b = Board("BAB", url, product={"quay": "Tiet kiem, linh lai cuoi ky"})
    for table in page.find_all("table"):
        grid = _grid(table)
        if len(grid) < 3 or not any("cuối kỳ" in c for c in grid[1]):
            continue
        b.effective = _effective(" ".join(grid[0]))
        col = next(i for i, c in enumerate(grid[1]) if "cuối kỳ" in c)
        for row in grid[2:]:
            if col < len(row):
                b.put("quay", _term(row[0]), _rate(row[col]))
    return b


def _eib() -> Board:
    page = "https://eximbank.com.vn/lai-suat-tiet-kiem"
    # href de nguyen dau cach: ".../files/TB LSHD VND KHBL hieu luc tu ngay 31102026.pdf"
    links = _links(_render(page, 20000), page, r"TB(?: |%20)LSHD(?: |%20)VND(?: |%20)KHBL.*\d{8}\.pdf$")
    if not links:
        raise RuntimeError("EIB: khong thay link 'TB LSHD VND KHBL hieu luc tu ngay ...'")

    def stamp(u):
        d = re.search(r"(\d{8})\.pdf$", u).group(1)
        return f"{d[4:]}-{d[2:4]}-{d[:2]}"
    url = max(links, key=stamp).replace(" ", "%20")
    content = _get(url).content
    lines = _pdf_lines(content)
    b = Board("EIB", url, effective=stamp(url), tier={"online": "KH chua phan hang, thu 2 - thu 6"},
              product={"quay": "Tiet kiem, tien gui ca nhan (A.1), lai cuoi ky", "online": "Tien gui Online (A.6)"})
    a1 = _find(lines, r"^A\.1 ")
    a2 = _find(lines, r"^A\.2 ", a1)
    for term, toks in _term_rows(lines, a1, a2).items():
        b.put("quay", term, _rate(toks[-1]))
    import pdfplumber
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for p in pdf.pages:
            text = p.extract_text() or ""
            if "A.6" not in text:
                continue
            words = p.extract_words()
            # dong tieu de dau tien sau 'thu 2 den thu 6' va dong 'Lai cuoi ky' ngay duoi no
            weekday = next(w for w in words if w["text"] == "6:" or "thứ 6" in w["text"]) if any(
                w["text"] == "6:" for w in words) else None
            top0 = weekday["top"] if weekday else 0
            rows: dict[int, list] = {}
            for w in words:
                if w["top"] > top0:
                    rows.setdefault(round(w["top"]), []).append(w)
            ordered = [rows[k] for k in sorted(rows)]
            head = next(r for r in ordered if any(w["text"] == "(tháng)" for w in r))
            terms = []
            for i, w in enumerate(head):
                if re.fullmatch(r"\d{1,2}", w["text"]) and i + 1 < len(head) and head[i + 1]["text"] == "T":
                    terms.append((int(w["text"]), (w["x0"] + head[i + 1]["x1"]) / 2))
            row = next(r for r in ordered if r[0]["top"] > head[0]["top"] and r[0]["text"] == "Lãi"
                       and len(r) > 2 and r[1]["text"] == "cuối")
            values = [((w["x0"] + w["x1"]) / 2, _rate(w["text"])) for w in row if re.fullmatch(r"\d{1,2},\d{1,2}", w["text"])]
            if not terms or not values:
                raise RuntimeError("EIB online: khong doc duoc bang A.6")
            for term, x in terms:
                b.put("online", term, min(values, key=lambda v: abs(v[0] - x))[1])
            break
    return b


# NH chua doc tu dong (kiem 07/11/2026); deposit_tiers.read() bu bang anh chup doc tay roi blog Techcombank.
GAPS = {
    "MBB": "bieu KHCN la PDF tren webcdn.mbbank.com.vn; CDN Akamai tra 'Access Denied' cho moi request ngoai trinh "
           "duyet, fetch tu trang /Fee bi chan khac nguon (CORS). Can tai qua DevTools (Network.getResponseBody).",
    "SSB": "seabank.com.vn/cong-cu-tien-ich/bieu-lai-suat: Edge headless treo qua 180 giay; so nam trong phan hoi "
           "server action (POST), chua dung lai duoc.",
}


BANKS = {
    "VCB": _vcb, "CTG": _ctg, "BID": _bid, "ACB": _acb, "MSB": _msb, "PGB": _pgb, "NAB": _nab,
    "OCB": _ocb, "VPB": _vpb, "BVB": _bvb, "HDB": _hdb, "SHB": _shb, "NVB": _nvb, "STB": _stb,
    "TPB": _tpb, "TCB": _tcb, "LPB": _lpb, "VIB": _vib, "BAB": _bab, "EIB": _eib,
}


# ---------------------------------------------------------------------------
# kiem dinh, ghi file

def check(board: Board) -> list[str]:
    problems = []
    if len(board.cells) < 4:
        problems.append(f"chi doc duoc {len(board.cells)} o")
    for (channel, term), rate in board.cells.items():
        if not 0.1 <= rate <= 12.0:
            problems.append(f"{channel} {term}T = {rate} ngoai khoang [0.1, 12]")
        if 1 <= term <= 5 and rate > CAP_1_5M + 1e-9:
            problems.append(f"{channel} {term}T = {rate} vuot tran NHNN {CAP_1_5M} (doc nham cot?)")
    return problems


def fetch(tickers=None) -> tuple[dict, dict]:
    boards, errors = {}, {}
    for ticker in tickers or BANKS:
        try:
            board = BANKS[ticker]()
            problems = check(board)
            if problems:
                errors[ticker] = "; ".join(problems)
            else:
                boards[ticker] = board
        except Exception as exc:
            errors[ticker] = f"{type(exc).__name__}: {exc}"[:300]
    return boards, errors


def read_master() -> list[dict]:
    if not MASTER.exists():
        return []
    with io.open(MASTER, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _key(row: dict) -> tuple:
    return (row["date"], row["ticker"], row["channel"], str(row["term_months"]))


def run(tickers=None) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    date = now.astimezone(VN_TZ).strftime("%Y-%m-%d")
    boards, errors = fetch(tickers)
    if not boards:
        raise RuntimeError(f"khong doc duoc NH nao: {errors}")
    new = []
    for board in boards.values():
        for (channel, term), rate in sorted(board.cells.items()):
            new.append({"date": date, "effective_date": board.effective, "ticker": board.ticker,
                        "term_months": str(term), "channel": channel, "rate_percent": f"{rate:g}",
                        "tier": board.tier.get(channel, "thap nhat"), "product": board.product.get(channel, ""),
                        "source": SOURCE_NAME, "source_url": board.url, "source_updated_at": board.updated,
                        "retrieved_at_utc": now.isoformat()})
    replace = {(date, t) for t in boards}
    kept = [r for r in read_master() if (r["date"], r["ticker"]) not in replace]
    rows = sorted(kept + new, key=lambda r: (r["date"], r["ticker"], r["channel"], int(r["term_months"])))
    with io.open(MASTER, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\r\n")
        w.writeheader()
        w.writerows(rows)
    with open("crawl_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{now.isoformat()}] deposit_official: {len(boards)} NH, {len(new)} o -> {MASTER}; "
                f"loi={errors or 'none'}\n")
    return {"date": date, "banks_ok": sorted(boards), "cells": len(new), "errors": errors}


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    picked = [a.upper() for a in sys.argv[1:]]
    if picked:
        boards, errors = fetch(picked)
        for t, b in boards.items():
            print(f"== {t} hieu luc {b.effective or '?'} | {b.url[:110]}")
            for channel in ("quay", "online"):
                print(f"   {channel:6s}", "  ".join(f"{term}T {b.cells[(channel, term)]:.2f}"
                                                 for term in TERMS if (channel, term) in b.cells))
        for t, e in errors.items():
            print(f"!! {t}: {e}")
    else:
        print(run())
