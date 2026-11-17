from __future__ import annotations

import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

OUT = Path("data/branch_network")
POINTS = OUT / "branch_points.csv"
BY_PROVINCE = OUT / "branch_by_province.csv"
PROVINCES = OUT / "provinces.csv"
TPB_OFFICIAL = OUT / "tpb_official_points.csv"

SOURCE_NAME = "openstreetmap"
SOURCE_URL = "https://www.openstreetmap.org/"
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
HEADERS = {"User-Agent": "KLTN-research/1.0 (thesis data collection; OSM ODbL)"}

TPB_URL = "https://tpb.vn/tim-diem-giao-dich"
TPB_SOURCE = "tpb.vn"

HARVARD = Path("data/external/vn_banking_system_2002_2021_data.csv")
HARVARD_CODE_TO_TICKER = {  # "BVB" cua Harvard la Bao Viet Bank; Ban Viet la "VCPB"
    "BIDV": "BID", "MB": "MBB", "LVB": "LPB", "SEAB": "SSB", "NCB": "NVB", "VCPB": "BVB",
    "BVB": "BAOVIETBANK", "OB": "OCEANBANK",
}

SECONDS_BETWEEN_QUERIES = 2.0
MAX_ATTEMPTS = 4
TIMEOUT = 300

POINT_COLUMNS = [
    "osm_type", "osm_id", "kind", "ticker", "brand_label", "wikidata",
    "province", "lat", "lon", "name", "addr_city", "addr_street",
    "source", "source_url", "retrieved_at_utc",
]

PROVINCE_COLUMNS = [
    "province", "ticker", "n_bank", "n_atm", "n_total",
]

TICKERS = [
    "VCB", "BID", "CTG", "MBB", "ACB", "TCB", "VPB", "STB", "HDB", "VIB", "TPB",
    "MSB", "OCB", "LPB", "SHB", "EIB", "SSB", "BAB", "BVB", "NAB", "NVB", "PGB",
]

BRAND_WIKIDATA = {
    "Q6122995": "VCB", "Q1003180": "BID", "Q7928459": "CTG", "Q10800269": "MBB",
    "Q727019": "ACB", "Q10541776": "TCB", "Q20025914": "VPB", "Q6123772": "STB",
    "Q10800273": "HDB", "Q49054349": "VIB", "Q7801033": "TPB", "Q10800277": "MSB",
    "Q7102288": "OCB", "Q15729124": "LPB", "Q124465825": "SHB", "Q10800271": "EIB",
    "Q10800276": "SSB", "Q10800266": "NAB",
}

NAME_PATTERNS = {
    "VCB": r"\bvietcombank\b|\bvcb\b",
    "BID": r"\bbidv\b",
    "CTG": r"vietin\s?bank|\bctg\b",
    "MBB": r"\bmb\s?bank\b|\bmb\b|military",
    "ACB": r"\bacb\b|acbbank",
    "TCB": r"\btechcombank\b|\btcb\b",
    "VPB": r"\bvp\s?bank\b",
    "STB": r"\bsacombank\b|\bstb\b",
    "HDB": r"\bhd\s?bank\b",
    "VIB": r"\bvib\b",
    "TPB": r"\btp\s?bank\b|\btpb\b",
    "MSB": r"\bmsb\b|maritime",
    "OCB": r"\bocb\b|phuong dong",
    "LPB": r"\blp\s?bank\b|lien\s?viet|loc phat",
    "SHB": r"\bshb\b",
    "EIB": r"\beximbank\b|\beib\b",
    "SSB": r"\bsea\s?bank\b|\bssb\b",
    "BAB": r"\bbac\s?a\b|\bbaca\s?bank\b",
    "BVB": r"\bbv\s?bank\b|ban viet|viet\s?capital",
    "NAB": r"\bnam\s?a\b",
    "NVB": r"\bncb\b|ncbbank|navibank|quoc dan|national citizen",
    "PGB": r"\bpg\s?bank\b|\bpgb\b",
}

NOISE_TOKENS = [
    "ngan hang tmcp", "ngan hang", "chi nhanh", "phong giao dich",
    "may pos", "pos", "atm", "cn ", "pgd ",
]

_COMPILED = {t: re.compile(p) for t, p in NAME_PATTERNS.items()}


def safe_call(label, func):
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return func()
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            pause = min(60, 10 * (2 ** (attempt - 1)))
            print(f"{label}: attempt {attempt}/{MAX_ATTEMPTS} failed ({last_error}); waiting {pause}s")
            time.sleep(pause)
    raise RuntimeError(f"{label}: failed after {MAX_ATTEMPTS} attempts: {last_error}")


def overpass(query: str, label: str) -> list[dict]:
    def _do():
        last = None
        for url in OVERPASS_ENDPOINTS:
            resp = requests.post(url, data={"data": query}, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code == 200:
                return resp.json()["elements"]
            last = f"{url} -> HTTP {resp.status_code}"
        raise RuntimeError(last or "khong endpoint nao tra ve 200")

    return safe_call(label, _do)


def normalise_label(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    for token in NOISE_TOKENS:
        text = text.replace(token, " ")
    return re.sub(r"\s+", " ", text).strip()


def match_ticker(tags: dict) -> tuple[str, str, str]:
    wikidata = tags.get("brand:wikidata") or tags.get("operator:wikidata") or ""
    label = tags.get("brand") or tags.get("operator") or tags.get("name") or ""
    if wikidata in BRAND_WIKIDATA:
        return BRAND_WIKIDATA[wikidata], label, wikidata
    normalised = normalise_label(label)
    if normalised:
        for ticker, pattern in _COMPILED.items():
            if pattern.search(normalised):
                return ticker, label, wikidata
    return "", label, wikidata


def fetch_provinces() -> pd.DataFrame:
    query = (
        '[out:json][timeout:180];'
        'area["ISO3166-1"="VN"][admin_level=2]->.vn;'
        'rel(area.vn)["admin_level"="4"]["boundary"="administrative"];'
        'out tags;'
    )
    elements = overpass(query, "provinces")
    rows = [{
        "osm_rel_id": e["id"],
        "area_id": 3600000000 + e["id"],
        "province": e.get("tags", {}).get("name", ""),
    } for e in elements]
    frame = pd.DataFrame(rows).sort_values("province").reset_index(drop=True)
    OUT.mkdir(parents=True, exist_ok=True)
    frame.to_csv(PROVINCES, index=False, encoding="utf-8-sig")
    return frame


def load_provinces(refresh: bool = False) -> pd.DataFrame:
    if not refresh and PROVINCES.exists():
        return pd.read_csv(PROVINCES, encoding="utf-8-sig")
    return fetch_provinces()


def fetch_province_points(area_id: int, province: str, retrieved_at: str) -> pd.DataFrame:
    query = (
        f'[out:json][timeout:180];area({area_id})->.p;'
        '(node["amenity"~"^(bank|atm)$"](area.p);'
        'way["amenity"~"^(bank|atm)$"](area.p););'
        'out tags center;'
    )
    elements = overpass(query, f"province {province}")
    rows = []
    for e in elements:
        tags = e.get("tags", {})
        ticker, label, wikidata = match_ticker(tags)
        centre = e.get("center") or {}
        rows.append({
            "osm_type": e.get("type"),
            "osm_id": e.get("id"),
            "kind": tags.get("amenity"),
            "ticker": ticker,
            "brand_label": label,
            "wikidata": wikidata,
            "province": province,
            "lat": e.get("lat", centre.get("lat")),
            "lon": e.get("lon", centre.get("lon")),
            "name": tags.get("name", ""),
            "addr_city": tags.get("addr:city", ""),
            "addr_street": tags.get("addr:street", ""),
            "source": SOURCE_NAME,
            "source_url": SOURCE_URL,
            "retrieved_at_utc": retrieved_at,
        })
    return pd.DataFrame(rows, columns=POINT_COLUMNS)


def build_points(refresh_provinces: bool = False) -> pd.DataFrame:
    OUT.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    provinces = load_provinces(refresh_provinces)

    frames, failures = [], []
    for _, row in provinces.iterrows():
        try:
            frame = fetch_province_points(int(row["area_id"]), row["province"], retrieved_at)
        except Exception as exc:
            failures.append((row["province"], str(exc)[:120]))
            print(f'{row["province"]:<28} LOI: {str(exc)[:100]}')
            continue
        frames.append(frame)
        mapped = int(frame["ticker"].ne("").sum())
        print(f'{row["province"]:<28} {len(frame):>5} POI  '
              f'{mapped:>5} thuoc 22 NH  '
              f'{int(frame["kind"].eq("bank").sum()):>4} bank / '
              f'{int(frame["kind"].eq("atm").sum()):>5} atm')
        time.sleep(SECONDS_BETWEEN_QUERIES)

    if failures:
        print(f"\n{len(failures)} tinh that bai:")
        for province, message in failures:
            print(f"  {province}: {message}")

    points = (pd.concat(frames, ignore_index=True) if frames
              else pd.DataFrame(columns=POINT_COLUMNS))
    points = points.drop_duplicates(subset=["osm_type", "osm_id"], keep="first")
    points = points.sort_values(["ticker", "province", "kind", "osm_id"])
    points.to_csv(POINTS, index=False, encoding="utf-8-sig")
    return points


def load_points() -> pd.DataFrame:
    if not POINTS.exists():
        return pd.DataFrame(columns=POINT_COLUMNS)
    return pd.read_csv(POINTS, encoding="utf-8-sig")


def build_by_province(points: pd.DataFrame | None = None) -> pd.DataFrame:
    if points is None:
        points = load_points()
    if points.empty:
        return pd.DataFrame(columns=PROVINCE_COLUMNS)

    mapped = points[points["ticker"].fillna("").ne("")]
    grid = mapped.pivot_table(index=["province", "ticker"], columns="kind",
                              values="osm_id", aggfunc="count").fillna(0)
    for kind in ("bank", "atm"):
        if kind not in grid.columns:
            grid[kind] = 0
    grid = grid.rename(columns={"bank": "n_bank", "atm": "n_atm"}).reset_index()
    grid["n_bank"] = grid["n_bank"].astype(int)
    grid["n_atm"] = grid["n_atm"].astype(int)
    grid["n_total"] = grid["n_bank"] + grid["n_atm"]
    grid = grid[PROVINCE_COLUMNS].sort_values(["ticker", "province"])
    OUT.mkdir(parents=True, exist_ok=True)
    grid.to_csv(BY_PROVINCE, index=False, encoding="utf-8-sig")
    return grid


def summary(points: pd.DataFrame | None = None) -> pd.DataFrame:
    grid = build_by_province(points)
    if grid.empty:
        return pd.DataFrame()
    n_provinces = len(load_provinces())
    rows = []
    for ticker, g in grid.groupby("ticker"):
        rows.append({
            "ticker": ticker,
            "n_bank": int(g["n_bank"].sum()),
            "n_atm": int(g["n_atm"].sum()),
            "n_total": int(g["n_total"].sum()),
            "provinces_present": int(g["province"].nunique()),
            "provinces_total": n_provinces,
            "province_coverage": round(g["province"].nunique() / n_provinces, 4),
            "top_province": g.sort_values("n_total", ascending=False)["province"].iloc[0],
        })
    frame = pd.DataFrame(rows)
    ordered = [t for t in TICKERS if t in set(frame["ticker"])]
    frame["order"] = frame["ticker"].map({t: i for i, t in enumerate(ordered)})
    return frame.sort_values("n_total", ascending=False).drop(columns="order")


def unmapped(points: pd.DataFrame | None = None, top: int = 30) -> pd.DataFrame:
    if points is None:
        points = load_points()
    if points.empty:
        return pd.DataFrame()
    rest = points[points["ticker"].fillna("").eq("")]
    counts = rest["brand_label"].fillna("").replace("", "(khong ten)").value_counts()
    return counts.head(top).rename_axis("brand_label").reset_index(name="n")


def tpb_official() -> pd.DataFrame:
    resp = safe_call("tpb.vn", lambda: requests.get(
        TPB_URL, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                                        "Chrome/124.0.0.0 Safari/537.36"}, timeout=40))
    text = resp.text
    anchor = re.search(r"danhSachLocation\s*=\s*\[", text)
    if anchor is None:
        raise RuntimeError("tpb.vn: khong tim thay mang danhSachLocation")
    start = anchor.end() - 1
    depth, end = 0, -1
    for i in range(start, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end == -1:
        raise RuntimeError("tpb.vn: mang danhSachLocation khong dong ngoac")

    records = json.loads(text[start:end])
    retrieved_at = datetime.now(timezone.utc).isoformat()
    rows = [{
        "ticker": "TPB",
        "kind": ("livebank" if "livebank" in str(r.get("title", "")).lower()
                 else "branch"),
        "raw_type": r.get("type", ""),
        "title": r.get("title", ""),
        "address": r.get("content", ""),
        "lat": (r.get("position") or {}).get("latitude", ""),
        "lon": (r.get("position") or {}).get("longitude", ""),
        "source": TPB_SOURCE,
        "source_url": TPB_URL,
        "retrieved_at_utc": retrieved_at,
    } for r in records]

    frame = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    frame.to_csv(TPB_OFFICIAL, index=False, encoding="utf-8-sig")
    return frame


def cross_check_harvard(points: pd.DataFrame | None = None) -> pd.DataFrame:
    if not HARVARD.exists():
        print("khong tim thay dataset Harvard -- bo qua phep chieu chieu")
        return pd.DataFrame()
    harvard = pd.read_csv(HARVARD)
    harvard["ticker"] = harvard["Bank Code"].map(HARVARD_CODE_TO_TICKER).fillna(harvard["Bank Code"])
    branches = harvard[harvard["Number of Branches"].notna()]
    latest = branches.sort_values("Year").groupby("ticker").tail(1)
    latest = latest[["ticker", "Year", "Number of Branches"]].rename(
        columns={"Year": "harvard_year", "Number of Branches": "harvard_branches"})

    osm = summary(points)
    if osm.empty:
        return pd.DataFrame()
    merged = osm.merge(latest, on="ticker", how="inner")
    merged["harvard_branches"] = merged["harvard_branches"].astype(int)
    merged["ratio_osm_over_harvard"] = (merged["n_bank"] / merged["harvard_branches"]).round(3)
    return merged.sort_values("harvard_branches", ascending=False)


def run(refresh_provinces: bool = False) -> dict:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    points = build_points(refresh_provinces)
    grid = build_by_province(points)
    table = summary(points)

    mapped = int(points["ticker"].fillna("").ne("").sum())
    tickers_seen = int(points.loc[points["ticker"].fillna("").ne(""), "ticker"].nunique())

    with open("crawl_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{retrieved_at}] branch_network: {len(points)} POI, {mapped} thuoc 22 NH, "
                f"{tickers_seen}/{len(TICKERS)} ticker, {len(grid)} dong bank-province, "
                f"{len(load_provinces())} tinh\n")

    return {"points": len(points), "mapped": mapped, "tickers_seen": tickers_seen,
            "bank_province_rows": len(grid), "summary_rows": len(table)}


def validate(points: pd.DataFrame | None = None) -> None:
    if points is None:
        points = load_points()
    if points.empty:
        print("chua co du lieu -- chay `python -m crawlers.branch_network` truoc")
        return

    points["ticker"] = points["ticker"].fillna("")
    provinces = load_provinces()
    mapped = points[points["ticker"].ne("")]
    seen = set(mapped["ticker"])

    print(f"{len(points)} POI, {len(mapped)} thuoc 22 NH ({len(mapped) / len(points):.1%}), "
          f"{len(seen)}/{len(TICKERS)} ticker, {points['province'].nunique()}/{len(provinces)} tinh")
    print()

    absent = [t for t in TICKERS if t not in seen]
    print(f"1. Ticker vang mat: {len(absent)}/{len(TICKERS)} -> {absent or 'khong thieu'}")
    print()

    table = summary(points)
    print("2. Mang luoi theo ngan hang (OSM, KHONG phai so chinh thuc):")
    for _, r in table.iterrows():
        print(f"   {r['ticker']:5s} {r['n_bank']:>5} diem giao dich  {r['n_atm']:>5} ATM  "
              f"= {r['n_total']:>5}  phu {r['provinces_present']:>2}/{r['provinces_total']} tinh "
              f"({r['province_coverage']:.0%})  dong nhat: {r['top_province']}")
    print()

    thin = table[table["province_coverage"] < 0.5]
    print(f"3. Ngan hang phu duoi 50% so tinh: {len(thin)}/{len(table)}")
    for _, r in thin.iterrows():
        print(f"   {r['ticker']:5s} chi co mat {r['provinces_present']}/{r['provinces_total']} tinh")
    print()

    dup = int(points.duplicated(subset=["osm_type", "osm_id"]).sum())
    print(f"4. Dong trung khoa (osm_type, osm_id): {dup}")
    print()

    rest = unmapped(points)
    total_unmapped = len(points) - len(mapped)
    print(f"5. POI khong map duoc: {total_unmapped} ({total_unmapped / len(points):.1%}) "
          f"-- module KHONG doan, liet ke de mo rong NAME_PATTERNS:")
    for _, r in rest.head(15).iterrows():
        print(f"   {r['n']:>5}  {r['brand_label']}")
    print()

    empty_province = points[points["province"].fillna("").eq("")]
    print(f"6. POI khong gan duoc tinh: {len(empty_province)}")
    print()

    check = cross_check_harvard(points)
    print("7. Doi chieu voi Harvard Number of Branches "
          "(DON VI KHAC NHAU -- chi doc thu hang, khong doc muc):")
    if check.empty:
        print("   khong doi chieu duoc")
    else:
        rank = check[["n_bank", "harvard_branches"]].corr(method="spearman").iloc[0, 1]
        pearson = check[["n_bank", "harvard_branches"]].corr().iloc[0, 1]
        print(f"   n = {len(check)} ngan hang | Spearman = {rank:.3f} | Pearson = {pearson:.3f}")
        for _, r in check.iterrows():
            print(f"   {r['ticker']:5s} OSM {r['n_bank']:>5}  Harvard {r['harvard_branches']:>5} "
                  f"({int(r['harvard_year'])})  ty le {r['ratio_osm_over_harvard']}")
    print()

    print("8. Doi chieu doc lap TPB (tpb.vn, ban NH tu cong bo):")
    if TPB_OFFICIAL.exists():
        official = pd.read_csv(TPB_OFFICIAL, encoding="utf-8-sig")
        osm_tpb = int(mapped[(mapped["ticker"] == "TPB")
                             & (mapped["kind"] == "bank")].shape[0])
        osm_tpb_all = int(mapped[mapped["ticker"] == "TPB"].shape[0])
        print(f"   tpb.vn: {len(official)} diem "
              f"({int(official['kind'].eq('branch').sum())} chi nhanh / "
              f"{int(official['kind'].eq('livebank').sum())} LiveBank)")
        print(f"   OSM   : {osm_tpb} diem giao dich, {osm_tpb_all} ke ca ATM")
        if len(official):
            print(f"   ty le OSM/cong bo = {osm_tpb_all / len(official):.2f}")
    else:
        print("   chua co -- chay `python -m crawlers.branch_network --tpb`")


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    argv = sys.argv[1:]

    if "--validate" in argv:
        validate()
    elif "--provinces" in argv:
        print(fetch_provinces().to_string(index=False))
    elif "--summary" in argv:
        print(summary().to_string(index=False))
    elif "--unmapped" in argv:
        print(unmapped(top=50).to_string(index=False))
    elif "--cross-check" in argv:
        print(cross_check_harvard().to_string(index=False))
    elif "--tpb" in argv:
        frame = tpb_official()
        print(f"{len(frame)} diem tu tpb.vn -> {TPB_OFFICIAL}")
        print(frame["kind"].value_counts().to_string())
    else:
        result = run(refresh_provinces="--refresh-provinces" in argv)
        print(f"\n{result['points']} POI | {result['mapped']} thuoc 22 NH | "
              f"{result['tickers_seen']}/{len(TICKERS)} ticker | "
              f"{result['bank_province_rows']} dong bank-province")
