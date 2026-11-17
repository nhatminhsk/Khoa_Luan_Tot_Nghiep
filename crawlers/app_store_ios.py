from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import pandas as pd
import requests

OUT_PATH = "data/app_reviews/app_catalog_ios.csv"
LOG_PATH = "crawl_log.txt"
LOOKUP_URL = "https://itunes.apple.com/lookup"
HEADERS = {"User-Agent": "Mozilla/5.0 (KLTN research; app catalog)"}

# ticker -> (app_id iOS, ten app ben Google Play de doi chieu 1-1)
APPS = {
    "ACB": (950141024, "ACB ONE"),
    "BAB": (1441408786, "BAC A BANK Mobile Banking"),
    "BID": (1061867449, "BIDV SmartBanking"),
    "BVB": (1526444697, "digimi"),
    "CTG": (689963454, "VietinBank iPay"),
    "EIB": (1571427361, "Eximbank EDigi"),
    "HDB": (1461658565, "HDBank"),
    "LPB": (1488794748, "LPBank"),
    "MBB": (1205807363, "MB Bank"),
    "MSB": (436134873, "MSB mBank"),
    "NAB": (1456997296, "Nam A Bank Open Banking"),
    "NVB": (1465217154, "NCB iziMobile"),
    "OCB": (6472261202, "OCB OMNI"),
    "PGB": (1537765475, "PGBank"),
    "SHB": (1661457183, "SHB SAHA"),
    "SSB": (846407152, "SeAMobile"),
    # Sacombank co 2 app ban le. 885814869 = mBanking, khop voi ban dang theo doi
    # ben Play; 1436283663 = SACOMBANK PAY la app khac, dung nham se lech han.
    "STB": (885814869, "SACOMBANK mBanking"),
    "TCB": (1548623362, "Techcombank Mobile"),
    "TPB": (450464147, "TPBank Mobile"),
    "VCB": (561433133, "VCB Digibank"),
    "VIB": (1626624790, "MyVIB"),
    "VPB": (1209349510, "VPBank NEO"),
}


def _log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")


def fetch(sleep=0.3):
    today = datetime.now(timezone.utc).date().isoformat()
    now = datetime.now(timezone.utc).isoformat()
    rows, missing = [], []
    for ticker, (app_id, play_name) in APPS.items():
        try:
            resp = requests.get(
                LOOKUP_URL,
                params={"id": app_id, "country": "vn", "entity": "software"},
                headers=HEADERS, timeout=30,
            )
            results = resp.json().get("results", [])
        except Exception as exc:
            missing.append((ticker, f"{type(exc).__name__}: {exc}"[:100]))
            time.sleep(sleep)
            continue
        if not results:
            missing.append((ticker, "lookup tra ve rong"))
            time.sleep(sleep)
            continue
        app = results[0]
        rows.append({
            "date": today,
            "ticker": ticker,
            "app_id": app_id,
            "app_name": app.get("trackName"),
            "play_counterpart": play_name,
            "developer": app.get("sellerName"),
            "score": app.get("averageUserRating"),
            "ratings": app.get("userRatingCount"),
            "score_current_version": app.get("averageUserRatingForCurrentVersion"),
            "ratings_current_version": app.get("userRatingCountForCurrentVersion"),
            "version": app.get("version"),
            "released": str(app.get("releaseDate", ""))[:10],
            "last_updated": str(app.get("currentVersionReleaseDate", ""))[:10],
            "min_os": app.get("minimumOsVersion"),
            "content_rating": app.get("contentAdvisoryRating"),
            "source": "apple_app_store",
            "source_url": f"https://apps.apple.com/vn/app/id{app_id}",
            "retrieved_at_utc": now,
        })
        time.sleep(sleep)
    return pd.DataFrame(rows), missing


def build(write=True):
    fresh, missing = fetch()
    if fresh.empty:
        raise RuntimeError("Khong lay duoc ma nao tu App Store.")

    if os.path.exists(OUT_PATH):
        old = pd.read_csv(OUT_PATH, encoding="utf-8-sig")
        combined = pd.concat([old, fresh], ignore_index=True)
        before = len(old)
    else:
        combined = fresh
        before = 0
    # Khoa chong trung: mot anh chup moi (ngay, ticker).
    combined = combined.drop_duplicates(subset=["date", "ticker"], keep="last")
    combined = combined.sort_values(["date", "ticker"])

    if write:
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        combined.to_csv(OUT_PATH, index=False, encoding="utf-8-sig",
                        lineterminator="\r\n")
        _log(
            f"app_store_ios: {len(fresh)}/{len(APPS)} ma, "
            f"{len(combined) - before} dong moi, {len(missing)} loi -> {OUT_PATH}"
        )

    return {
        "tickers_fetched": len(fresh),
        "tickers_expected": len(APPS),
        "missing": missing,
        "new_rows": len(combined) - before,
        "total_rows": len(combined),
        "snapshot_dates": int(combined["date"].nunique()),
        "path": OUT_PATH,
    }


def validate():
    ios = pd.read_csv(OUT_PATH, encoding="utf-8-sig")
    latest = ios.sort_values("date").groupby("ticker").tail(1)
    res = {
        "snapshot_date": str(latest["date"].max()),
        "tickers": int(latest["ticker"].nunique()),
        "score_range": [round(float(latest["score"].min()), 2),
                        round(float(latest["score"].max()), 2)],
        "total_ratings": int(latest["ratings"].sum()),
    }

    play_path = "data/app_reviews/app_catalog.csv"
    if os.path.exists(play_path):
        play = pd.read_csv(play_path, encoding="utf-8-sig")
        play = play.sort_values("date").groupby("ticker").tail(1)[
            ["ticker", "score", "ratings"]
        ].rename(columns={"score": "play_score", "ratings": "play_ratings"})
        merged = latest[["ticker", "score", "ratings"]].rename(
            columns={"score": "ios_score", "ratings": "ios_ratings"}
        ).merge(play, on="ticker", how="left")
        both = merged.dropna(subset=["play_score"])
        gap = both["ios_score"] - both["play_score"]
        res["ios_vs_play"] = {
            "n_comparable": len(both),
            "pearson_r": round(float(both["ios_score"].corr(both["play_score"])), 4),
            "spearman_r": round(float(
                both["ios_score"].rank().corr(both["play_score"].rank())), 4),
            "gap_min_pp": round(float(gap.min()), 2),
            "gap_max_pp": round(float(gap.max()), 2),
            "gap_mean_pp": round(float(gap.mean()), 2),
            "banks_ios_ratings_exceed_play": int(
                (both["ios_ratings"] > both["play_ratings"]).sum()),
            "only_on_ios": merged[merged["play_score"].isna()]["ticker"].tolist(),
        }
    return res


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--validate" in sys.argv:
        print(json.dumps(validate(), indent=2, ensure_ascii=False, default=str))
    else:
        print(json.dumps(build(), indent=2, ensure_ascii=False, default=str))
