from __future__ import annotations

import re
import time
from datetime import date

import pandas as pd
import requests

from crawlers import macro

API = "https://www.nso.gov.vn/wp-json/wp/v2/posts"
SEARCH = "chỉ số giá tiêu dùng chỉ số giá vàng"
SLUG_PREFIX = "chi-so-gia-tieu-dung"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

MONTH_WORDS = {
    "một": 1, "mot": 1, "giêng": 1, "gieng": 1,
    "hai": 2, "ba": 3, "tư": 4, "tu": 4, "bốn": 4, "bon": 4,
    "năm": 5, "nam": 5, "sáu": 6, "sau": 6, "bảy": 7, "bay": 7,
    "tám": 8, "tam": 8, "chín": 9, "chin": 9, "mười": 10, "muoi": 10,
    "mười một": 11, "muoi mot": 11, "mười hai": 12, "muoi hai": 12,
}

STOP_MARKERS = re.compile(
    r"Chỉ số giá vàng"
    r"|Trong mức tăng"
    r"|Trong mức giảm"
    r"|nhóm hàng hóa và dịch vụ"
    r"|\b[IVX]{1,4}\.\s+[A-ZĐÁÀÂÊÔƠƯ]"
)

ADVERB = r"(?:nhẹ\s+|mạnh\s+|khoảng\s+)?"

NOT_HEADLINE_CPI = re.compile(
    r"bình quân"
    r"|cả năm"
    r"|quý\s+(?:i|ii|iii|iv)\b"
    r"|lạm phát cơ bản"
    r"|chỉ số giá vàng|chỉ số giá đô la|giá vàng|giá đô la"
    r"|nhóm\s"
    r"|(?:\d{1,2}|một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười|mười một|mười hai)"
    r"\s+tháng\s+(?:năm|đầu năm)",
    re.IGNORECASE,
)

CPI_SUBJECT = re.compile(r"CPI|chỉ số giá tiêu dùng", re.IGNORECASE)


def _num(raw: str) -> float:
    return float(raw.replace(".", "").replace(",", "."))


def _strip_html(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _normalise(text: str) -> str:
    text = re.sub(r"(?<=[\d,])\s+(?=[\d,])", "", text)
    return re.sub(r"\s+%", "%", text)


def parse_month(title: str, slug: str, published: str) -> str | None:
    low = title.lower()

    year = None
    m = re.search(r"năm\s+(20\d{2})", low)
    if m:
        year = int(m.group(1))

    month = None
    m = re.search(r"tháng\s+(\d{1,2})\b", low)
    if m:
        month = int(m.group(1))
    else:
        m = re.search(
            r"(?<!\d\s)tháng\s+(mười hai|mười một|mười|một|hai|ba|tư|bốn|năm|sáu|bảy|tám|chín)\b",
            low,
        )
        if m:
            month = MONTH_WORDS[m.group(1)]

    if month is None:
        m = re.search(r"(\d{1,2})\s+năm\s+(20\d{2})", low)
        if m:
            month, year = int(m.group(1)), int(m.group(2))

    if month is None:
        m = re.search(r"(?:thang-)?(\d{1,2})-nam-(20\d{2})", slug)
        if m:
            month, year = int(m.group(1)), int(m.group(2))
    if year is None:
        m = re.search(r"nam-(20\d{2})", slug)
        if m:
            year = int(m.group(1))

    if month is None or year is None:
        pub = date.fromisoformat(published[:10])
        y, mo = (pub.year, pub.month - 1) if pub.month > 1 else (pub.year - 1, 12)
        month, year = month or mo, year or y

    if not 1 <= month <= 12:
        return None
    return f"{year:04d}-{month:02d}"


def _anchors(month: str) -> tuple[str, str]:
    year, mon = int(month[:4]), int(month[5:])
    prev_m, prev_y = (mon - 1, year) if mon > 1 else (12, year - 1)

    mom = rf"tháng (?:trước|0?{prev_m}/{prev_y})"
    yoy = rf"(?:cùng kỳ năm (?:trước|{year - 1})|tháng 0?{mon}/{year - 1})"
    return mom, yoy


def parse_figures(content_html: str, month: str,
                  truncate: bool = True) -> tuple[float | None, float | None]:
    text = _normalise(_strip_html(content_html))
    stop = STOP_MARKERS.search(text) if truncate else None
    if stop and stop.start() > 0:
        text = text[:stop.start()]

    def grab(anchor: str) -> float | None:
        candidates = (
            (rf"(?:ổn định|không đổi)\s*so với {anchor}", "zero"),
            (rf"(tăng|giảm)\s+{ADVERB}([\d.,]+)%\s*so với {anchor}", "signed"),
            (rf"so với {anchor}[^%.]{{0,60}}?(tăng|giảm)\s+{ADVERB}([\d.,]+)%", "signed"),
        )
        hits = []
        for pattern, kind in candidates:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                if NOT_HEADLINE_CPI.search(text[max(0, m.start() - 60):m.start()]):
                    continue
                if not CPI_SUBJECT.search(text[max(0, m.start() - 90):m.end()]):
                    continue
                hits.append((m.start(), kind, m))

        if not hits:
            return None
        _, kind, m = min(hits, key=lambda hit: hit[0])
        if kind == "zero":
            return 0.0
        value = _num(m.group(2))
        return -value if m.group(1) == "giảm" else value

    mom_anchor, yoy_anchor = _anchors(month)
    return grab(mom_anchor), grab(yoy_anchor)


def fetch_posts(session: requests.Session | None = None, pause: float = 0.3) -> list[dict]:
    s = session or requests.Session()
    s.headers.update(HEADERS)
    out, page = {}, 1
    while True:
        r = s.get(
            API,
            params={"search": SEARCH, "per_page": 100, "page": page,
                    "_fields": "id,date,slug,link,title,content"},
            timeout=60,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        for post in batch:
            if post["slug"].startswith(SLUG_PREFIX):
                out[post["id"]] = post
        total_pages = int(r.headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break
        page += 1
        time.sleep(pause)
    return list(out.values())


def build_frame(posts: list[dict]) -> pd.DataFrame:
    rows = []
    for post in posts:
        title = _strip_html(post["title"]["rendered"])
        month = parse_month(title, post["slug"], post["date"])
        if month is None:
            continue
        mom, yoy = parse_figures(post["content"]["rendered"], month)
        if mom is None and yoy is None:
            continue
        rows.append({
            "month": month,
            "cpi_yoy_percent": yoy,
            "cpi_mom_percent": mom,
            "source_url": post["link"],
            "note": title,
        })
    df = pd.DataFrame(rows, columns=macro.CPI_COLUMNS)
    return df.sort_values("month").drop_duplicates(subset=["month"], keep="last")


def backfill(since: str = "2018-01", write: bool = True,
             posts: list[dict] | None = None) -> pd.DataFrame:
    macro.ensure_files()
    df = build_frame(posts if posts is not None else fetch_posts())
    df = df[df["month"] >= since]

    if not write:
        return df

    existing = pd.read_csv(macro.cpi_path(), encoding="utf-8-sig",
                           dtype={"month": str}).set_index("month")
    incoming = df.set_index("month")

    conflicts, added, filled = [], [], []
    for month, row in incoming.iterrows():
        if month not in existing.index:
            existing.loc[month] = row
            added.append(month)
            continue
        for column in ("cpi_yoy_percent", "cpi_mom_percent"):
            old, new = existing.loc[month, column], row[column]
            if pd.isna(old) and pd.notna(new):
                existing.loc[month, column] = new
                filled.append(f"{month}.{column.split('_')[1]}")
            elif pd.notna(old) and pd.notna(new) and abs(old - new) >= 0.005:
                conflicts.append(f"{month}.{column.split('_')[1]}: giu {old}, nguon moi {new}")

    result = existing.sort_index().reset_index()
    result.to_csv(macro.cpi_path(), index=False, encoding="utf-8-sig")

    print(f"thang moi: {', '.join(added) or 'khong'}")
    print(f"o duoc bu: {', '.join(filled) or 'khong'}")
    if conflicts:
        print("XUNG DOT (khong ghi de, can kiem tra tay):")
        for line in conflicts:
            print("  " + line)
    return result


if __name__ == "__main__":
    result = backfill()
    print(f"cpi.csv now holds {len(result)} months: "
          f"{result['month'].min()} -> {result['month'].max()}")
