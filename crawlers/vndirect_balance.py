from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone

import pandas as pd

URL = ("https://api-finfo.vndirect.com.vn/v4/financial_statements?q=code:{t}~reportType:QUARTER~modelType:101"
       "~itemCode:12700,412000,412100,412200,413300&size=2000")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
TICKERS = "ACB BAB BID BVB CTG EIB HDB LPB MBB MSB NAB NVB OCB PGB SHB SSB STB TCB TPB VCB VIB VPB".split()
ITEMS = {12700: "total_assets_vnd", 412000: "loans_net_vnd", 412100: "loans_gross_vnd", 412200: "loan_provision_vnd",
         413300: "deposits_vnd"}
OUT = "data/credit/bank_balance_vndirect_quarterly.csv"
# o da chung minh sai (xem docstring): de trong so lieu, giu dong voi ghi chu
BAD = {("BVB", p): "so cua BaoViet Bank (ma BVB truoc khi Ban Viet niem yet 2017)" for p in
       [f"{y}-Q{q}" for y in range(2006, 2017) for q in (1, 2, 3, 4)]}
BAD[("OCB", "2013-Q2")] = "du no/tien gui/TTS thap ~10 lan so voi hai quy lien ke"


def clean(w: pd.DataFrame) -> pd.DataFrame:
    w = w.copy()
    key = list(zip(w.ticker, w.period))
    bad = pd.Series([k in BAD for k in key], index=w.index)
    for c in [*ITEMS.values(), "ldr_net_percent"]:
        w.loc[bad, c] = float("nan")
    w["note"] = [BAD.get(k, "") for k in key]
    return w


def fetch(tickers=TICKERS, sleep=2.0) -> pd.DataFrame:
    rows = []
    for t in tickers:
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(URL.format(t=t), headers=UA), timeout=60) as r:
                    rows += json.load(r)["data"]
                break
            except Exception:  # API doi khi tra loi cham
                time.sleep(5 * (attempt + 1))
        time.sleep(sleep)
    d = pd.DataFrame(rows)
    d["period"] = pd.to_datetime(d.fiscalDate).dt.year.astype(str) + "-Q" + pd.to_datetime(d.fiscalDate).dt.quarter.astype(str)
    w = d.pivot_table(index=["code", "period"], columns="itemCode", values="numericValue", aggfunc="first")
    w = w.rename(columns=ITEMS).reset_index().rename(columns={"code": "ticker"})
    w = w.mask(w == 0)  # nguon ghi 0 cho o chua co (vd tien gui truoc 2007-Q3)
    w["ldr_net_percent"] = (w.loans_net_vnd / w.deposits_vnd * 100).round(4)
    w["source"] = "VNDirect api-finfo v4 model 101"
    w["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return w.sort_values(["ticker", "period"])[["ticker", "period", *ITEMS.values(), "ldr_net_percent", "source", "retrieved_at_utc"]]


if __name__ == "__main__":
    w = clean(fetch())
    w.to_csv(OUT, index=False, encoding="utf-8-sig")
    pre = w[(w.period >= "2012-Q1") & (w.period < "2018-Q1") & w.ldr_net_percent.notna()]
    print(f"{len(w)} dong, {w.ticker.nunique()} NH, {w.period.min()}..{w.period.max()}; LDR 2012-2017: {len(pre)} o -> {OUT}")
