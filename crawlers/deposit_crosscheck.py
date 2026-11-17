from __future__ import annotations

import csv
import io
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUT = Path("data/interest_rates")
MASTER = OUT / "deposit_crosscheck_daily.csv"
DEPOSIT = OUT / "deposit_daily.csv"
SITEMAP = "https://cafef.vn/sitemap.xml"
SOURCE_NAME = "cafef_daily"
TERM = 12
CHANNEL = "online"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "vi,en;q=0.9",
}
MAX_ATTEMPTS = 4
COLUMNS = ["date", "bank_cafef", "bank_name", "ticker", "term_months", "channel",
           "rate_percent", "checksum_ok", "source", "source_url", "retrieved_at_utc"]

# Ten CafeF -> ten trong deposit_daily.csv (None = nguon kia khong co ngan hang nay)
ALIASES = {
    "LPBank": "LP Bank", "Bac A Bank": "Bắc Á Bank", "BacABank": "Bắc Á Bank",
    "MBV": None, "MB": "MB Bank", "VPBank": "VP Bank", "VCBNeo": "VCB Neo",
    "KienlongBank": "Kiên Long Bank", "PVcomBank": "PVComBank",
    "VietinBank": "Vietinbank", "HDBank": None, "GPBank": None,
    "SCB": None, "Saigonbank": None, "ABBank": "An Binh Bank",
    "NamABank": "Nam A Bank", "Nam A Bank": "Nam A Bank", "TPBank": "TPBank",
    "OCB": "OCB", "MSB": "MSB", "VietBank": "Vietbank", "Vietbank": "Vietbank",
    "ACB": "ACB", "Agribank": "Agribank", "BIDV": "BIDV", "Eximbank": "Eximbank",
    "SHB": "SHB", "Sacombank": "Sacombank", "Techcombank": "Techcombank",
    "VIB": "VIB", "Vietcombank": "Vietcombank",
    "PGBank": None, "NCB": None, "SeABank": None, "BaoVietBank": None,
    "BVBank": None, "VietABank": None, "OceanBank": None, "CBBank": None,
    "DongABank": None, "VikkiBank": None,
}
# Khop ten dai truoc ("MBV" truoc "MB", "VCBNeo" truoc "VCB")
BANK_RE = re.compile("|".join(re.escape(b) for b in
                              sorted(ALIASES, key=len, reverse=True)))

RATE_RE = re.compile(r"(\d{1,2}(?:[.,]\d{1,2})?)\s*%/năm")
# Ky han di ngay sau mot con so: "cho 6 thang", "tai ky han 12 va 18 thang"
TERM_RE = re.compile(r"^[\s,;]*(?:cho|tại|ở)?\s*(?:kỳ hạn\s*)?"
                     r"((?:\d{1,2}(?:\s*(?:,|và|-)\s*)?)+)\s*tháng")
GROUP_RE = re.compile(r"^[^.]{0,40}?\b(?:gồm|có|là)\b")
# "duoi 6%/nam", "tu 7%/nam tro len", "thap hon 1%/nam" -- nguong, khong phai lai suat
THRESH_BEFORE = re.compile(r"(?:dưới|trên|từ|hơn|khoảng)\s*$")
THRESH_AFTER = re.compile(r"^\s*trở lên")
# Hai ten ngan hang chi thuoc cung mot liet ke neu giua chung chi co dau phay / "va"
LINK_RE = re.compile(r"^[\s,;]*(?:và|,)?[\s,;]*$")
# "ky han 13 thang len 8,7%/nam" -- ky han ghi TRUOC con so
TERM_BEFORE_RE = re.compile(r"kỳ hạn\s*((?:\d{1,2}(?:\s*(?:,|và|-)\s*)?)+)\s*tháng")


def _num(raw: str) -> float:
    return float(raw.replace(",", "."))


def safe_get(label: str, url: str) -> str:
    last = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            return r.text
        except Exception as exc:
            last = type(exc).__name__ + ": " + str(exc)
            if attempt < MAX_ATTEMPTS:
                time.sleep(min(30, 5 * attempt))
    raise RuntimeError(label + ": that bai sau " + str(MAX_ATTEMPTS) + " lan: " + str(last))


def discover(year: int, months: list[int]) -> dict:
    idx = safe_get("sitemap", SITEMAP)
    want = set(months)
    urls = {}
    pattern = (r"<loc>(https://cafef\.vn/sitemaps/sitemaps-" + str(year)
               + r"-(\d{1,2})-[^<]+)</loc>")
    for chunk_url, chunk_month in re.findall(pattern, idx):
        if int(chunk_month) not in want:
            continue
        body = safe_get("chunk " + chunk_url, chunk_url)
        for u, d, m in re.findall(
                r"<loc>(https://cafef\.vn/lai-suat-ngan-hang-(\d{1,2})-(\d{1,2})-tai-[^<]+)</loc>",
                body):
            urls["%04d-%02d-%02d" % (year, int(m), int(d))] = u
        time.sleep(0.5)
    return urls


def article_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for bad in soup.select("script,style,.box-tinlienquan,.tinlienquan"):
        bad.decompose()
    body = soup.select_one("div.detail-content") or soup.select_one("#mainContent") or soup
    text = body.get_text(" ", strip=True)
    m = re.search(r"Theo (?:biểu|bảng) lãi suất", text)
    return text[m.start():] if m else text


def _terms_after(text: str, pos: int):
    m = TERM_RE.match(text[pos:pos + 60])
    if not m:
        return None
    return [int(x) for x in re.findall(r"\d{1,2}", m.group(1))]


def _terms_before(text: str, pos: int):
    ms = list(TERM_BEFORE_RE.finditer(text[max(0, pos - 30):pos]))
    if not ms:
        return None
    return [int(x) for x in re.findall(r"\d{1,2}", ms[-1].group(1))]


def _banks_before(seg: str) -> list:
    ms = list(BANK_RE.finditer(seg))
    if not ms:
        return []
    i = len(ms) - 1
    while i > 0 and LINK_RE.match(seg[ms[i - 1].end():ms[i].start()]):
        i -= 1
    return [m.group(0) for m in ms[i:]]


def parse(text: str):
    rates = [(m.start(), m.end(), _num(m.group(1))) for m in RATE_RE.finditer(text)]
    out, prev_end, last_names = {}, 0, []
    for i, (start, end, value) in enumerate(rates):
        seg = text[prev_end:start]
        nxt = rates[i + 1][0] if i + 1 < len(rates) else len(text)
        if GROUP_RE.match(text[end:nxt]):        # "... gom A, B, C va D"
            names = BANK_RE.findall(text[end:nxt])
        else:                                     # "Techcombank niem yet 6,75%/nam"
            names = _banks_before(seg)
            if not names and "." not in seg:
                # cau ke tiep cua cung mot liet ke: "; va 6,8%/nam cho ky han 12 va 18 thang"
                names = last_names
        if names:
            last_names = names
        prev_end = end

        if (THRESH_BEFORE.search(text[max(0, start - 14):start])
                or THRESH_AFTER.match(text[end:end + 12])):
            continue                      # nguong ("duoi 6%/nam"), khong phai lai suat NH
        terms = _terms_after(text, end)
        if terms is None:
            terms = _terms_before(text, start)
        if terms is not None and TERM not in terms:
            continue                      # con so nay thuoc ky han khac
        for n in names:
            out.setdefault(n, value)

    claims = {}
    m = re.search(r"có\s*(\d+)\s*ngân hàng\s*(?:đang\s*)?niêm yết\s*(?:lãi suất\s*)?"
                  r"từ\s*(\d{1,2}(?:[.,]\d{1,2})?)\s*%/năm trở lên", text)
    if m:
        claims["n_at_least"] = (int(m.group(1)), _num(m.group(2)))
    m = re.search(r"tại\s*(\d+)\s*ngân hàng", text)
    if m:
        claims["n_banks_surveyed"] = int(m.group(1))
    m = re.search(r"thấp hơn\s*(\d{1,2}(?:[.,]\d{1,2})?)\s*(?:%/năm|điểm)", text)
    if m:
        claims["big4_gap_vs_top"] = _num(m.group(1))
    return out, claims


def validate(parsed: dict, claims: dict) -> list:
    problems = []
    if "n_at_least" in claims:
        want, threshold = claims["n_at_least"]
        got = sum(1 for v in parsed.values() if v >= threshold)
        if got != want:
            problems.append("bai noi %d NH >= %.2f%%, trich duoc %d"
                            % (want, threshold, got))
    if "big4_gap_vs_top" in claims and parsed:
        big4 = [parsed[b] for b in ("Agribank", "BIDV", "Vietcombank", "VietinBank")
                if b in parsed]
        if big4:
            gap = max(parsed.values()) - max(big4)
            if abs(gap - claims["big4_gap_vs_top"]) > 0.011:
                problems.append("bai noi Big4 thap hon %.2f diem, tinh duoc %.2f"
                                % (claims["big4_gap_vs_top"], gap))
    return problems


def read_master():
    if not MASTER.exists():
        return COLUMNS, []
    with io.open(MASTER, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    return rows[0], [r for r in rows[1:] if r and r[0].strip()]


def _ticker_map() -> dict:
    if not DEPOSIT.exists():
        return {}
    with io.open(DEPOSIT, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return dict((r["bank_name"], r["ticker"]) for r in rows if r.get("ticker"))


def run(year: int = None, months: list = None) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    retrieved_at = now.isoformat()
    year = year or now.year
    months = months or [now.month]

    header, existing = read_master()
    have = set(r[0] for r in existing)
    tickers = _ticker_map()

    urls = discover(year, months)
    added, problems, skipped = [], {}, 0
    for date in sorted(urls):
        if date in have:
            skipped += 1
            continue
        text = article_text(safe_get("bai " + date, urls[date]))
        parsed, claims = parse(text)
        if not parsed:
            problems[date] = ["khong trich duoc dong nao"]
            continue
        bad = validate(parsed, claims)
        if bad:
            problems[date] = bad          # van ghi, nhung danh dau checksum_ok=False
        for name in sorted(parsed):
            mapped = ALIASES.get(name)
            added.append([date, name, mapped or "", tickers.get(mapped or "", ""),
                          str(TERM), CHANNEL, ("%g" % parsed[name]),
                          "False" if bad else "True",
                          SOURCE_NAME, urls[date], retrieved_at])
        time.sleep(0.6)

    if added:
        with io.open(MASTER, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, lineterminator="\r\n")
            w.writerow(header)
            w.writerows(sorted(existing + added, key=lambda r: (r[0], r[1])))

    days = sorted(set(r[0] for r in added))
    with open("crawl_log.txt", "a", encoding="utf-8") as f:
        f.write("[" + retrieved_at + "] deposit_crosscheck: " + str(len(days))
                + " ngay moi " + str(days) + ", " + str(len(added)) + " dong, "
                + str(skipped) + " ngay da co, checksum loi=" + str(problems or "none")
                + " -> " + str(MASTER) + "\n")
    return {"days_added": len(days), "days": days, "rows_added": len(added),
            "skipped": skipped, "problems": problems, "written": bool(added)}


def compare(date: str = None) -> dict:
    import pandas as pd
    cross = pd.read_csv(MASTER)
    ours = pd.read_csv(DEPOSIT)
    date = date or cross.date.max()
    c = cross[(cross.date == date) & cross.bank_name.notna() & cross.checksum_ok]
    o = ours[(ours.date <= date) & (ours.term_months == TERM) & (ours.channel == CHANNEL)]
    if o.empty:
        raise RuntimeError("deposit_daily.csv khong co du lieu %d thang %s" % (TERM, CHANNEL))
    o = o[o.date == o.date.max()]
    merged = c.merge(o[["bank_name", "rate_percent"]], on="bank_name",
                     suffixes=("_cafef", "_ta"), how="left")
    merged["lech"] = merged.rate_percent_ta - merged.rate_percent_cafef
    return {"date_cafef": date, "date_ta": o.date.max(),
            "table": merged[["bank_name", "bank_cafef", "rate_percent_cafef",
                             "rate_percent_ta", "lech"]].sort_values("lech")}


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--compare" in sys.argv:
        r = compare()
        print("CafeF ngay %s  vs  deposit_daily ngay %s  (%d thang, %s)\n"
              % (r["date_cafef"], r["date_ta"], TERM, CHANNEL))
        t = r["table"]
        print(t.to_string(index=False, na_rep="(khong co)"))
        stuck = t[t.lech.abs() >= 0.5]
        print("\nKET GIA (lech >= 0.5 diem): %d/%d ngan hang doi chieu duoc"
              % (len(stuck), int(t.rate_percent_ta.notna().sum())))
        for _, row in stuck.iterrows():
            print("   %-14s CafeF %.2f  ta %.2f  lech %+.2f"
                  % (row.bank_name, row.rate_percent_cafef, row.rate_percent_ta, row.lech))
    else:
        arg = [a for a in sys.argv[1:] if not a.startswith("--")]
        months = [int(x) for x in arg[0].split(",")] if arg else None
        res = run(months=months)
        print("ngay moi   :", res["days"] or "khong")
        print("dong them  :", res["rows_added"], "| ngay da co:", res["skipped"])
        if res["problems"]:
            print("CHECKSUM LOI:")
            for d, ps in res["problems"].items():
                print("   ", d, "->", "; ".join(ps))
        else:
            print("checksum   : dat")
