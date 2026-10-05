from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from crawlers import vci_ratio

RAW = Path("data/vnstock_financial/raw")
OUT = Path("data/credit")
MASTER = OUT / "bank_credit_quarterly.csv"

BS_FIELDS = {
    "BS_LOANS_TO_CUSTOMERS": "loans_vnd",
    "BS_PROVISION_LOANS_TO_CUSTOMERS": "loan_provision_vnd",
    "BS_CUSTOMER_DEPOSITS": "deposits_vnd",
    "BS_TOTAL_ASSETS": "total_assets_vnd",
}
IS_FIELDS = {"IS_PROVISION_FOR_CREDIT_LOSSES": "provision_expense_vnd"}
RT_FIELDS = {
    "RT_BANK_NPL": "npl_percent",
    "RT_BANK_LDR": "ldr_percent",
    "RT_BANK_NPL_COVERAGE": "npl_coverage_percent",
    "RT_BANK_NIM": "nim_percent",
    "RT_BANK_CAR": "car_percent",
}
NEGATED = {"npl_coverage_percent"}
ZERO_IS_MISSING = {"npl_percent", "ldr_percent", "npl_coverage_percent", "car_percent"}

COLUMNS = [
    "period", "period_end", "ticker",
    "loans_vnd", "deposits_vnd", "total_assets_vnd",
    "loans_qoq_percent", "loans_yoy_percent",
    "loans_over_assets_percent", "ldr_computed_percent",
    "npl_percent", "npl_coverage_percent", "ldr_percent", "nim_percent",
    "loan_provision_vnd", "provision_expense_vnd", "provision_over_loans_percent",
    "car_percent", "source", "retrieved_at_utc",
]

QUARTER_END = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}


def tickers() -> list[str]:
    return sorted({p.name.split("_")[0] for p in RAW.glob("*_balance_sheet_quarter.csv")})


def period_end(period: str) -> str:
    year, quarter = period.split("-Q")
    return f"{year}-{QUARTER_END[int(quarter)]}"


def _wide(ticker: str, statement: str, fields: dict[str, str]) -> pd.DataFrame:
    path = RAW / f"{ticker}_{statement}_quarter.csv"
    if not path.exists():
        return pd.DataFrame()
    # ratio quy cua VCI co quy chep lai (2021-Q4 = 2021-Q3) - doc qua lop da sua.
    if statement == "ratio":
        df = vci_ratio.read(path)
    else:
        df = pd.read_csv(path, encoding="utf-8-sig")
    df = df[df["id"].isin(fields)].copy()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    wide = df.pivot_table(index="period", columns="id", values="value", aggfunc="last")
    return wide.rename(columns=fields)


def build_bank(ticker: str) -> pd.DataFrame:
    bs = _wide(ticker, "balance_sheet", BS_FIELDS)
    inc = _wide(ticker, "income_statement", IS_FIELDS)
    rt = _wide(ticker, "ratio", RT_FIELDS)
    if bs.empty:
        return pd.DataFrame()

    df = bs.join(inc, how="outer").join(rt, how="outer")
    df.index.name = "period"
    df = df.reset_index()
    df["_key"] = df["period"].str.replace("-Q", "", regex=False).astype(int)
    df = df.sort_values("_key").drop(columns="_key").reset_index(drop=True)

    for column in RT_FIELDS.values():
        if column not in df:
            df[column] = pd.NA
            continue
        if column in ZERO_IS_MISSING:
            df.loc[df[column] == 0, column] = pd.NA
        df[column] = df[column] * 100
        if column in NEGATED:
            df[column] = -df[column]

    loans = df["loans_vnd"]
    df["loans_qoq_percent"] = loans.pct_change(1) * 100
    df["loans_yoy_percent"] = loans.pct_change(4) * 100
    df["loans_over_assets_percent"] = loans / df["total_assets_vnd"] * 100
    df["ldr_computed_percent"] = loans / df["deposits_vnd"] * 100
    df["provision_over_loans_percent"] = df["loan_provision_vnd"].abs() / loans * 100

    df["ticker"] = ticker
    df["period_end"] = df["period"].map(period_end)
    df["source"] = "vnstock_financial/raw"
    return df


def build(write: bool = True) -> pd.DataFrame:
    frames = [build_bank(t) for t in tickers()]
    df = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    df["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    df = df.reindex(columns=COLUMNS)
    for column in df.columns:
        if column.endswith("_percent"):
            df[column] = pd.to_numeric(df[column], errors="coerce").round(4)
    df = df.sort_values(["ticker", "period"]).reset_index(drop=True)

    if write:
        OUT.mkdir(parents=True, exist_ok=True)
        df.to_csv(MASTER, index=False, encoding="utf-8-sig")
        print(f"ghi {MASTER}: {len(df)} dong, {df['ticker'].nunique()} NH, "
              f"{df['period'].min()} -> {df['period'].max()}")
    return df


def validate(df: pd.DataFrame | None = None) -> None:
    if df is None:
        df = pd.read_csv(MASTER, encoding="utf-8-sig")

    print(f"{len(df)} bank-quarter, {df['ticker'].nunique()} NH, "
          f"{df['period'].min()} -> {df['period'].max()}\n")

    print("do phu tung truong (so o co gia tri / tong so o):")
    for column in ["loans_vnd", "deposits_vnd", "npl_percent", "ldr_percent",
                   "npl_coverage_percent", "nim_percent", "car_percent",
                   "provision_expense_vnd"]:
        filled = df[column].notna().sum()
        print(f"  {column:28s} {filled:4d}/{len(df)}  ({filled / len(df):5.1%})")

    print("\nso quy co NPL theo NH:")
    per_bank = df.groupby("ticker")["npl_percent"].apply(lambda s: s.notna().sum())
    print("  " + ", ".join(f"{t}:{n}" for t, n in per_bank.items()))
    print(f"  thap nhat {per_bank.min()} quy, cao nhat {per_bank.max()} quy")

    both = df.dropna(subset=["ldr_percent", "ldr_computed_percent"])
    if not both.empty:
        gap = (both["ldr_percent"] - both["ldr_computed_percent"])
        print(f"\nLDR nha cung cap vs LDR tu bang can doi ({len(both)} cap):")
        print(f"  tuong quan r = {both['ldr_percent'].corr(both['ldr_computed_percent']):.4f}")
        print(f"  chenh lech trung vi {gap.median():+.2f} diem, "
              f"|lech| < 5 diem o {(gap.abs() < 5).mean():.1%} so cap")

    npl = df.dropna(subset=["npl_percent"])
    print(f"\nNPL: {npl['npl_percent'].min():.2f}% - {npl['npl_percent'].max():.2f}%, "
          f"trung vi {npl['npl_percent'].median():.2f}%")
    top = npl.nlargest(8, "npl_percent")
    print("  8 gia tri cao nhat (kiem tra outlier truoc khi chuan hoa TOPSIS):")
    for _, row in top.iterrows():
        print(f"    {row['ticker']} {row['period']}: {row['npl_percent']:.2f}%")

    car_filled = df["car_percent"].notna().sum()
    print(f"\nCAR chi co {car_filled}/{len(df)} o ({car_filled / len(df):.1%}) "
          "-> KHONG dung lam tieu chi xep hang")

    growth = df.dropna(subset=["loans_yoy_percent"])
    print(f"\ntang truong tin dung YoY: {len(growth)} quan sat, "
          f"trung vi {growth['loans_yoy_percent'].median():.2f}%/nam")
    extreme = growth[growth["loans_yoy_percent"].abs() > 100]
    print(f"  |YoY| > 100%: {len(extreme)} dong")
    for _, row in extreme.iterrows():
        print(f"    {row['ticker']} {row['period']}: {row['loans_yoy_percent']:.1f}%")


if __name__ == "__main__":
    import sys

    if "--validate" in sys.argv:
        validate()
    else:
        validate(build())
