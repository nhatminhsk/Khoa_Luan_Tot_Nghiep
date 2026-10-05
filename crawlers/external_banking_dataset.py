from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

OUT = Path("data/external")
XLSX_PATH = OUT / "vn_banking_system_2002_2021.xlsx"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
DATAVERSE_FILE_URL = "https://dataverse.harvard.edu/api/access/datafile/7677329"

DATASET_CODE_TO_TICKER = {
    "BIDV": "BID", "MB": "MBB", "LVB": "LPB", "SEAB": "SSB", "NCB": "NVB",
}


def download(force: bool = False) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    if XLSX_PATH.exists() and not force:
        return XLSX_PATH
    resp = requests.get(DATAVERSE_FILE_URL, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    XLSX_PATH.write_bytes(resp.content)
    return XLSX_PATH


def ingest() -> dict:
    path = download()

    data = pd.read_excel(path, sheet_name="Data")
    data["ticker"] = data["Bank Code"].map(DATASET_CODE_TO_TICKER).fillna(data["Bank Code"])
    data_csv = OUT / "vn_banking_system_2002_2021_data.csv"
    data.to_csv(data_csv, index=False, encoding="utf-8-sig")

    banks = pd.read_excel(path, sheet_name="Banks List").dropna(subset=["Bank Code"])
    banks_csv = OUT / "vn_banking_system_2002_2021_banks_list.csv"
    banks.to_csv(banks_csv, index=False, encoding="utf-8-sig")

    n_overlap = data["ticker"].isin(list(DATASET_CODE_TO_TICKER.values()) + [
        "VCB", "CTG", "ACB", "TCB", "VPB", "STB", "HDB", "VIB", "TPB", "MSB",
        "OCB", "SHB", "EIB", "BAB", "BVB", "NAB", "PGB",
    ]).sum()

    return {
        "xlsx_path": str(path),
        "data_csv": str(data_csv),
        "banks_csv": str(banks_csv),
        "rows": len(data),
        "year_range": (int(data["Year"].min()), int(data["Year"].max())),
        "n_bank_codes": data["Bank Code"].nunique(),
        "rows_matching_22_tickers": int(n_overlap),
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    summary = ingest()
    for k, v in summary.items():
        print(f"{k}: {v}")
