from __future__ import annotations

import csv
import io
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUT = Path("data/interest_rates")
MASTER = OUT / "deposit_24hmoney_daily.csv"
DEPOSIT = OUT / "deposit_daily.csv"
URL = "https://24hmoney.vn/lai-suat-gui-ngan-hang"
SOURCE_NAME = "24hmoney"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "vi,en;q=0.9",
}
MAX_ATTEMPTS = 4
COLUMNS = ["date", "effective_date", "bank_24hmoney", "bank_name", "ticker",
           "term_months", "channel", "rate_percent", "source", "source_updated_at",
           "source_url", "retrieved_at_utc"]

# date           = ngay CHUP (lan dau nhin thay bang nay)
# effective_date = ngay CUA CHINH BANG, doc tu "Cap nhat luc" in tren trang
# Hai cai nay khac nhau that: snapshot Wayback 18/03/2026 van dang bang cua
# 16/12/2025 -- nguon dung yen 3 thang. Khoa chong trung dung effective_date,
# nen chay lai hang ngay khong sinh dong moi tru khi nguon that su doi bang.

# Nhan dat NGAY TREN moi bang -- dung de nhan kenh, khong dua vao thu tu bang
CHANNEL_LABELS = [("quay", "gửi tại Quầy"), ("online", "gửi Trực tuyến")]

# Ten 24hmoney -> (ten trong deposit_daily.csv | None, ticker | "")
BANKS = {
    "ACB": ("ACB", "ACB"), "Agribank": ("Agribank", ""),
    "An Bình Bank": ("An Binh Bank", ""), "BIDV": ("BIDV", "BID"),
    "Bắc Á Bank": ("Bắc Á Bank", "BAB"), "Eximbank": ("Eximbank", "EIB"),
    "Kiên Long Bank": ("Kiên Long Bank", ""), "LPBank": ("LP Bank", "LPB"),
    "MBBank": ("MB Bank", "MBB"), "MSB": ("MSB", "MSB"),
    "Nam Á Bank": ("Nam A Bank", "NAB"), "OCB": ("OCB", "OCB"),
    "PVCombank": ("PVComBank", ""), "SHB": ("SHB", "SHB"),
    "Sacombank": ("Sacombank", "STB"), "TPBank": ("TPBank", "TPB"),
    "Techcombank": ("Techcombank", "TCB"), "VIB": ("VIB", "VIB"),
    "VPBank": ("VP Bank", "VPB"), "VietBank": ("Vietbank", ""),
    "Vietcombank": ("Vietcombank", "VCB"), "VietinBank": ("Vietinbank", "CTG"),
    # Nam ngan hang nguon chinh KHONG co -- day la phan 24hmoney bu them
    "HDBank": (None, "HDB"), "SeABank": (None, "SSB"), "BVBank": (None, "BVB"),
    "NCB": (None, "NVB"), "PGBank": (None, "PGB"),
    # Con lai: khong nam trong 22 ma niem yet cua de tai
    "Saigonbank": (None, ""), "SCB": (None, ""), "GPBANK": (None, ""),
    "Việt Á Bank": (None, ""), "Bảo Việt Bank": (None, ""), "CIMB Bank": (None, ""),
    "UOB": (None, ""), "Woori Bank": (None, ""), "Shinhan Bank": (None, ""),
    "Standard Chartered": (None, ""), "HSBC": (None, ""), "VCBNeo": (None, ""),

    # --- Bien the ten trong LICH SU Wayback (2023-2025) ---
    # Hai ngan hang DOI TEN that, khong phai viet tat:
    "LienVietPostBank": ("LP Bank", "LPB"),      # doi ten thanh LPBank nam 2023
    "VietCapitalBank": (None, "BVB"),            # doi ten thanh BVBank nam 2023
    # Viet tat / viet hoa khac nhau qua cac nam:
    "MB": ("MB Bank", "MBB"), "MBB": ("MB Bank", "MBB"),
    "Bắc Á": ("Bắc Á Bank", "BAB"), "Nam Á": ("Nam A Bank", "NAB"),
    "Kiên Long": ("Kiên Long Bank", ""), "ABBank": ("An Binh Bank", ""),
    "PVcomBank": ("PVComBank", ""), "TPB": ("TPBank", "TPB"),
    "SGB": (None, ""), "Việt Á": (None, ""), "Bảo Việt": (None, ""),
    "GPBank": (None, ""),
    # Ngoai 22 ma niem yet:
    "Đông Á": (None, ""), "Đông Á Bank": (None, ""),
    "CBBANK": (None, ""), "CBBank": (None, ""),
    "OCEANBANK": (None, ""), "OceanBank": (None, ""),
    "Hong Leong": (None, ""), "Indovina": (None, ""),
    "PublicBank": (None, ""), "VRB": (None, ""),
}
# Ten rac tung xuat hien khi trang render hong -- bo, khong doan ngan hang
JUNK_NAMES = {"null", "none", "undefined", "-", "n/a"}
UPDATED_RE = re.compile(r"Cập nhật lúc:\s*([\d:]+\s*\d{2}/\d{2}/\d{4})")
TERM_RE = re.compile(r"(\d{1,2})\s*tháng", re.IGNORECASE)


def safe_get(url: str) -> str:
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
    raise RuntimeError("24hmoney: that bai sau " + str(MAX_ATTEMPTS) + " lan: " + str(last))


def _table_for(soup, label: str):
    node = soup.find(string=lambda s: s and label in s)
    if node is None:
        return None, None
    table = node.find_parent().find_next("table") if node.find_parent() else None
    if table is None:
        return None, None
    stamp = None
    probe = node
    for _ in range(8):                       # moc cap nhat nam gan nhan
        probe = probe.find_next(string=True)
        if probe is None:
            break
        m = UPDATED_RE.search(str(probe))
        if m:
            stamp = re.sub(r"\s+", " ", m.group(1)).strip()
            break
    return table, stamp


def parse(html: str) -> tuple:
    soup = BeautifulSoup(html, "lxml")
    rows, stamps = [], []
    for channel, label in CHANNEL_LABELS:
        table, stamp = _table_for(soup, label)
        if table is None:
            raise RuntimeError("khong thay bang cho nhan %r -- trang doi cau truc" % label)
        if stamp:
            stamps.append(stamp)
        grid = [[c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                for tr in table.find_all("tr")]
        head = grid[0]
        terms = {}
        for i, cell in enumerate(head[1:], start=1):
            m = TERM_RE.search(cell)
            if m:
                terms[i] = int(m.group(1))
        if not terms:
            raise RuntimeError("khong doc duoc ky han tu header: %r" % head)
        for line in grid[1:]:
            if not line or not line[0]:
                continue
            bank = line[0]
            if bank.strip().lower() in JUNK_NAMES:
                continue      # trang tung render hong 1 dong thanh "null" (10/08/2024)
            for i, term in terms.items():
                if i >= len(line):
                    continue
                raw = line[i].replace("%", "").strip()
                if raw in ("", "-", "--"):
                    continue
                try:
                    rate = float(raw.replace(",", "."))
                except ValueError:
                    continue
                rows.append((bank, term, channel, rate))
    return rows, (stamps[0] if stamps else "")


def validate(rows: list) -> list:
    problems = []
    bad = [r for r in rows if not (0.1 <= r[3] <= 15.0)]
    if bad:
        problems.append("%d o ngoai khoang [0.1, 15.0]: %s" % (len(bad), bad[:5]))
    by = {}
    for bank, term, channel, rate in rows:
        by.setdefault((bank, term), {})[channel] = rate
    flip = [(k, v) for k, v in by.items()
            if "quay" in v and "online" in v and v["quay"] - v["online"] > 0.5]
    if flip:
        problems.append("%d o co quay CAO HON online >0.5 diem (bat thuong): %s"
                        % (len(flip), [(k[0], k[1], v) for k, v in flip[:5]]))
    unknown = sorted(set(r[0] for r in rows) - set(BANKS))
    if unknown:
        problems.append("ten ngan hang chua map: %s" % unknown)
    return problems


def _effective_date(stamp: str, fallback: str) -> str:
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", stamp or "")
    return "%s-%s-%s" % (m.group(3), m.group(2), m.group(1)) if m else fallback


def _key(row):
    return (row[1], row[2], row[5], row[6])


def _write(header, rows):
    with io.open(MASTER, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(header)
        w.writerows(sorted(rows, key=_key))


def read_master():
    if not MASTER.exists():
        return COLUMNS, []
    with io.open(MASTER, encoding="utf-8-sig", newline="") as f:
        grid = list(csv.reader(f))
    return grid[0], [r for r in grid[1:] if r and r[0].strip()]


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    retrieved_at = now.isoformat()
    date = now.strftime("%Y-%m-%d")

    rows, stamp = parse(safe_get(URL))
    problems = validate(rows)

    header, existing = read_master()
    have = set(_key(r) for r in existing)
    eff = _effective_date(stamp, date)
    added = []
    for bank, term, channel, rate in rows:
        mapped, ticker = BANKS.get(bank, (None, ""))
        row = [date, eff, bank, mapped or "", ticker, str(term), channel,
               ("%g" % rate), SOURCE_NAME, stamp, URL, retrieved_at]
        if _key(row) not in have:
            have.add(_key(row))
            added.append(row)

    if added:
        _write(header, existing + added)

    with open("crawl_log.txt", "a", encoding="utf-8") as f:
        f.write("[" + retrieved_at + "] deposit_24hmoney: " + str(len(added))
                + " dong moi (" + str(len(rows)) + " o doc duoc), nguon cap nhat="
                + str(stamp or "?") + ", canh bao=" + str(problems or "none")
                + " -> " + str(MASTER) + "\n")
    return {"date": date, "effective_date": eff, "source_updated_at": stamp,
            "cells_read": len(rows), "rows_added": len(added),
            "problems": problems, "written": bool(added)}


def remap() -> dict:
    header, rows = read_master()
    if not rows:
        return {"rows": 0, "changed": 0, "unmapped": []}
    changed = 0
    for r in rows:
        mapped, ticker = BANKS.get(r[2], (None, ""))
        new_name, new_ticker = mapped or "", ticker
        if (r[3], r[4]) != (new_name, new_ticker):
            r[3], r[4] = new_name, new_ticker
            changed += 1
    _write(header, rows)
    unmapped = sorted(set(r[2] for r in rows) - set(BANKS))
    return {"rows": len(rows), "changed": changed, "unmapped": unmapped}


CDX = ("http://web.archive.org/cdx/search/cdx?url=24hmoney.vn/lai-suat-gui-ngan-hang*"
       "&output=json&fl=timestamp,original,statuscode&collapse=timestamp:8&limit=5000")


def backfill(pause: float = 1.2) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).isoformat()

    snaps = None
    for attempt in range(5):            # CDX hay tra ve rong khi bi bop bang thong
        body = requests.get(CDX, headers=HEADERS, timeout=90).text
        if body.strip().startswith("["):
            snaps = json.loads(body)[1:]
            break
        time.sleep(8 * (attempt + 1))
    if snaps is None:
        raise RuntimeError("Wayback CDX khong tra ve JSON sau 5 lan thu")
    snaps = [x for x in snaps
             if x[1].rstrip("/").endswith("lai-suat-gui-ngan-hang") and x[2] == "200"]

    header, existing = read_master()
    have = set(_key(r) for r in existing)
    added, failed, boards = [], {}, set()
    for ts, orig, _ in snaps:
        snap_date = "%s-%s-%s" % (ts[:4], ts[4:6], ts[6:8])
        try:
            html = safe_get("http://web.archive.org/web/%sid_/%s" % (ts, orig))
            cells, stamp = parse(html)
        except Exception as exc:
            failed[snap_date] = str(exc)[:90]
            time.sleep(pause)
            continue
        eff = _effective_date(stamp, snap_date)
        boards.add(eff)
        for bank, term, channel, rate in cells:
            mapped, ticker = BANKS.get(bank, (None, ""))
            row = [snap_date, eff, bank, mapped or "", ticker, str(term), channel,
                   ("%g" % rate), SOURCE_NAME, stamp,
                   "http://web.archive.org/web/%s/%s" % (ts, orig), retrieved_at]
            if _key(row) not in have:
                have.add(_key(row))
                added.append(row)
        time.sleep(pause)

    if added:
        _write(header, existing + added)
    with open("crawl_log.txt", "a", encoding="utf-8") as f:
        f.write("[" + retrieved_at + "] deposit_24hmoney backfill: " + str(len(snaps))
                + " snapshot Wayback, " + str(len(boards)) + " bang phan biet, "
                + str(len(added)) + " dong moi, " + str(len(failed))
                + " snapshot khong doc duoc -> " + str(MASTER) + "\n")
    return {"snapshots": len(snaps), "distinct_boards": len(boards),
            "rows_added": len(added), "failed": failed,
            "range": (min(boards), max(boards)) if boards else None}


def compare(term: int = 12, channel: str = "online"):
    import pandas as pd
    h = pd.read_csv(MASTER)
    h = h[(h.term_months == term) & (h.channel == channel) & h.bank_name.notna()]
    h = h[h.effective_date == h.effective_date.max()].set_index("bank_name").rate_percent

    o = pd.read_csv(DEPOSIT)
    o = o[(o.term_months == term) & (o.channel == channel)]
    o = o[o.date == o.date.max()].set_index("bank_name").rate_percent

    cross = OUT / "deposit_crosscheck_daily.csv"
    c = pd.Series(dtype=float)
    if cross.exists() and term == 12 and channel == "online":
        cc = pd.read_csv(cross)
        cc = cc[cc.checksum_ok & cc.bank_name.notna()]
        cc = cc[cc.date == cc.date.max()]
        c = cc.set_index("bank_name").rate_percent

    df = pd.DataFrame({"laisuattietkiem": o, "cafef": c, "24hmoney": h}).dropna(how="all")
    df["bien_do"] = df.max(axis=1) - df.min(axis=1)
    return df.sort_values("bien_do", ascending=False)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--compare" in sys.argv:
        df = compare()
        print("Doi chieu 3 nguon -- 12 thang, online\n")
        print(df.to_string(na_rep="-"))
        n = int((df.bien_do >= 0.5).sum())
        print("\n%d/%d ngan hang lech >= 0.5 diem giua cac nguon" % (n, len(df)))
        print("bien do lon nhat: %.2f diem" % df.bien_do.max())
    elif "--remap" in sys.argv:
        r = remap()
        print("dong           :", r["rows"], "| cap nhat lai:", r["changed"])
        print("ten chua map   :", ", ".join(r["unmapped"]) or "khong con")
    elif "--backfill" in sys.argv:
        r = backfill()
        print("snapshot Wayback :", r["snapshots"])
        print("bang phan biet   :", r["distinct_boards"],
              ("(%s -> %s)" % r["range"]) if r["range"] else "")
        print("dong them        :", r["rows_added"])
        if r["failed"]:
            print("snapshot khong doc duoc:", len(r["failed"]))
            for d, why in list(r["failed"].items())[:10]:
                print("   ", d, "->", why)
    else:
        r = run()
        print("ngay          :", r["date"])
        print("bang hieu luc :", r["effective_date"])
        print("nguon cap nhat:", r["source_updated_at"] or "(khong thay moc)")
        print("o doc duoc    :", r["cells_read"], "| dong moi:", r["rows_added"])
        if r["problems"]:
            print("CANH BAO:")
            for p in r["problems"]:
                print("   ", p)
        else:
            print("kiem dinh     : dat")
