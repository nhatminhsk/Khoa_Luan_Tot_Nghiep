from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

import pandas as pd
import requests

OUT = Path("data/interest_rates")
MASTER = OUT / "bank_lending_rates_monthly.csv"
SITEMAP = "https://vietnamnet.vn/sitemap-article-{month:02d}-{year}-{part:02d}.xml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "vi,en;q=0.9",
}

COLUMNS = [
    "month", "bank_key", "bank_name", "ticker", "lending_avg_percent", "change_vs_prev_point",
    "spread_vs_deposit_point", "deposit_avg_percent", "deposit_avg_implied_percent",
    "from_mixed_table", "source_url", "article_title", "note", "retrieved_at_utc",
]


SLUG_KEEP = re.compile(r"lai-suat|lai-vay|cho-vay")
SLUG_DROP = re.compile(r"euro-2024|bong-da|truc-tiep|nhan-dinh|du-doan|ket-qua-|video-")

TABLE = re.compile(r"<table[^>]*>(.*?)</table>", re.S)
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)

CAPTION = re.compile(r"L[ÃA]I\s*SU[ẤA]T\s+(?:CHO\s*VAY\s+|HUY\s*Đ[ỘO]NG\s+)?B[ÌI]NH\s*QU[ÂA]N", re.I)
CAPTION_DEPOSIT_LED = re.compile(r"L[ÃA]I\s*SU[ẤA]T\s*HUY\s*Đ[ỘO]NG\s*B[ÌI]NH\s*QU[ÂA]N", re.I)
CAPTION_MIXED = re.compile(r"G[ẦA]N\s*NH[ẤA]T", re.I)
MONTH_COLUMN = re.compile(r"TH[ỜO]I\s*[ĐD]I[ỂE]M\s*C[ÔO]NG\s*B[ỐO]", re.I)
ROW_MONTH = re.compile(r"th[áa]ng\s*(\d{1,2})(?:\s*/\s*(20\d{2}))?", re.I)
CHANGE_FIXED_BASE = re.compile(r"SO\s*V[ỚO]I\s*(?:TH[ÁA]NG\s*)?\d{1,2}\s*/\s*20\d{2}", re.I)
CAPTION_MONTH = re.compile(r"TH[ÁA]NG\s*(\d{1,2})(?:\s*/\s*(20\d{2}))?", re.I)
COMPARISON_BASE = re.compile(r"SO\s*V[ỚO]I\s*$", re.I)

CELL_MONTH = re.compile(r"th[áa]ng\s*(\d{1,2})(?:\s*/\s*(20\d{2}))?", re.I)
ANNOTATION = re.compile(r"\s*\([^)]*\)\s*$")

HEADER_CELL = re.compile(r"^(?:ng[âa]n\s*h[àa]ng|nh|stt|t[êe]n\s|l[ãa]i\s*su[ấa]t)", re.I)
NUMBER = re.compile(r"-?\d+(?:[.,]\d+)*")

RATE_MIN, RATE_MAX = 0.0, 50.0

TICKERS = {
    "ACB": "ACB", "BACABANK": "BAB", "BACA": "BAB",
    "BIDV": "BID", "BVBANK": "BVB", "VIETINBANK": "CTG", "EXIMBANK": "EIB",
    "HDBANK": "HDB", "LPBANK": "LPB", "MB": "MBB", "MBBANK": "MBB",
    "MSB": "MSB", "NAMABANK": "NAB", "NCB": "NVB", "OCB": "OCB",
    "PGBANK": "PGB", "SHB": "SHB", "SEABANK": "SSB", "SACOMBANK": "STB",
    "TECHCOMBANK": "TCB", "TPBANK": "TPB", "VIETCOMBANK": "VCB",
    "VIB": "VIB", "VPBANK": "VPB",
}

NOT_LISTED = {
    "SCB", "AGRIBANK", "KIENLONGBANK", "MBV", "VCBNEO", "SAIGONBANK",
    "PVCOMBANK", "VIETABANK", "VIKKIBANK", "GPBANK", "BAOVIETBANK", "KLB",
    "ABBANK", "VIETBANK", "DONGABANK", "OCEANBANK", "CBBANK", "VRB",
    "COOPBANK", "HONGLEONG", "SHINHANBANK", "WOORIBANK", "UOB", "PUBLICBANK",
    "INDOVINABANK", "IVB", "VIETCAPITALBANK", "BAOVIET", "HONGLEONGBANK",
}


def _num(raw: str) -> float | None:
    m = NUMBER.search(raw)
    if not m:
        return None
    token = m.group(0)
    head, sep, tail = token.rpartition(",") if "," in token else token.rpartition(".")
    if not sep:
        return float(token)
    return float(re.sub(r"[.,]", "", head) + "." + tail)


def _text(html: str) -> str:
    plain = unescape(re.sub(r"<[^>]+>", " ", html))
    return re.sub(r"\s+", " ", plain.replace("\xa0", " ")).strip()


ALIASES = {
    "KLB": "KIENLONGBANK",
    "HONGLEONG": "HONGLEONGBANK",
    "IVB": "INDOVINABANK",
    "BAOVIET": "BAOVIETBANK",
}


def _key(bank_name: str) -> str:
    key = re.sub(r"[^A-Z0-9]", "", bank_name.upper())
    return ALIASES.get(key, key)


def month_urls(year: int, month: int, session: requests.Session) -> list[str]:
    out: list[str] = []
    for part in range(1, 20):
        r = session.get(SITEMAP.format(year=year, month=month, part=part), timeout=60)
        if r.status_code != 200:
            break
        locs = re.findall(r"<loc>([^<]+)</loc>", r.text)
        if not locs:
            break
        out += locs
    return out


def candidate_urls(since: tuple[int, int] = (2024, 3),
                   until: tuple[int, int] | None = None,
                   session: requests.Session | None = None,
                   pause: float = 0.1) -> list[str]:
    s = session or requests.Session()
    s.headers.update(HEADERS)
    today = datetime.now(timezone.utc)
    until = until or (today.year, today.month)

    urls: list[str] = []
    year, month = since
    while (year, month) <= until:
        urls += month_urls(year, month, s)
        year, month = (year, month + 1) if month < 12 else (year + 1, 1)
        time.sleep(pause)
    return [u for u in urls if SLUG_KEEP.search(u) and not SLUG_DROP.search(u)]


def _cells(row_html: str) -> list[str]:
    cells = [_text(c) for c in CELL.findall(row_html)]
    while cells and not cells[0]:
        cells.pop(0)
    if len(cells) > 2 and re.fullmatch(r"\d{1,2}", cells[0]) and not _num(cells[1]):
        cells = cells[1:]
    return cells


def _title_row(table_html: str) -> str:
    for row in ROW.findall(table_html):
        text = " ".join(c for c in _cells(row) if c).strip()
        if text:
            return text
    return ""


def _header_row(table_html: str) -> list[str]:
    for row in ROW.findall(table_html):
        cells = _cells(row)
        if len(cells) < 2 or not any(cells):
            continue
        if CAPTION.search(" ".join(cells)):
            continue
        return cells
    return []


def _month_column(table_html: str) -> int | None:
    header = _header_row(table_html)
    for i, cell in enumerate(header):
        if MONTH_COLUMN.search(cell):
            return i
    return None


def _looks_like_banks(rows: list[list[str]], need: float = 0.6) -> bool:
    if not rows:
        return False
    known = sum(1 for r in rows if _key(r[0]) in TICKERS or _key(r[0]) in NOT_LISTED)
    return known >= max(3, need * len(rows))


def _data_rows(table_html: str) -> list[list[str]]:
    out = []
    for row in ROW.findall(table_html):
        cells = _cells(row)
        if len(cells) < 2 or not cells[0] or len(cells[0]) > 40:
            continue
        if HEADER_CELL.match(cells[0]):
            continue
        value = _num(cells[1])
        if value is None or not RATE_MIN < value <= RATE_MAX:
            continue
        out.append(cells)
    return out


def find_table(html: str) -> tuple[str, str] | None:
    best, best_rows = None, 0
    for table in TABLE.findall(html):
        title = _title_row(table)
        if not CAPTION.search(title):
            continue
        if CAPTION_MIXED.search(title) and _month_column(table) is None:
            continue
        rows = _data_rows(table)
        if not _looks_like_banks(rows):
            continue
        if len(rows) > best_rows:
            best, best_rows = (table, title), len(rows)
    return best if best_rows >= 5 else None


def _layout(table_html: str, title: str) -> str:
    rows = _data_rows(table_html)
    triples = [
        (_num(r[1]), _num(r[2]), _num(r[3]))
        for r in rows if len(r) >= 4
    ]
    triples = [t for t in triples if None not in t]
    if triples:
        consistent = sum(1 for a, b, c in triples if abs(a - b - c) < 0.02)
        if consistent >= max(3, int(0.8 * len(triples))):
            return "combined"
    return "lending_led"


def parse_table(table_html: str, caption: str, fallback_month: str) -> tuple[str, list[dict]]:
    m = None
    for candidate in CAPTION_MONTH.finditer(caption):
        if not COMPARISON_BASE.search(caption[max(0, candidate.start() - 12):candidate.start()]):
            m = candidate
            break
    if m and m.group(2):
        month = f"{m.group(2)}-{int(m.group(1)):02d}"
    elif m:
        year = int(fallback_month[:4])
        if int(m.group(1)) == 12 and fallback_month[5:] == "01":
            year -= 1
        month = f"{year}-{int(m.group(1)):02d}"
    else:
        month = fallback_month

    layout = _layout(table_html, caption)
    mislabelled = layout == "lending_led" and bool(CAPTION_DEPOSIT_LED.search(caption))
    month_col = _month_column(table_html)
    header = _header_row(table_html)
    fixed_base = bool(CHANGE_FIXED_BASE.search(" ".join(header)))
    mixed = month_col is not None

    rows = []
    for cells in _data_rows(table_html):
        bank, rest = cells[0], cells[1:]

        note = ""
        own_month = month
        if month_col is not None and len(cells) > month_col:
            rm = ROW_MONTH.search(cells[month_col])
            if rm:
                mm = int(rm.group(1))
                if rm.group(2):
                    year = int(rm.group(2))
                else:
                    year = int(month[:4]) - (1 if mm > int(month[5:]) else 0)
                own_month = f"{year}-{mm:02d}"
                note = (f"cong bo gan nhat, thang lay tu cot '{header[month_col]}' "
                        f"= {cells[month_col].strip()}")
        cm = None if month_col is not None else (
            CELL_MONTH.search(rest[0]) or CELL_MONTH.search(bank))
        if cm:
            note = f"{bank} | {rest[0]}"
            if cm.group(2):
                own_month = f"{cm.group(2)}-{int(cm.group(1)):02d}"
            else:
                year = int(month[:4]) + (1 if int(cm.group(1)) == 1 and month[5:] == "12" else 0)
                own_month = f"{year}-{int(cm.group(1)):02d}"
        bank = ANNOTATION.sub("", bank).strip()

        first = _num(rest[0])
        second = _num(rest[1]) if len(rest) > 1 else None
        third = _num(rest[2]) if len(rest) > 2 else None

        if layout == "combined":
            lending, deposit, spread, change = first, second, third, None
        else:
            lending, change, spread, deposit = first, second, third, None

        if fixed_base and change is not None:
            note = (note + " | " if note else "") + \
                f"cot thay doi tinh theo goc co dinh ('{header[2] if len(header) > 2 else '?'}'), KHONG phai so voi thang lien truoc -> bo"
            change = None
        key = _key(bank)
        rows.append({
            "month": own_month,
            "bank_key": key,
            "bank_name": bank,
            "ticker": TICKERS.get(key, ""),
            "lending_avg_percent": lending,
            "change_vs_prev_point": change,
            "spread_vs_deposit_point": spread,
            "deposit_avg_percent": deposit,
            "deposit_avg_implied_percent": (
                round(lending - spread, 4)
                if deposit is None and None not in (lending, spread) else None
            ),
            "from_mixed_table": mixed,
            "note": note
                    + (f" [layout={layout}]" if layout != "lending_led" else "")
                    + (" [caption ghi 'huy dong' nhung cot la lai suat cho vay"
                       " -- doi chieu thang lien truoc/lien sau, xem"
                       " CAPTION_DEPOSIT_LED]" if mislabelled else ""),
            "_unmapped": key not in TICKERS and key not in NOT_LISTED,
        })
    return month, rows


def build_frame(articles: list[dict]) -> pd.DataFrame:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    unmapped: set[str] = set()
    out = []
    for art in articles:
        hit = find_table(art["html"])
        if not hit:
            continue
        table_html, caption = hit
        pub = art["published"]
        py, pm = int(pub[:4]), int(pub[5:7])
        fallback = f"{py if pm > 1 else py - 1}-{(pm - 1) or 12:02d}"
        _, rows = parse_table(table_html, caption, fallback)
        for row in rows:
            if row.pop("_unmapped"):
                unmapped.add(row["bank_name"])
            row["source_url"] = art["url"]
            row["article_title"] = art["title"]
            row["retrieved_at_utc"] = now
            out.append(row)

    if unmapped:
        print("ten NH chua map (kiem tra TICKERS/NOT_LISTED): " + ", ".join(sorted(unmapped)))

    df = pd.DataFrame(out, columns=COLUMNS)
    if df.empty:
        return df
    return (df.sort_values(["month", "bank_key", "retrieved_at_utc"])
              .drop_duplicates(subset=["month", "bank_key"], keep="last")
              .reset_index(drop=True))


def fetch_articles(urls: list[str], session: requests.Session | None = None,
                   pause: float = 0.15) -> list[dict]:
    s = session or requests.Session()
    s.headers.update(HEADERS)
    out = []
    for url in urls:
        try:
            html = s.get(url, timeout=45).text
        except requests.RequestException:
            continue
        if not CAPTION.search(_text(html)):
            continue
        title = re.search(r'"headline":\s*"([^"]*)"', html)
        pub = re.search(r'"datePublished":\s*"(\d{4}-\d{2}-\d{2})', html)
        out.append({
            "url": url,
            "html": html,
            "title": title.group(1) if title else "",
            "published": pub.group(1) if pub else datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        })
        time.sleep(pause)
    return out


def merge(df: pd.DataFrame, write: bool = True) -> pd.DataFrame:
    OUT.mkdir(parents=True, exist_ok=True)
    if not MASTER.exists():
        pd.DataFrame(columns=COLUMNS).to_csv(MASTER, index=False, encoding="utf-8-sig")
    if not write or df.empty:
        return df

    existing = pd.read_csv(MASTER, encoding="utf-8-sig", dtype={"month": str})
    key = ["month", "bank_key"]
    have = set(map(tuple, existing[key].values)) if not existing.empty else set()

    fresh = df[~df[key].apply(tuple, axis=1).isin(have)]
    if fresh.empty:
        result = existing
    elif existing.empty:
        result = fresh
    else:
        result = pd.concat([existing, fresh], ignore_index=True)
    result = result.sort_values(key).reset_index(drop=True)
    result.to_csv(MASTER, index=False, encoding="utf-8-sig")

    print(f"dong moi: {len(fresh)} / {len(df)} dong doc duoc")
    print(f"master: {len(result)} dong, {result['month'].nunique()} thang "
          f"({result['month'].min()} -> {result['month'].max()})")
    return result


MIN_BANKS_FOR_SURVEY = 15


def coverage(df: pd.DataFrame | None = None) -> pd.DataFrame:
    if df is None:
        df = pd.read_csv(MASTER, encoding="utf-8-sig", dtype={"month": str})
    if df.empty:
        return df
    mixed = df.get("from_mixed_table", pd.Series(False, index=df.index)).fillna(False).astype(bool)
    per = df.assign(_mixed=mixed).groupby("month").agg(
        so_nh=("bank_key", "nunique"),
        co_ticker=("ticker", lambda s: s.replace("", pd.NA).notna().sum()),
        cat_ngang=("_mixed", "sum"),
        ls_min=("lending_avg_percent", "min"),
        ls_max=("lending_avg_percent", "max"),
    )
    per["so_nh_khao_sat"] = (df[~mixed].groupby("month").bank_key.nunique()
                             .reindex(per.index).fillna(0).astype(int))
    per["dung_duoc"] = per.so_nh_khao_sat >= MIN_BANKS_FOR_SURVEY
    return per


def bank_coverage(df: pd.DataFrame | None = None) -> pd.DataFrame:
    if df is None:
        df = pd.read_csv(MASTER, encoding="utf-8-sig", dtype={"month": str})
    if df.empty:
        return df
    good = coverage(df)
    good = set(good.index[good.dung_duoc])
    panel = df[df.month.isin(good)]
    n_months = len(good)
    per = panel.groupby("bank_key").agg(
        so_thang=("month", "nunique"),
        ticker=("ticker", "first"),
        ls_tb=("lending_avg_percent", "mean"),
    )
    per["ty_le"] = (per.so_thang / n_months).round(3) if n_months else pd.NA
    return per.sort_values("so_thang")


def validate(df: pd.DataFrame | None = None) -> None:
    if df is None:
        df = pd.read_csv(MASTER, encoding="utf-8-sig", dtype={"month": str})
    if df.empty:
        print("chua co du lieu")
        return

    cov = coverage(df)
    print(cov.to_string())

    fanned = cov[cov.cat_ngang > 0]
    if not fanned.empty:
        print(f"\nthang tu bang 'cong bo gan nhat' (KHONG phai khao sat thang): "
              f"{', '.join(fanned.index)}")
        print(f"  -> loc bang df[~df.from_mixed_table] truoc khi tinh trung vi/sai phan")
    thin = cov[(cov.cat_ngang == 0) & (cov.so_nh_khao_sat < MIN_BANKS_FOR_SURVEY)]
    if not thin.empty:
        print(f"thang qua it NH (<{MIN_BANKS_FOR_SURVEY}) du la bang thang: "
              + ", ".join(f"{m} ({int(cov.loc[m, 'so_nh_khao_sat'])} NH)" for m in thin.index))
    print(f"thang dung duoc cho phan tich chuoi: {int(cov.dung_duoc.sum())}/{len(cov)}")

    bc = bank_coverage(df)
    if not bc.empty:
        sparse = bc[bc.ty_le < 0.5]
        print(f"\nNH co mat duoi 50% so thang dung duoc ({int(cov.dung_duoc.sum())} thang):")
        for k, r in sparse.iterrows():
            tick = r.ticker if isinstance(r.ticker, str) and r.ticker else "-"
            print(f"  {k:<14} {int(r.so_thang):>2}/{int(cov.dung_duoc.sum())} thang  ticker={tick}")
        print("  -> nguon khong dang, khong phai loi crawler (VPB chi co trong 1/15 bang goc)")

    rate = df["lending_avg_percent"]
    print(f"\nkhoang lai suat: {rate.min():.2f}% - {rate.max():.2f}%")
    out_of_range = df[(rate < 3) | (rate > 20)]
    print(f"ngoai khoang 3-20%: {len(out_of_range)} dong")

    chk = df.dropna(subset=["change_vs_prev_point"]).copy()
    chk = chk[chk["change_vs_prev_point"].abs() > 0]
    suspicious = chk[
        (chk["change_vs_prev_point"] - chk["lending_avg_percent"]).abs() < 1e-9
    ]
    print(f"dong co 'thay doi' == 'lai suat' (loi nguon): {len(suspicious)}")
    for _, row in suspicious.iterrows():
        print(f"  {row['month']} {row['bank_name']}: {row['lending_avg_percent']}")

    sbv_path = Path("data/loan_rates/loan_industry_avg.csv")
    if sbv_path.exists():
        sbv = pd.read_csv(sbv_path, encoding="utf-8-sig")
        sbv["month"] = sbv["date"].str[:7]
        sbv = sbv.set_index("month")[["loan_vnd_avg_min", "loan_vnd_avg_max"]]
        is_mixed = (df.get("from_mixed_table", pd.Series(False, index=df.index))
                      .fillna(False).astype(bool))
        panel = df[~is_mixed]
        panel = panel[panel.month.isin(cov.index[cov.dung_duoc])]
        med = panel.groupby("month")["lending_avg_percent"].median()
        n_banks = panel.groupby("month")["bank_key"].nunique()
        both = pd.concat([med.rename("median"), n_banks.rename("n"), sbv], axis=1).dropna()
        inside = (both["median"] >= both["loan_vnd_avg_min"]) & (both["median"] <= both["loan_vnd_avg_max"])
        midpoint = (both["loan_vnd_avg_min"] + both["loan_vnd_avg_max"]) / 2
        print(f"\ndoi chieu voi ban cong bo SBV ({len(both)} thang):")
        print(f"  trung vi tung NH nam trong khoang SBV: {inside.sum()}/{len(both)} thang")
        print(f"  tuong quan voi trung diem khoang SBV: r = {both['median'].corr(midpoint):.4f}")
        print(f"  chenh lech trung vi: {(both['median'] - midpoint).median():+.2f} diem")
        for month in both.index[~inside]:
            print(f"  ngoai khoang: {month} (chi {int(both.loc[month, 'n'])} NH cong bo)")

    dep = df.dropna(subset=["deposit_avg_implied_percent"])
    if not dep.empty:
        d = dep["deposit_avg_implied_percent"]
        print(f"\nlai suat huy dong suy ra: {d.min():.2f}% - {d.max():.2f}% "
              f"(trung vi {d.median():.2f}%)")
        print(f"  am hoac < 1%: {(d < 1).sum()} dong")


def run(since: tuple[int, int] = (2024, 3), write: bool = True) -> pd.DataFrame:
    session = requests.Session()
    session.headers.update(HEADERS)
    urls = candidate_urls(since=since, session=session)
    print(f"ung vien: {len(urls)} bai")
    articles = fetch_articles(urls, session=session)
    print(f"bai co nhac 'cho vay binh quan': {len(articles)}")
    df = build_frame(articles)
    print(f"doc duoc {len(df)} dong, {df['month'].nunique() if not df.empty else 0} thang")
    return merge(df, write=write)


if __name__ == "__main__":
    import sys

    if "--validate" in sys.argv:
        validate()
    elif "--coverage" in sys.argv:
        print(coverage().to_string())
    else:
        run()
