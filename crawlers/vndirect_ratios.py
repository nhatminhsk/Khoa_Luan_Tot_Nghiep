from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone

import pandas as pd

URL = ("https://api-finfo.vndirect.com.vn/v4/ratios?q=code:{t}~itemCode:57016,57017,52001,52002,57050,57012"
       "~reportDate:gte:2017-01-01&size=5000")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
TICKERS = "ACB BAB BID BVB CTG EIB HDB LPB MBB MSB NAB NVB OCB PGB SHB SSB STB TCB TPB VCB VIB VPB".split()
ITEMS = {57016: "npl_percent", 57017: "npl_coverage_percent", 52001: "roaa_percent", 52002: "roae_percent",
         57050: "nim_percent", 57012: "ldr_percent"}
OUT = "data/credit/bank_ratios_vndirect_quarterly.csv"


def fetch(tickers=TICKERS, sleep=1.0) -> pd.DataFrame:
    rows = []
    for t in tickers:
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(URL.format(t=t), headers=UA), timeout=60) as r:
                    rows += [dict(ticker=t, **x) for x in json.load(r)["data"]]
                break
            except Exception:  # API doi khi tra loi cham
                time.sleep(5 * (attempt + 1))
        time.sleep(sleep)
    d = pd.DataFrame(rows)
    day = pd.to_datetime(d.reportDate)
    d = d[day.dt.is_quarter_end].assign(period=day.dt.year.astype(str) + "-Q" + day.dt.quarter.astype(str))
    d["itemCode"] = d["itemCode"].astype(int)  # API tra ma dang chuoi
    w = d.pivot_table(index=["ticker", "period"], columns="itemCode", values="value", aggfunc="last")
    w = (w.rename(columns=ITEMS) * 100).round(4).reset_index()
    w["source"] = "VNDirect api-finfo v4 ratios"
    w["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return w.sort_values(["ticker", "period"])[["ticker", "period", *ITEMS.values(), "source", "retrieved_at_utc"]]


if __name__ == "__main__":
    w = fetch()
    w.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"{len(w)} dong, {w.ticker.nunique()} NH, {w.period.min()}..{w.period.max()} -> {OUT}")
