from __future__ import annotations

from pathlib import Path

import pandas as pd

OUT = Path("data/macro")

POLICY_RATE_COLUMNS = ["date_effective", "rate_type", "rate_percent", "source_url", "note"]
CPI_COLUMNS = ["month", "cpi_yoy_percent", "cpi_mom_percent", "source_url", "note"]
CREDIT_GROWTH_COLUMNS = ["year", "credit_growth_percent", "as_of_date", "announced_by",
                         "source_url", "note"]


def policy_rate_path() -> Path:
    return OUT / "policy_rate.csv"


def cpi_path() -> Path:
    return OUT / "cpi.csv"


def credit_growth_path() -> Path:
    return OUT / "credit_growth.csv"


def ensure_files() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for path, columns in [(policy_rate_path(), POLICY_RATE_COLUMNS), (cpi_path(), CPI_COLUMNS),
                          (credit_growth_path(), CREDIT_GROWTH_COLUMNS)]:
        if not path.exists():
            pd.DataFrame(columns=columns).to_csv(path, index=False, encoding="utf-8-sig")


def log_policy_rate(date_effective: str, rate_type: str, rate_percent: float, source_url: str, note: str = ""):
    ensure_files()
    df = pd.read_csv(policy_rate_path(), encoding="utf-8-sig")
    row = {"date_effective": date_effective, "rate_type": rate_type, "rate_percent": rate_percent,
           "source_url": source_url, "note": note}
    df = pd.DataFrame([row]) if df.empty else pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df = df.drop_duplicates(subset=["date_effective", "rate_type"], keep="last")
    df.to_csv(policy_rate_path(), index=False, encoding="utf-8-sig")
    return df


def log_cpi(month: str, cpi_yoy_percent: float, cpi_mom_percent: float, source_url: str, note: str = ""):
    ensure_files()
    df = pd.read_csv(cpi_path(), encoding="utf-8-sig")
    row = {"month": month, "cpi_yoy_percent": cpi_yoy_percent, "cpi_mom_percent": cpi_mom_percent,
           "source_url": source_url, "note": note}
    df = pd.DataFrame([row]) if df.empty else pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df = df.drop_duplicates(subset=["month"], keep="last")
    df.to_csv(cpi_path(), index=False, encoding="utf-8-sig")
    return df


if __name__ == "__main__":
    ensure_files()
    print(f"ensured {policy_rate_path()} and {cpi_path()} exist")
