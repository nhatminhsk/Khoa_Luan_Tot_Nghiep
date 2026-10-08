from __future__ import annotations

import csv
import io
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUT = Path("data/loan_rates")
MASTER = OUT / "loan_industry_avg.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "vi,en;q=0.9",
}

BASE = "https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/tai-chinh"
YEAR_PAGES = {
    2024: BASE + "/72108/lai-suat-cho-vay-lai-suat-tien-gui-ngan-hang-moi-nhat",
    2025: BASE + "/81092/lai-suat-cho-vay-lai-suat-tien-gui-ngan-hang-moi-nhat-nam-2025",
    2026: BASE + "/106712/thong-tin-lai-suat-ngan-hang-nam-2026-lai-suat-tien-gui-lai-suat-cho-vay-bao-nhieu",
}

MAX_ATTEMPTS = 5

HEADER_RE = re.compile(r"THÁNG\s*(\d{1,2})\s*:|ngân hàng tháng\s*(\d{1,2})/(\d{4})")

NUM = r"\d+(?:[.,]\d+)?"
FIG = r"(" + NUM + r")\s*(?:[-–]\s*(" + NUM + r"))?\s*%/năm"
GAP = r"[^%]{0,60}?"

DEPOSIT_TAILS = {
    "deposit_0_to_1m": "đối với tiền gửi không kỳ hạn",
    "deposit_1_to_6m": "kỳ hạn từ 1 tháng đến dưới 6 tháng",
    "deposit_6_to_12m": "kỳ hạn từ 6 tháng đến 12 tháng",
    "deposit_12_to_24m": "kỳ hạn từ trên 12 tháng đến 24 tháng",
    "deposit_over_24m": "kỳ hạn trên 24 tháng",
}
LOAN_RE = re.compile(r"cho vay mới và cũ còn dư nợ ở mức\s*" + FIG)
PRIORITY_RE = re.compile(r"lĩnh vực ưu tiên\s*(?:ở mức\s*)?khoảng\s*" + FIG)

FIELDS = ["deposit_0_to_1m", "deposit_1_to_6m", "deposit_6_to_12m",
          "deposit_12_to_24m", "deposit_over_24m", "loan_vnd_avg",
          "loan_priority_short_term"]

# ---------------------------------------------------------------------------
# NGUON GOC (tu 07/10/2026 la nguon chinh cho thang moi): ban "Developments of interest
# rates applied by credit institutions (<thang> <nam>)" NHNN dang moi thang tren sbv.gov.vn,
# so lieu nam trong file PDF dinh kem (tieng Anh). Thang 8/2026 dang ngay 18/09.
#
# Vi sao doi: thuvienphapluat (YEAR_PAGES) dung o thang 6/2026, nen suot thang 9 crawler bao
# "no new month" ma khong loi gi trong khi NHNN da dang thang 7 va 8. Ban chep lai cung co the
# sai: VNBA chep thang 8 thanh lai cho vay uu tien 3,9% trong khi ban goc NHNN ghi 4,0%.
# YEAR_PAGES giu lai cho --selfcheck va lich su 2024-2025.
#
# BAY:
#   - Slug trang KHONG deu: tieu de co ngoac "(June 2026)" -> slug co gach cuoi "june-2026-";
#     tieu de khong ngoac "July 2026" -> "july-2026". Thu ca hai (SBV_TAILS).
#   - Moi thang mot nguoi dich, cau chu doi: thang 7 viet "mobilization interest rates",
#     "0.1% - 0.2%", "1month", va bo "p.a." o ky han tren 24 thang. Regex phai chiu ca hai kieu.
#   - Do nhanh ~10 request lien tiep thi sbv.gov.vn chan IP (403 ca trang chu) mot luc lau.
#     Vi vay chi do thang ke tiep sau thang cuoi trong file, nghi SBV_PAUSE giay giua cac lan,
#     va gap 403 thi dung ngay, bao "blocked" chu khong thu tiep.
# ---------------------------------------------------------------------------
SBV_ARTICLE = ("https://sbv.gov.vn/en/w/developments-of-interest-rates-applied-by-credit-"
               "institutions-{month}-{year}{tail}")
SBV_TAILS = ("-", "")
SBV_HOST = "https://sbv.gov.vn"
SBV_PAUSE = 4
MONTHS_EN = ["january", "february", "march", "april", "may", "june", "july", "august",
             "september", "october", "november", "december"]
SBV_PDF_RE = re.compile(r'href="(/documents/20117/[^"]+?\.pdf[^"]*)"')

EN_NUM = r"\d+(?:\.\d+)?"
EN_FIG = r"(" + EN_NUM + r")\s*%?\s*(?:[-–—]\s*(" + EN_NUM + r"))?\s*%\s*(?:p\.\s*a\.)?"
EN_MONTH = r"\s*-?\s*month"
EN_DEPOSIT_TAILS = {
    "deposit_0_to_1m": r"for demand and below 1" + EN_MONTH,
    "deposit_1_to_6m": r"for 1" + EN_MONTH + r" to below 6" + EN_MONTH,
    "deposit_6_to_12m": r"for 6" + EN_MONTH + r" to (?:below )?12" + EN_MONTH,
    "deposit_12_to_24m": r"for (?:over )?12" + EN_MONTH + r"(?: plus)? to 24" + EN_MONTH,
    "deposit_over_24m": r"for (?:over )?24" + EN_MONTH,
}
EN_LOAN_RE = re.compile(r"average lending interest rates? (?:were|was)\s*(?:between|at|around|about|from)?\s*"
                        + EN_FIG + r"\s*for new loans", re.I)
EN_PRIORITY_RE = re.compile(r"priority sectors?(?: and areas)?\s*(?:was|were)\s*"
                            r"(?:at|about|around|approximately)?\s*" + EN_FIG, re.I)


def safe_fetch(label, func):
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return func()
        except Exception as exc:
            last_error = type(exc).__name__ + ": " + str(exc)
            pause = min(60, 10 * (2 ** (attempt - 1)))
            print(label + ": attempt " + str(attempt) + "/" + str(MAX_ATTEMPTS)
                  + " failed (" + last_error + "); waiting " + str(pause) + "s")
            time.sleep(pause)
    raise RuntimeError(label + ": failed after " + str(MAX_ATTEMPTS) + " attempts: " + str(last_error))


def vn_num(s):
    return None if s is None else float(s.replace(",", "."))


def fmt(x):
    return "" if x is None else ("%.1f" % x if x == int(x) else "%g" % x)


def pair(m):
    if not m:
        return None, None
    lo = vn_num(m.group(1))
    hi = vn_num(m.group(2)) if m.group(2) else lo
    return lo, hi


def fetch_year(year):
    url = YEAR_PAGES[year]

    def _do():
        r = requests.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return r.text

    return BeautifulSoup(safe_fetch("fetch tvpl " + str(year), _do), "lxml").get_text(" ", strip=True), url


def split_months(text, default_year):
    hits = list(HEADER_RE.finditer(text))
    for i, h in enumerate(hits):
        month = int(h.group(1) or h.group(2))
        year = int(h.group(3)) if h.group(3) else default_year
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        yield year, month, text[h.end():end]


def parse_block(block):
    deposit_part = block.split("Lãi suất tiền gửi USD")[0]

    loan_part = block
    anchor = loan_part.find("cho vay mới và cũ")
    if anchor >= 0:
        for marker in ("Lãi suất cho vay USD", "Lãi suất USD"):
            idx = loan_part.find(marker, anchor)
            if idx > 0:
                loan_part = loan_part[:idx]
                break

    out = {}
    for field, tail in DEPOSIT_TAILS.items():
        out[field] = pair(re.search(FIG + GAP + re.escape(tail), deposit_part))
    out["loan_vnd_avg"] = pair(LOAN_RE.search(loan_part))
    out["loan_priority_short_term"] = pair(PRIORITY_RE.search(loan_part))
    return out


def parse_sbv_text(text):
    """Ban tieng Anh cua NHNN -> cung dang ket qua voi parse_block()."""
    text = re.sub(r"\s+", " ", text.replace(" ", " "))
    usd = text.find("in USD")  # doan VND dung truoc lan dau nhac USD (tien gui USD)
    deposit_part = text[:usd] if usd > 0 else text
    m = re.search(r"2\.\s*Lending", text)
    loan_part = text[m.start():] if m else text
    usd = loan_part.find("in USD")
    loan_part = loan_part[:usd] if usd > 0 else loan_part

    out = {}
    for field, tail in EN_DEPOSIT_TAILS.items():
        out[field] = pair(re.search(EN_FIG + r"\s*" + tail, deposit_part, re.I))
    out["loan_vnd_avg"] = pair(EN_LOAN_RE.search(loan_part))
    out["loan_priority_short_term"] = pair(EN_PRIORITY_RE.search(loan_part))
    return out


def sbv_pdf_text(content):
    import pymupdf

    with pymupdf.open(stream=content, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


def fetch_sbv_month(year, month, session):
    """Trang + PDF cua mot thang. Tra (status, vals, url, title); status: ok / missing / blocked / bad."""
    for tail in SBV_TAILS:
        url = SBV_ARTICLE.format(month=MONTHS_EN[month - 1], year=year, tail=tail)
        r = session.get(url, timeout=30)
        time.sleep(SBV_PAUSE)
        if r.status_code == 403:
            return "blocked", None, url, ""
        if r.status_code == 404:
            continue
        r.raise_for_status()
        link = SBV_PDF_RE.search(r.text)
        if not link:
            return "bad", None, url, "trang khong co file PDF dinh kem"
        title = BeautifulSoup(r.text, "lxml").title
        title = (title.get_text(strip=True) if title else "").split(" - Ngân hàng")[0]
        pdf = session.get(SBV_HOST + link.group(1).replace("&amp;", "&"), timeout=60)
        time.sleep(SBV_PAUSE)
        if pdf.status_code == 403:
            return "blocked", None, url, title
        if b"%PDF" not in pdf.content[:1024]:
            return "bad", None, url, "file dinh kem khong phai PDF (HTTP %d)" % pdf.status_code
        text = sbv_pdf_text(pdf.content)
        # chan file nham thang: tieu de trong PDF phai nhac dung thang/nam dang tim
        if not re.search(MONTHS_EN[month - 1] + r"\s+" + str(year), text, re.I):
            return "bad", None, url, "PDF khong ghi thang %d/%d" % (month, year)
        return "ok", parse_sbv_text(text), url, title
    return "missing", None, "", ""


def next_months(last_date, today=None):
    """Cac thang sau thang cuoi trong file, toi thang truoc thang hien tai."""
    today = today or datetime.now(timezone.utc).date()
    y, m = int(last_date[:4]), int(last_date[5:7])
    out = []
    while True:
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        if (y, m) >= (today.year, today.month):
            return out
        out.append((y, m))


def scrape_sbv(months):
    """Thang nao NHNN da dang. Dung o thang dau tien chua co (thang sau khong the co truoc)."""
    session = requests.Session()
    session.headers.update(HEADERS)
    found, status = {}, []
    for y, m in months:
        st, vals, url, title = fetch_sbv_month(y, m, session)
        status.append("%04d-%02d:%s" % (y, m, st))
        if st != "ok":
            break
        found["%04d-%02d-01" % (y, m)] = (vals, url, "NHNN (sbv.gov.vn) - " + title)
    return found, status


def read_master():
    if not MASTER.exists():
        return None, []
    with io.open(MASTER, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    return rows[0], [r for r in rows[1:] if r and r[0].strip()]


def scrape(years):
    found = {}
    for year in years:
        text, url = fetch_year(year)
        for y, mth, block in split_months(text, year):
            found["%04d-%02d-01" % (y, mth)] = (parse_block(block), url,
                                                 "NHNN - dien bien lai suat TCTD thang %d/%d" % (mth, y))
        time.sleep(1)
    return found


def blank_cells(row, idx):
    """Ten cac o so lieu con de trong trong mot dong da co."""
    out = []
    for field in FIELDS:
        for bound in ("min", "max"):
            if not row[idx[field + "_" + bound]].strip():
                out.append(field + "_" + bound)
    return out


def run(years=None) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    log_path = Path("crawl_log.txt")
    years = years or [max(YEAR_PAGES)]

    header, existing = read_master()
    if header is None:
        raise RuntimeError(str(MASTER) + " missing -- refusing to recreate it from scratch")
    idx = dict((name, i) for i, name in enumerate(header))
    by_date = dict((r[0], r) for r in existing)

    # Nguon goc NHNN truoc (chi cac thang sau thang cuoi trong file), roi ban chep lai cua
    # thuvienphapluat de bu o trong / bao lech. Trung thang thi ban NHNN thang.
    sbv_found, sbv_status = scrape_sbv(next_months(max(by_date)))
    found = scrape(years)
    found.update(sbv_found)
    added, incomplete, filled, conflicts = [], [], [], []

    for date in sorted(found):
        vals, url, title = found[date]
        row = by_date.get(date)

        if row is not None:
            # Dong da co: CHI dien o trong, khong bao gio ghi de o da co so.
            # O da co ma lech voi nguon thi bao conflict de nguoi kiem tra.
            touched = False
            for field in FIELDS:
                for bound, got in zip(("min", "max"), vals[field]):
                    col = idx[field + "_" + bound]
                    new, cur = fmt(got), row[col].strip()
                    if not cur:
                        if new:
                            row[col] = new
                            filled.append(date + " " + field + "_" + bound + "=" + new)
                            touched = True
                    elif new and cur != new:
                        conflicts.append(date + " " + field + "_" + bound
                                         + ": file=" + cur + " nguon=" + new)
            if touched:
                row[idx["retrieved_at_utc"]] = retrieved_at
            continue

        if vals["loan_vnd_avg"] == (None, None):
            incomplete.append(date)
            continue
        new_row = [date, url, title]
        for field in FIELDS:
            lo, hi = vals[field]
            new_row += [fmt(lo), fmt(hi)]
        new_row.append(retrieved_at)
        added.append(new_row)

    # Quet TOAN BO file (khong chi thang vua scrape) de bat o trong con sot lai.
    # Day la buoc bat duoc ca thang ma nguon chua dang, vi du 2026-07.
    all_rows = sorted(existing + added, key=lambda r: r[0])
    still_blank = dict((r[0], blank_cells(r, idx)) for r in all_rows if blank_cells(r, idx))

    skipped = len(found) - len(added) - len(incomplete)
    summary = {"added": len(added), "months": [r[0] for r in added], "skipped": skipped,
               "incomplete": incomplete, "filled": filled, "conflicts": conflicts,
               "still_blank": still_blank, "sbv": sbv_status}

    if not added and not filled:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("[" + retrieved_at + "] loan_rates: no new month (" + str(skipped)
                    + " already recorded, incomplete=" + str(incomplete or "none")
                    + ", still_blank=" + str(sorted(still_blank) or "none")
                    + ", conflicts=" + str(len(conflicts))
                    + ", sbv=" + str(sbv_status or "none")
                    + "), file left untouched\n")
        summary["written"] = False
        return summary

    with io.open(MASTER, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(header)
        w.writerows(all_rows)

    with open(log_path, "a", encoding="utf-8") as f:
        f.write("[" + retrieved_at + "] loan_rates: added " + str(summary["months"])
                + ", filled " + str(len(filled)) + " o trong " + str(filled or "")
                + ", still_blank=" + str(sorted(still_blank) or "none")
                + ", conflicts=" + str(len(conflicts))
                + ", sbv=" + str(sbv_status or "none")
                + " -> " + str(MASTER) + "\n")
    summary["written"] = True
    return summary


def parser_selfcheck(years=None):
    years = years or sorted(YEAR_PAGES)
    header, existing = read_master()
    idx = dict((name, i) for i, name in enumerate(header))
    found = scrape(years)

    checked = mismatches = 0
    problems = []
    for row in existing:
        if row[0] not in found:
            continue
        vals = found[row[0]][0]
        for field in FIELDS:
            for bound, got in zip(("min", "max"), vals[field]):
                stored = row[idx[field + "_" + bound]].strip()
                parsed = fmt(got)
                checked += 1
                if stored != parsed:
                    mismatches += 1
                    problems.append("%s %s_%s: file=%r parser=%r"
                                    % (row[0], field, bound, stored, parsed))
    return {"checked": checked, "mismatches": mismatches, "problems": problems}


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--selfcheck" in sys.argv:
        result = parser_selfcheck()
        print("so gia tri doi chieu:", result["checked"])
        print("so sai lech:", result["mismatches"])
        for p in result["problems"][:40]:
            print("  ", p)
    else:
        r = run()
        print("NHNN (sbv.gov.vn):", r["sbv"] or "khong co thang nao can do")
        print("them thang moi:", r["months"] or "khong")
        print("dien o trong :", len(r["filled"]))
        for x in r["filled"][:40]:
            print("   ", x)
        if r["conflicts"]:
            print("LECH so voi nguon (KHONG ghi de):", len(r["conflicts"]))
            for x in r["conflicts"][:40]:
                print("   ", x)
        if r["still_blank"]:
            print("VAN CON O TRONG:")
            for d in sorted(r["still_blank"]):
                print("   ", d, "->", ", ".join(r["still_blank"][d]))
        else:
            print("khong con o trong nao")
