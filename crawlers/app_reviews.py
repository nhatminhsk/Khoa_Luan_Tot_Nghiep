from __future__ import annotations

import socket
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

OUT = Path("data/app_reviews")
CATALOG = OUT / "app_catalog.csv"
MONTHLY = OUT / "app_reviews_monthly.csv"

SOURCE_NAME = "google_play"
STORE_URL = "https://play.google.com/store/apps/details?id={app_id}&hl=vi&gl=VN"
SEARCH_URL = "https://play.google.com/store/search"

LANG = "vi"
COUNTRY = "vn"

BATCH = 200
SECONDS_BETWEEN_BATCHES = 0.2
SECONDS_BETWEEN_APPS = 1.0
MAX_ATTEMPTS = 4

OVERLAP_DAYS = 3
MAX_REVIEWS_PER_APP = 60000
SOCKET_TIMEOUT = 60

DROPPED_PERSONAL_FIELDS = ("userName", "userImage")

COLUMNS = [
    "ticker", "app_id", "app_role", "review_id", "at_utc", "score", "thumbs_up",
    "app_version", "content", "replied", "replied_at_utc",
    "source", "source_url", "retrieved_at_utc",
]

CATALOG_COLUMNS = [
    "date", "ticker", "app_id", "app_role", "app_name", "title", "developer",
    "score", "ratings", "reviews_with_text", "installs", "min_installs",
    "version", "released", "last_updated", "source", "source_url", "retrieved_at_utc",
]

MONTHLY_COLUMNS = [
    "month", "ticker", "app_id", "app_role", "n_reviews", "mean_score", "median_score",
    "pct_1star", "pct_5star", "pct_with_content", "n_with_content", "thumbs_up_sum",
    "n_versions", "reply_rate", "bombing_days", "usable",
]

TICKERS = [
    "VCB", "BID", "CTG", "MBB", "ACB", "TCB", "VPB", "STB", "HDB", "VIB", "TPB",
    "MSB", "OCB", "LPB", "SHB", "EIB", "SSB", "BAB", "BVB", "NAB", "NVB", "PGB",
]

APPS = {
    "VCB": [{"app_id": "com.VCB", "app_name": "VCB Digibank", "role": "retail"}],
    "BID": [{"app_id": "com.vnpay.bidv", "app_name": "BIDV SmartBanking", "role": "retail"}],
    "CTG": [{"app_id": "com.vietinbank.ipay", "app_name": "VietinBank iPay", "role": "retail"}],
    "MBB": [{"app_id": "com.mbmobile", "app_name": "MB Bank", "role": "retail"}],
    "ACB": [{"app_id": "mobile.acb.com.vn", "app_name": "ACB ONE", "role": "retail"}],
    "TCB": [{"app_id": "vn.com.techcombank.bb.app", "app_name": "Techcombank Mobile", "role": "retail"}],
    "VPB": [{"app_id": "com.vnpay.vpbankonline", "app_name": "VPBank NEO", "role": "retail"}],
    "STB": [
        {"app_id": "src.com.sacombank", "app_name": "SACOMBANK mBanking", "role": "retail"},
        {"app_id": "com.sacombank.ewallet", "app_name": "SACOMBANK PAY", "role": "wallet"},
    ],
    "HDB": [{"app_id": "com.vnpay.hdbank", "app_name": "HDBank", "role": "retail"}],
    "VIB": [{"app_id": "com.vib.myvib2", "app_name": "MyVIB", "role": "retail"}],
    "TPB": [
        {"app_id": "com.tpb.mb.gprsandroid", "app_name": "TPBank Mobile", "role": "retail"},
        {"app_id": "vn.tpbank.savy", "app_name": "TPBank Savy", "role": "savings"},
    ],
    "MSB": [
        {"app_id": "vn.com.msb.smartBanking", "app_name": "MSB mBank (Ca nhan)", "role": "retail"},
        {"app_id": "com.msb.digibank.retail", "app_name": "MSB Digital Bank", "role": "successor"},
    ],
    "OCB": [{"app_id": "vn.com.ocb.awe", "app_name": "OCB OMNI", "role": "retail"}],
    "LPB": [
        {"app_id": "vn.com.lpb.lienviet24h", "app_name": "LPBank", "role": "retail"},
        {"app_id": "vn.com.lpbank.digibank", "app_name": "LPBank Plus", "role": "successor"},
    ],
    "SHB": [{"app_id": "vn.shb.saha.mbanking", "app_name": "SHB SAHA", "role": "retail"}],
    "EIB": [{"app_id": "com.vnpay.EximBankOmni", "app_name": "Eximbank EDigi", "role": "retail"}],
    "SSB": [{"app_id": "vn.com.seabank.mb1", "app_name": "SeAMobile", "role": "retail"}],
    "BAB": [{"app_id": "com.bab.retailUAT", "app_name": "BAC A BANK Mobile Banking", "role": "retail"}],
    "BVB": [
        {"app_id": "vn.banvietbank.mobilebanking", "app_name": "digimi", "role": "retail"},
        {"app_id": "io.lifestyle.plus", "app_name": "Timo by BVBank", "role": "partner"},
    ],
    "NAB": [{"app_id": "ops.namabank.com.vn", "app_name": "Nam A Bank Open Banking", "role": "retail"}],
    "NVB": [{"app_id": "com.ncb.bank", "app_name": "NCB iziMobile", "role": "retail"}],
    "PGB": [{"app_id": "pgbankApp.pgbank.com.vn", "app_name": "PGBank", "role": "retail"}],
}

DISCOVER_QUERIES = {
    "VCB": "Vietcombank", "BID": "BIDV SmartBanking", "CTG": "VietinBank iPay",
    "MBB": "MBBank", "ACB": "ACB ONE", "TCB": "Techcombank", "VPB": "VPBank NEO",
    "STB": "Sacombank", "HDB": "HDBank", "VIB": "MyVIB", "TPB": "TPBank",
    "MSB": "MSB mBank", "OCB": "OCB OMNI", "LPB": "LPBank", "SHB": "SHB ngan hang",
    "EIB": "Eximbank", "SSB": "SeABank", "BAB": "BacABank", "BVB": "BVBank Digimi",
    "NAB": "Nam A Bank", "NVB": "NCB iziMobile", "PGB": "PGBank",
}

DEFAULT_ROLES = ("retail",)

MIN_REVIEWS_PER_MONTH = 10
BOMBING_MIN_REVIEWS = 20
BOMBING_DAILY_FACTOR = 5.0
BOMBING_MIN_1STAR_SHARE = 0.6


def _require_scraper():
    try:
        from google_play_scraper import Sort, app as gp_app, reviews as gp_reviews
    except ImportError as exc:
        raise RuntimeError(
            "thieu google-play-scraper: pip install google-play-scraper (xem requirements.txt)"
        ) from exc
    return Sort, gp_app, gp_reviews


def safe_call(label, func):
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return func()
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            pause = min(60, 5 * (2 ** (attempt - 1)))
            print(f"{label}: attempt {attempt}/{MAX_ATTEMPTS} failed ({last_error}); waiting {pause}s")
            time.sleep(pause)
    raise RuntimeError(f"{label}: failed after {MAX_ATTEMPTS} attempts: {last_error}")


def path_for(ticker: str) -> Path:
    return OUT / f"{ticker}.csv"


def selected_apps(tickers: list[str] | None = None,
                  roles: tuple[str, ...] = DEFAULT_ROLES) -> list[tuple[str, dict]]:
    pairs = []
    for ticker in (tickers or TICKERS):
        for entry in APPS.get(ticker, []):
            if roles and entry["role"] not in roles:
                continue
            pairs.append((ticker, entry))
    return pairs


def _stamp(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, float) and pd.isna(value):
        return ""
    return pd.Timestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def _epoch_stamp(value) -> str:
    if value is None or isinstance(value, str):
        return value or ""
    try:
        return pd.Timestamp(int(value), unit="s").strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return ""


def _normalise(raw: list[dict], ticker: str, entry: dict, retrieved_at: str) -> pd.DataFrame:
    rows = []
    for r in raw:
        content = (r.get("content") or "").replace("\r", " ").replace("\n", " ").strip()
        rows.append({
            "ticker": ticker,
            "app_id": entry["app_id"],
            "app_role": entry["role"],
            "review_id": r.get("reviewId"),
            "at_utc": _stamp(r.get("at")),
            "score": r.get("score"),
            "thumbs_up": r.get("thumbsUpCount"),
            "app_version": r.get("reviewCreatedVersion") or r.get("appVersion") or "",
            "content": content,
            "replied": bool(r.get("replyContent")),
            "replied_at_utc": _stamp(r.get("repliedAt")),
            "source": SOURCE_NAME,
            "source_url": STORE_URL.format(app_id=entry["app_id"]),
            "retrieved_at_utc": retrieved_at,
        })
    return pd.DataFrame(rows, columns=COLUMNS)


def fetch_reviews(entry: dict, stop_at: pd.Timestamp | None,
                  max_reviews: int) -> tuple[list[dict], str, str]:
    Sort, _, gp_reviews = _require_scraper()
    app_id = entry["app_id"]
    token = None
    collected: list[dict] = []
    reason = "max_reviews"

    while len(collected) < max_reviews:
        current = token
        batch, token = safe_call(
            f"{app_id} batch {len(collected) // BATCH + 1}",
            lambda: gp_reviews(app_id, lang=LANG, country=COUNTRY, sort=Sort.NEWEST,
                               count=BATCH, continuation_token=current),
        )
        if not batch:
            if not collected:
                raise RuntimeError(
                    f"{app_id}: batch dau tien rong -- nhieu kha nang mat mang/DNS, "
                    "KHONG phai app het review")
            reason = "het_review"
            break
        collected.extend(batch)
        if len(collected) % (BATCH * 25) == 0:
            print(f"   {app_id}: {len(collected)} review", flush=True)
        stamps = [r["at"] for r in batch if r.get("at")]
        oldest = min(stamps) if stamps else None
        if stop_at is not None and oldest is not None and pd.Timestamp(oldest) < stop_at:
            reason = "cham_moc_cu"
            break
        if token is None:
            reason = "het_token"
            break
        time.sleep(SECONDS_BETWEEN_BATCHES)

    all_stamps = [r["at"] for r in collected if r.get("at")]
    oldest_at = _stamp(min(all_stamps)) if all_stamps else ""
    return collected, reason, oldest_at


def update_app(ticker: str, entry: dict, retrieved_at: str, backfill: bool = False,
               max_reviews: int = MAX_REVIEWS_PER_APP) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    path = path_for(ticker)
    existing = (pd.read_csv(path, encoding="utf-8-sig", dtype={"review_id": str})
                if path.exists() else pd.DataFrame(columns=COLUMNS))

    same_app = existing[existing["app_id"] == entry["app_id"]] if len(existing) else existing
    stop_at = None
    if not backfill and len(same_app):
        newest = pd.to_datetime(same_app["at_utc"], errors="coerce").max()
        if pd.notna(newest):
            stop_at = newest - timedelta(days=OVERLAP_DAYS)

    raw, reason, oldest_at = fetch_reviews(entry, stop_at, max_reviews)
    fresh = _normalise(raw, ticker, entry, retrieved_at)

    known = set(same_app["review_id"]) if len(same_app) else set()
    n_new = int((~fresh["review_id"].isin(known)).sum()) if len(fresh) else 0

    merged = pd.concat([existing, fresh], ignore_index=True) if len(fresh) else existing
    merged = merged.drop_duplicates(subset=["app_id", "review_id"], keep="last")
    merged = merged.sort_values(["app_id", "at_utc"])
    merged.to_csv(path, index=False, encoding="utf-8-sig")

    app_rows = merged[merged["app_id"] == entry["app_id"]]
    first = last = ""
    if len(app_rows):
        stamps = app_rows["at_utc"].dropna().astype(str)
        first, last = stamps.min()[:10], stamps.max()[:10]

    return {
        "ticker": ticker, "app_id": entry["app_id"], "app_role": entry["role"],
        "fetched": len(fresh), "new": n_new, "rows": len(app_rows),
        "stop_reason": reason, "oldest_fetched": oldest_at[:10],
        "first": first, "last": last,
    }


def update_all(tickers: list[str] | None = None, roles: tuple[str, ...] = DEFAULT_ROLES,
               backfill: bool = False, max_reviews: int = MAX_REVIEWS_PER_APP) -> pd.DataFrame:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    previous_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(SOCKET_TIMEOUT)
    results, failures = [], []
    for ticker, entry in selected_apps(tickers, roles):
        try:
            summary = update_app(ticker, entry, retrieved_at, backfill, max_reviews)
            results.append(summary)
            print(f'{ticker:5s} {entry["app_id"]:<32} +{summary["new"]:>6} moi  '
                  f'{summary["rows"]:>7} dong  {summary["first"]} -> {summary["last"]}  '
                  f'({summary["stop_reason"]})', flush=True)
        except Exception as exc:
            failures.append((ticker, entry["app_id"], str(exc)[:120]))
            print(f'{ticker:5s} {entry["app_id"]:<32} LOI: {str(exc)[:120]}', flush=True)
        time.sleep(SECONDS_BETWEEN_APPS)
    socket.setdefaulttimeout(previous_timeout)

    if failures:
        print(f"\n{len(failures)} app that bai:")
        for ticker, app_id, message in failures:
            print(f"  {ticker} {app_id}: {message}")
    return pd.DataFrame(results)


def fetch_catalog(tickers: list[str] | None = None,
                  roles: tuple[str, ...] = DEFAULT_ROLES) -> pd.DataFrame:
    _, gp_app, _ = _require_scraper()
    socket.setdefaulttimeout(SOCKET_TIMEOUT)
    OUT.mkdir(parents=True, exist_ok=True)
    run_date = datetime.now().strftime("%Y-%m-%d")
    retrieved_at = datetime.now(timezone.utc).isoformat()

    rows = []
    for ticker, entry in selected_apps(tickers, roles):
        app_id = entry["app_id"]
        try:
            d = safe_call(f"catalog {app_id}",
                          lambda: gp_app(app_id, lang=LANG, country=COUNTRY))
        except Exception as exc:
            print(f"{ticker:5s} {app_id:<32} catalog LOI: {str(exc)[:100]}")
            continue
        rows.append({
            "date": run_date, "ticker": ticker, "app_id": app_id,
            "app_role": entry["role"], "app_name": entry["app_name"],
            "title": d.get("title"), "developer": d.get("developer"),
            "score": d.get("score"), "ratings": d.get("ratings"),
            "reviews_with_text": d.get("reviews"), "installs": d.get("installs"),
            "min_installs": d.get("minInstalls"), "version": d.get("version"),
            "released": d.get("released"), "last_updated": _epoch_stamp(d.get("updated")),
            "source": SOURCE_NAME, "source_url": STORE_URL.format(app_id=app_id),
            "retrieved_at_utc": retrieved_at,
        })
        time.sleep(SECONDS_BETWEEN_BATCHES)

    fresh = pd.DataFrame(rows, columns=CATALOG_COLUMNS)
    if CATALOG.exists():
        existing = pd.read_csv(CATALOG, encoding="utf-8-sig")
        combined = pd.concat([existing, fresh], ignore_index=True)
    else:
        combined = fresh
    combined = combined.drop_duplicates(subset=["date", "app_id"], keep="last")
    combined = combined.sort_values(["date", "ticker", "app_id"])
    combined.to_csv(CATALOG, index=False, encoding="utf-8-sig")
    return fresh


def load_reviews(tickers: list[str] | None = None) -> pd.DataFrame:
    frames = []
    for ticker in (tickers or TICKERS):
        path = path_for(ticker)
        if path.exists():
            frames.append(pd.read_csv(path, encoding="utf-8-sig", dtype={"review_id": str}))
    if not frames:
        return pd.DataFrame(columns=COLUMNS)
    return pd.concat(frames, ignore_index=True)


def _daily_stats(group: pd.DataFrame):
    daily = group.groupby(group["at_utc"].astype(str).str[:10])
    counts = daily.size()
    share_1star = daily["score"].apply(lambda s: (s == 1).mean())
    return counts, share_1star


def _bombing_days(group: pd.DataFrame) -> int:
    counts, share_1star = _daily_stats(group)
    if counts.empty:
        return 0
    baseline = max(counts.median() * BOMBING_DAILY_FACTOR, BOMBING_MIN_REVIEWS)
    return int(((counts >= baseline) & (share_1star >= BOMBING_MIN_1STAR_SHARE)).sum())


def build_monthly(df: pd.DataFrame | None = None) -> pd.DataFrame:
    if df is None:
        df = load_reviews()
    if df.empty:
        return pd.DataFrame(columns=MONTHLY_COLUMNS)

    work = df.copy()
    work["month"] = work["at_utc"].astype(str).str[:7]
    work["score"] = pd.to_numeric(work["score"], errors="coerce")
    work["thumbs_up"] = pd.to_numeric(work["thumbs_up"], errors="coerce").fillna(0)
    work["has_content"] = work["content"].astype(str).str.strip().ne("")
    work["has_reply"] = work["replied"].astype(str).str.lower().eq("true")
    versions = work["app_version"].astype(str).str.strip()
    work["has_version"] = versions.ne("") & versions.ne("nan")

    rows = []
    for (month, ticker, app_id), g in work.groupby(["month", "ticker", "app_id"]):
        n = len(g)
        rows.append({
            "month": month, "ticker": ticker, "app_id": app_id,
            "app_role": g["app_role"].iloc[0],
            "n_reviews": n,
            "mean_score": round(float(g["score"].mean()), 4),
            "median_score": float(g["score"].median()),
            "pct_1star": round(float((g["score"] == 1).mean()), 4),
            "pct_5star": round(float((g["score"] == 5).mean()), 4),
            "pct_with_content": round(float(g["has_content"].mean()), 4),
            "n_with_content": int(g["has_content"].sum()),
            "thumbs_up_sum": int(g["thumbs_up"].sum()),
            "n_versions": int(g.loc[g["has_version"], "app_version"].nunique()),
            "reply_rate": round(float(g["has_reply"].mean()), 4),
            "bombing_days": _bombing_days(g),
            "usable": bool(n >= MIN_REVIEWS_PER_MONTH),
        })

    monthly = pd.DataFrame(rows, columns=MONTHLY_COLUMNS)
    monthly = monthly.sort_values(["ticker", "app_id", "month"])
    OUT.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(MONTHLY, index=False, encoding="utf-8-sig")
    return monthly


def coverage(df: pd.DataFrame | None = None) -> pd.DataFrame:
    if df is None:
        df = load_reviews()
    if df.empty:
        return pd.DataFrame()
    work = df.copy()
    work["month"] = work["at_utc"].astype(str).str[:7]
    rows = []
    for (ticker, app_id), g in work.groupby(["ticker", "app_id"]):
        months = sorted(g["month"].unique())
        span = pd.period_range(months[0], months[-1], freq="M")
        rows.append({
            "ticker": ticker, "app_id": app_id, "app_role": g["app_role"].iloc[0],
            "n_reviews": len(g), "first": months[0], "last": months[-1],
            "months_with_data": len(months), "months_in_span": len(span),
            "months_missing": len(span) - len(months),
            "mean_score": round(float(pd.to_numeric(g["score"], errors="coerce").mean()), 3),
        })
    return pd.DataFrame(rows).sort_values(["ticker", "app_id"])


def discover(tickers: list[str] | None = None) -> pd.DataFrame:
    import re

    import requests

    _, gp_app, _ = _require_scraper()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
    rows = []
    for ticker in (tickers or TICKERS):
        query = DISCOVER_QUERIES[ticker]
        resp = safe_call(f"search {ticker}", lambda: requests.get(
            SEARCH_URL, params={"q": query, "c": "apps", "hl": LANG, "gl": COUNTRY},
            headers=headers, timeout=25))
        found = []
        for m in re.finditer(r"/store/apps/details\?id=([A-Za-z0-9_\.]+)", resp.text):
            if m.group(1) not in found:
                found.append(m.group(1))
        found = found[:5]
        pinned = {e["app_id"] for e in APPS.get(ticker, [])}
        for app_id in found:
            try:
                d = gp_app(app_id, lang=LANG, country=COUNTRY)
            except Exception as exc:
                rows.append({"ticker": ticker, "app_id": app_id,
                             "title": f"LOI {type(exc).__name__}", "developer": "",
                             "score": None, "reviews_with_text": None, "installs": "",
                             "in_APPS": app_id in pinned})
                continue
            rows.append({"ticker": ticker, "app_id": app_id, "title": d.get("title"),
                         "developer": d.get("developer"), "score": d.get("score"),
                         "reviews_with_text": d.get("reviews"), "installs": d.get("installs"),
                         "in_APPS": app_id in pinned})
            time.sleep(SECONDS_BETWEEN_BATCHES)
        for app_id in sorted(pinned - set(found)):
            rows.append({"ticker": ticker, "app_id": app_id,
                         "title": "KHONG CON TRONG TOP 5 TIM KIEM", "developer": "",
                         "score": None, "reviews_with_text": None, "installs": "",
                         "in_APPS": True})
        time.sleep(SECONDS_BETWEEN_BATCHES)
    return pd.DataFrame(rows)


def run(tickers: list[str] | None = None, roles: tuple[str, ...] = DEFAULT_ROLES,
        backfill: bool = False, max_reviews: int = MAX_REVIEWS_PER_APP) -> dict:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    frame = update_all(tickers, roles, backfill, max_reviews)
    catalog = fetch_catalog(tickers, roles)
    monthly = build_monthly()

    apps_ok = len(frame)
    apps_total = len(selected_apps(tickers, roles))
    n_new = int(frame["new"].sum()) if apps_ok else 0
    n_rows = int(frame["rows"].sum()) if apps_ok else 0
    latest = frame["last"].max() if apps_ok else ""

    with open("crawl_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{retrieved_at}] app_reviews: {apps_ok}/{apps_total} apps ok, "
                f"{n_new} reviews added, {n_rows} rows total, {len(catalog)} catalog rows, "
                f"{len(monthly)} bank-month, latest={latest}\n")

    if apps_ok < apps_total:
        raise RuntimeError(f"app_reviews: chi {apps_ok}/{apps_total} app thanh cong")

    return {"apps_ok": apps_ok, "apps_total": apps_total, "reviews_added": n_new,
            "rows_total": n_rows, "catalog_rows": len(catalog),
            "monthly_rows": len(monthly), "latest_review": latest}


def validate(df: pd.DataFrame | None = None) -> None:
    if df is None:
        df = load_reviews()
    if df.empty:
        print("chua co du lieu -- chay `python -m crawlers.app_reviews --backfill` truoc")
        return

    work = df.copy()
    work["score"] = pd.to_numeric(work["score"], errors="coerce")
    work["month"] = work["at_utc"].astype(str).str[:7]
    seen = set(work["ticker"].unique())
    total = len(work)

    print(f"{total} review, {work['app_id'].nunique()} app, "
          f"{len(seen)}/{len(TICKERS)} ticker, "
          f"{work['month'].min()} -> {work['month'].max()}")
    print()

    absent = [t for t in TICKERS if t not in seen]
    print(f"1. Ticker vang mat: {len(absent)}/{len(TICKERS)} -> {absent or 'khong thieu'}")
    print()

    cov = coverage(work)
    print("2. Do phu tung app:")
    for _, r in cov.iterrows():
        flag = "" if r["months_missing"] == 0 else f"  THIEU {r['months_missing']} thang"
        print(f"   {r['ticker']:5s} {r['app_id']:<32} {r['n_reviews']:>7} review  "
              f"{r['first']} -> {r['last']}  "
              f"{r['months_with_data']:>3}/{r['months_in_span']:>3} thang"
              f"  sao={r['mean_score']}{flag}")
    print()

    thin = cov[cov["months_missing"] > 0]
    print(f"3. App co lo hong thang: {len(thin)}/{len(cov)}")
    for _, r in thin.iterrows():
        g = work[work["app_id"] == r["app_id"]]
        months = set(g["month"])
        span = pd.period_range(r["first"], r["last"], freq="M").astype(str)
        missing = [m for m in span if m not in months]
        print(f"   {r['ticker']:5s} {r['app_id']:<32} thieu: {', '.join(missing[:12])}"
              f"{' ...' if len(missing) > 12 else ''}")
    print()

    dup = int(work.duplicated(subset=["app_id", "review_id"]).sum())
    print(f"4. Dong trung khoa (app_id, review_id): {dup}")
    print()

    print("5. Phan bo sao toan bo:")
    for star, n in work["score"].value_counts().sort_index().items():
        print(f"   {int(star)} sao: {n:>7} ({n / total:.1%})")
    print()

    print(f"6. Ngay nghi review bombing (>= {BOMBING_MIN_REVIEWS} review, "
          f">= {BOMBING_DAILY_FACTOR:.0f}x trung vi ngay, "
          f">= {BOMBING_MIN_1STAR_SHARE:.0%} mot sao):")
    any_bomb = False
    for app_id, g in work.groupby("app_id"):
        counts, share = _daily_stats(g)
        baseline = max(counts.median() * BOMBING_DAILY_FACTOR, BOMBING_MIN_REVIEWS)
        hits = counts[(counts >= baseline) & (share >= BOMBING_MIN_1STAR_SHARE)]
        for day, n in hits.items():
            any_bomb = True
            print(f"   {g['ticker'].iloc[0]:5s} {app_id:<32} {day}  {n:>5} review  "
                  f"{share[day]:.0%} mot sao")
    if not any_bomb:
        print("   khong ngay nao vuot nguong")
    print()

    empty = work[work["content"].astype(str).str.strip().eq("")]
    five_empty = empty[empty["score"] == 5]
    print(f"7. Review khong noi dung: {len(empty)} ({len(empty) / total:.1%}), "
          f"trong do 5 sao: {len(five_empty)} "
          f"({len(five_empty) / max(len(empty), 1):.1%})")
    by_day = five_empty.groupby([five_empty["ticker"],
                                 five_empty["at_utc"].astype(str).str[:10]]).size()
    spikes = by_day[by_day >= BOMBING_MIN_REVIEWS].sort_values(ascending=False)
    print(f"   ngay co >= {BOMBING_MIN_REVIEWS} review 5-sao-khong-noi-dung: {len(spikes)}")
    for (ticker, day), n in spikes.head(10).items():
        print(f"   {ticker:5s} {day}  {n:>5} review")
    print()

    multi = {t: v for t, v in APPS.items() if len(v) > 1}
    print(f"8. Ticker co nhieu hon 1 app (KHONG duoc noi thanh mot chuoi): {len(multi)}")
    for ticker, entries in multi.items():
        print(f"   {ticker:5s} " + " | ".join(f'{e["app_id"]} ({e["role"]})' for e in entries))
    print()

    leaked = [c for c in DROPPED_PERSONAL_FIELDS if c in work.columns]
    print(f"9. Truong ca nhan bi luu nham: "
          f"{leaked or 'khong co (userName/userImage da loai)'}")
    print()

    if CATALOG.exists():
        cat = pd.read_csv(CATALOG, encoding="utf-8-sig")
        stamps = pd.to_datetime(cat["last_updated"], errors="coerce")
        bad = int((stamps < pd.Timestamp("2010-01-01")).sum() + int(stamps.isna().sum()))
        print(f"10. app_catalog.last_updated ngoai khoang hop le (< 2010 hoac rong): "
              f"{bad}/{len(cat)}")
        gap = cat[["ticker", "app_id", "ratings", "reviews_with_text"]].dropna()
        if len(gap):
            share = (gap["reviews_with_text"] / gap["ratings"]).median()
            print(f"    ty le luot cham co noi dung (trung vi): {share:.1%} "
                  f"-- phan con lai KHONG lay duoc")
    else:
        print("10. chua co app_catalog.csv")


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    argv = sys.argv[1:]

    def _opt(name, cast=str, default=None):
        for i, a in enumerate(argv):
            if a == name and i + 1 < len(argv):
                return cast(argv[i + 1])
            if a.startswith(name + "="):
                return cast(a.split("=", 1)[1])
        return default

    picked = _opt("--tickers")
    picked = [t.strip().upper() for t in picked.split(",")] if picked else None
    picked_roles = _opt("--roles")
    picked_roles = (tuple(r.strip() for r in picked_roles.split(","))
                    if picked_roles else DEFAULT_ROLES)
    cap = _opt("--max-reviews", int, MAX_REVIEWS_PER_APP)

    if "--validate" in argv:
        validate()
    elif "--coverage" in argv:
        print(coverage().to_string(index=False))
    elif "--monthly" in argv:
        result = build_monthly()
        print(f"{len(result)} dong bank-month -> {MONTHLY}")
        print(result.tail(15).to_string(index=False))
    elif "--discover" in argv:
        print(discover(picked).to_string(index=False))
    else:
        summary = run(picked, picked_roles, backfill="--backfill" in argv, max_reviews=cap)
        print(f"\n{summary['apps_ok']}/{summary['apps_total']} app OK | "
              f"{summary['reviews_added']} review moi | {summary['rows_total']} dong tong | "
              f"{summary['monthly_rows']} dong bank-month | "
              f"moi nhat {summary['latest_review']}")
