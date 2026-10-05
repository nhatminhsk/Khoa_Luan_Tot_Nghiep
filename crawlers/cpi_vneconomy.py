from __future__ import annotations

import html
import re

import pandas as pd
import requests

from crawlers import cpi_nso, macro

HEADERS = cpi_nso.HEADERS

SOURCES: dict[str, str] = {
    "2019-04": "https://vneconomy.vn/cpi-binh-quan-4-thang-nam-2019-tang-thap-nhat-trong-3-nam.htm",
    "2021-11": "https://vneconomy.vn/gia-xang-dau-leo-thang-keo-cpi-thang-11-tang.htm",
    "2025-06": "https://vneconomy.vn/cpi-binh-quan-6-thang-tang-3-27-lam-phat-van-trong-tam-kiem-soat.htm",
    "2025-09": "https://vneconomy.vn/cpi-thang-9-tang-042-lam-phat-van-trong-tam-kiem-soat.htm",
}

MANUAL: dict[str, tuple[str, float, str, str]] = {
    "2019-10": (
        "cpi_mom_percent", 0.59,
        "https://tuoitre.vn/cpi-thang-10-tang-0-59-20191029093445899.htm",
        "Ban cong bo NSO thang 10/2019 khong neu MoM cua CPI, chi neu lam phat co ban",
    ),
    "2019-12": (
        "cpi_yoy_percent", 5.23,
        "https://bnews.vn/nam-2019-cpi-tang-binh-quan-thap-nhat-trong-3-nam-gan-day/143613.html",
        "Ban cong bo NSO thang 12/2019 khong neu YoY cua CPI, chi neu lam phat co ban. "
        "Ban tin TTXVN dan hop bao Tong cuc Thong ke: 'CPI thang 12 nam 2019 tang 1,4% so voi "
        "thang truoc va tang 5,23% so voi thang 12 nam 2018'. Bai Vietstock trich truoc day "
        "KHONG chua con so 5,23 - chi co MoM 1,4 va binh quan nam 2,79.",
    ),
    "2019-09": (
        "cpi_yoy_percent", 1.98,
        "https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2019/10/"
        "bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2019/",
        "Ban cong bo NSO thang 9/2019 khong neu YoY cua CPI, chi neu lam phat co ban (1,96). "
        "Bao cao quy III neu nguyen van 'tang 1,98% so voi cung ky nam 2018'. Truoc day tro "
        "vao gso.gov.vn - ten mien do nay chi phuc vu chung chi cua nso.gov.vn nen khong ket "
        "noi duoc; day la cung mot trang tren ten mien moi.",
    ),
    "2020-07": (
        "cpi_yoy_percent", 3.39,
        "",
        "SUY RA, chua co trich dan truc tiep. Ban cong bo NSO thang 7/2020 khong neu YoY "
        "cua CPI, chi neu lam phat co ban (2,31). Tinh tu 3,17 (T6/2020) x (1+0,0040)/(1+0,0018); "
        "kiem cheo nguoc ra 3,17 cho T8/2020 (file co 3,18) va dua binh quan nam 2020 "
        "len 3,24 so voi 3,23 cong bo. CAN XAC MINH truoc khi trich dan trong luan van.",
    ),
}

UNRESOLVED: tuple[str, ...] = ()


def article_text(url: str, session: requests.Session | None = None) -> str:
    s = session or requests.Session()
    s.headers.update(HEADERS)
    raw = s.get(url, timeout=60).text
    raw = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", raw)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)))


def build_frame(session: requests.Session | None = None) -> pd.DataFrame:
    s = session or requests.Session()
    rows = []
    for month, url in sorted(SOURCES.items()):
        mom, yoy = cpi_nso.parse_figures(article_text(url, s), month, truncate=False)
        if mom is None and yoy is None:
            continue
        rows.append({
            "month": month,
            "cpi_yoy_percent": yoy,
            "cpi_mom_percent": mom,
            "source_url": url,
            "note": f"VnEconomy - bu khuyet cho ban cong bo NSO thang {month}",
        })
    return pd.DataFrame(rows, columns=macro.CPI_COLUMNS)


def backfill(write: bool = True) -> pd.DataFrame:
    macro.ensure_files()
    fills = build_frame().set_index("month")
    existing = pd.read_csv(macro.cpi_path(), encoding="utf-8-sig", dtype={"month": str})
    existing = existing.set_index("month")

    filled = []
    for month, row in fills.iterrows():
        if month not in existing.index:
            existing.loc[month] = row
            filled.append(f"{month} (thang moi)")
            continue
        for column in ("cpi_yoy_percent", "cpi_mom_percent"):
            if pd.isna(existing.loc[month, column]) and pd.notna(row[column]):
                existing.loc[month, column] = row[column]
                existing.loc[month, "note"] = (
                    f"{existing.loc[month, 'note']} | {column} bu tu VnEconomy: {row['source_url']}"
                )
                filled.append(f"{month}.{column}")

    for month, (column, value, url, note) in MANUAL.items():
        if month not in existing.index:
            continue
        annotation = f"{column}={value} ({note}): {url}".rstrip(": ")
        current = str(existing.loc[month, "note"])
        stripped = re.sub(rf"\s*\|\s*{re.escape(column)}=.*?(?=\s\|\s|$)", "", current)
        if existing.loc[month, column] != value or current != f"{stripped} | {annotation}":
            existing.loc[month, column] = value
            existing.loc[month, "note"] = f"{stripped} | {annotation}"
            filled.append(f"{month}.{column} (sua tay)")

    result = existing.sort_index().reset_index()
    if write:
        result.to_csv(macro.cpi_path(), index=False, encoding="utf-8-sig")
    print("Da bu:", ", ".join(filled) if filled else "khong co o nao trong")
    return result


if __name__ == "__main__":
    df = backfill()
    print(f"cpi.csv: {len(df)} thang, thieu yoy {int(df['cpi_yoy_percent'].isna().sum())}, "
          f"thieu mom {int(df['cpi_mom_percent'].isna().sum())}")
    print(f"Chua bu duoc: {', '.join(UNRESOLVED)}")
