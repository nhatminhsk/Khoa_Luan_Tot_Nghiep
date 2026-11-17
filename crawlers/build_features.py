from __future__ import annotations

import glob
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

PANEL = "data/model/bank_panel_quarterly.csv"
FIN = "data/vnstock_financial/financial_long.csv"
NOTE = "data/vnstock_financial/note_long.csv"
CAR = "data/credit/bank_car_halfyear.csv"
INDUSTRY = "data/credit/loans_by_industry_group_wide.csv"
INDUSTRY_ROWS = "data/credit/loans_by_industry_annual.csv"
AGRI ="data/policy_credit/agri_loans_annual.csv"
PROGRAMS = "data/policy_credit/program_participation.csv"
DISASTER = "data/policy_credit/disaster_provinces.csv"
BRANCH = "data/branch_network/branch_by_province.csv"
OWNERSHIP = "data/ownership/bank_ownership.csv"
APP = "data/app_reviews/app_reviews_monthly.csv"
DEPOSIT = "data/interest_rates/deposit_24hmoney_daily.csv"
LENDING = "data/interest_rates/bank_lending_rates_monthly.csv"
CPI = "data/macro/cpi.csv"
PRICE_IDX = "data/macro/price_indices.csv"
POLICY_RATE = "data/macro/policy_rate.csv"
CREDIT_GROWTH = "data/macro/credit_growth.csv"
VNINDEX = "data/market/VNINDEX.csv"
PRICE_DIR = "data/price"
OUT = "data/model/features_quarterly.csv"
SPEC_OUT = "data/model/feature_spec.csv"
LOG_PATH = "crawl_log.txt"

KEYS = ["period", "period_end", "ticker"]
MIN_SESSIONS = 20
MIN_REVIEWS = 30
# Cua so hieu luc cua su kien thien tai (ngay bao den -> het han co cau no).
DISASTER_WINDOW = {"YAGI_TT53": ("2024-09-07", "2025-12-31"), "BAO_10_11_12_CV9651": ("2025-07-01", "2026-12-31")}

META: dict[str, dict] = {}
CLEAN_LOG: dict[str, int] = {}


def _meta(name, group, source, formula, unit="%", processing="quý", kind="theo NH-quý"):
    META[name] = dict(group=group, source=source, formula=formula, unit=unit, processing=processing, kind=kind)


def _read(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False, **kw)


def _log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")


def _qidx(period: pd.Series) -> pd.Series:
    return period.str[:4].astype(int) * 4 + period.str[-1].astype(int) - 1


def _to_period(dates: pd.Series) -> pd.Series:
    d = pd.to_datetime(dates)
    return d.dt.year.astype(str) + "-Q" + d.dt.quarter.astype(str)


def _div(num, den, name, scale=100.0):
    num, den = pd.Series(num, dtype="float64"), pd.Series(den, dtype="float64")
    bad = den.isna() | (den <= 0)
    out = (num / den.where(~bad)) * scale
    out = out.replace([np.inf, -np.inf], np.nan)
    CLEAN_LOG[name] = int(((den <= 0) & num.notna()).sum())  # chi dem o co mau <= 0, khong dem o thieu lich su
    return out


def _growth(cur, base, name):
    cur, base = pd.Series(cur, dtype="float64"), pd.Series(base, dtype="float64")
    bad = base.isna() | (base <= 0)
    CLEAN_LOG[name] = int(((base <= 0) & cur.notna()).sum())
    return ((cur / base.where(~bad)) - 1) * 100


def _growth_sym(cur, base):
    cur, base = pd.Series(cur, dtype="float64"), pd.Series(base, dtype="float64")
    den = cur.abs() + base.abs()
    return (200 * (cur - base) / den.where(den > 0)).replace([np.inf, -np.inf], np.nan)


# --------------------------------------------------------------------------- khung
def _grid() -> pd.DataFrame:
    p = _read(PANEL)
    p = p.drop(columns=[c for c in p.columns if c.endswith("_src") or c == "built_at_utc"])
    # Chi phi von va loi suat TSSL bang dung 0 la o thieu con sot (nguon ghi 0 thay vi rong).
    for c in ("cof_ttm_percent", "earning_asset_yield_ttm_percent"):
        zero = p[c] == 0
        CLEAN_LOG[f"{c}_zero_as_missing"] = int(zero.sum())
        p.loc[zero, c] = np.nan
    p["qi"] = _qidx(p.period)
    return p.sort_values(["ticker", "qi"]).reset_index(drop=True)


PANEL_META = {
    "loans_qoq_percent": ("G Quy mô & tăng trưởng", "Tăng trưởng dư nợ so quý trước", "%"),
    "loans_yoy_percent": ("G Quy mô & tăng trưởng", "Tăng trưởng dư nợ so cùng kỳ", "%"),
    "loans_over_assets_percent": ("L Thanh khoản", "Dư nợ / tổng tài sản", "%"),
    "ldr_computed_percent": ("L Thanh khoản", "Dư nợ / tiền gửi khách hàng", "%"),
    "npl_coverage_percent": ("A Chất lượng tài sản", "Dự phòng / nợ xấu", "%"),
    "provision_over_loans_percent": ("A Chất lượng tài sản", "Dự phòng / dư nợ", "%"),
    "loans_g2_percent": ("A Chất lượng tài sản", "Nợ nhóm 2 / dư nợ", "%"),
    "casa_percent": ("L Thanh khoản", "Tiền gửi không kỳ hạn / tổng tiền gửi", "%"),
    "loans_short_share_percent": ("L Thanh khoản", "Cho vay ngắn hạn / dư nợ", "%"),
    "loans_medium_share_percent": ("L Thanh khoản", "Cho vay trung hạn / dư nợ", "%"),
    "loans_long_share_percent": ("L Thanh khoản", "Cho vay dài hạn / dư nợ", "%"),
    "vnd_deposit_share_percent": ("S Nhạy cảm thị trường", "Tiền gửi VNĐ / tiền gửi theo loại tiền", "%"),
    "deposit_cost_implied_ttm_percent": ("E Thu nhập & chi phí vốn", "Trả lãi tiền gửi TTM / tiền gửi bình quân (suy ra)", "%"),
    "roe_ttm_percent": ("E Thu nhập & chi phí vốn", "ROE TTM (MAS)", "%"),
    "roa_ttm_percent": ("E Thu nhập & chi phí vốn", "ROA TTM (MAS)", "%"),
    "cir_ttm_approx_percent": ("M Quản trị", "Chi phí / thu nhập TTM (MAS, xấp xỉ)", "%"),
    "pe": ("T Thị trường", "P/E (MAS)", "lần"),
    "pb": ("T Thị trường", "P/B (MAS)", "lần"),
    "eps_vnd": ("T Thị trường", "EPS (MAS)", "đồng"),
    "bvps_vnd": ("T Thị trường", "Giá trị sổ sách / cổ phiếu (MAS)", "đồng"),
    "beta": ("T Thị trường", "Beta (MAS)", "lần"),
    "dividend_yield": ("T Thị trường", "Tỷ suất cổ tức (MAS)", "%"),
    "car_percent": ("C Vốn", "CAR đúng quý công bố (Q2, Q4)", "%"),
    "npl_percent": ("A Chất lượng tài sản", "Nợ xấu / dư nợ (thuyết minh → VCI)", "%"),
    "cof_ttm_percent": ("E Thu nhập & chi phí vốn", "Chi phí vốn TTM (VCI → MAS)", "%"),
    "nim_ttm_percent": ("E Thu nhập & chi phí vốn", "Biên lãi thuần TTM (VCI → MAS)", "%"),
    "earning_asset_yield_ttm_percent": ("E Thu nhập & chi phí vốn", "Lợi suất tài sản sinh lãi TTM (MAS → suy ra)", "%"),
    "loans_vnd": ("G Quy mô & tăng trưởng", "Dư nợ (đồng) — mức tuyệt đối", "đồng"),
    "deposits_vnd": ("G Quy mô & tăng trưởng", "Tiền gửi khách hàng (đồng) — mức tuyệt đối", "đồng"),
    "total_assets_vnd": ("G Quy mô & tăng trưởng", "Tổng tài sản (đồng) — mức tuyệt đối", "đồng"),
    "loan_provision_vnd": ("A Chất lượng tài sản", "Dự phòng cho vay (đồng) — mức tuyệt đối", "đồng"),
}


# --------------------------------------------------------------------------- BCTC
FIN_IDS = {
    "TA": "BS_TOTAL_ASSETS", "EQ": "BS_EQUITY", "TL": "BS_TOTAL_LIABILITIES",
    "LOANS": "BS_LOANS_TO_CUSTOMERS_GROSS", "DEP": "BS_CUSTOMER_DEPOSITS",
    "CASH": "BS_CASH_AND_PRECIOUS_METALS", "SBV": "BS_BALANCES_WITH_SBV",
    "PLAC": "BS_PLACEMENTS_AND_LOANS_TO_CREDIT_INSTITUTIONS", "TRAD": "BS_TRADING_SECURITIES",
    "INVSEC": "BS_INVESTMENT_SECURITIES", "BORR_CI": "BS_PLACEMENTS_AND_BORROWINGS_FROM_CREDIT_INSTITUTIONS",
    "GOV": "BS_DUE_TO_GOVERNMENT_AND_SBV", "PAPERS": "BS_VALUABLE_PAPERS_ISSUED", "RETAINED": "BS_RETAINED_EARNINGS",
    "NII": "IS_NET_INTEREST_INCOME", "FEE": "IS_NET_FEE_AND_COMMISSION_INCOME", "TOI": "IS_TOTAL_OPERATING_INCOME",
    "PPOP": "IS_OPERATING_PROFIT_BEFORE_PROVISION_FOR_CREDIT_LOSSES", "PROV_EXP": "IS_PROVISION_FOR_CREDIT_LOSSES",
    "NPAT": "IS_NET_PROFIT_AFTER_TAX", "CFO": "CF_NET_CASH_FLOWS_FROM_OPERATING_ACTIVITIES",
    "RECOV": "CF_COLLECTIONS_FROM_BAD_DEBTS_WRITTEN_OFF", "DIV_PAID": "CF_DIVIDENDS_PAID",
    "INT_RECV": "BS_INTEREST_AND_FEE_RECEIVABLES",
}
NOTE_IDS = {
    "DEP_TYPE": "NT_BS_DEPOSITS_BY_TYPE_OF_DEPOSITS", "N_SUB": "NT_BS_SUBSTANDARD", "N_DOUBT": "NT_BS_DOUBTFUL",
    "N_BAD": "NT_BS_BAD", "INV_TOTAL": "NT_BS_INVESTMENT_SECURITIES",
    "INV_GOV": "NT_BS_INVESTMENT_SECURITIES_GOVERNMENT_BONDS",
    "INV_CI": "NT_BS_INVESTMENT_SECURITIES_SECURITIES_ISSUED_BY_LOCAL_CREDIT_INSTITUTIONS",
    "INV_CORP": "NT_BS_INVESTMENT_SECURITIES_SECURITIES_ISSUED_BY_LOCAL_ECONOMIC_ENTITIES",
    "DEP_INT": "NT_IS_DEPOSIT_INTEREST_EXPENSES", "PAPER_INT": "NT_IS_INTEREST_EXPENSES_FOR_ISSUANCE_OF_VALUABLE_PAPERS",
    "LOAN_INT": "NT_IS_INTEREST_INCOME_FROM_LOANS_TO_CUSTOMERS", "SALARY": "NT_IS_SALARY_AND_ALLOWANCES",
    "DEP_INS": "NT_IS_INSURANCE_AND_DEPOSIT_INSURANCE_FEES",
    "LOANS_INDIV": "NT_BS_INDIVIDUALS", "LOANS_BY_CUST": "NT_BS_LOANS_AND_ADVANCES_BY_TYPES_OF_CUSTOMERS",
    "DEP_INDIV": "NT_BS_DEPOSITS_BY_TYPE_OF_CUSTOMERS_INDIVIDUALS", "DEP_BY_CUST": "NT_BS_DEPOSITS_BY_TYPE_OF_CUSTOMERS",
    "VAMC": "NT_BS_SPECIAL_BONDS_ISSUED_BY_VAMC",
}
FLOWS = {"NII", "FEE", "TOI", "PPOP", "PROV_EXP", "NPAT", "CFO", "RECOV", "DIV_PAID",
         "DEP_INT", "PAPER_INT", "LOAN_INT", "SALARY", "DEP_INS"}


def _wide(path, ids, freq_filter=True, corrections=False):
    d = _read(path, usecols=lambda c: c in {"ticker", "freq", "period", "id", "value"})
    if freq_filter:
        d = d[d.freq == "quarter"]
    d = d[d.id.isin(ids.values())]
    if corrections:  # o VCI ghi sai da doi chieu BCTC goc (note_long giu nguyen ban sao nguon)
        from crawlers import vnstock_note
        d, applied, skipped = vnstock_note._apply_corrections(d)
        CLEAN_LOG["note_corrections_applied"] = len(applied)
        CLEAN_LOG["note_corrections_skipped"] = len(skipped)
    w = d.pivot_table(index=["ticker", "period"], columns="id", values="value", aggfunc="first")
    w = w.rename(columns={v: k for k, v in ids.items()}) / 1e9  # dong -> ty dong
    return w.reset_index()


def _indiv_share_audited() -> pd.DataFrame:
    ind = _read(INDUSTRY_ROWS)
    ind = ind[ind.industry_group == "INDIV"]
    return pd.DataFrame({"ticker": ind.ticker, "period": ind.year.astype(str) + "-Q4",
                         "audited": 100 * ind.value_mn_vnd / ind.table_total_mn_vnd})


def _retail_share(g: pd.DataFrame) -> pd.Series:
    share = _div(g.LOANS_INDIV, g.LOANS_BY_CUST, "retail_loan_share_pct")
    audited = g[["ticker", "period"]].merge(_indiv_share_audited(), on=["ticker", "period"], how="left")["audited"]
    audited.index = g.index
    CLEAN_LOG["retail_share_note_vs_audited_gap_over_0_5pp"] = int(((share - audited).abs() > 0.5).sum())
    fill = share.isna() & audited.notna()
    CLEAN_LOG["retail_share_q4_from_audited_industry_table"] = int(fill.sum())
    return share.where(~fill, audited)


def add_financial(g: pd.DataFrame) -> pd.DataFrame:
    w = _wide(FIN, FIN_IDS).merge(_wide(NOTE, NOTE_IDS, freq_filter=False, corrections=True), on=["ticker", "period"], how="outer")
    g = g.merge(w, on=["ticker", "period"], how="left").sort_values(["ticker", "qi"]).reset_index(drop=True)
    for c in ("PROV_EXP", "DIV_PAID"):  # KQKD/LCTT luu chi phi la so am -> tri tuyet doi truoc khi cong don
        g[c] = g[c].abs()
    # Thuyet minh ghi 0 khi NH khong tach dong (chi luong, tra lai tien gui, cho vay ca nhan...) va co vai
    # o am vo nghia -> NaN. Rieng tra lai giay to co gia: 0 la that (NH khong phat hanh).
    for c in ("SALARY", "DEP_INS", "DEP_INT", "LOAN_INT", "LOANS_INDIV", "DEP_INDIV"):
        bad = g[c] <= 0
        CLEAN_LOG[f"{c.lower()}_nonpositive_as_missing"] = int(bad.sum())
        g.loc[bad, c] = np.nan
    bad = g.PAPER_INT < 0
    CLEAN_LOG["paper_int_negative_as_missing"] = int(bad.sum())
    g.loc[bad, "PAPER_INT"] = np.nan
    # EIB 2024-Q4: VCI don tien gui ca nhan sang dong "khac" (ca nhan 0,1 ty / 167.448 ty) -> khong NHTM nao duoi 1%.
    bad = g.DEP_INDIV < 0.01 * g.DEP_BY_CUST
    CLEAN_LOG["dep_indiv_under_1pct_as_missing"] = int(bad.sum())
    g.loc[bad, "DEP_INDIV"] = np.nan
    bad = g.VAMC < 0  # SHB 2018-Q1 ghi am: trai phieu VAMC gop khong the am
    CLEAN_LOG["vamc_negative_as_missing"] = int(bad.sum())
    g.loc[bad, "VAMC"] = np.nan
    bad = g.INV_TOTAL <= 0
    CLEAN_LOG["inv_total_zero_as_missing"] = int(bad.sum())
    g.loc[bad, ["INV_TOTAL", "INV_GOV"]] = np.nan
    bad = g.INV_GOV > g.INV_TOTAL * 1.001
    CLEAN_LOG["gov_bond_over_total_invsec"] = int(bad.sum())
    g.loc[bad, "INV_GOV"] = np.nan
    by = g.groupby("ticker", group_keys=False)
    ttm = {c: by[c].transform(lambda s: s.rolling(4, min_periods=4).sum()) for c in FLOWS}
    avg = {c: by[c].transform(lambda s: s.rolling(5, min_periods=4).mean()) for c in ("TA", "EQ", "LOANS", "DEP")}
    lag4 = lambda s: by[s].shift(4)  # noqa: E731
    opex = ttm["TOI"] - ttm["PPOP"]

    F, N, S = "financial_long.csv", "note_long.csv", "financial_long + note_long"
    new = {}

    def put(name, series, group, source, formula, unit="%", processing="quý: TTM / bình quân 5 mốc"):
        new[name] = series
        _meta(name, group, source, formula, unit, processing)

    put("equity_to_assets_pct", _div(g.EQ, g.TA, "equity_to_assets_pct"), "C Vốn", F, "Vốn chủ / tổng tài sản", processing="quý: số dư cuối kỳ")
    put("equity_to_loans_pct", _div(g.EQ, g.LOANS, "equity_to_loans_pct"), "C Vốn", F, "Vốn chủ / dư nợ gộp", processing="quý: số dư cuối kỳ")
    put("retained_to_equity_pct", _div(g.RETAINED, g.EQ, "retained_to_equity_pct"), "C Vốn", F, "LN chưa phân phối / vốn chủ", processing="quý: số dư cuối kỳ")
    put("dividend_payout_ttm_pct", _div(ttm["DIV_PAID"], ttm["NPAT"], "dividend_payout_ttm_pct"), "C Vốn", F, "Cổ tức tiền mặt đã trả TTM / LNST TTM")
    put("credit_cost_ttm_pct", _div(ttm["PROV_EXP"], avg["LOANS"], "credit_cost_ttm_pct"), "A Chất lượng tài sản", F, "Chi phí dự phòng tín dụng TTM / dư nợ bình quân")
    put("recovery_ttm_pct", _div(ttm["RECOV"], avg["LOANS"], "recovery_ttm_pct"), "A Chất lượng tài sản", F, "Thu hồi nợ đã xử lý TTM / dư nợ bình quân")
    put("npl_group5_share_pct", _div(g.N_BAD, g.N_SUB + g.N_DOUBT + g.N_BAD, "npl_group5_share_pct"), "A Chất lượng tài sản", N, "Nợ nhóm 5 / nợ xấu (nhóm 3–5)", processing="quý: số dư cuối kỳ")
    # Ung vien them ngay 13/10/2026 khi ra lai du lieu cu (experiments.feature_effect do tac dung).
    put("accrued_interest_to_assets_pct", _div(g.INT_RECV, g.TA, "accrued_interest_to_assets_pct"), "A Chất lượng tài sản", F,
        "Lãi và phí phải thu (lãi dự thu) / tổng tài sản", processing="quý: số dư cuối kỳ")
    put("vamc_bonds_to_assets_pct", _div(g.VAMC, g.TA, "vamc_bonds_to_assets_pct"), "A Chất lượng tài sản", S,
        "Trái phiếu đặc biệt VAMC (gộp) / tổng tài sản", processing="quý: số dư cuối kỳ; 0 là thật (NH không còn bán nợ cho VAMC)")
    put("cir_ttm_pct", _div(opex, ttm["TOI"], "cir_ttm_pct"), "M Quản trị", F, "(TNHĐ − LN trước dự phòng) TTM / TNHĐ TTM")
    put("opex_to_assets_ttm_pct", _div(opex, avg["TA"], "opex_to_assets_ttm_pct"), "M Quản trị", F, "Chi phí hoạt động TTM / tổng tài sản bình quân")
    put("staff_cost_share_pct", _div(ttm["SALARY"], opex, "staff_cost_share_pct"), "M Quản trị", S, "Chi lương, phụ cấp TTM / chi phí hoạt động TTM")
    put("deposit_insurance_to_deposits_pct", _div(ttm["DEP_INS"], avg["DEP"], "deposit_insurance_to_deposits_pct"), "M Quản trị", S, "Phí bảo hiểm tiền gửi TTM / tiền gửi bình quân")
    put("roaa_ttm_pct", _div(ttm["NPAT"], avg["TA"], "roaa_ttm_pct"), "E Thu nhập & chi phí vốn", F, "LNST TTM / tổng tài sản bình quân")
    put("roae_ttm_pct", _div(ttm["NPAT"], avg["EQ"], "roae_ttm_pct"), "E Thu nhập & chi phí vốn", F, "LNST TTM / vốn chủ bình quân")
    put("ppop_to_assets_ttm_pct", _div(ttm["PPOP"], avg["TA"], "ppop_to_assets_ttm_pct"), "E Thu nhập & chi phí vốn", F, "LN trước dự phòng TTM / tổng tài sản bình quân")
    put("noii_share_ttm_pct", _div(ttm["TOI"] - ttm["NII"], ttm["TOI"], "noii_share_ttm_pct"), "E Thu nhập & chi phí vốn", F, "Thu nhập ngoài lãi TTM / TNHĐ TTM")
    put("fee_share_ttm_pct", _div(ttm["FEE"], ttm["TOI"], "fee_share_ttm_pct"), "E Thu nhập & chi phí vốn", F, "Lãi thuần dịch vụ TTM / TNHĐ TTM")
    put("loan_yield_ttm_pct", _div(ttm["LOAN_INT"], avg["LOANS"], "loan_yield_ttm_pct"), "E Thu nhập & chi phí vốn", S, "Thu lãi cho vay TTM / dư nợ bình quân")
    put("retail_loan_share_pct", _retail_share(g), "P Chính sách & cơ cấu tín dụng", N + " + loans_by_industry_annual",
        "Cho vay cá nhân / dư nợ phân theo nhóm khách hàng",
        processing="quý: số dư cuối kỳ; NH chỉ công bố nửa năm/năm thì quý giữa để trống; "
                   "quý 4 thiếu lấy dòng 'Cá nhân' của bảng ngành BCTC kiểm toán (MSB, NVB, TCB)")
    put("retail_deposit_share_pct", _div(g.DEP_INDIV, g.DEP_BY_CUST, "retail_deposit_share_pct"), "L Thanh khoản", N,
        "Tiền gửi cá nhân / tiền gửi phân theo nhóm khách hàng",
        processing="quý: số dư cuối kỳ; NH chỉ công bố nửa năm/năm thì quý giữa để trống; dòng cá nhân ≤ 0 hoặc < 1% tổng → NaN")
    put("deposit_rate_paid_ttm_pct", _div(ttm["DEP_INT"], avg["DEP"], "deposit_rate_paid_ttm_pct"), "E Thu nhập & chi phí vốn", S, "Trả lãi tiền gửi TTM / tiền gửi bình quân")
    put("npat_yoy_sym_pct", _growth_sym(ttm["NPAT"], by["NPAT"].transform(lambda s: s.rolling(4, min_periods=4).sum().shift(4))),
        "E Thu nhập & chi phí vốn", F, "Tăng trưởng đối xứng LNST TTM so cùng kỳ: 200(a−b)/(|a|+|b|)", processing="quý: TTM, đối xứng [−200, 200]")
    put("toi_yoy_sym_pct", _growth_sym(ttm["TOI"], by["TOI"].transform(lambda s: s.rolling(4, min_periods=4).sum().shift(4))),
        "E Thu nhập & chi phí vốn", F, "Tăng trưởng đối xứng TNHĐ TTM so cùng kỳ: 200(a−b)/(|a|+|b|)", processing="quý: TTM, đối xứng [−200, 200]")
    put("liquid_assets_pct", _div(g.CASH + g.SBV + g.PLAC + g.TRAD, g.TA, "liquid_assets_pct"), "L Thanh khoản", F,
        "(Tiền + tiền gửi NHNN + tiền gửi/cho vay TCTD + CK kinh doanh) / tổng tài sản", processing="quý: số dư cuối kỳ")
    put("deposits_to_liabilities_pct", _div(g.DEP, g.TL, "deposits_to_liabilities_pct"), "L Thanh khoản", F, "Tiền gửi khách hàng / tổng nợ", processing="quý: số dư cuối kỳ")
    put("interbank_funding_pct", _div(g.BORR_CI, g.TL, "interbank_funding_pct"), "L Thanh khoản", F, "Tiền gửi và vay TCTD khác / tổng nợ", processing="quý: số dư cuối kỳ")
    put("papers_funding_pct", _div(g.PAPERS, g.TL, "papers_funding_pct"), "L Thanh khoản", F, "Giấy tờ có giá phát hành / tổng nợ", processing="quý: số dư cuối kỳ")
    put("gov_sbv_funding_pct", _div(g.GOV, g.TL, "gov_sbv_funding_pct"), "L Thanh khoản", F, "Nợ Chính phủ và NHNN / tổng nợ", processing="quý: số dư cuối kỳ")
    put("cfo_to_assets_ttm_pct", _div(ttm["CFO"], avg["TA"], "cfo_to_assets_ttm_pct"), "L Thanh khoản", F, "Lưu chuyển tiền thuần HĐKD TTM / tổng tài sản bình quân")
    put("invsec_to_assets_pct", _div(g.INVSEC, g.TA, "invsec_to_assets_pct"), "S Nhạy cảm thị trường", F, "Chứng khoán đầu tư / tổng tài sản", processing="quý: số dư cuối kỳ")
    put("gov_bond_share_invsec_pct", _div(g.INV_GOV, g.INV_TOTAL, "gov_bond_share_invsec_pct"), "S Nhạy cảm thị trường", N, "Trái phiếu Chính phủ / chứng khoán đầu tư", processing="quý: số dư cuối kỳ")
    put("corp_bond_to_assets_pct", _div(g.INV_CORP, g.TA, "corp_bond_to_assets_pct"), "S Nhạy cảm thị trường", S, "Trái phiếu TCKT trong nước / tổng tài sản", processing="quý: số dư cuối kỳ")
    put("ci_bond_to_assets_pct", _div(g.INV_CI, g.TA, "ci_bond_to_assets_pct"), "S Nhạy cảm thị trường", S, "Trái phiếu TCTD khác / tổng tài sản", processing="quý: số dư cuối kỳ")
    put("paper_interest_share_pct", _div(ttm["PAPER_INT"], ttm["PAPER_INT"] + ttm["DEP_INT"], "paper_interest_share_pct"), "L Thanh khoản", N,
        "Trả lãi giấy tờ có giá TTM / (trả lãi GTCG + trả lãi tiền gửi) TTM")
    put("log_total_assets", np.log(g.TA.where(g.TA > 0)), "G Quy mô & tăng trưởng", F, "ln(tổng tài sản, tỷ đồng)", unit="ln", processing="quý: số dư cuối kỳ")
    put("assets_yoy_pct", _growth(g.TA, lag4("TA"), "assets_yoy_pct"), "G Quy mô & tăng trưởng", F, "Tổng tài sản so cùng kỳ", processing="quý: số dư cuối kỳ")
    put("deposits_yoy_pct", _growth(g.DEP, lag4("DEP"), "deposits_yoy_pct"), "G Quy mô & tăng trưởng", F, "Tiền gửi khách hàng so cùng kỳ", processing="quý: số dư cuối kỳ")
    put("equity_yoy_pct", _growth(g.EQ, lag4("EQ"), "equity_yoy_pct"), "G Quy mô & tăng trưởng", F, "Vốn chủ so cùng kỳ", processing="quý: số dư cuối kỳ")
    tot = g.groupby("period")[["LOANS", "DEP"]].transform("sum")
    put("loan_market_share_pct", _div(g.LOANS, tot.LOANS, "loan_market_share_pct"), "G Quy mô & tăng trưởng", F, "Dư nợ / tổng dư nợ 22 NH cùng quý", processing="quý: số dư cuối kỳ")
    put("deposit_market_share_pct", _div(g.DEP, tot.DEP, "deposit_market_share_pct"), "G Quy mô & tăng trưởng", F, "Tiền gửi / tổng tiền gửi 22 NH cùng quý", processing="quý: số dư cuối kỳ")
    g = pd.concat([g.drop(columns=list(FIN_IDS) + list(NOTE_IDS)), pd.DataFrame(new, index=g.index)], axis=1)

    by = g.groupby("ticker")
    g["yield_cof_spread_pp"] = g.earning_asset_yield_ttm_percent - g.cof_ttm_percent
    _meta("yield_cof_spread_pp", "E Thu nhập & chi phí vốn", "bank_panel_quarterly", "Lợi suất TSSL TTM − chi phí vốn TTM", "điểm %")
    for col, nm in (("nim_ttm_percent", "nim"), ("cof_ttm_percent", "cof"), ("npl_percent", "npl"), ("casa_percent", "casa"),
                    ("ldr_computed_percent", "ldr"), ("roe_ttm_percent", "roe")):
        g[f"{nm}_chg_qoq_pp"] = by[col].diff()
        g.loc[by.qi.diff() != 1, f"{nm}_chg_qoq_pp"] = np.nan
        _meta(f"{nm}_chg_qoq_pp", "D Động lượng", "bank_panel_quarterly", f"Thay đổi {col} so quý trước", "điểm %")
    return g


# --------------------------------------------------------------------------- tan suat khac
def _asof_annual(period: pd.Series) -> pd.Series:
    y = period.str[:4].astype(int)
    return np.where(period.str[-1] == "4", y, y - 1)


def add_car(g):
    car = _read(CAR)[["ticker", "period", "car_percent"]].dropna()
    y, h = car.period.str[:4].astype(int), car.period.str[-1]
    rows = []
    for (t, yy, hh, v) in zip(car.ticker, y, h, car.car_percent):
        qs = [(yy, 2), (yy, 3)] if hh == "1" else [(yy, 4), (yy + 1, 1)]
        rows += [(t, f"{a}-Q{b}", v) for a, b in qs]
    m = pd.DataFrame(rows, columns=["ticker", "period", "car_asof_percent"]).drop_duplicates(["ticker", "period"], keep="last")
    _meta("car_asof_percent", "C Vốn", "bank_car_halfyear", "CAR hợp nhất gần nhất đã công bố", processing="nửa năm → as-of 2 quý")
    return g.merge(m, on=["ticker", "period"], how="left")


def add_annual_structure(g):
    g["asof_year"] = _asof_annual(g.period)
    ind = _read(INDUSTRY).rename(columns={"year": "asof_year"})
    groups = {"A": "nông, lâm, thủy sản", "C": "công nghiệp chế biến", "F": "xây dựng", "G": "thương mại", "L": "bất động sản"}
    cols = {f"share_pct_{k}": f"ind_share_{k}_asof_pct" for k in groups}
    g = g.merge(ind[["ticker", "asof_year"] + list(cols)].rename(columns=cols), on=["ticker", "asof_year"], how="left")
    for k, v in groups.items():
        _meta(f"ind_share_{k}_asof_pct", "P Chính sách & cơ cấu tín dụng", "loans_by_industry_group_wide", f"Tỷ trọng dư nợ ngành {v} (BCTC kiểm toán)",
              processing="năm → as-of (Q4/Y, Q1–Q3/Y+1)")
    agri = _read(AGRI)[["ticker", "year", "agri_share_pct"]].rename(columns={"year": "asof_year", "agri_share_pct": "agri_share_asof_pct"})
    g = g.merge(agri, on=["ticker", "asof_year"], how="left")
    _meta("agri_share_asof_pct", "P Chính sách & cơ cấu tín dụng", "agri_loans_annual", "Dư nợ nông, lâm, thủy sản / dư nợ theo ngành",
          processing="năm → as-of (Q4/Y, Q1–Q3/Y+1)")
    cg = _read(CREDIT_GROWTH)[["year", "credit_growth_percent"]].rename(columns={"year": "asof_year", "credit_growth_percent": "system_credit_growth_asof_pct"})
    g = g.merge(cg, on="asof_year", how="left")
    _meta("system_credit_growth_asof_pct", "V Vĩ mô", "credit_growth", "Tăng trưởng tín dụng toàn hệ thống năm gần nhất",
          processing="năm → as-of", kind="chung mọi NH")
    return g.drop(columns="asof_year")


def add_policy(g):
    q_end = pd.to_datetime(g.period_end)
    pp = _read(PROGRAMS)
    codes = sorted(pp.program_code.unique())
    for code in codes:
        sub = pp[(pp.program_code == code) & (pp.participates == 1)]
        start = pd.to_datetime(sub.list_as_of.iloc[0]) if len(sub) else None
        name = f"prog_{code.lower()}"
        g[name] = (g.ticker.isin(sub.ticker) & (q_end >= start)).astype(int) if start is not None else 0
        _meta(name, "P Chính sách & cơ cấu tín dụng", "program_participation", f"= 1 nếu NH có trong danh sách {code} và quý kết thúc sau ngày danh sách",
              unit="0/1", processing="sự kiện → hiệu lực từ list_as_of")
    g["n_programs_active"] = g[[f"prog_{c.lower()}" for c in codes]].sum(axis=1)
    _meta("n_programs_active", "P Chính sách & cơ cấu tín dụng", "program_participation", "Số chương trình tín dụng chính sách đang tham gia",
          unit="số", processing="sự kiện → hiệu lực từ list_as_of")

    br = _read(BRANCH)
    br["prov"] = br.province.str.replace(r"^(Thành phố|Tỉnh)\s+", "", regex=True)
    total = br.groupby("ticker").n_bank.sum()
    dp = _read(DISASTER)
    expo = pd.Series(0.0, index=g.index)
    q_start = pd.to_datetime(g.period.str[:4] + "-" + ((g.period.str[-1].astype(int) - 1) * 3 + 1).astype(str).str.zfill(2) + "-01")
    for ev, (a, b) in DISASTER_WINDOW.items():
        provs = set(dp.loc[dp.event_code == ev, "province_2025"])
        share = br[br.prov.isin(provs)].groupby("ticker").n_bank.sum().div(total).mul(100).reindex(total.index).fillna(0)
        active = (q_end >= pd.Timestamp(a)) & (q_start <= pd.Timestamp(b))
        expo = np.maximum(expo, np.where(active, g.ticker.map(share).fillna(0), 0))
    g["disaster_branch_share_pct"] = expo
    _meta("disaster_branch_share_pct", "P Chính sách & cơ cấu tín dụng", "disaster_provinces + branch_by_province",
          "% chi nhánh nằm ở tỉnh bị thiên tai trong cửa sổ hiệu lực (Yagi 9/2024–12/2025; bão 10–12 7/2025–)",
          processing="sự kiện × ảnh chụp chi nhánh 2026 (giả định mạng lưới ổn định)")
    return g


def add_static(g):
    # File ghi noi moi lan crawl (tu 01/10/2026 co hon mot anh chup): chi lay anh chup moi nhat cua moi NH.
    ow = _read(OWNERSHIP).sort_values("date").drop_duplicates("ticker", keep="last")
    asof = datetime.strptime(ow.date.max(), "%Y-%m-%d").strftime("%d/%m/%Y")
    ow = ow[["ticker", "state_own_percent", "foreign_own_percent", "foreign_room_percent"]]
    ow["foreign_room_used_pct"] = _div(ow.foreign_own_percent, ow.foreign_room_percent, "foreign_room_used_pct")
    g = g.merge(ow.drop(columns="foreign_room_percent"), on="ticker", how="left")
    for c, f in (("state_own_percent", "Sở hữu nhà nước"), ("foreign_own_percent", "Sở hữu nước ngoài"),
                 ("foreign_room_used_pct", "Sở hữu nước ngoài / room tối đa")):
        _meta(c, "M Quản trị", "bank_ownership", f"{f} (ảnh chụp {asof})", processing="ảnh chụp → lặp mọi quý", kind="tĩnh theo NH")
    br = _read(BRANCH).groupby("ticker").agg(n_bank=("n_bank", "sum"), n_atm=("n_atm", "sum"), n_prov=("province", "nunique"))
    br["log_branches"] = np.log1p(br.n_bank)
    br["atm_per_branch"] = _div(br.n_atm, br.n_bank, "atm_per_branch", scale=1.0)
    br = br.rename(columns={"n_prov": "n_provinces_present"})[["log_branches", "atm_per_branch", "n_provinces_present"]]
    g = g.merge(br.reset_index(), on="ticker", how="left")
    for c, f, u in (("log_branches", "ln(1 + số chi nhánh/PGD trên OSM)", "ln"), ("atm_per_branch", "Số ATM / số chi nhánh", "lần"),
                    ("n_provinces_present", "Số tỉnh (34 tỉnh mới) có chi nhánh", "số")):
        _meta(c, "G Quy mô & tăng trưởng", "branch_by_province", f, u, processing="ảnh chụp OSM → lặp mọi quý", kind="tĩnh theo NH")
    return g


APP_SPIKE_RATIO, APP_SPIKE_STARS, APP_SPIKE_BASE = 3.0, 1.0, 6


def app_spike_months(m: pd.DataFrame) -> pd.Series:
    flag = pd.Series(False, index=m.index)
    for _, g in m.sort_values(["ticker", "month"]).groupby("ticker"):
        base = []  # (n, diem) cac thang khong gan co, co review
        for i, r in g.iterrows():
            prev = base[-APP_SPIKE_BASE:]
            if len(prev) >= 3 and r.n_reviews >= MIN_REVIEWS:
                n = np.array([p[0] for p in prev], float)
                s = np.array([p[1] for p in prev], float)
                if (r.n_reviews >= APP_SPIKE_RATIO * np.median(n)
                        and abs(r.mean_score - (n * s).sum() / n.sum()) >= APP_SPIKE_STARS):
                    flag[i] = True
                    continue
            if r.n_reviews > 0:
                base.append((r.n_reviews, r.mean_score))
    return flag


def add_customer(g):
    m = _read(APP)
    spike = app_spike_months(m)
    CLEAN_LOG["app_spike_months_excluded_from_scores"] = int(spike.sum())
    m["period"] = _to_period(m.month + "-01")
    # So review (app_reviews_log) giu ca thang co dot; diem, % 1 sao, ty le tra loi bo thang co dot
    m.loc[spike, ["mean_score", "pct_1star", "reply_rate"]] = np.nan
    m["n_scored"] = m.n_reviews.where(~spike, 0)
    m["w_score"] = m.mean_score * m.n_scored
    m["w_1star"] = m.pct_1star * m.n_scored
    m["w_reply"] = m.reply_rate * m.n_scored
    q = m.groupby(["ticker", "period"]).agg(n=("n_reviews", "sum"), ns=("n_scored", "sum"), s=("w_score", "sum"),
                                            o=("w_1star", "sum"), r=("w_reply", "sum")).reset_index()
    thin = q.ns < MIN_REVIEWS
    CLEAN_LOG["app_quarters_below_min_reviews"] = int(thin.sum())
    q["app_reviews_log"] = np.log1p(q.n)
    q["app_mean_score"] = (q.s / q.ns).where(~thin)
    q["app_pct_1star"] = (q.o / q.ns * 100).where(~thin)
    q["app_reply_rate_pct"] = (q.r / q.ns * 100).where(~thin)
    g = g.merge(q[["ticker", "period", "app_reviews_log", "app_mean_score", "app_pct_1star", "app_reply_rate_pct"]], on=["ticker", "period"], how="left")
    src = "app_reviews_monthly (app bán lẻ Play Store)"
    _meta("app_reviews_log", "K Khách hàng số", src, "ln(1 + số review trong quý)", "ln", "tháng → tổng quý")
    _meta("app_mean_score", "K Khách hàng số", src, "Điểm sao trung bình có trọng số số review", "sao", f"tháng → trung bình trọng số, bỏ tháng có đợt review bất thường (app_spike_months); quý < {MIN_REVIEWS} review → NaN")
    _meta("app_pct_1star", "K Khách hàng số", src, "% review 1 sao", "%", f"tháng → trung bình trọng số, bỏ tháng có đợt review bất thường (app_spike_months); quý < {MIN_REVIEWS} review → NaN")
    _meta("app_reply_rate_pct", "K Khách hàng số", src, "% review được NH phản hồi", "%", f"tháng → trung bình trọng số, bỏ tháng có đợt review bất thường (app_spike_months); quý < {MIN_REVIEWS} review → NaN")
    return g


def add_rates(g):
    # 24hmoney tron bac so tien o mot so NH (Sacombank) - doc qua lop dua ve bac thap nhat.
    from crawlers import deposit_tiers
    d = deposit_tiers.read(DEPOSIT)
    d = d[d.ticker.notna() & (d.term_months == 12)]
    d["period"] = _to_period(d.date)
    q = d.groupby(["ticker", "period", "channel"]).rate_percent.mean().unstack("channel").reset_index()
    q = q.rename(columns={"online": "dep12_online_pct", "quay": "dep12_counter_pct"})
    q["dep12_online_spread_pp"] = q.dep12_online_pct - q.groupby("period").dep12_online_pct.transform("mean")
    g = g.merge(q[["ticker", "period", "dep12_online_pct", "dep12_counter_pct", "dep12_online_spread_pp"]], on=["ticker", "period"], how="left")
    src = "deposit_24hmoney_daily"
    _meta("dep12_online_pct", "R Lãi suất niêm yết", src, "Lãi suất tiết kiệm 12 tháng online, trung bình các ngày quan sát", processing="ngày → trung bình quý")
    _meta("dep12_counter_pct", "R Lãi suất niêm yết", src, "Lãi suất tiết kiệm 12 tháng tại quầy", processing="ngày → trung bình quý")
    _meta("dep12_online_spread_pp", "R Lãi suất niêm yết", src, "Lãi suất 12 tháng online − trung bình 22 NH cùng quý", "điểm %", "ngày → trung bình quý")
    ln = _read(LENDING)
    ln = ln[ln.ticker.notna()]
    ln["period"] = _to_period(ln.month + "-01")
    lq = ln.groupby(["ticker", "period"]).lending_avg_percent.mean().rename("lending_avg_pct").reset_index()
    g = g.merge(lq, on=["ticker", "period"], how="left")
    _meta("lending_avg_pct", "R Lãi suất niêm yết", "bank_lending_rates_monthly", "Lãi suất cho vay bình quân NH công bố", processing="tháng → trung bình quý")
    return g


def _daily_quarter(df, prefix):
    df = df.copy()
    df["date"] = pd.to_datetime(df.time)
    df = df.sort_values("date")
    df["period"] = _to_period(df.date)
    df["lr"] = np.log(df.close / df.close.shift(1))
    df["value_vnd"] = df.close * 1000 * df.volume  # gia luu theo nghin dong
    q = df.groupby("period").agg(close=("close", "last"), n=("close", "size"), vol=("lr", "std"),
                                 adtv=("value_vnd", "mean")).reset_index()
    q["ret"] = (q.close / q.close.shift(1) - 1) * 100
    thin = q.n < MIN_SESSIONS
    q.loc[thin, ["ret", "vol", "adtv"]] = np.nan
    q["vol"] = q.vol * np.sqrt(252) * 100
    return q.rename(columns={"ret": f"{prefix}_ret_q_pct", "vol": f"{prefix}_vol_q_pct", "adtv": f"{prefix}_adtv"}), int(thin.sum())


def add_market(g):
    frames, thin_total = [], 0
    for f in sorted(glob.glob(os.path.join(PRICE_DIR, "*.csv"))):
        q, thin = _daily_quarter(_read(f), "stock")
        q["ticker"] = os.path.basename(f)[:3]
        frames.append(q)
        thin_total += thin
    px = pd.concat(frames)
    CLEAN_LOG["price_quarters_below_min_sessions"] = thin_total
    px["log_adtv"] = np.log(px.stock_adtv.where(px.stock_adtv > 0))
    idx, _ = _daily_quarter(_read(VNINDEX), "vnindex")
    g = g.merge(px[["ticker", "period", "stock_ret_q_pct", "stock_vol_q_pct", "log_adtv"]], on=["ticker", "period"], how="left")
    g = g.merge(idx[["period", "vnindex_ret_q_pct", "vnindex_vol_q_pct"]], on="period", how="left")
    g["excess_ret_q_pct"] = g.stock_ret_q_pct - g.vnindex_ret_q_pct
    src = "data/price"
    _meta("stock_ret_q_pct", "T Thị trường", src, "Lợi suất cổ phiếu trong quý", processing=f"ngày → quý; < {MIN_SESSIONS} phiên → NaN")
    _meta("stock_vol_q_pct", "T Thị trường", src, "Độ lệch chuẩn lợi suất log ngày × √252", processing=f"ngày → quý; < {MIN_SESSIONS} phiên → NaN")
    _meta("log_adtv", "T Thị trường", src, "ln(giá trị giao dịch bình quân phiên, đồng)", "ln", f"ngày → quý; < {MIN_SESSIONS} phiên → NaN")
    _meta("excess_ret_q_pct", "T Thị trường", "data/price + VNINDEX", "Lợi suất cổ phiếu − lợi suất VN-Index trong quý", processing="ngày → quý")
    _meta("vnindex_ret_q_pct", "V Vĩ mô", "VNINDEX", "Lợi suất VN-Index trong quý", processing="ngày → quý", kind="chung mọi NH")
    _meta("vnindex_vol_q_pct", "V Vĩ mô", "VNINDEX", "Biến động VN-Index (năm hóa)", processing="ngày → quý", kind="chung mọi NH")
    return g


def add_macro(g):
    cpi = _read(CPI)
    cpi["period"] = _to_period(cpi.month + "-01")
    pi = _read(PRICE_IDX)
    pi["period"] = _to_period(pi.month + "-01")
    mq = cpi.groupby("period").cpi_yoy_percent.mean().rename("cpi_yoy_q_pct").to_frame().join(
        pi.groupby("period")[["core_inflation_yoy_percent", "usd_index_yoy_percent", "gold_index_yoy_percent"]].mean().rename(
            columns={"core_inflation_yoy_percent": "core_cpi_yoy_q_pct", "usd_index_yoy_percent": "usd_index_yoy_q_pct",
                     "gold_index_yoy_percent": "gold_index_yoy_q_pct"}), how="outer").reset_index()
    g = g.merge(mq, on="period", how="left")
    pr = _read(POLICY_RATE)
    pr["date_effective"] = pd.to_datetime(pr.date_effective)
    ends = pd.to_datetime(pd.Series(sorted(g.period_end.unique())))
    for rt, nm in (("tai_cap_von", "refinancing_rate_pct"), ("tai_chiet_khau", "rediscount_rate_pct"), ("cho_vay_qua_dem", "overnight_sbv_rate_pct")):
        s = pr[pr.rate_type == rt].sort_values("date_effective")
        vals = [s.loc[s.date_effective <= e, "rate_percent"].iloc[-1] if (s.date_effective <= e).any() else np.nan for e in ends]
        g = g.merge(pd.DataFrame({"period_end": ends.dt.strftime("%Y-%m-%d"), nm: vals}), on="period_end", how="left")
        _meta(nm, "V Vĩ mô", "policy_rate", f"Lãi suất {rt.replace('_', ' ')} NHNN có hiệu lực cuối quý", processing="sự kiện → giá trị cuối quý", kind="chung mọi NH")
    for c, f in (("cpi_yoy_q_pct", "CPI so cùng kỳ"), ("core_cpi_yoy_q_pct", "Lạm phát cơ bản so cùng kỳ"),
                 ("usd_index_yoy_q_pct", "Chỉ số giá USD so cùng kỳ"), ("gold_index_yoy_q_pct", "Chỉ số giá vàng so cùng kỳ")):
        _meta(c, "V Vĩ mô", "cpi / price_indices (NSO)", f"{f}, trung bình 3 tháng", processing="tháng → trung bình quý", kind="chung mọi NH")
    return g


def build(write=True) -> dict:
    META.clear()
    CLEAN_LOG.clear()
    g = _grid()
    for col, (grp, formula, unit) in PANEL_META.items():
        _meta(col, grp, "bank_panel_quarterly", formula, unit, "đã chuẩn hóa ở build_panel")
    g = add_financial(g)
    g = add_car(g)
    g = add_annual_structure(g)
    g = add_policy(g)
    g = add_static(g)
    g = add_customer(g)
    g = add_rates(g)
    g = add_market(g)
    g = add_macro(g)

    feats = [c for c in g.columns if c in META]
    missing_meta = [c for c in g.columns if c not in META and c not in KEYS + ["qi"]]
    if missing_meta:
        raise ValueError(f"cot chua khai bao META: {missing_meta}")
    g[feats] = g[feats].replace([np.inf, -np.inf], np.nan)
    out = g.sort_values(["period", "ticker"])[KEYS + feats].reset_index(drop=True)
    if len(out) != 770 or out.duplicated(["ticker", "period"]).any():
        raise ValueError(f"khung sai: {len(out)} dong, trung khoa {int(out.duplicated(['ticker', 'period']).sum())}")
    num = out.select_dtypes("number").columns
    out[num] = out[num].round(6)
    if write:
        out.to_csv(OUT, index=False, encoding="utf-8-sig")
        spec = pd.DataFrame([{"feature": f, **META[f]} for f in feats])
        spec.to_csv(SPEC_OUT, index=False, encoding="utf-8-sig")
        _log(f"build_features: {len(out)} dong x {len(feats)} dac trung -> {OUT}; o bi lam sach: "
             + ", ".join(f"{k}={v}" for k, v in CLEAN_LOG.items() if v))
    return {"rows": len(out), "features": len(feats), "cleaned_cells": {k: v for k, v in CLEAN_LOG.items() if v}, "path": OUT}


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(build(), indent=2, ensure_ascii=False))
