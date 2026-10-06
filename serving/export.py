"""Xuất các bảng phục vụ cho web app vào data/serving/.

Đây là hợp đồng dữ liệu giữa pipeline Python và backend Java (webapp/backend):
  - Pipeline ghi CSV UTF-8 (không BOM), dấu thập phân là dấu chấm, ngày dạng ISO.
  - Backend nạp các file này vào cơ sở dữ liệu của nó (DataImportService), mỗi file thay
    toàn bộ bảng tương ứng. File không có thì bảng giữ nguyên.
  - Mọi số đều đi qua lớp đã làm sạch của pipeline (deposit_tiers.read, bank_panel_quarterly),
    backend không tự sửa số.

Ba file kết quả thuật toán (rankings.csv, forecasts.csv, app_aspects.csv) CHƯA được sinh ở
đây; schema của chúng ghi trong data/serving/README.md. Khi mô hình chốt, bước huấn luyện
ghi thẳng ba file đó vào data/serving/ và giao diện tự hiện kết quả.

Chạy (từ thư mục gốc D:/KLTN):
    python -m serving.export
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from crawlers import deposit_tiers

OUT = Path("data/serving")
PANEL = Path("data/model/bank_panel_quarterly.csv")
LENDING = Path("data/interest_rates/bank_lending_rates_monthly.csv")
PLAY_CATALOG = Path("data/app_reviews/app_catalog.csv")
IOS_CATALOG = Path("data/app_reviews/app_catalog_ios.csv")
REVIEWS_MONTHLY = Path("data/app_reviews/app_reviews_monthly.csv")
PROGRAM_PARTICIPATION = Path("data/policy_credit/program_participation.csv")
PROGRAM_RATES = Path("data/policy_credit/program_rates.csv")
CPI = Path("data/macro/cpi.csv")
OWNERSHIP = Path("data/ownership/bank_ownership.csv")

FIRST_PERIOD = "2019-Q1"  # mốc dữ liệu của đề tài (89% ô thiếu nằm ở năm 2018)
FIRST_MONTH = "2019-01"

# ticker -> (tên thường gọi, tên đầy đủ)
BANKS = {
    "ACB": ("ACB", "Ngân hàng TMCP Á Châu"),
    "BAB": ("BAC A BANK", "Ngân hàng TMCP Bắc Á"),
    "BID": ("BIDV", "Ngân hàng TMCP Đầu tư và Phát triển Việt Nam"),
    "BVB": ("BVBank", "Ngân hàng TMCP Bản Việt"),
    "CTG": ("VietinBank", "Ngân hàng TMCP Công Thương Việt Nam"),
    "EIB": ("Eximbank", "Ngân hàng TMCP Xuất Nhập khẩu Việt Nam"),
    "HDB": ("HDBank", "Ngân hàng TMCP Phát triển Thành phố Hồ Chí Minh"),
    "LPB": ("LPBank", "Ngân hàng TMCP Lộc Phát Việt Nam"),
    "MBB": ("MB", "Ngân hàng TMCP Quân đội"),
    "MSB": ("MSB", "Ngân hàng TMCP Hàng Hải Việt Nam"),
    "NAB": ("Nam A Bank", "Ngân hàng TMCP Nam Á"),
    "NVB": ("NCB", "Ngân hàng TMCP Quốc Dân"),
    "OCB": ("OCB", "Ngân hàng TMCP Phương Đông"),
    "PGB": ("PGBank", "Ngân hàng TMCP Thịnh vượng và Phát triển"),
    "SHB": ("SHB", "Ngân hàng TMCP Sài Gòn – Hà Nội"),
    "SSB": ("SeABank", "Ngân hàng TMCP Đông Nam Á"),
    "STB": ("Sacombank", "Ngân hàng TMCP Sài Gòn Thương Tín"),
    "TCB": ("Techcombank", "Ngân hàng TMCP Kỹ Thương Việt Nam"),
    "TPB": ("TPBank", "Ngân hàng TMCP Tiên Phong"),
    "VCB": ("Vietcombank", "Ngân hàng TMCP Ngoại thương Việt Nam"),
    "VIB": ("VIB", "Ngân hàng TMCP Quốc tế Việt Nam"),
    "VPB": ("VPBank", "Ngân hàng TMCP Việt Nam Thịnh Vượng"),
}
TICKERS = sorted(BANKS)

# Chỉ tiêu hiển thị trên hồ sơ ngân hàng và trang so sánh. Nhóm theo khung CAMELS như
# feature_spec.csv. direction là chiều "tốt hơn" nhìn từ độ an toàn của ngân hàng; NEUTRAL
# nghĩa là không tô màu tốt/xấu (LDR, tăng trưởng, quy mô không có chiều tốt tuyệt đối).
# (code, cột trong panel, tên, nhóm, đơn vị, chiều, mô tả)
INDICATORS = [
    ("car", "car_percent", "Hệ số an toàn vốn (CAR)", "C", "PERCENT", "HIGHER_BETTER",
     "Vốn tự có / tài sản có rủi ro. Công bố nửa năm (quý 2, quý 4)."),
    ("npl", "npl_percent", "Tỷ lệ nợ xấu (NPL)", "A", "PERCENT", "LOWER_BETTER",
     "Nợ nhóm 3–5 / tổng dư nợ, theo thuyết minh BCTC."),
    ("loans_g2", "loans_g2_percent", "Nợ cần chú ý (nhóm 2)", "A", "PERCENT", "LOWER_BETTER",
     "Nợ nhóm 2 / tổng dư nợ."),
    ("npl_coverage", "npl_coverage_percent", "Bao phủ nợ xấu", "A", "PERCENT", "HIGHER_BETTER",
     "Dự phòng rủi ro / nợ xấu."),
    ("cir", "cir_ttm_approx_percent", "Chi phí / thu nhập (CIR)", "M", "PERCENT", "LOWER_BETTER",
     "Chi phí hoạt động / tổng thu nhập hoạt động, cộng 4 quý (xấp xỉ)."),
    ("nim", "nim_ttm_percent", "Biên lãi thuần (NIM)", "E", "PERCENT", "HIGHER_BETTER",
     "Thu nhập lãi thuần / tài sản sinh lãi bình quân, cộng 4 quý."),
    ("roa", "roa_ttm_percent", "ROA", "E", "PERCENT", "HIGHER_BETTER",
     "Lợi nhuận sau thuế / tổng tài sản bình quân, cộng 4 quý."),
    ("roe", "roe_ttm_percent", "ROE", "E", "PERCENT", "HIGHER_BETTER",
     "Lợi nhuận sau thuế / vốn chủ sở hữu bình quân, cộng 4 quý."),
    ("cof", "cof_ttm_percent", "Chi phí vốn (COF)", "E", "PERCENT", "LOWER_BETTER",
     "Chi phí lãi / nguồn vốn chịu lãi bình quân, cộng 4 quý."),
    ("asset_yield", "earning_asset_yield_ttm_percent", "Lợi suất tài sản sinh lãi", "E", "PERCENT",
     "NEUTRAL", "Thu nhập lãi / tài sản sinh lãi bình quân, cộng 4 quý."),
    ("casa", "casa_percent", "Tỷ lệ CASA", "L", "PERCENT", "HIGHER_BETTER",
     "Tiền gửi không kỳ hạn / tổng tiền gửi khách hàng."),
    ("ldr", "ldr_computed_percent", "Dư nợ / tiền gửi (LDR)", "L", "PERCENT", "NEUTRAL",
     "Dư nợ cho vay / tiền gửi khách hàng (tính trên số BCTC, không phải LDR theo quy định)."),
    ("loans_growth_yoy", "loans_yoy_percent", "Tăng trưởng dư nợ so cùng kỳ", "G", "PERCENT", "NEUTRAL",
     "Dư nợ cuối quý so với cùng quý năm trước."),
    ("total_assets", "total_assets_vnd", "Tổng tài sản", "G", "VND", "NEUTRAL",
     "Tổng tài sản cuối quý."),
    ("deposits", "deposits_vnd", "Tiền gửi khách hàng", "G", "VND", "NEUTRAL",
     "Tiền gửi của khách hàng cuối quý."),
]

# Nhóm chương trình để trang Vay gợi ý theo mục đích vay.
PROGRAM_CATEGORY = {
    "NOXH_145K": "HOUSING",
    "NOXH_U35": "HOUSING",
    "G30K_2013": "HOUSING",
    "NLTS_185K": "AGRICULTURE",
    "NLTS_100K": "AGRICULTURE",
    "LTS_15K": "AGRICULTURE",
    "SME_7125": "BUSINESS",
    "HATANG_500K": "INFRASTRUCTURE",
}


def _write(frame: pd.DataFrame, name: str) -> int:
    path = OUT / name
    frame.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
    print(f"  {name:28s} {len(frame):>7,d} dòng")
    return len(frame)


def export_banks() -> pd.DataFrame:
    # Catalog ghi nối theo ngày crawl: mỗi mã có nhiều dòng, chỉ lấy tên app ở lần chụp mới nhất
    # (không lọc thì play.get(t) trả về cả một Series và chuỗi repr của nó bị ghi vào CSV).
    play = pd.read_csv(PLAY_CATALOG)
    play = play[play["app_role"] == "retail"].sort_values("date").drop_duplicates("ticker", keep="last")
    play = play.set_index("ticker")["app_name"]
    ios = pd.read_csv(IOS_CATALOG).sort_values("date").drop_duplicates("ticker", keep="last")
    ios = ios.set_index("ticker")["app_name"]
    rows = [{
        "ticker": t,
        "short_name": BANKS[t][0],
        "full_name": BANKS[t][1],
        "app_name": play.get(t, ios.get(t)),
    } for t in TICKERS]
    return pd.DataFrame(rows)


def export_indicators() -> pd.DataFrame:
    return pd.DataFrame([{
        "code": code, "name": name, "camels_group": group, "unit": unit,
        "direction": direction, "description": desc, "display_order": i,
    } for i, (code, _col, name, group, unit, direction, desc) in enumerate(INDICATORS)])


def export_bank_quarterly() -> pd.DataFrame:
    panel = pd.read_csv(PANEL)
    panel = panel[(panel["period"] >= FIRST_PERIOD) & panel["ticker"].isin(TICKERS)]
    columns = {col: code for code, col, *_ in INDICATORS}
    long = panel.melt(id_vars=["ticker", "period", "period_end"], value_vars=list(columns),
                      var_name="column", value_name="value").dropna(subset=["value"])
    long["indicator"] = long["column"].map(columns)
    return long[["ticker", "period", "period_end", "indicator", "value"]].sort_values(
        ["ticker", "indicator", "period"])


def export_deposit_rates() -> pd.DataFrame:
    rates = deposit_tiers.read()
    rates = rates[rates["ticker"].isin(TICKERS)].copy()
    rates["channel"] = rates["channel"].map({"online": "ONLINE", "quay": "COUNTER"})
    rates = rates.dropna(subset=["channel", "rate_percent"])
    rates["term_months"] = rates["term_months"].astype(int)
    rates = rates.drop_duplicates(["date", "ticker", "term_months", "channel"], keep="last")
    rates = rates.rename(columns={"date": "rate_date"})
    return rates[["rate_date", "ticker", "term_months", "channel", "rate_percent", "source"]].sort_values(
        ["rate_date", "ticker", "channel", "term_months"])


def export_lending_rates() -> pd.DataFrame:
    lend = pd.read_csv(LENDING)
    lend = lend[lend["ticker"].isin(TICKERS)].dropna(subset=["lending_avg_percent"])
    lend = lend.drop_duplicates(["month", "ticker"], keep="last")
    return lend[["month", "ticker", "lending_avg_percent", "deposit_avg_percent", "source_url"]].sort_values(
        ["month", "ticker"])


def export_app_store() -> pd.DataFrame:
    play = pd.read_csv(PLAY_CATALOG)
    play = play[(play["app_role"] == "retail") & play["ticker"].isin(TICKERS)]
    ios = pd.read_csv(IOS_CATALOG)
    ios = ios[ios["ticker"].isin(TICKERS)]
    # Hai catalog được ghi nối theo ngày crawl; web chỉ giữ ảnh chụp mới nhất của mỗi mã × kho.
    play = play.sort_values("date").drop_duplicates("ticker", keep="last")
    ios = ios.sort_values("date").drop_duplicates("ticker", keep="last")
    frames = [
        play.assign(store="GOOGLE_PLAY")[["ticker", "store", "date", "app_name", "score", "ratings"]],
        ios.assign(store="APP_STORE")[["ticker", "store", "date", "app_name", "score", "ratings"]],
    ]
    return pd.concat(frames).rename(columns={"date": "snapshot_date"}).sort_values(["ticker", "store"])


def export_app_reviews_monthly() -> pd.DataFrame:
    monthly = pd.read_csv(REVIEWS_MONTHLY)
    monthly = monthly[(monthly["app_role"] == "retail") & monthly["ticker"].isin(TICKERS)
                      & (monthly["month"] >= FIRST_MONTH)]
    return monthly[["ticker", "month", "n_reviews", "mean_score", "pct_1star", "pct_5star", "usable"]]


def export_programs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    part = pd.read_csv(PROGRAM_PARTICIPATION)
    part = part[part["ticker"].isin(TICKERS)]
    programs = (part[["program_code", "program_name"]].drop_duplicates("program_code")
                .assign(category=lambda f: f["program_code"].map(PROGRAM_CATEGORY).fillna("OTHER")))
    participation = part[["program_code", "ticker", "participates", "list_as_of", "source_url"]]
    rates = pd.read_csv(PROGRAM_RATES)
    rates = rates[rates["program_code"].isin(programs["program_code"])]
    rates = rates[["program_code", "borrower_group", "valid_from", "valid_to", "rate_pct_year",
                   "spread_below_avg_min_pct", "spread_below_avg_max_pct", "source_url"]]
    return programs, participation, rates


def export_macro_cpi() -> pd.DataFrame:
    """Lạm phát theo tháng (CPI so với cùng kỳ năm trước), để web tính lãi suất thực = lãi niêm yết − lạm phát."""
    cpi = pd.read_csv(CPI)
    cpi = cpi[cpi["month"] >= FIRST_MONTH].dropna(subset=["cpi_yoy_percent"])
    cpi = cpi.drop_duplicates("month", keep="last")
    return cpi[["month", "cpi_yoy_percent", "cpi_mom_percent", "source_url"]].sort_values("month")


def export_bank_ownership() -> pd.DataFrame:
    """Tỷ lệ sở hữu nhà nước / nước ngoài, lấy ảnh chụp mới nhất của từng ngân hàng."""
    own = pd.read_csv(OWNERSHIP)
    own = own[own["ticker"].isin(TICKERS)].sort_values("date").drop_duplicates("ticker", keep="last")
    own = own.rename(columns={"date": "as_of_date"})
    return own[["ticker", "as_of_date", "state_own_percent", "foreign_own_percent", "foreign_room_percent",
                "source"]].sort_values("ticker")


def export_datasets(parts: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Ngày cập nhật và độ phủ của từng nguồn cho trang Tổng quan và Phương pháp."""
    deposit = parts["deposit_rates"]
    latest = deposit[deposit["rate_date"] == deposit["rate_date"].max()]
    quarterly = parts["bank_quarterly"]
    lending = parts["lending_rates"]
    latest_lending = lending[lending["month"] == lending["month"].max()]
    app = parts["app_store"]
    reviews = parts["app_reviews_monthly"]
    participation = parts["program_participation"]
    cpi = parts["macro_cpi"]
    ownership = parts["bank_ownership"]
    rows = [
        ("deposit_rates", "Lãi suất tiết kiệm niêm yết", "24hmoney (đối chiếu CafeF, web ngân hàng)",
         "DAILY", deposit["rate_date"].max(), len(deposit),
         f"{latest['ticker'].nunique()}/22 ngân hàng có số ngày gần nhất"),
        ("lending_rates", "Lãi suất cho vay bình quân", "Báo VietnamNet tổng hợp số ngân hàng công bố",
         "MONTHLY", lending["month"].max(), len(lending),
         f"{latest_lending['ticker'].nunique()}/22 ngân hàng có số tháng gần nhất"),
        ("bank_quarterly", "Chỉ tiêu tài chính theo quý", "BCTC và thuyết minh (vnstock: VCI, MAS)",
         "QUARTERLY", quarterly["period"].max(), len(quarterly),
         f"{quarterly['ticker'].nunique()}/22 ngân hàng, từ {FIRST_PERIOD}"),
        ("app_store", "Điểm ứng dụng trên kho ứng dụng", "Google Play, App Store",
         "SNAPSHOT", app["snapshot_date"].max(), len(app),
         f"Google Play {app[app['store'] == 'GOOGLE_PLAY']['ticker'].nunique()}/22, "
         f"App Store {app[app['store'] == 'APP_STORE']['ticker'].nunique()}/22"),
        ("app_reviews_monthly", "Đánh giá ứng dụng theo tháng", "Google Play (532.007 review)",
         "MONTHLY", reviews["month"].max(), len(reviews),
         f"{reviews['ticker'].nunique()}/22 ngân hàng, từ {FIRST_MONTH}"),
        ("programs", "Chương trình tín dụng chính sách", "Văn bản NHNN, báo chí (nhập tay)",
         "IRREGULAR", participation["list_as_of"].max(), len(participation),
         "Chỉ có việc tham gia; giải ngân theo ngân hàng không được công bố"),
        ("macro_cpi", "Lạm phát (CPI so với cùng kỳ)", "Tổng cục Thống kê (NSO), thông cáo hằng tháng",
         "MONTHLY", cpi["month"].max(), len(cpi), f"Từ {FIRST_MONTH}; dùng để tính lãi suất thực"),
        ("bank_ownership", "Cơ cấu sở hữu (nhà nước, nước ngoài)", "vnstock (VCI, thông tin doanh nghiệp)",
         "SNAPSHOT", ownership["as_of_date"].max(), len(ownership),
         f"{ownership['ticker'].nunique()}/22 ngân hàng"),
    ]
    return pd.DataFrame(rows, columns=["dataset", "name", "source", "frequency", "last_updated",
                                       "row_count", "coverage_note"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"Xuất bảng phục vụ vào {OUT}/")
    parts = {
        "banks": export_banks(),
        "indicators": export_indicators(),
        "bank_quarterly": export_bank_quarterly(),
        "deposit_rates": export_deposit_rates(),
        "lending_rates": export_lending_rates(),
        "app_store": export_app_store(),
        "app_reviews_monthly": export_app_reviews_monthly(),
        "macro_cpi": export_macro_cpi(),
        "bank_ownership": export_bank_ownership(),
    }
    parts["programs"], parts["program_participation"], parts["program_rates"] = export_programs()
    parts["datasets"] = export_datasets(parts)
    for name, frame in parts.items():
        _write(frame, f"{name}.csv")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
