"""Du no nong-lam-thuy san nhap tay tu BCTC kiem toan -> chuoi nam day du.

Nguon so lieu vnstock (`Finance(source="VCI").note()`, dong
NT_BS_AGRICULTURE_AND_FORESTRY) chi co 97/176 o cuoi nam 2018-2025 cho 22 ngan
hang. Phan con thieu duoc doc tay tu bang "Phan tich du no cho vay theo nganh"
trong thuyet minh BCTC hop nhat kiem toan va ghi vao:

    data/policy_credit/agri_loans_fill_template.csv   <- NHAP TAY O DAY
    data/policy_credit/agri_loans_annual.csv          <- file cho mo hinh (script nay ghi)

Cach nhap mot dong trong file mau:
    status                             ghi dung chuoi "đã nhập" (co dau); hoac "BCTC không tách dòng"
                                       neu bang nganh khong co dong nong nghiep -- de trong so, KHONG ghi 0
    agri_forestry_fishery_loans_mn_vnd so dong nong-lam-thuy san, TRIEU dong, bo dau cham
    total_loans_by_industry_mn_vnd     dong tong cuoi bang nganh, TRIEU dong
    industry_label_in_fs               ten dong dung nhu BCTC ghi
    read_from_fs_year, column          BCTC nam nao, cot "Số cuối năm" hay "Số đầu năm"
    pdf_page, fs_url                   trang PDF (so trang cua trinh doc, khong phai so in) va link

Da kiem 14/09/2026: 46 o doc tu 25 BCTC khop OCR va khop cot % in san trong BCTC
(xem data/policy_credit/README.md).

O "chưa có file" duoc tu dien tu data/credit/loans_by_industry_annual.csv neu bang nganh
cua NH-nam do da co dung mot dong nhom A (nhap bang nganh o
data/credit/loans_by_industry_manual/fill_template.xlsx, chay crawlers.loans_by_industry truoc).

Chay:
    python -m crawlers.agri_loans_manual              # ap file mau vao chuoi nam
    python -m crawlers.agri_loans_manual --validate
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DIR = Path("data/policy_credit")
TEMPLATE = DIR / "agri_loans_fill_template.csv"
ANNUAL = DIR / "agri_loans_annual.csv"
INDUSTRY = Path("data/credit/loans_by_industry_annual.csv")

FILLED = "đã nhập"
NO_LINE = "BCTC không tách dòng"
MISSING = "chưa có file"
# Canh bao gay chuoi giua hai nam lien ke: doi hon 5 diem %, hoac gap hon 2,5 lan
# khi muc lon hon >= 1%. Nguong nay bat dung cac cho NH doi cach phan nganh da biet
# (HDB 2023-2024, SHB 2023-2024, TPB 2023-2024, MSB 2023-2024).
JUMP_PP = 5.0
JUMP_RATIO = 2.5


def _load():
    tpl = pd.read_csv(TEMPLATE, encoding="utf-8-sig")
    ann = pd.read_csv(ANNUAL, encoding="utf-8-sig")
    tpl["year"] = tpl.period.str[:4].astype(int)
    return tpl, ann


def _check_template(tpl: pd.DataFrame) -> list[str]:
    errors = []
    done = tpl[tpl.status == FILLED]
    for r in done.itertuples():
        key = f"{r.ticker} {r.period}"
        if pd.isna(r.agri_forestry_fishery_loans_mn_vnd) or pd.isna(r.total_loans_by_industry_mn_vnd):
            errors.append(f"{key}: status '{FILLED}' nhung thieu so")
            continue
        if r.agri_forestry_fishery_loans_mn_vnd < 0 or r.agri_forestry_fishery_loans_mn_vnd > r.total_loans_by_industry_mn_vnd:
            errors.append(f"{key}: du no nong nghiep am hoac lon hon tong")
        if r.total_loans_by_industry_mn_vnd < 1_000_000:
            errors.append(f"{key}: tong {r.total_loans_by_industry_mn_vnd:,.0f} qua nho -- nhap nham don vi (ty dong)?")
        if r.total_loans_by_industry_mn_vnd > 5_000_000_000:
            errors.append(f"{key}: tong qua lon -- BCTC ghi DONG chua chia 1.000.000?")
        if pd.isna(r.fs_url) or not str(r.fs_url).startswith("http"):
            errors.append(f"{key}: thieu fs_url")
    no_line = tpl[(tpl.status == NO_LINE) & tpl.agri_forestry_fishery_loans_mn_vnd.notna()]
    errors += [f"{r.ticker} {r.period}: '{NO_LINE}' thi phai de trong so" for r in no_line.itertuples()]
    dup = tpl[tpl.duplicated(["ticker", "period"], keep=False)]
    errors += [f"{r.ticker} {r.period}: trung dong" for r in dup.itertuples()]
    return errors


def _fill_from_industry(tpl: pd.DataFrame, ann: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    """O 'chua co file' -> lay dong nhom A cua bang nganh; tra ve (tpl, o da dien, bang nganh khong co dong A).
    Bo qua o da co so trong agri_loans_annual.csv (nguoi dung dien thang vao file nam)."""
    if not INDUSTRY.exists():
        return tpl, [], []
    ind = pd.read_csv(INDUSTRY, encoding="utf-8-sig")
    typed = set(zip(ann.ticker[ann.agri_loans_mn_vnd.notna()], ann.year[ann.agri_loans_mn_vnd.notna()]))
    filled, no_a = [], []
    for i, r in tpl[tpl.status == MISSING].iterrows():
        if (r.ticker, r.year) in typed:
            continue
        t = ind[(ind.ticker == r.ticker) & (ind.year == r.year)]
        if t.empty:
            continue
        a = t[t.industry_group == "A"]
        if len(a) != 1:
            no_a.append(f"{r.ticker} {r.period}: bang nganh co {len(a)} dong nhom A -- kiem tay, co the '{NO_LINE}'")
            continue
        x = a.iloc[0]
        tpl.loc[i, ["status", "agri_forestry_fishery_loans_mn_vnd", "total_loans_by_industry_mn_vnd",
                    "industry_label_in_fs", "read_from_fs_year", "column", "pdf_page", "fs_url", "note"]] = [
            FILLED, x.value_mn_vnd, x.table_total_mn_vnd, x.industry_label, x.source_fs_year, x.source_column,
            x.pdf_page, x.fs_url, f"Lấy từ {INDUSTRY.as_posix()}"]
        filled.append(f"{r.ticker} {r.period}")
    return tpl, filled, no_a


def build() -> dict:
    tpl, ann = _load()
    tpl, from_industry, no_agri_line = _fill_from_industry(tpl, ann)
    if from_industry:
        tpl.drop(columns=["year"]).to_csv(TEMPLATE, index=False, encoding="utf-8-sig")
    errors = _check_template(tpl)
    if errors:
        return {"status": "error", "errors": errors}

    ann = ann.set_index(["ticker", "year"])
    applied = 0
    for r in tpl[tpl.status.isin([FILLED, NO_LINE])].itertuples():
        idx = (r.ticker, r.year)
        if idx not in ann.index:
            continue
        agri = r.agri_forestry_fishery_loans_mn_vnd
        tot = r.total_loans_by_industry_mn_vnd
        page = "" if pd.isna(r.pdf_page) else f" (trang {int(r.pdf_page)})"
        ann.loc[idx, ["agri_loans_mn_vnd", "total_loans_by_industry_mn_vnd", "agri_share_pct", "source", "reference"]] = [
            agri, tot, round(agri / tot * 100, 4) if pd.notna(agri) else None, "bctc_kiem_toan", f"{r.fs_url}{page}",
        ]
        applied += 1
    ann = ann.reset_index()
    ann.to_csv(ANNUAL, index=False, encoding="utf-8-sig")
    return {"status": "ok", "applied_rows": applied, "filled_from_industry_table": from_industry,
            "industry_table_without_agri_line": no_agri_line, **validate()}


def validate() -> dict:
    tpl, ann = _load()
    warnings = []
    s = ann.pivot(index="ticker", columns="year", values="agri_share_pct")
    for t, row in s.iterrows():
        vals = row.dropna()
        for (y0, v0), (y1, v1) in zip(vals.items(), list(vals.items())[1:]):
            hi, lo = max(v0, v1), min(v0, v1)
            big_ratio = hi >= 1 and (lo == 0 or hi / lo > JUMP_RATIO)
            if y1 == y0 + 1 and (abs(v1 - v0) > JUMP_PP or big_ratio):
                warnings.append(f"{t} {y0}->{y1}: {v0:.2f}% -> {v1:.2f}% (kiem lai hoac do NH doi phan nganh)")
    differs = []
    if INDUSTRY.exists():
        ind = pd.read_csv(INDUSTRY, encoding="utf-8-sig")
        a = ind[ind.industry_group == "A"].groupby(["ticker", "year"]).filter(lambda g: len(g) == 1)
        both = ann.merge(a[["ticker", "year", "value_mn_vnd"]], on=["ticker", "year"]).dropna(subset=["agri_loans_mn_vnd"])
        both = both[(both.agri_loans_mn_vnd - both.value_mn_vnd).abs() > 1]
        differs = [f"{r.ticker} {r.year}: agri {r.agri_loans_mn_vnd:,.0f} vs bang nganh {r.value_mn_vnd:,.0f}"
                   for r in both.itertuples()]
    return {
        "template_errors": _check_template(tpl),
        "agri_differs_from_industry_table": differs,
        "template_status": tpl.status.value_counts().to_dict(),
        "annual_cells_with_value": int(ann.agri_loans_mn_vnd.notna().sum()),
        "annual_cells_total": int(len(ann)),
        "by_source": ann.source.fillna("").replace("", "(trong)").value_counts().to_dict(),
        "jump_warnings": warnings,
    }


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out = validate() if "--validate" in sys.argv else build()
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    if out.get("status") == "error" or out.get("template_errors"):
        sys.exit(1)
