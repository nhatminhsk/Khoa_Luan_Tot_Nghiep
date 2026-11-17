from __future__ import annotations

import csv
import io
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from crawlers.deposit_24hmoney import HEADERS, MAX_ATTEMPTS

OUT = Path("data/interest_rates")
MASTER = OUT / "deposit_techcombank_daily.csv"
URL = "https://techcombank.com/thong-tin/blog/lai-suat-tiet-kiem"
SOURCE_NAME = "techcombank_blog"

COLUMNS = ["date", "effective_date", "bank_techcombank", "bank_name", "ticker",
           "term_months", "channel", "rate_percent", "source", "source_updated_at",
           "source_url", "retrieved_at_utc"]

VN_TZ = timezone(timedelta(hours=7))
# Doan van ngay tren moi bang; "tai quay" va "online" chi phan biet duoc o day
TABLE_INTRO = "cập nhật tại thời điểm"
CHANNEL_LABELS = [("online", "online"), ("quay", "tại quầy")]
TITLE_DATE_RE = re.compile(r"hôm nay\s+(\d{1,2})/(\d{1,2})/(\d{4})")
TERM_RE = re.compile(r"(\d{1,2})\s*tháng", re.IGNORECASE)
RATE_RE = re.compile(r"^\d+(?:[.,]\d+)?")

# Ten tren trang -> (ten trong deposit_daily.csv | None, ticker | "")
BANKS = {
    "ACB": ("ACB", "ACB"), "Agribank": ("Agribank", ""), "ABBank": ("An Binh Bank", ""),
    "BIDV": ("BIDV", "BID"), "BacABank": ("Bắc Á Bank", "BAB"), "Eximbank": ("Eximbank", "EIB"),
    "Kienlongbank": ("Kiên Long Bank", ""), "LPBank": ("LP Bank", "LPB"),
    "MBBank": ("MB Bank", "MBB"), "MSB": ("MSB", "MSB"), "NamABank": ("Nam A Bank", "NAB"),
    "OCB": ("OCB", "OCB"), "PVcomBank": ("PVComBank", ""), "SHB": ("SHB", "SHB"),
    "TPBank": ("TPBank", "TPB"), "Techcombank": ("Techcombank", "TCB"), "VIB": ("VIB", "VIB"),
    "VPBank": ("VP Bank", "VPB"), "VietBank": ("Vietbank", ""),
    "Vietcombank": ("Vietcombank", "VCB"), "VietinBank": ("Vietinbank", "CTG"),
    "VCB Neo (CBBank)": ("VCB Neo", ""), "CBBank": ("VCB Neo", ""),
    "HDBank": (None, "HDB"), "SeABank": (None, "SSB"), "NCB": (None, "NVB"),
    "PG Bank": (None, "PGB"), "Viet Capital Bank (BVBANK)": (None, "BVB"),
    # Ngoai 22 ma niem yet:
    "GPBank": (None, ""), "SCB": (None, ""), "Saigonbank": (None, ""), "VietABank": (None, ""),
    "Vikki Bank": (None, ""), "BAOVIET Bank": (None, ""), "OceanBank": (None, ""),
}


def fetch() -> tuple:
    last = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            r = requests.get(URL, headers=HEADERS, timeout=30)
            r.raise_for_status()
            r.encoding = "utf-8"
            stamp = r.headers.get("Last-Modified", "")
            if stamp:
                stamp = parsedate_to_datetime(stamp).astimezone(VN_TZ).strftime("%H:%M:%S %d/%m/%Y")
            return r.text, stamp
        except Exception as exc:
            last = type(exc).__name__ + ": " + str(exc)
            if attempt < MAX_ATTEMPTS:
                time.sleep(min(30, 5 * attempt))
    raise RuntimeError("techcombank: that bai sau " + str(MAX_ATTEMPTS) + " lan: " + str(last))


def _channel_of(table) -> str:
    intro = table.find_previous(lambda t: t.name in ("p", "h2", "h3") and TABLE_INTRO in t.get_text())
    text = intro.get_text(" ", strip=True) if intro else ""
    for channel, label in CHANNEL_LABELS:
        if label in text:
            return channel
    raise RuntimeError("khong nhan ra kenh cua bang, doan van: %r -- trang doi cau truc" % text[:120])


def parse(html: str) -> tuple:
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for table in soup.find_all("table"):
        grid = [[c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                for tr in table.find_all("tr")]
        if not grid or not grid[0] or grid[0][0] != "Ngân hàng":
            continue                       # bang "Luu y" cung la the table
        channel = _channel_of(table)
        terms = {}
        for i, cell in enumerate(grid[0][1:], start=1):
            m = TERM_RE.search(cell)
            if m:
                terms[i] = int(m.group(1))
        if not terms:
            raise RuntimeError("khong doc duoc ky han tu header: %r" % grid[0])
        for line in grid[1:]:
            if not line or not line[0]:
                continue
            for i, term in terms.items():
                if i >= len(line):
                    continue
                m = RATE_RE.match(line[i])  # o Techcombank co them chu "Tham khao: Bieu phi, lai suat"
                if m:
                    rows.append((line[0], term, channel, float(m.group(0).replace(",", "."))))
    if not rows:
        raise RuntimeError("khong thay bang lai suat nao -- trang doi cau truc")
    title = soup.title.get_text() if soup.title else ""
    m = TITLE_DATE_RE.search(title)
    return rows, ("%s-%02d-%02d" % (m.group(3), int(m.group(2)), int(m.group(1))) if m else "")


def validate(rows: list) -> list:
    problems = []
    channels = set(r[2] for r in rows)
    if channels != {"quay", "online"}:
        problems.append("thieu kenh: chi co %s" % sorted(channels))
    bad = [r for r in rows if not (0.1 <= r[3] <= 15.0)]
    if bad:
        problems.append("%d o ngoai khoang [0.1, 15.0]: %s" % (len(bad), bad[:5]))
    unknown = sorted(set(r[0] for r in rows) - set(BANKS))
    if unknown:
        problems.append("ten ngan hang chua map: %s" % unknown)
    return problems


def _key(row):
    return (row[1], row[2], row[5], row[6])


def read_master():
    if not MASTER.exists():
        return COLUMNS, []
    with io.open(MASTER, encoding="utf-8-sig", newline="") as f:
        grid = list(csv.reader(f))
    return grid[0], [r for r in grid[1:] if r and r[0].strip()]


def _write(header, rows):
    with io.open(MASTER, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(header)
        w.writerows(sorted(rows, key=_key))


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    retrieved_at = now.isoformat()
    date = now.strftime("%Y-%m-%d")

    html, stamp = fetch()
    rows, title_date = parse(html)
    problems = validate(rows)
    if not title_date:
        problems.append("khong doc duoc ngay trong tieu de, dung ngay chup")
    eff = title_date or date

    header, existing = read_master()
    have = set(_key(r) for r in existing)
    added = []
    for bank, term, channel, rate in rows:
        mapped, ticker = BANKS.get(bank, (None, ""))
        row = [date, eff, bank, mapped or "", ticker, str(term), channel, ("%g" % rate),
               SOURCE_NAME, stamp, URL, retrieved_at]
        if _key(row) not in have:
            have.add(_key(row))
            added.append(row)

    if added:
        _write(header, existing + added)

    with open("crawl_log.txt", "a", encoding="utf-8") as f:
        f.write("[" + retrieved_at + "] deposit_techcombank: " + str(len(added))
                + " dong moi (" + str(len(rows)) + " o doc duoc), ngay tren trang=" + eff
                + ", Last-Modified=" + str(stamp or "?") + ", canh bao=" + str(problems or "none")
                + " -> " + str(MASTER) + "\n")
    return {"date": date, "effective_date": eff, "source_updated_at": stamp, "cells_read": len(rows),
            "rows_added": len(added), "problems": problems, "written": bool(added)}


if __name__ == "__main__":
    print(run())
