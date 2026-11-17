from __future__ import annotations

import json
import os
import statistics
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import pandas as pd

OUT_PATH = "data/macro/world_bank_annual.csv"
LOG_PATH = "crawl_log.txt"
PANEL = "data/model/bank_panel_quarterly.csv"

API = "https://api.worldbank.org/v2/country/VNM/indicator/{code}"
SOURCE_PAGE = "https://data.worldbank.org/indicator/{code}?locations=VN"
START_YEAR, END_YEAR = 2000, 2026

# Ma World Bank -> ten cot trong file ket qua. Chi giu nhung chi tieu that su
# lien quan den de tai; bo qua phan con lai cua WDI.
INDICATORS = {
    "FR.INR.DPST": "deposit_rate_percent",
    "FR.INR.LEND": "lending_rate_percent",
    "FR.INR.LNDP": "rate_spread_point",
    "FR.INR.RINR": "real_rate_percent",
    "FB.AST.NPER.ZS": "npl_percent",
    "FB.BNK.CAPA.ZS": "bank_capital_to_assets_percent",
    "FS.AST.PRVT.GD.ZS": "private_credit_over_gdp_percent",
}

# Mien hop ly de bat loi nguon, khong phai de loc bo gia tri that.
BOUNDS = {
    "deposit_rate_percent": (0.0, 30.0),
    "lending_rate_percent": (0.0, 40.0),
    "rate_spread_point": (-5.0, 20.0),
    # 2010 dat -20,50%: lam phat theo giam phat GDP vot len trong khi lai suat
    # cho vay chi 13,14%. Day la so THAT cua nam do, khong phai loi nguon -
    # nen nguong phai rong hon, giong nguyen tac HARD/SOFT ben validate.py.
    "real_rate_percent": (-30.0, 30.0),
    "npl_percent": (0.0, 50.0),
    "bank_capital_to_assets_percent": (0.0, 30.0),
    "private_credit_over_gdp_percent": (0.0, 300.0),
}


def _log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")


def _get(url, attempts=3, timeout=45):
    last = None
    for i in range(attempts):
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (KLTN research crawler)"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            if i < attempts - 1:
                time.sleep(2 * (i + 1))
    raise RuntimeError(f"khong tai duoc sau {attempts} lan: {url} ({last})")


def fetch(code):
    url = (f"{API.format(code=code)}?format=json&per_page=200"
           f"&date={START_YEAR}:{END_YEAR}")
    payload = _get(url)

    # Loi cua API tra ve dang [{"message": [...]}] chu khong phai [meta, data].
    if not isinstance(payload, list) or len(payload) < 2:
        raise RuntimeError(f"{code}: API tra ve dang la - {str(payload)[:160]}")

    meta, rows = payload[0], payload[1]
    if rows is None:
        return {}, int(meta.get("total", 0))

    values = {}
    for row in rows:
        if row.get("value") is None:
            continue
        values[int(row["date"])] = float(row["value"])
    return values, int(meta.get("total", len(rows)))


def build(write=True):
    frames = {}
    summary = {}
    for code, column in INDICATORS.items():
        values, total = fetch(code)
        frames[column] = values
        summary[column] = {
            "code": code,
            "years_with_value": len(values),
            "years_returned": total,
            "first_year": min(values) if values else None,
            "last_year": max(values) if values else None,
        }

    years = sorted({y for v in frames.values() for y in v})
    table = pd.DataFrame({"year": years})
    for column, values in frames.items():
        table[column] = table["year"].map(values)

    table["source"] = "World Bank WDI"
    table["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
    numeric = [c for c in INDICATORS.values()]
    table[numeric] = table[numeric].round(4)

    if write:
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        table.to_csv(OUT_PATH, index=False, encoding="utf-8-sig",
                     lineterminator="\r\n")
        _log(f"world_bank: {len(table)} nam, {len(INDICATORS)} chi tieu -> {OUT_PATH}")

    return {"rows": len(table), "path": OUT_PATH,
            "year_range": [years[0], years[-1]] if years else None,
            "indicators": summary}


def _corr(left, right):
    n = len(left)
    if n < 3:
        return None
    ml, mr = sum(left) / n, sum(right) / n
    cov = sum((a - ml) * (b - mr) for a, b in zip(left, right))
    var = (sum((a - ml) ** 2 for a in left) * sum((b - mr) ** 2 for b in right)) ** 0.5
    return cov / var if var else None


def _crosscheck(panel, wb, panel_col, wb_col, label, expect_offset=None):
    panel = panel[panel["period"].str.endswith("Q4")].copy()
    panel["year"] = panel["period"].str[:4].astype(int)
    rows = []
    for year, group in panel.groupby("year"):
        series = group[panel_col].dropna()
        target = wb.loc[wb["year"] == year, wb_col]
        if not len(series) or not len(target) or pd.isna(target.iloc[0]):
            continue
        rows.append((year, float(series.median()), float(target.iloc[0])))
    if len(rows) < 3:
        print(f"   {label}: chi {len(rows)} nam trung nhau, khong du de doi chung")
        return

    print(f"   {label}")
    print(f"      {'nam':6s}{'panel':>9s}{'WorldBank':>11s}{'lech':>8s}")
    for year, a, b in rows:
        print(f"      {year:<6d}{a:9.2f}{b:11.2f}{a - b:+8.2f}")
    median_gap = statistics.median(a - b for _, a, b in rows)
    r = _corr([a for _, a, _ in rows], [b for _, _, b in rows])
    print(f"      tuong quan r = {r:+.3f} tren {len(rows)} nam | "
          f"lech trung vi {median_gap:+.2f} diem")
    if expect_offset is not None and abs(median_gap - expect_offset) > 1.0:
        print(f"      [!] lech trung vi da doi nhieu so voi muc da do "
              f"({expect_offset:+.2f}) - xem lai truoc khi trich dan")


def validate():
    if not os.path.exists(OUT_PATH):
        print(f"chua co {OUT_PATH} - chay `python -m crawlers.world_bank` truoc")
        return 1
    wb = pd.read_csv(OUT_PATH, encoding="utf-8-sig")

    print(f"{len(wb)} nam, {wb['year'].min()} -> {wb['year'].max()}\n")

    print("1. Do phu tung chi tieu:")
    for column in INDICATORS.values():
        series = wb[column].dropna()
        if not len(series):
            print(f"   [!] {column:34s} KHONG co gia tri nao")
            continue
        years = wb.loc[series.index, "year"]
        print(f"   {column:34s} {len(series):2d} nam | "
              f"{int(years.min())}-{int(years.max())} | "
              f"gan nhat {series.iloc[-1]:.2f}")
    print()

    print("2. Gia tri ngoai mien hop ly:")
    bad = 0
    for column, (low, high) in BOUNDS.items():
        series = wb[column].dropna()
        out = series[(series < low) | (series > high)]
        if len(out):
            bad += len(out)
            print(f"   [!] {column}: {len(out)} o ngoai [{low}, {high}]")
    print(f"   {'khong co o nao ngoai mien' if not bad else f'{bad} o can xem lai'}")
    print()

    print("3. Nam bi hong giua chuoi (khong tinh phan duoi/tren cua chuoi):")
    holes = 0
    for column in INDICATORS.values():
        series = wb[["year", column]].dropna()
        if len(series) < 3:
            continue
        span = range(int(series["year"].min()), int(series["year"].max()) + 1)
        missing = sorted(set(span) - set(series["year"].astype(int)))
        if missing:
            holes += 1
            print(f"   {column:34s} thieu {missing}")
    print(f"   {'khong chuoi nao bi hong giua' if not holes else f'{holes} chuoi co lo'}")
    print()

    if not os.path.exists(PANEL):
        print("(chua co panel de doi chung)")
        return 0
    panel = pd.read_csv(PANEL, encoding="utf-8-sig")

    print("4. Doi chung voi panel 22 ngan hang (trung vi, quy 4):")
    print("   Hai ben do hai thu khac nhau nen KHONG ky vong bang nhau;")
    print("   cai dang xem la chieu, diem ngoat, va do on dinh cua muc lech.\n")
    _crosscheck(panel, wb, "cof_ttm_percent", "deposit_rate_percent",
                "Chi phi von (COF) vs lai suat tien gui", expect_offset=0.47)
    print()
    _crosscheck(panel, wb, "npl_percent", "npl_percent",
                "NPL nhom niem yet vs NPL toan he thong")
    print()
    _crosscheck(panel, wb, "earning_asset_yield_ttm_percent", "lending_rate_percent",
                "Loi suat tai san sinh loi vs lai suat cho vay")
    print()

    print("5. Khoang cach NPL - phat hien can dua vao luan van:")
    q4 = panel[panel["period"].str.endswith("Q4")].copy()
    q4["year"] = q4["period"].str[:4].astype(int)
    listed = q4.groupby("year")["npl_percent"].median()
    joined = wb.set_index("year")["npl_percent"].rename("he_thong").to_frame()
    joined["niem_yet"] = listed
    joined = joined.dropna()
    joined["khoang_cach"] = joined["he_thong"] - joined["niem_yet"]
    recent = joined[joined.index >= 2023]
    early = joined[joined.index < 2023]
    if len(recent) and len(early):
        print(f"   truoc 2023: khoang cach trung vi "
              f"{early['khoang_cach'].median():+.2f} diem")
        print(f"   tu 2023   : khoang cach trung vi "
              f"{recent['khoang_cach'].median():+.2f} diem")
        print("   -> 22 ngan hang niem yet la nua khoe cua he thong; ket qua xep hang")
        print("      KHONG suy rong ra ca nganh duoc, nhat la tu 2023.")
    return 0


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if "--validate" in sys.argv:
        raise SystemExit(validate())

    result = build()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    validate()
