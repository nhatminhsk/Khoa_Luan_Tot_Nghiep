# KLTN — Hệ thống hỗ trợ ra quyết định chọn ngân hàng (gửi tiết kiệm / vay)

Khóa luận tốt nghiệp: hỗ trợ người dùng chọn ngân hàng để gửi tiết kiệm hoặc vay, dựa trên phân tích dữ liệu tài chính bằng ML/DL, cho các ngân hàng niêm yết tại Việt Nam.

## Trạng thái hiện tại

Giai đoạn **thu thập dữ liệu**. Phần mô hình (LSTM dự báo + TOPSIS/AHP xếp hạng) và giao diện demo (Streamlit) là các giai đoạn tiếp theo, chưa triển khai.

## Cấu trúc dự án

```
crawl_interest_rates.ipynb # Crawler lãi suất tiết kiệm hàng ngày
crawl_loan_rates.ipynb     # Crawler lãi suất vay (industry-average, best-effort)
crawl_macro.ipynb          # Vĩ mô: SBV policy rate / CPI
crawlers/                  # Logic crawler dùng chung, import bởi cả notebook lẫn run_daily_crawl.py
  deposit_rates.py
  deposit_24hmoney.py      # Đối chứng #1: bảng HTML 24hmoney — 38 NH x 7 kỳ hạn x 2 kênh, đủ 22/22 ticker
  deposit_crosscheck.py    # Đối chứng #2: văn xuôi CafeF hàng ngày — CHỈ ô 12 tháng/online, nhưng lùi được lịch sử
  loan_rates.py
  lending_rates_bank.py    # Lãi suất cho vay bình quân THEO TỪNG NH (VietnamNet chép lại bản NH tự công bố)
  credit.py                # Tín dụng theo từng NH: dư nợ, tăng trưởng, NPL, LDR — dựng từ BCTC đã có
  macro.py                 # Schema + helper nhập tay cho policy_rate.csv / cpi.csv
  lending_yield.py         # Lợi suất tài sản sinh lời theo NH — SUY RA từ NIM + COF, lùi được về 2018
  cpi_nso.py               # Crawler CPI từ REST API của NSO (nso.gov.vn) — nguồn chính, tự động
  cpi_vneconomy.py         # Bù ô CPI mà NSO để trống, từ VnEconomy — chỉ bù, không ghi đè
  policy_rate.py           # Lịch sử lãi suất điều hành SBV (bảng tra cứu đã đối chiếu)
  credit_growth.py         # Tăng trưởng tín dụng toàn hệ thống theo NĂM (bảng tra cứu đã đối chiếu)
  price.py                 # Giá cổ phiếu OHLCV hàng ngày, 22 NH — làm mới cửa sổ 7 ngày gần nhất
  app_reviews.py           # Đánh giá app ngân hàng số trên Google Play, 22/22 NH — dữ liệu PHÍA NGƯỜI DÙNG
  branch_network.py        # Mạng lưới điểm giao dịch + ATM theo tỉnh, từ OpenStreetMap — xem giới hạn 9
  vnstock_ratio_mas.py     # Chỉ số theo quý từ nguồn MAS — VÁ ô 2021-Q2 mà VCI để trống ở 21/22 NH
  vci_ratio.py             # Lớp đọc ratio quý VCI: gỡ lỗi 2021-Q4 chép 2021-Q3 / lệch một quý (22/22 NH)
  deposit_tiers.py         # Lớp đọc 24hmoney: đưa mọi NH về bậc số tiền thấp nhất (ghi đè Sacombank theo biểu 26/08/2026)
  vnstock_note.py          # Thuyết minh BCTC: 5 nhóm nợ -> NPL, tiền gửi KKH -> CASA, cơ cấu kỳ hạn
  repricing_gap.py         # Khe hở định lại lãi suất (chữ S của CAMELS) — NHẬP TAY từ thuyết minh BCTC PDF
  app_store_ios.py         # Chỉ số app trên Apple App Store, 22/22 NH — chỉ điểm tổng hợp, không có review
  build_panel.py           # Gộp mọi nguồn thành 1 panel bank-quarter sẵn sàng cho mô hình
  validate.py              # Cổng chất lượng dữ liệu — chạy tự động cuối build_panel, xem mục riêng bên dưới
  price_index_nso.py       # Chỉ số giá USD / vàng / lạm phát cơ bản — cùng bài NSO mà cpi_nso.py đã tải
  world_bank.py            # 7 chuỗi vĩ mô ngân hàng của World Bank — dùng làm ĐỐI CHỨNG, không cho TOPSIS
  bank_ownership.py        # Sở hữu nhà nước, room ngoại, danh sách cổ đông — 22/22 NH
  market_index.py          # VN-Index + VN30, nhân tố thị trường cho mô hình
run_daily_crawl.py         # Chạy deposit_rates + loan_rates mỗi ngày (dùng cho Task Scheduler)
requirements.txt
data/
  vnstock_financial/raw/   # BCTC ĐẦY ĐỦ (84 dòng CĐKT, 26 KQKD, 51 LCTT, 60 chỉ số) x 22 NH — tải bằng `vnstock_merge --fetch`
  vnstock_financial/financial_long.csv  # 176 file raw gộp thành 1 bảng long (dựng bằng crawlers/vnstock_merge.py)
  vnstock_financial/raw_mas/     # Chỉ số theo quý từ nguồn MAS x 22 NH (lịch sử về 2012-Q1)
  vnstock_financial/ratio_mas_ttm.csv  # MAS đã cộng 4 quý thành TTM — 1.158 dòng, 2012-Q1 → 2026-Q2
  vnstock_financial/raw_note/    # Thuyết minh BCTC theo quý x 22 NH, đủ 210 chỉ tiêu (nguồn sơ cấp của NPL và CASA)
  vnstock_financial/note_long.csv  # 210 chỉ tiêu thuyết minh x 22 NH gộp thành 1 bảng long (dựng bằng vnstock_note.py)
  policy_credit/           # Tín dụng chính sách nhập tay: tham gia gói NHNN, lãi suất, tỉnh thiên tai, dư nợ nông nghiệp
  _archive/vnstock_financial_2026-08-20_tomtat/  # Bản BCTC tóm tắt cũ (13/11/3/13 dòng) trước khi tải đầy đủ
  model/bank_panel_quarterly.csv # PANEL CHÍNH cho mô hình: 748 dòng, mỗi cột tỷ lệ kèm cột `*_src`
  model/data_inventory.csv       # Kiểm kê 639+ file: vai trò và quyết định giữ/bỏ (crawlers/inventory.py)
  model/features_quarterly.csv   # 120 đặc trưng ứng viên × 748 NH-quý, đã làm sạch (crawlers/build_features.py)
  model/feature_catalog.csv      # Mỗi đặc trưng: nhóm, công thức, độ phủ, cờ, Giữ/Loại + lý do (crawlers/select_features.py)
  model/features_selected.csv    # Chỉ các đặc trưng "Giữ" — đầu vào mô hình (chưa điền khuyết, chưa winsorize)
  model/features_ranking_latest.csv # 22 NH × giá trị gần nhất trong 4 quý cuối — đầu vào xếp hạng
  market/                  # VNINDEX.csv + VN30.csv — OHLCV hàng ngày, 2015-01-05 → nay
  ownership/               # bank_ownership.csv (22 NH) + bank_shareholders.csv (1.124 dòng)
  price/                   # Giá cổ phiếu OHLCV hàng ngày x 22 NH
  external/                # Dataset học thuật ngoài (xem crawlers/external_banking_dataset.py)
  interest_rates/
    deposit_daily.csv      # Lãi suất tiết kiệm theo NH/kỳ hạn/kênh, tích lũy hàng ngày
    deposit_raw/           # Snapshot thô mỗi ngày
    deposit_24hmoney_daily.csv    # Đối chứng 24hmoney — bảng HTML, 7 kỳ hạn x 2 kênh, có mốc cập nhật của nguồn
    deposit_crosscheck_daily.csv  # Đối chứng CafeF — chỉ 12 tháng/online, có cột checksum_ok
    bank_lending_rates_monthly.csv  # Lãi suất cho vay bình quân theo từng NH, hàng tháng (CÔNG BỐ, từ 2025-01)
    bank_earning_asset_yield_quarterly.csv  # Lợi suất tài sản sinh lời theo NH (SUY RA, 2018-Q1→2026-Q2)
  loan_rates/
    loan_industry_avg.csv  # Lãi suất bình quân ngành (gửi + vay), 1 dòng/tháng số liệu, 2024-01 → 2026-08
  credit/
    bank_credit_quarterly.csv  # Tín dụng theo NH/quý: dư nợ, tăng trưởng, NPL, LDR, dự phòng
    bank_asset_quality_quarterly.csv # NPL (5 nhóm nợ), CASA, cơ cấu kỳ hạn — từ thuyết minh BCTC
    bank_repricing_gap.csv # Khe hở định lại lãi suất theo NH/quý — bảng công việc nhập tay
    loans_by_industry_annual.csv # Dư nợ theo ngành từ BCTC kiểm toán, cuối năm 2018-2025, 143/176 NH-năm (crawlers/loans_by_industry.py)
    loans_by_industry_group_wide.csv # Như trên, dạng rộng: tỷ trọng % theo mã nhóm ngành
    loans_by_industry_manual/    # 20 file chép tay + sources.csv (link BCTC, trang PDF) — nguồn sự thật của 2 file trên
      fill_template.xlsx         # NHẬP TAY: 20 BCTC không có trên Vietstock, bù 33 NH-năm còn thiếu (hướng dẫn trong file)
  app_reviews/
    {TICKER}.csv           # 1 dòng = 1 đánh giá app (sao, nội dung, ngày, phiên bản) x 22 NH
    app_catalog.csv        # Snapshot chỉ số cấp app mỗi lần chạy (điểm hiển thị, số lượt, lượt cài)
    app_reviews_monthly.csv # Panel bank-month đã tổng hợp — file dùng cho mô hình
  branch_network/
    branch_points.csv      # 1 dòng = 1 điểm (chi nhánh/PGD hoặc ATM) từ OSM, có toạ độ + tỉnh
    branch_by_province.csv # Đếm theo (tỉnh, ngân hàng): n_bank, n_atm, n_total
    provinces.csv          # 34 tỉnh/thành sau sáp nhập 2025, lấy từ OSM
    tpb_official_points.csv # Bản TPBank tự công bố — dùng làm đối chứng độc lập
  macro/
    price_indices.csv      # Chỉ số giá USD / vàng / lạm phát cơ bản theo tháng (từ NSO)
    world_bank_annual.csv  # 7 chỉ tiêu World Bank 2000-2024 — thước đo kiểm định độc lập
    policy_rate.csv        # Lãi suất điều hành SBV (event log, 11 sự kiện)
    cpi.csv                # CPI hàng tháng (NSO + bù từ VnEconomy)
    credit_growth.csv      # Tăng trưởng tín dụng toàn hệ thống, 8 năm 2018-2025, mỗi dòng 1 source_url
  powerbi/                 # Bản chụp star-schema CŨ — script dựng đã bị xoá, KHÔNG dùng làm input mô hình
  _archive/                # Dữ liệu cũ/hỏng, giữ lại tham khảo, KHÔNG dùng làm input mô hình
crawl_log.txt               # Log chung cho tất cả crawler
```

## Nguồn dữ liệu

| Dữ liệu | Nguồn | Tần suất | Ghi chú |
|---|---|---|---|
| Báo cáo tài chính (BS/IS/CF/ratio) | vnstock (qua `vnstock_data`, sponsor package) | Đã crawl 1 lần, **2018-Q1 → 2026-Q2** (34 quý) + 8 năm 2018-2025 | 22 ngân hàng niêm yết → **748 bank-quarter** là đơn vị mô hình hóa thực tế. **34 quý chỉ đúng cho BS/IS/CF; file `ratio` chỉ có 21–33 quý** (OCB/SSB 21, MSB/BVB/NAB/PGB 22) — đây chính là gốc của độ phủ lệch ở COF và NPL, đừng giả định mọi trường đều dài 34 quý. `data/vnstock_financial/availability.csv` là audit trail; `requested_period == 'year_fallback'` chỉ đánh dấu **file theo năm** (88/176 dòng, mỗi NH×report có 1), không có nghĩa là chuỗi quý tương ứng bị thiếu — cột `periods_found` mới là số kỳ thật. |
| Giá cổ phiếu | vnstock (`crawlers/price.py`) | Chạy được hàng ngày | OHLCV, **47.074 phiên, 2015-09-28 → 2026-08-21**. Không chỉ append: mỗi lần chạy **làm mới 7 ngày gần nhất**, vì dòng của phiên mới nhất thường được chụp giữa phiên (ACB 20/08 từng ghi close 22,00/KL 1,6tr trong khi phiên đóng thật là 21,95/KL 7,59tr), và VCI còn điều chỉnh nhẹ khối lượng vài ngày sau. |
| Lãi suất tiết kiệm | `laisuattietkiem.vn` | Hàng ngày (crawl thủ công hoặc lịch tự động) | 23 ngân hàng, **17/22 ticker**, theo kỳ hạn (1-36 tháng) và kênh (tại quầy/trực tuyến). Không có API lịch sử — bắt đầu tích lũy từ ngày chạy đầu tiên. Nguồn chỉ đưa **một mức cho mỗi (NH, kênh, kỳ hạn)** và không nói mức đó ứng với bậc số tiền nào — xem mục schema. Chạy `python -m crawlers.deposit_rates --validate` để soát. |
| Lãi suất vay + huy động bình quân ngành | Bản công bố **"Diễn biến lãi suất TCTD"** hàng tháng của SBV. **Từ 07/10/2026 đọc thẳng bản gốc** trên sbv.gov.vn (trang tiếng Anh *Developments of interest rates applied by credit institutions*, số liệu trong PDF đính kèm); ThuVienPhapLuat (nguồn cũ, dừng ở tháng 6/2026) giữ cho lịch sử và `--selfcheck` (`crawlers/loan_rates.py`) | Hàng tháng | **32 tháng, 2024-01 → 2026-08, không thiếu tháng nào.** Vẫn là nguồn cho **bình quân toàn ngành**; lãi suất vay theo từng NH nay có riêng (dòng dưới) và được đối chiếu ngược lại với chính bản công bố này. Nguồn gốc dttktt.sbv.gov.vn từ chối kết nối, nhưng trang tin tiếng Anh trên sbv.gov.vn thì đọc được (tìm ra 07/10/2026); CafeF (nguồn cũ) chỉ đăng đúng 1 lần trong 8 tháng nên đã bỏ. Không lùi được trước 2024: nguồn cũ hơn chỉ báo chỉ tiêu khác (bình quân *giao dịch phát sinh mới*, một con số) và cấu trúc kỳ hạn trước đây gộp "12 tháng trở lên". |
| **Lãi suất cho vay bình quân theo TỪNG ngân hàng** | Bản các NH tự công bố theo Công điện 18/CĐ-TTg (05/03/2024), đọc qua bảng VietnamNet chép lại (`crawlers/lending_rates_bank.py`) | Hàng tháng | **375 dòng, 19 tháng liên tục 2025-01 → 2026-07 (không thiếu tháng nào), 21/22 ticker có lãi suất cho vay** — VPB chỉ có 1 tháng và chỉ có lãi suất huy động. Kèm `chênh lệch so với lãi suất huy động` do NH công bố → suy ra được lãi suất huy động bình quân của chính NH đó. Trang công bố của từng NH render client-side và không lưu lịch sử nên không scrape được; báo chí là đường duy nhất có back-history. **2024 đã kiểm cạn nguồn** — xem mục schema. |
| Tăng trưởng tín dụng toàn hệ thống | Bảng tra cứu trong `crawlers/credit_growth.py`, chép từ công bố của NHNN | Theo năm | **8 năm 2018-2025**, chỉ số cuối năm. Không scrape được (NSO bỏ mục ngân hàng, sbv.gov.vn có WAF, báo chí đưa dạng văn xuôi). **Cố ý không lưu số theo quý** — xem lý do ở mục giới hạn. Mỗi dòng có `as_of_date` + `announced_by` + `source_url`. |
| **Tín dụng theo từng ngân hàng** (dư nợ, tăng trưởng, NPL, LDR, dự phòng) | Dựng từ BCTC đã crawl (`crawlers/credit.py`) | Theo quý | **748 bank-quarter, 22 NH, 2018-Q1 → 2026-Q2.** Dư nợ và tiền gửi phủ **100%, không một ô trống**. NPL/LDR/NIM 21-33 quý mỗi NH — phủ tốt hơn hẳn COF. |
| Lãi suất điều hành SBV | Bảng tra cứu trong `crawlers/policy_rate.py`, đối chiếu từ văn bản Quyết định | Sự kiện (vài lần/năm) | **11 sự kiện 2017-2026** (33 dòng × 3 loại lãi suất). sbv.gov.vn có WAF (F5 BIG-IP) chặn request tự động → không scrape được; mỗi lần đổi là một Quyết định riêng nên chép tay 1 lần hợp lý hơn. Mỗi dòng có `source_url` để trích dẫn. |
| **Lợi suất tài sản sinh lời theo từng ngân hàng** (SUY RA) | Dựng từ `RT_BANK_NIM` + `RT_BANK_COF` + bảng cân đối (`crawlers/lending_yield.py`) | Theo quý | **540 bank-quarter, 22 NH, 2018-Q1 → 2026-Q2.** Đây là **cách duy nhất có chuỗi phía CHO VAY lùi được về 2018** — lãi suất cho vay công bố không tồn tại trước 03/2024. **KHÔNG phải lãi suất cho vay**: là lợi suất gộp trên toàn bộ tài sản sinh lời (gồm cả trái phiếu, tiền gửi liên NH lợi suất thấp) nên thấp hơn lãi suất cho vay ~0,9 điểm. Đối chiếu chéo với số công bố: xem mục schema. |
| **Chi phí vốn theo từng ngân hàng (COF)** | Trường `RT_BANK_COF` trong file ratio của vnstock, dựng bởi `crawlers/cost_of_funds.py` | Theo quý | **540 bank-quarter, 22 NH, 2018-Q1 → 2026-Q2.** Biến **phía huy động** có lịch sử dài và khác nhau giữa các ngân hàng. Cặp đối xứng phía cho vay là `bank_earning_asset_yield_quarterly.csv` (dòng trên) — hai file dùng chung cơ sở **trailing 12 tháng** và chung độ phủ. **Trừ nhau KHÔNG ra NIM**: quan hệ thật là `lợi suất tài sản = NIM + COF × (IBL/tài sản sinh lời)`, nên hiệu `lợi suất − COF` luôn thấp hơn NIM, bình quân 0,44 điểm (lệch 0,05–1,30 trên 540 dòng, không một dòng nào trùng trong sai số 0,01). Cần NIM thì dùng thẳng cột `nim_ttm_percent`; công thức trên đã kiểm ngược toàn bộ 540 dòng, sai số tối đa 0,0004. |
| CPI | **`crawlers/cpi_nso.py`** (chính, REST API NSO) + **`crawlers/cpi_vneconomy.py`** (bù khuyết) | Hàng tháng | **103/103 tháng 2018-01 → 2026-07, không còn ô trống.** GSO đã đổi tên thành NSO, tên miền `gso.gov.vn` nay chỉ phục vụ chứng chỉ của `nso.gov.vn`; site mới chạy WordPress nên `/wp-json/wp/v2/posts` trả về toàn văn bài công bố. |
| **Đánh giá app ngân hàng số** (sao, nội dung, ngày, phiên bản) | Google Play, đọc bằng `crawlers/app_reviews.py` (thư viện `google-play-scraper`) | Chạy được hàng ngày, dữ liệu lùi được về quá khứ | **22/22 ticker đều có app bán lẻ đã đối chiếu** — độ phủ ngân hàng tốt nhất trong toàn bộ đề tài, hơn cả lãi suất tiết kiệm (17/22) và lãi suất cho vay theo NH (21/22 nhưng thủng nặng). Đây là nguồn **phía người dùng** duy nhất; mọi file khác đều là phía cung. Lịch sử tuỳ ngân hàng, sớm nhất đã thấy là **2018-11** (BAB). Chỉ lấy được đánh giá **có nội dung** — phần chấm sao suông không truy xuất được, xem mục schema. |
| **Mạng lưới điểm giao dịch + ATM theo tỉnh** | OpenStreetMap qua Overpass API (`crawlers/branch_network.py`) | Chạy lại bất cứ lúc nào | **5.904 POI toàn quốc, 3.550 thuộc 22 NH, 22/22 ticker, 34 tỉnh.** Miễn phí, không cần API key, giấy phép ODbL nên trích dẫn được. **KHÔNG dùng được làm tiêu chí quy mô mạng lưới** — đối chiếu với Harvard chỉ cho Spearman 0,414 và tỉ lệ phủ lệch tới 37 lần giữa các ngân hàng. Xem giới hạn 9 trước khi dùng. |
| **Chỉ số theo quý — nguồn MAS** (NIM, COF, lợi suất TSSL, ROE, ROA, CIR, EPS, BVPS, P/E, P/B, beta) | `vnstock_data` source=`MAS` (`crawlers/vnstock_ratio_mas.py`) | Chạy lại bất cứ lúc nào | **1.158 bank-quarter, 2012-Q1 → 2026-Q2, 22/22 ticker.** Lý do tồn tại: file `ratio` của VCI **thiếu quý 2021-Q2 ở 21/22 NH** (chỉ NVB có) — lỗi phía nguồn, vì BS/IS/CF đều đủ 34/34. MAS phủ 99,9% trên 748 ô so với 87,4% của VCI, và bổ sung 5 chỉ tiêu VCI không có: EPS, BVPS, beta, tỷ suất cổ tức và **RT_BANK_YIEA** (lợi suất tài sản sinh lãi — trước phải suy ra). **BẪY: MAS ghi theo TỪNG QUÝ, VCI ghi trượt 12 tháng** — tỉ lệ \|VCI\|/\|MAS\| trung vị 3,84–4,04, và MAS để COF/CIR dấu dương. Phải cộng 4 quý; sai số so với TTM của VCI: NIM 0,015 điểm (p95 0,167), COF 0,081 (p95 0,255), ROA 0,027, ROE 0,303. MAS **không có** NPL, LDR, bao phủ nợ xấu, CAR. |
| **Thuyết minh BCTC** (5 nhóm nợ, tiền gửi KKH/có kỳ hạn, cơ cấu kỳ hạn cho vay, chi trả lãi tiền gửi) | `vnstock_data` `Finance.note` source=`VCI` (`crawlers/vnstock_note.py`) | Chạy lại bất cứ lúc nào | **737 bank-quarter, 34/34 quý, 22/22 ticker — không thủng 2021-Q2.** Nguồn **sơ cấp** của NPL: bảng cân đối đã crawl chỉ có 13 dòng tổng hợp, không phân nhóm nợ, nên đây là đường duy nhất tính NPL tại chỗ. NPL = (nhóm 3+4+5)/tổng dư nợ, đối chiếu với cột cũ trên 649 ô: lệch **trung vị 0,0000 điểm**, 93,7% khớp trong 0,05 điểm, và phủ thêm 88 ô. Còn cho **CASA** (chưa từng có trong đề tài, tương quan **−0,862** với chi phí vốn), cơ cấu kỳ hạn cho vay, và một cách đo chi phí huy động thứ ba độc lập. |
| **Chỉ số app trên Apple App Store** | iTunes Lookup API, store VN (`crawlers/app_store_ios.py`) | Chạy được hàng ngày, **không lùi được lịch sử** | **22/22 ticker**, tổng 3,81 triệu lượt đánh giá — lấp luôn BID và VCB đang vắng trong `app_catalog.csv` bên Play. **Chỉ lấy được điểm tổng hợp**: RSS review của Apple đã bị bỏ (trả HTTP 200 với 0 entry), trang app chỉ nhúng 8–10 review cố định từ 2020–2021. **Điểm iOS và điểm Play chỉ tương quan 0,445** (Spearman 0,447), chênh từ −0,87 (PGB) tới +1,54 (NAB) — nên tiêu chí hài lòng người dùng có ba cách đo cho ba thứ hạng khác nhau, phải chốt một. |
| **Chỉ số giá đô la Mỹ, chỉ số giá vàng, lạm phát cơ bản** | Cùng bài công bố NSO mà `cpi_nso.py` đã tải (`crawlers/price_index_nso.py`) | Hàng tháng | **104 tháng 2018-01 → 2026-09** (thiếu 2025-06). Từ 07/10/2026 chạy trong crawl hằng ngày (`price_index_nso.run()`: chỉ thêm tháng mới / bù ô trống). Chi phí mạng để thêm bằng không — bài viết đã được tải sẵn để bóc CPI. Vàng và đô la là **hai kênh cạnh tranh trực tiếp** với tiền gửi, nên đáng có trong một hệ thống tư vấn gửi tiết kiệm. Độ phủ: USD 98/104 MoM và 95/104 YoY; vàng 91/104 MoM nhưng chỉ 60/104 YoY; lạm phát cơ bản 73/104 MoM và 41/104 YoY (lạm phát cơ bản từng tháng chỉ có trong PDF đính kèm bài, bản HTML chỉ nêu bình quân N tháng). **Bẫy đã xử lý:** nguồn dùng cùng cụm “chỉ số giá đô la Mỹ” cho cả chỉ số DXY thế giới lẫn chỉ số USD trong nước, và câu về thế giới thường đứng trước — lấy nhầm sẽ ra chuỗi hoàn toàn khác. Hai cột yếu là do nguồn đổi cách viết từ 2021 (chỉ còn nêu số bình quân N tháng), không phải lỗi parser. |
| **Cơ cấu sở hữu ngân hàng** (sở hữu nhà nước, sở hữu nước ngoài, room ngoại, vốn hoá, thanh khoản) | `vnstock_data` `Company.overview` + `Company.shareholders` (`crawlers/bank_ownership.py`) | Ảnh chụp, chạy lại để tích luỹ | **22/22 ticker**, kèm 1.124 dòng cổ đông. Chiều dữ liệu mà kho trước đây hoàn toàn không có, và khó biện minh nếu thiếu trong hệ thống chọn nơi **gửi tiền**: sở hữu nhà nước xấp xỉ mức bảo trợ ngầm. Nhóm Nhà nước chi phối tách hẳn — BID 76,7%, VCB 74,8%, CTG 64,5%, MBB 43,2%, rồi **khoảng trống 34,6 điểm** xuống OCB 8,6%. Room ngoại: BVB, LPB, VIB bị chặn ở 5%; MBB và TCB gần kín room. **Không phải chuỗi thời gian** — nguồn chỉ trả trạng thái hiện tại. |
| **Chỉ số thị trường** (VN-Index, VN30) | `vnstock_data` `Quote` (`crawlers/market_index.py`) | Hàng ngày, làm mới cửa sổ 7 ngày | **2.915 phiên mỗi chỉ số, 2015-01-05 → 2026-09-09** — trùng khớp cửa sổ dữ liệu giá cổ phiếu, và **0 phiên nào có trong `price/` mà thiếu ở chỉ số**. Cho nhân tố thị trường để tách biến động chung khỏi phần riêng của từng ngân hàng. Lưu ý độ dài phụ thuộc tham số `start`: hỏi với `start=2018` thì VN30 chỉ trả 2.166 phiên, dễ tưởng nhầm chuỗi bắt đầu từ 2018. |
| **Chuỗi đối chứng quốc tế** (lãi suất tiền gửi, lãi suất cho vay, chênh lệch, lãi suất thực, nợ xấu, vốn/tài sản, tín dụng tư nhân/GDP) | World Bank WDI API (`crawlers/world_bank.py`) | Theo năm | **7 chỉ tiêu, 2000 → 2024**, miễn phí và không cần khoá. Lý do tồn tại: giới hạn 2 ghi rằng lý do **quyết định** để loại CafeF là *"không có gì để kiểm chéo"* với lãi suất huy động lùi lịch sử — `FR.INR.DPST` phủ 2000-2023, đúng toàn bộ khoảng trống đó. **Đã đo trùng khớp:** COF của panel vs lãi suất tiền gửi WB **r = +0,840**, lệch trung vị **+0,48 điểm**; NPL vs nợ xấu WB **r = +0,900**. **Chỉ dùng được CHIỀU và ĐIỂM NGOẶT, không dùng được MỨC**: WB lấy `FR.INR.DPST` từ IMF IFS và đó là *mức niêm yết đại diện*, không phải chi phí thực trả bình quân gia quyền — chính WB ghi kèm cảnh báo *"terms and conditions differ by country, limiting their comparability"*. Giả thuyết "COF cao hơn vì gồm cả vay liên NH và trái phiếu" **đã kiểm và bác bỏ**: cột chỉ-riêng-tiền-gửi lệch +1,04 điểm, xa hơn COF chứ không gần hơn. Phép đối chứng âm: NIM cho r = −0,479, nên r = +0,840 không phải do cùng xu thế. **KHÔNG dùng cho TOPSIS** — theo năm và toàn hệ thống, không phân biệt được giữa 22 NH. **Bốn chuỗi lãi suất dừng ở 2023** và tín dụng tư nhân/GDP dừng ở 2022, nên World Bank chỉ kiểm định được 2018-2023, không kiểm định được 2024-2026; chỉ `npl_percent` và `bank_capital_to_assets_percent` chạy tới 2024. **Phát hiện kèm theo:** khoảng cách NPL giữa nhóm niêm yết và toàn hệ thống nhảy từ **+0,27 điểm** (trước 2023) lên **+3,02 điểm** (từ 2023) — 22 NH niêm yết là nửa khoẻ của hệ thống, nên kết quả xếp hạng không suy rộng ra cả ngành. |
| VNIBOR | — | — | Đã bỏ qua — không tìm được nguồn miễn phí ổn định (FiinGroup có API nhưng trả phí). |
| Đặc trưng tài chính bổ sung (deposits, loans, assets, NPL, interest income/expense, labour productivity...) | [Harvard Dataverse](https://doi.org/10.7910/DVN/RIWA3B) — "A Dataset for the Vietnamese Banking System (2002–2021)", Thanh Ngo (Massey University), CC0 | Đã tải 1 lần (dataset tĩnh) | 45 ngân hàng (kể cả chưa niêm yết như Agribank), 2002-2022, 667 dòng bank-year. **Không có lãi suất %** — chỉ bổ sung cho phần sức khỏe tài chính, mở rộng độ phủ ngân hàng và kéo dài lịch sử về trước 2015. Đã map 5 mã ngân hàng khác tên (BID↔BIDV, MBB↔MB, LPB↔LVB, SSB↔SEAB, NVB↔NCB) sang đúng ticker. |

## Schema các file dữ liệu chính

**`data/model/bank_panel_quarterly.csv`** — PANEL CHÍNH cho mô hình (748 dòng = 22 NH × 34 quý, 2018-Q1 → 2026-Q2)

Dựng bằng `python -m crawlers.build_panel` (chỉ đọc lại các file đã có, không gọi mạng). Đây là file duy nhất mô hình nên đọc; mọi file khác là nguồn hoặc trung gian.

Mỗi cột tỷ lệ đi kèm một cột **`<tên>_src`** ghi rõ ô đó lấy từ đâu — `vci` / `mas` / `note` / `derived` / `halfyear` — để truy nguyên được trong khoá luận. Thứ tự ưu tiên:

| Cột | Ưu tiên 1 | Ưu tiên 2 | Độ phủ |
|---|---|---|---|
| `npl_percent` | `note` (sơ cấp) | `vci` | 98,5% |
| `npl_coverage_percent` | `vci` (629 ô) | `note` = \|dự phòng cho vay\| / nợ nhóm 3–5 (108 ô) | 98,5% |
| `casa_percent` | `note` | — | 98,5% |
| `cof_ttm_percent` | `vci` (525 ô) | `mas` (213 ô) | 98,7% |
| `nim_ttm_percent` | `vci` (634 ô) | `mas` (104 ô) | 98,7% |
| `earning_asset_yield_ttm_percent` | `mas` (công bố) | `derived` (suy ra) | 98,7% |
| `car_percent` | `halfyear` (H1→Q2, H2→Q4) | — | 38,9% |

**Điều file này giải quyết.** Trước khi có nó, chuỗi quý *liên tục* dài nhất mà mọi ngân hàng đạt được đều đúng bằng **20 quý**, tất cả bắt đầu ở 2021-Q3 — không phải giới hạn của dữ liệu mà là ô 2021-Q2 bị thiếu đang cắt đôi chuỗi 34 quý. Sau khi vá bằng MAS và `note`:

| | Trước | Sau |
|---|---|---|
| Chuỗi liên tục dài nhất, trung vị | 20 quý | **34 quý** |
| Ngân hàng đạt ≥ 30 quý liên tục | 0 | **20/22** |
| Ngân hàng đạt ≥ 20 quý liên tục | 15/22 | **22/22** |
| Tổng bank-quarter dùng được | 300 | **726** |
| Ngân hàng có dữ liệu ở 2021-Q2 | 1/22 | **22/22** |

Ngắn nhất giờ là BVB 27 quý (2019-Q4 → 2026-Q2), do chuỗi của chính ngân hàng này bắt đầu muộn chứ không phải do thủng.

**Sửa 15/09/2026 — ratio VCI lệch một quý quanh 2021-Q4.** Mọi cột lấy từ `vci` đọc qua `crawlers/vci_ratio.py` (xem mục `bank_credit_quarterly.csv`). Hệ quả trên panel: 2021-Q4 mang số thật của quý đó, còn 2022-Q1 lấy NIM/COF từ `mas` và bao phủ từ `note`. Cột `npl_coverage_percent` có thêm nguồn dự phòng `note`: công thức này khớp VCI đến 0,5 điểm ở 97% ô có cả hai nguồn, nên nó cũng lấp luôn 88 ô VCI vốn để trống (2018–2020, 2021-Q2, NVB 2025-Q2/Q3). Không cột "Giữ/Loại" nào đổi quyết định; `features_ranking_latest.csv` không đổi ô nào.

**Vẫn phải nhớ khi dùng:** `car_percent` chỉ có ở quý 2 và quý 4 (nguồn là bảng nửa năm nhập tay); `earning_asset_yield_ttm_percent` lấy số công bố của MAS chứ không còn là số suy ra — hai cách chỉ tương quan 0,781 và lệch trung vị 0,12 điểm, nên kết quả cũ dựng trên bản suy ra sẽ khác.


**`data/interest_rates/deposit_daily.csv`**
`date, bank_name, ticker, term_months, channel, rate_percent, prev_rate_percent, source, retrieved_at_utc`
- `ticker`: mã trong 22 ngân hàng niêm yết (rỗng nếu ngân hàng không niêm yết, ví dụ Agribank).
- `channel`: `quay` (tại quầy) hoặc `online` (trực tuyến).
- `prev_rate_percent`: mức lãi suất trước đó, nếu nguồn có ghi chú thay đổi (không phải luôn có). **Không cùng cơ sở với `rate_percent` ở mọi ngân hàng** — xem bẫy MSB bên dưới.
- **`rate_percent` CHƯA XÁC ĐỊNH BẬC SỐ TIỀN.** Nguồn chỉ đưa một mức cho mỗi (NH, kênh, kỳ hạn) và không có cột bậc tiền nào, trong khi các NH thực tế niêm yết theo bậc. Đối chiếu Sacombank 2026-08 với bảng CafeF thì **7/8 kỳ hạn trùng khớp cột "từ 2 tỷ"** (3 tháng 4,75; 6 tháng 6,40; 12 tháng 6,10; 24 tháng 6,90), gợi ý nguồn đăng bậc cao — nhưng đó mới là **1 NH × 1 ngày**, và nguồn không có gì để xác nhận. Người gửi 100 triệu ở Sacombank thực nhận 5,90% kỳ hạn 12 tháng chứ không phải 6,10%. **Phải nói rõ đây là "mức nguồn công bố, chưa xác định bậc" khi dùng cho xếp hạng**, đừng gọi là lãi suất người gửi nhận được.
- Nguồn còn phân biệt **phương thức trả lãi** (cuối kỳ / trả trước / định kỳ hàng tháng) mà bảng này không có chiều đó — cùng một kỳ hạn ở SHB có tới 3 mức khác nhau tuỳ phương thức.

**Kiểm định lãi suất tiết kiệm** — chạy `python -m crawlers.deposit_rates --validate`:

| Phép kiểm tra | Kết quả (2026-09-02) |
|---|---|
| Chuỗi ngày liên tục — **ngày bỏ lỡ là mất vĩnh viễn** | **11 ngày, THIẾU 2** (29-30/08, thứ Bảy + Chủ nhật) |
| Giá trị < 1,0% ở kỳ hạn ≥ 1 tháng | **11 ô** — đều là Sacombank 1 tháng/quầy = 0,5%, lặp cả 11 ngày |
| Bước nhảy > 2 điểm so với cột "Trước đó" của nguồn | **55/1.122 ô** — MSB (6 và 9 tháng, cả 2 kênh) và Sacombank |
| Độ phủ kênh | **7/23 NH thiếu hẳn một kênh** |
| Ticker vắng mặt trong 22 NH | **5/22** — HDB, SSB, BVB, NVB, PGB |
| Dòng trùng khoá | **0** |

- **Lỗi từ nguồn, không tự sửa** (cùng nguyên tắc với `lending_rates_bank.py`): ô Sacombank `1 tháng / tại quầy` ghi `0.5%Trước đó: 4.75%` trong **cả 11 snapshot thô**. 0,5% là mức **"dưới 1 tháng"**, không phải kỳ hạn 1 tháng — toàn bộ 22 NH còn lại nằm trong 2,1-4,75%, và CafeF ghi Sacombank 1 tháng = 4,75%. Parser đọc đúng những gì nguồn đăng; `--validate` liệt kê ra, module **không đoán hộ**. Phải lọc ô này trước khi build feature.
- **Nguồn gần như TĨNH, và đó không phải vì thị trường yên.** 11 ngày (21/08-02/09) chỉ sinh ra **2 trạng thái**: 21-31/08 giống hệt nhau **từng byte** ở cả 9 snapshot thô, 01-02/09 giống hệt nhau. Đúng **một ô** đổi trong toàn bộ cửa sổ (BIDV 18 tháng/online 6,8 → 6,6 ngày 01/09). Nghĩa là 3.267 dòng chỉ mang thông tin của **2 lát cắt** — within-variation gần bằng 0. Thứ quyết định độ dài chuỗi hữu ích không phải *số ngày crawl* mà là *số lần nguồn đổi giá*, và tần suất đó rất thấp. Đừng hồi quy theo ngày trên file này.
- **Bẫy `prev_rate_percent` của MSB**: cột "Trước đó" ghi 8,5% cho kỳ hạn 6 tháng và 8,3% cho 9 tháng, trong khi mức hiện hành là 6,1-6,3%. Chênh 2,2 điểm là **không thể** với một lần điều chỉnh lãi suất; 8,5%/năm cũng nằm ngoài hẳn mặt bằng thị trường (~6,4%). Nhiều khả năng là **lãi suất đặc biệt/khuyến mại** cho khoản tiền lớn, tức **khác cơ sở** với cột chính. Không được lấy `rate_percent - prev_rate_percent` làm mức thay đổi lãi suất.
- `TERM_MAP` phủ **đúng cả 8 cột** nguồn đưa ra (1, 3, 6, 9, 12, 18, 24, 36 tháng) — không bỏ sót kỳ hạn nào.

**`data/interest_rates/deposit_24hmoney_daily.csv`** — đối chứng #1 (24hmoney.vn)
`date, effective_date, bank_24hmoney, bank_name, ticker, term_months, channel, rate_percent, source, source_updated_at, source_url, retrieved_at_utc`
- Bảng HTML thật: **38 NH × 7 kỳ hạn (1, 3, 6, 12, 18, 24, 36) × 2 kênh = 478 ô/ngày**. Không có kỳ hạn 9 tháng.
- Bảng được nhận diện theo **nhãn** ("gửi tại Quầy" / "gửi Trực tuyến"), không theo chỉ số bảng — trang đổi bố cục thì crawler báo lỗi thay vì lặng lẽ đọc nhầm kênh.
- **`date` vs `effective_date` là hai thứ khác nhau, và khác thật.** `date` = ngày chụp; `effective_date` = ngày của chính bảng, đọc từ `source_updated_at` mà trang tự đóng dấu (`13:30:03 03/09/2026`). Snapshot Wayback ngày **18/03/2026 vẫn đang hiển thị bảng của 16/12/2025** — nguồn đứng yên 3 tháng nhưng trang vẫn mở bình thường. **Khoá chống trùng dùng `effective_date`**, nên chạy hàng ngày không sinh dòng mới trừ khi nguồn thật sự đổi bảng, và số "bảng phân biệt" mới là độ dài chuỗi thật.
- **Có lịch sử 2023 → nay** qua Wayback Machine: `python -m crawlers.deposit_24hmoney --backfill`. Hiện **12.502 dòng, 27 bảng phân biệt, 2023-01-27 → 2026-09-03** (xem giới hạn 2). Mật độ thưa và không đều (~quý một bảng), không phải chuỗi ngày.
- **Ngân hàng đổi tên phải map tay**: lịch sử dùng `LienVietPostBank` (nay là LPBank) và `VietCapitalBank` (nay là BVBank), cùng nhiều biến thể viết tắt (`MB`/`MBB`, `Bắc Á`, `Nam Á`, `TPB`, `PVcomBank` vs `PVCombank`). Sau khi bổ sung alias, chạy `--remap` để áp lại lên file đã có — khoá chống trùng không chứa `bank_name` nên chạy lại `--backfill` sẽ KHÔNG tự cập nhật cột đó. Độ phủ sau remap: **22/22 ticker ở cả 4 năm**.
- Ngày **10/08/2024** trang render hỏng một dòng thành tên `null` (lãi suất thật, không biết của NH nào) — `JUNK_NAMES` loại, module **không đoán** ngân hàng.
- **Bù đúng 5 ticker nguồn chính thiếu** (HDB, SSB, BVB, NVB, PGB) → **22/22**, và có `online` cho cả 6 NH mà nguồn chính bỏ trống kênh đó.
- Kiểm định nội bộ cảnh báo khi `quầy > online` quá 0,5 điểm: hiện **11 ô**, hầu hết Bắc Á Bank — nghi số `online` của 24hmoney cũ ở NH này.

**`data/interest_rates/deposit_crosscheck_daily.csv`** — đối chứng #2 (loạt bài CafeF hàng ngày)
`date, bank_cafef, bank_name, ticker, term_months, channel, rate_percent, checksum_ok, source, source_url, retrieved_at_utc`
- Nguồn là **văn xuôi, 0 thẻ `<table>`** (đã kiểm HTML thô — đúng như giới hạn 2 mô tả). Chỉ trích đúng **một ô: 12 tháng / online**, là trục mà gần như mọi NH đều được nêu. Không dựng panel đa kỳ hạn từ văn xuôi.
- **Vì sao parser văn xuôi ở đây kiểm định được, trái với kết luận ở giới hạn 2**: loạt bài này **tự mang số tổng hợp** ("có N ngân hàng niêm yết từ 7%/năm trở lên", "Big4 thấp hơn 1 điểm so với ACB"). `validate()` đối chiếu kết quả trích với chính các con số đó và ghi vào cột **`checksum_ok`**. Checksum này bắt được 2 lỗi thật lúc dựng: Big4 mất trắng 4 NH, và kỳ hạn **13 tháng** của SCB (8,7%) lọt vào ô 12 tháng.
- Hiện **21/31 ngày checksum đạt**; `--compare` chỉ dùng ngày đạt. 10 ngày còn lại lệch 1-2 NH ở nhóm ≥7% — **phải lọc `checksum_ok` trước khi dùng**.
- Lùi được về **01/08/2026 (31 ngày)** qua sitemap CafeF, gồm cả 29-30/08 mà nguồn chính mất.

**Ba nguồn, cùng một ô, KHÔNG cùng một số** — phát hiện quan trọng nhất về lãi suất tiết kiệm (03/09/2026)

Chạy `python -m crawlers.deposit_24hmoney --compare`. Cùng ngày, cùng định nghĩa (VND, khách hàng cá nhân, trực tuyến, kỳ hạn 12 tháng): **18/23 NH khớp, 5/23 lệch ≥ 0,5 điểm**.

| Ngân hàng | laisuattietkiem | CafeF | 24hmoney | Biên độ |
|---|---|---|---|---|
| **ACB** | 5,70 | **7,80** | 5,70 | **2,10** |
| Vietcombank | 5,90 | 6,80 | 5,90 | 0,90 |
| Vietinbank | – | 6,80 | 5,90 | 0,90 |
| Bắc Á Bank | – | 7,10 | 6,40 | 0,70 |
| Sacombank | – | 7,50 | 7,00 | 0,50 |

**Ca ACB đã phân xử bằng biểu do chính ACB công bố** (`acb.com.vn/lai-suat-tien-gui`, mục *"3. TIỀN GỬI ONLINE, LÃI CUỐI KỲ"*): kỳ hạn 12 tháng = **5,70** (<200 tr) / 5,80 / 5,85 / **5,90** (≥5 tỷ), cộng thưởng bậc thang tối đa 0,20 → **trần tuyệt đối 6,10**. Không tồn tại mức 7,80.

→ **laisuattietkiem.vn và 24hmoney đúng; CafeF sai.** Đáng chú ý: con số 7,80 được **nhiều báo đăng lại** (kenh14, ngoisao.vn, EBC, vietnam.vn) nhưng tất cả đều là hạ nguồn của cùng một bảng. **Số được nhiều báo lặp lại không phải bằng chứng độc lập** — chỉ biểu của chính ngân hàng mới phân xử được.

Hệ quả phải nêu trong luận văn:
- Nguồn chính **không bị kẹt giá** như nghi ban đầu — ở ca kiểm được, nó khớp đúng biểu ngân hàng (bậc thấp nhất, <200 triệu).
- Nhưng xếp hạng "NH nào trả cao nhất" **đảo ngược theo nguồn**: ACB đứng #1 theo CafeF, gần bét theo hai nguồn kia. Dùng một nguồn báo chí duy nhất là đủ để lật kết luận.
- **Đã phân xử thêm ngày 15/09/2026** (đọc bằng trình duyệt vì các trang render bằng JS). 24hmoney đúng ở cả ba ca; con số của CafeF không có trên biểu của ngân hàng:
  - **Vietcombank**: tab "Tiền gửi trực tuyến" trên `vietcombank.com.vn` ghi 12 tháng **5,90%** (cập nhật 10:01 15/09/2026). Tạp chí Thương Gia 09/2026 cũng ghi mức cao nhất là 6% cho cả online.
  - **Vietinbank**: `vietinbank.vn` chỉ có bảng tại quầy (12 tháng 5,9%); VietnamBiz (bảng 14/09/2026) ghi "gửi online có lãi suất tương tự tại quầy". Câu "Big4 đồng loạt 6,8% online" trên kenh14/CafeF là hạ nguồn của cùng bảng sai.
  - **Sacombank**: biểu PDF hiệu lực 26/08/2026 có phần online theo 3 bậc tiền: 7,00 (<50 triệu) / 7,30 / **7,50** (≥500 triệu). 24hmoney lấy bậc thấp nhất, CafeF lấy bậc cao nhất — cả hai đúng nhưng khác bậc.
    - 24hmoney **trộn bậc** ở hai chỗ: tại quầy 1/3/6/12 tháng = 4,60/4,60/6,30/6,00 là bậc 500 triệu–2 tỷ; online 1/3 tháng = 4,8/4,75 là bậc ≥ 500 triệu.
    - **Đã sửa** bằng `crawlers/deposit_tiers.py`: ghi đè 6 ô về bậc thấp nhất (tại quầy 4,50/4,50/6,20/5,90; online 4,50/4,50).
    - Chỉ áp từ ngày hiệu lực 26/08/2026, và chỉ khi 24hmoney vẫn ghi đúng số cũ. Khi Sacombank đổi biểu, ô ngừng được ghi đè và `validate` báo WARN `deposit.tier`.
    - `build_features` và `experiments.eda` đọc lãi suất qua `deposit_tiers.read()`; file crawl giữ nguyên số của nguồn.
  - **BIDV 6,8% online / 5,9% tại quầy là thật**: VietnamBiz 02/06/2026 đưa tin BIDV tăng online lên 6,6/6,8% từ tháng 6/2026, trùng ngày đổi trong dữ liệu. **SeABank 5,0%** (thấp nhất 22 NH) cũng thật: VietnamNet 05/08/2026 ghi đúng mức này, biểu tại quầy trên `seabank.com.vn` khớp 24hmoney.
  - Bắc Á Bank: hai nguồn đã khớp nhau (7,10) từ 09/2026.

**`data/loan_rates/loan_industry_avg.csv`**
`date, article_url, article_title, deposit_0_to_1m_min/max, deposit_1_to_6m_min/max, deposit_6_to_12m_min/max, deposit_12_to_24m_min/max, deposit_over_24m_min/max, loan_vnd_avg_min/max, loan_priority_short_term_min/max, retrieved_at_utc`
- Mỗi dòng ứng với **1 tháng số liệu**, không phải 1 ngày và không phải 1 bài báo. `date` = ngày đầu tháng của **kỳ số liệu** (ví dụ `2026-06-01` = số liệu tháng 6/2026, dù bài công bố ngày 21/07) — dùng ngày đăng báo sẽ làm chuỗi lệch pha ~1 tháng so với CPI/policy rate khi join.
- Khi min = max (ví dụ `deposit_over_24m` tháng 12/2025 = 6.8/6.8) là do SBV công bố một con số đơn, không phải khoảng.
- **Điểm gãy cấu trúc:** từ 2024-01 đến 2026-02 SBV ghi phạm vi *"NHTM trong nước"*; từ **2026-03** đổi thành *"nhóm NHTM nhà nước và nhóm NHTM cổ phần"*. Nên kiểm định break tại điểm này trước khi hồi quy xuyên suốt.
- Tháng 2026-07 từng để trống **10 trường `deposit_*`** (lần nhập tay chỉ điền phần cho vay). **Đã bổ sung 03/09/2026** từ chính bài đang ghi ở `article_url` — bài đó vốn có đủ số liệu tiền gửi. File hiện **không còn ô trống nào**. Lưu ý bản công bố tháng 7 KHÔNG có trên trang nguồn ThuVienPhapLuat (trang này mới tới tháng 6), nên dòng 2026-07 là nhập tay.
- **Nguồn gốc NHNN (từ 07/10/2026).** Tháng 8/2026 lấy thẳng từ PDF của NHNN (đăng 18/09). Bản chép lại có thể sai: VNBA chép lãi cho vay ngắn hạn ưu tiên tháng 8 thành 3,9% trong khi bản gốc ghi **4,0%** (bằng trần). Parser bản tiếng Anh khớp 14/14 ô với dòng 2026-06 và 2026-07 sẵn có, dù hai tháng do hai người dịch viết khác nhau (tháng 7: *mobilization interest rates*, `0.1% - 0.2%`, `1month`, bỏ `p.a.`). Bẫy: slug trang không đều (`june-2026-` có gạch cuối vì tiêu đề có ngoặc, `july-2026` thì không) nên thử cả hai; dò nhanh khoảng 10 request liên tiếp thì sbv.gov.vn chặn IP (403 cả trang chủ) một lúc, nên module chỉ dò các tháng sau tháng cuối trong file, nghỉ 4 giây giữa các request, và gặp 403 thì dừng, ghi `sbv=[...:blocked]` vào log.
- `crawlers/loan_rates.py` **không bao giờ ghi đè ô đã có số** (file này có dòng nhập tay). Với dòng đã có nó chỉ **điền ô đang để trống**; ô đã có số mà lệch với nguồn thì báo `conflicts` chứ không tự sửa. Không mở file để ghi khi không có gì thay đổi. Mỗi lần chạy quét **toàn bộ** file và báo `still_blank` — trước 03/09/2026 ô trống của dòng đã có bị `continue` bỏ qua trước cả bước kiểm tra, nên log báo `incomplete=none` trong khi tháng 7 thiếu 10 ô. Chạy `python -m crawlers.loan_rates --selfcheck` để đối chiếu parser với toàn bộ dữ liệu đã có (hiện **406 giá trị, 0 sai lệch**).

**`data/interest_rates/bank_lending_rates_monthly.csv`** (375 dòng, **19 tháng liên tục 2025-01 → 2026-07, không thiếu tháng nào**)
`month, bank_key, bank_name, ticker, lending_avg_percent, change_vs_prev_point, spread_vs_deposit_point, deposit_avg_percent, deposit_avg_implied_percent, from_mixed_table, source_url, article_title, note, retrieved_at_utc`
- **Nguồn có 2 kiểu bảng khác nhau**, module tự nhận diện (`note` ghi `[layout=...]` khi không phải kiểu thường):
  - `lending_led` — `NH | cho vay | thay đổi | chênh lệch`. Kiểu phổ biến nhất.
  - `combined` — `STT | NH | cho vay | huy động | chênh lệch`. Nhận diện bằng **phép thử số học** `cho vay − huy động = chênh lệch` (đúng trên ≥80% số dòng), không dựa vào chữ trong header vì header đổi liên tục.
- `deposit_avg_percent` = lãi suất huy động bình quân **do NH công bố** (30 dòng, chỉ từ bảng `combined` tháng 2025-01). Khác với `deposit_avg_implied_percent` là số suy ra từ chênh lệch.
- `bank_key`: tên đã chuẩn hoá — **dùng cái này để join/dedup, không dùng `bank_name`**. Cùng một NH được viết "KLB" tháng này, "KIENLONGBANK" tháng sau; "VIET A BANK" và "VietABank" xen kẽ. Các cặp viết tắt/viết đủ được gộp qua `ALIASES` trong module (KLB→KIENLONGBANK, HONGLEONG→HONGLEONGBANK, IVB→INDOVINABANK). **Không gộp** các vụ đổi tên sau tiếp quản (VCBNEO, MBV, VIKKIBANK) — gộp sẽ nối hai chế độ sở hữu vào một chuỗi.
- `deposit_avg_implied_percent` = `lending_avg_percent − spread_vs_deposit_point`. **Là số SUY RA, không phải số được công bố** — để riêng cột nên không nhầm với số trích dẫn được. Khoảng thực tế 1,85%-9,38%, trung vị 5,37% (336 dòng).
- `from_mixed_table` (bool, 24 dòng `True`) — dòng đến từ bảng "theo công bố gần nhất", **không thuộc một khảo sát tháng nào**. Lọc bằng `df[~df.from_mixed_table]` trước khi tính trung vị hay sai phân. Chi tiết ở mục bảng "công bố gần nhất" bên dưới.
- **Độ phủ rất lệch theo NH**: ACB/BAB/BVB/BID/LPB 15 tháng, nhưng **VPB chỉ 1**, HDB 2, NVB 3, SHB 4, ABBANK 5, MSB 6. Phải quyết định lọc trước khi đưa vào TOPSIS. Đây **không phải lỗi crawler**: đối chiếu từng dòng của cả 15 bảng nguồn với bảng master cho thấy module đọc đúng những gì được in ra — VPB chỉ có mặt trong **1 trên 15 bảng**. Xem `crawlers.lending_rates_bank.bank_coverage()`.
- **Tháng không dùng được cho phân tích chuỗi** — `coverage()` đánh dấu bằng cột `dung_duoc` (14/19 tháng đạt). Hai lý do khác nhau: 2025-02/04/05/06 toàn dòng cắt ngang (`from_mixed_table`), còn 2025-11 là bảng tháng thật nhưng chỉ có **1 NH**. Đừng đọc trung vị các tháng này như trung vị toàn ngành.
- **Bảng 10/2025 bị nguồn gắn nhãn sai — cột là lãi suất CHO VAY, không phải huy động.** Caption ghi "LÃI SUẤT HUY ĐỘNG BÌNH QUÂN" và header ghi "LSHĐ BÌNH QUÂN", nhưng bốn kiểm chứng độc lập đều bác bỏ nhãn đó: (1) so với 09/2025 cột này khớp lãi suất **cho vay** lệch trung vị **+0,02 điểm** (MAE 0,24 trên 23 NH chung), trong khi lệch **+2,76** so với phía huy động — VIETINBANK đọc 5,09 / 5,07 / 5,10 qua 09, 10, 12-2025 và SCB 5,40 / 5,39 / 5,39, cùng NH cùng thứ tự in; (2) cột chênh lệch **không đổi** (CTG 1,82 → 1,79 → 1,80), bảng đã đổi phía thì không thể giữ nguyên spread của phía cũ; (3) cột "THAY ĐỔI SO VỚI THÁNG 9" **do chính nguồn công bố** bằng đúng hiệu (giá trị T10 − lãi suất cho vay T9) ở **21/23 NH**; (4) tiêu đề bài là "Biến động lãi suất **cho vay**". Thứ tự cột y hệt `lending_led` nên bảng được đọc như bình thường, mâu thuẫn caption ghi vào `note`. **Suy `cho vay = huy động + chênh lệch` là sai** — chính phép đó đẩy cả 23 NH nhảy trung vị +2,69 điểm một tháng rồi tụt lại, vì nó cộng spread lên một số vốn đã là lãi suất cho vay.
- **Bảng "theo công bố gần nhất" — hai bài, xử lý KHÁC nhau.** Mỗi dòng của loại bảng này là lần công bố gần nhất của riêng ngân hàng đó, nên không có một tháng nào để quy cả bảng về.
  - Bài **03/07/2025** in thêm **cột thứ 5 `THỜI ĐIỂM CÔNG BỐ`** ghi tháng cho từng dòng ("Tháng 5", "Tháng 6"… xuống tới "Tháng 1"). Bảng này **datable theo từng dòng** và là nguồn duy nhất còn lại cho 2025-02/04/05/06 — 24 dòng, rải ra 2025-02 (4 dòng), 2025-03 (2), 2025-04 (1), 2025-05 (16), 2025-06 (1). Đúng 24 dòng này mang `from_mixed_table = True`.
  - **Mỗi dòng là một quan sát thật, nhưng các tháng chúng rơi vào không phải khảo sát cắt ngang.** Một bài đơn lẻ trải ra nửa năm, nên trung vị của 2025-05 là trung vị của 16 NH tự chọn thời điểm công bố, không phải mặt bằng thị trường tháng 5. Lọc `from_mixed_table` trước mọi phép có chiều thời gian. Lưu ý 2025-03 **vẫn dùng được**: nó có 27 dòng từ bảng tháng 3 thật, cộng thêm 2 dòng cắt ngang lẫn vào — nên `dung_duoc` đếm trên dòng khảo sát chứ không trên tổng.
  - Bài **26/07/2025** không có cột đó. Không gì trong bảng cho biết dòng nào thuộc tháng nào → **vẫn bỏ**, không đoán.
  - Bản dựng đầu tiên gán cả hai bảng vào một tháng (29 dòng vào "2025-05", 29 dòng vào "2025-06") — **sai**; bản thứ hai bỏ cả hai — **mất dữ liệu thật**. Đúng là đọc theo cột.
  - Cột "THAY ĐỔI SO VỚI 1/2025" của bảng này là **gốc cố định**, giống nhau cho mọi dòng bất kể dòng đó thuộc tháng nào — **không phải** biến động so tháng liền trước. Module bỏ giá trị đó thay vì lưu vào `change_vs_prev_point`, và ghi lý do vào `note`.
- **Toàn bộ 2024 vẫn không lấp được, và điều này đã được kiểm bằng cách mạnh nhất**: quét lại 2024-03 → 2025-01 **không lọc theo caption** (chấm điểm bằng chính nội dung: ≥5 dòng, ≥60% ô đầu là tên NH nhận diện được, cột 2 đọc ra số 3-20%) → 194 bảng ứng viên, sau khi loại biểu lãi suất huy động theo kỳ hạn chỉ còn **2 bảng**, và cả hai đều **không phải LSCVBQ**: một là "LÃI SUẤT CƠ SỞ" (18/03/2024), một là bảng 05/04/2024 trộn ba loại số trong cùng một cột (lãi suất cơ sở `LSCS`, khoảng `6,5 - 11,33`, và bình quân thật) phân biệt bằng cột `GHI CHÚ`. Chỉ 4/22 ticker có dòng ghi đúng "LSCV bình quân" (STB 7,09; BID 6,49; VCB 6,40; CTG 6,30) và bài **không nói số thuộc tháng nào**. **Cố ý không nạp** — trộn lãi suất cơ sở vào chuỗi bình quân là đúng loại sai làm hỏng cả chuỗi. Muốn có 2024 thì phải nhập tay từ trang công bố của từng NH.
- **Bẫy false positive đã chặn**: bài 11/02/2025 đăng bảng "LÃI SUẤT HUY ĐỘNG BÌNH QUÂN THÁNG 12/2024 THEO CÔNG BỐ CỦA NHNN" mà các dòng là **kỳ hạn**, không phải ngân hàng (`1 tháng đến dưới 6 tháng | 3,1-4,0%/năm`). Nó lọt mọi phép thử hình dạng — đúng 5 dòng, ô đầu ngắn, ô thứ hai ra số hợp lệ — và sẽ chèn 5 "ngân hàng" giả mang số bình quân ngành mà đề tài đã giữ đúng chỗ ở `loan_industry_avg.csv`. `_looks_like_banks` yêu cầu ≥60% ô đầu khớp `TICKERS`/`NOT_LISTED`.
- **Bẫy "so với tháng N"**: tiêu đề "LÃI SUẤT CHO VAY BÌNH QUÂN MỚI NHẤT ... SO VỚI THÁNG 1/2025" báo số **tháng 3**, tháng 1 chỉ là mốc so sánh. Lấy tháng đầu tiên trong tiêu đề sẽ xếp nhầm cả bảng vào tháng 1 — cùng loại bẫy `crawlers/cpi_nso.py` xử lý bằng `_anchors`.
- **Lỗi từ nguồn, không tự sửa**: 2 dòng có cột "thay đổi" bằng đúng cột "lãi suất" (PGBANK 2026-05, NAM A BANK 2026-07). `--validate` liệt kê ra, module không đoán hộ.

**Kiểm định lãi suất cho vay theo NH** — chạy `python -m crawlers.lending_rates_bank --validate`:

| Phép kiểm tra | Kết quả |
|---|---|
| Trung vị các NH có nằm trong khoảng SBV công bố (`loan_industry_avg.csv`) | **16/18 tháng**. Hai tháng trượt là 2025-06 và 2025-11 — **đều là tháng chỉ có 1 NH**, không phải mặt bằng thị trường |
| Tương quan với trung điểm khoảng SBV | **r = 0,8161**, chênh lệch trung vị **−0,37 điểm** |
| Khoảng giá trị | 5,09% - 11,34%, không dòng nào ngoài 3-20% |
| Dòng mới thêm có tạo bước nhảy bất thường không | Không: trung vị \|Δ\| giữa hai tháng liền có dữ liệu của cùng một NH là **0,09 điểm**; không dòng 2025-05 nào nằm trong 10 bước nhảy lớn nhất |

> Đây là hai chuỗi độc lập cho cùng một đại lượng: một bên là các NH tự công bố (qua báo), một bên là bản công bố của SBV. Chúng khớp nhau ở mức trên.

**`data/vnstock_financial/financial_long.csv`** (197.669 dòng, 22 NH, dạng long)
`ticker, statement, freq, period, id, name, order, level, off_balance, unit, value`
- Dựng bằng `python -m crawlers.vnstock_merge` (chỉ đọc lại `data/vnstock_financial/raw/`, không gọi mạng). `raw/` vẫn là nguồn sự thật; file này là **dẫn xuất**, dựng lại lúc nào cũng được. Tải lại `raw/` bằng `python -m crawlers.vnstock_merge --fetch`.
- **Từ 14/09/2026 là bản đầy đủ**:
  - `balance_sheet` có 84 id, trong đó 57 id có số ở ≥50% trên 748 ô; `income_statement` 26 id (21); `cash_flow` 51 id (31); `ratio` 60 id.
  - Bản cũ (35.556 dòng) chỉ có 13/11/3/13 id, lưu ở `data/_archive/vnstock_financial_2026-08-20_tomtat/`.
  - Mọi id cũ đều còn. 35.556 ô cũ: 31.501 trùng tuyệt đối, 450 lệch do MBB cũ làm tròn, 123 do nguồn cập nhật lại (P/E–P/B kỳ mới nhất, HDB 2024 năm, HDB/SHB 2026-Q2).
  - Panel sau khi dựng lại chỉ đổi đúng các ô đó; cổng `validate` giữ nguyên 0 ERROR.
- **Cột `name` giờ là tiếng Việt** ("TỔNG CỘNG TÀI SẢN"): `lang="en"` không có tác dụng với bản đầy đủ. Chọn chỉ tiêu bằng `id`, không bằng `name`. `validate.check_ratio_shape` đã chuyển sang khớp theo `id`.
- Gộp đúng 176 file `{TICKER}_{statement}_{freq}.csv` = 22 mã × {balance_sheet, cash_flow, income_statement, ratio} × {quarter, year}. Ticker/statement/freq vốn **chỉ nằm trong tên file**, nay thành cột thật nên đọc được nhiều NH từ cùng một frame mà không phải glob.
- **Không mất mát**: cả 8 nhóm đều chỉ có đúng 1 schema qua 22 mã. `--validate` đối chiếu **từng ô với cả 176 file nguồn**, không chỉ đếm dòng.
- Đọc bằng `pd.read_csv(..., dtype=vnstock_merge.READ_DTYPES)`. Hai cột có dtype dễ gây bất ngờ do gộp: `period` chứa lẫn `"2018-Q1"` và `"2018"` nên phải giữ là chuỗi; `off_balance` là bool trong file balance_sheet nhưng nhận NaN từ 3 loại kia nên thành object — dùng dtype `boolean` (nullable) để mask vẫn chạy.
- `off_balance` chỉ có giá trị ở `statement == 'balance_sheet'` (77.561 dòng), trống ở phần còn lại. Đây là cái giá của việc gộp 4 loại báo cáo vào một bảng, đã cân nhắc khi chọn dạng này.
- Kỳ báo cáo: quarter 2018-Q1 → 2026-Q2 (34 kỳ), year 2018 → 2025 (8 kỳ). Lưu ý cảnh báo ở bảng nguồn phía trên: **file `ratio` chỉ có 21–33 quý** tuỳ NH, đừng giả định mọi `id` đều dài 34 quý.

**`data/credit/bank_credit_quarterly.csv`** (748 dòng, 22 NH, 2018-Q1 → 2026-Q2)
`period, period_end, ticker, loans_vnd, deposits_vnd, total_assets_vnd, loans_qoq_percent, loans_yoy_percent, loans_over_assets_percent, ldr_computed_percent, npl_percent, npl_coverage_percent, ldr_percent, nim_percent, loan_provision_vnd, provision_expense_vnd, provision_over_loans_percent, car_percent, source, retrieved_at_utc`
- Dựng bằng `python -m crawlers.credit` (đọc lại từ `data/vnstock_financial/raw`, không gọi mạng).
- **Bẫy trong dữ liệu thô — cùng loại với COF**: các trường ratio lưu **dạng phân số** dù `unit` ghi `%` (NPL trung vị thô 0,0183 = 1,83%); `RT_BANK_NPL_COVERAGE` **âm ở cả 649/649 ô**; NPL = 0,0 ở 5 ô (đều là NVB) là placeholder thiếu dữ liệu chứ không phải nợ xấu bằng 0. Module xử lý cả ba.
- **CAR chỉ có 88/748 ô (11,8%)**, trống hẳn 2021 và 2026, NVB không có quý nào → **không dùng làm tiêu chí xếp hạng**.
- **NVB là outlier thật, không phải lỗi**: NPL 35,28% (2024-Q2) và giữ luôn 8 giá trị cao nhất toàn bộ dữ liệu. Sẽ bóp méo chuẩn hoá min-max của TOPSIS — cần winsorize hoặc tách riêng.
- Dự phòng trên bảng cân đối mang **dấu âm** (contra-asset), giữ nguyên dấu như công bố; `provision_over_loans_percent` quy về số dương.
- `loans_vnd` là **dư nợ ròng** (đã trừ dự phòng); `npl_percent` tính trên dư nợ gộp. STB 2026-Q2: 608.852 + 27.177 dự phòng = 636.029 tỷ, đúng mẫu số của NPL 7,54%. Nhân `loans_vnd × npl_percent` sẽ ra nợ xấu thấp hơn thật.
- **Lỗi nguồn đã gỡ (15/09/2026): ratio VCI lệch một quý quanh 2021-Q4, ở đủ 22/22 NH.**
  - Ở 20 NH, dòng 2021-Q4 là **bản chép nguyên 2021-Q3**: 21–22 chỉ tiêu tài chính trùng từng chữ số. Quý bình thường chỉ có 0–2 chỉ tiêu trùng. BAB, BVB thì để trống 2021-Q4.
  - Dòng **2022-Q1 mang số thật của 2021-Q4**: bao phủ nợ xấu VCI 2022-Q1 khớp số tính từ thuyết minh 2021-Q4 đến 0,01 điểm. Bằng chứng ngoài: VCB công bố bao phủ cuối 2021 là **424%** (báo chí 10/01/2022); thuyết minh cho 424,36%, còn VCI ghi 242,85% ở 2021-Q4.
  - `crawlers/vci_ratio.py` sửa ngay tại tầng đọc. Nếu thuyết minh xác nhận dòng quý sau là số của quý trước thì chuyển về đúng quý (20 NH); không xác nhận được thì để trống (SHB 2021-Q4, PGB 2022-Q1). Chỉ tiêu định giá thị trường và CASA không bị chép nên không đụng tới. Lỗ hổng 2021-Q2 không có bằng chứng lệch quý nên giữ nguyên.
  - `raw/` và `financial_long.csv` vẫn là bản sao nguyên trạng của nguồn. Module nào đọc `raw/*_ratio_quarter.csv` để tính toán phải gọi `vci_ratio.read()`; `python -m crawlers.vci_ratio` in bảng các ô đã sửa kèm bằng chứng.
  - Trước khi sửa, 19 NH có NIM, bao phủ, NPL, LDR của 2021-Q4 sai (VCB bao phủ 242,85% thay vì 424,36%; NVB NPL 1,94% thay vì 3,00%). `validate` không bắt được vì mọi giá trị đều nằm trong miền hợp lệ.

**Kiểm định dữ liệu tín dụng** — chạy `python -m crawlers.credit --validate`:

| Phép kiểm tra | Kết quả |
|---|---|
| Dư nợ / tiền gửi / dự phòng (BS) | **748/748 ô, 100%** — trường đầy đủ nhất của cả đề tài |
| LDR nhà cung cấp vs LDR tự tính lại `loans/deposits` từ bảng cân đối | **r = 0,9941**, lệch trung vị +1,37 điểm, **98,0%** số cặp lệch < 5 điểm |
| Số quý có NPL, thấp nhất / cao nhất trong 22 NH | 21 / 33 quý — **giữ được đủ 22 NH**, khác hẳn COF (thấp nhất 6 quý) |
| Tăng trưởng tín dụng YoY | 660 quan sát, trung vị 16,57%/năm, **0 dòng có \|YoY\| > 100%** |

**`data/credit/bank_repricing_gap.csv`** (66 dòng = 22 NH × 3 quý 2025-Q4, 2026-Q1, 2026-Q2; tính đến 11/09/2026 mới có số của TCB 2025-Q4)
`ticker, period, as_of_date, co_so, gap_qua_han, gap_khong_nhay_cam, gap_duoi_1t, gap_1_3t, gap_3_6t, gap_6_12t, gap_1_5n, gap_tren_5n, gap_tong_cong, tong_tai_san, tong_no_phai_tra, thuyet_minh, trang, nguon, do_tin_cay, source_url, note, ngay_nhap`
- Biến đại diện cho chữ **S** của CAMELS. **Không API nào có số này**: hai dòng tài sản sinh lãi và nợ phải trả lãi trong `Finance.note()` rỗng 0/748 ô. Phải chép tay dòng **"Mức chênh nhạy cảm với lãi suất nội bảng"** trong thuyết minh "Rủi ro lãi suất" của BCTC PDF.
- **Đơn vị kỳ là quý**, cùng khoá với panel. Bảng này chắc chắn có trong BCTC năm (Q4) và thường có trong BCTC bán niên (Q2). Với BCTC quý, ACB **có** in bảng trong thuyết minh chọn lọc quý I/2026 (mẫu B05a/TCTD-HN); các ngân hàng khác chưa kiểm.
- **Bẫy đã gặp**: một số ngân hàng (ACB) in thêm dòng **"Mức chênh nhạy cảm với lãi suất nội, ngoại bảng"** ngay dưới dòng nội bảng. **Không lấy dòng đó**: TCB chỉ in dòng nội bảng, nên phải lấy nội bảng mới so được giữa các ngân hàng. Lấy nhầm thì phép đối chiếu 1 vẫn khớp, nhưng phép đối chiếu 2 lệch đúng bằng phần cam kết ngoại bảng (ACB 2026-Q1: +43.037). Nếu ngân hàng không in bảng trong kỳ đó, để trống ô số và ghi `nguon = khong_cong_bo`, `--check` sẽ tách nhóm này riêng thay vì báo "còn thiếu".
- **Đây là bảng công việc**: ô trống nghĩa là chưa nhập, và `crawlers/repricing_gap.py` không bao giờ ghi đè ô đã có số. Có thể dán thẳng số dạng PDF (`88.862.676`, `(99.974.325)`, `-`); file lưu từ Excel bằng dấu `;` cũng đọc được.
- **Mẫu số là tổng tài sản của chính bảng thuyết minh**, không lấy từ bảng cân đối. Bảng thuyết minh chưa trừ dự phòng, nên với TCB là 1.203.452 tỷ so với 1.192.344 tỷ trên bảng cân đối.
- `--check` chạy 2 phép đối chiếu: tổng 8 cột khe hở = ô tổng cộng, và tổng tài sản − tổng nợ = ô tổng cộng. Hai phép này bắt được lỗi gõ và lỗi quên dấu ngoặc.
- `--ratios` trả `gap_12t_percent` (khe hở tích luỹ 12 tháng / tổng tài sản); bản trị tuyệt đối dùng làm tiêu chí chi phí trong TOPSIS. Cột `doi_chieu` cho biết bảng đã khớp hay chưa; **dòng `lech` không được đưa vào xếp hạng**.
- Mẫu TCB 31/12/2025: khe hở 12 tháng chỉ +1,69%, nhưng tích luỹ 1 tháng là +7,38% và 6 tháng là −3,51%. Con số 12 tháng che mất độ lệch ở giữa.

**`data/macro/policy_rate.csv`**: `date_effective, rate_type, rate_percent, source_url, note`
- 33 dòng = 11 sự kiện × 3 `rate_type` (`tai_cap_von`, `tai_chiet_khau`, `cho_vay_qua_dem`), từ 2017-07-10 đến 2023-06-19.
- Đây là **event log**, không phải chuỗi ngày. Dùng `policy_rate.as_daily_series()` để forward-fill thành chuỗi theo ngày khi ghép làm feature.
- QĐ 1123/QĐ-NHNN (hiệu lực 19/06/2023) vẫn còn hiệu lực tính đến 08/2026 — lãi suất điều hành đứng yên suốt 2024-2026.

**`data/macro/credit_growth.csv`**: `year, credit_growth_percent, as_of_date, announced_by, source_url, note`
- **8 dòng, 2018-2025**, chỉ số **cuối năm**. Dựng bằng `python -m crawlers.credit_growth`; sửa `HISTORY` trong module chứ đừng sửa CSV.
- **Cố ý không lưu số theo quý.** Ba lý do, đều đã kiểm chứng:
  1. NHNN chốt số ở những ngày khác nhau giữa các năm (21/03, 24/03, 29/09, 30/06...) nên hai nguồn có thể cùng đúng mà vẫn lệch nhau.
  2. Hai cơ quan nhà nước không khớp trên cùng một mốc: 30/09/2024 NHNN ghi **9,00%**, Tổng cục Thống kê ghi **8,53%**.
  3. Các bảng "theo quý 2018-2024" lưu hành trên mạng có sai số thật và **sai rải rác, không theo quy luật** — một bảng đã kiểm có 2019 ghi 13,89% (đó là số của 2018), 2024 ghi 14,05% (đúng là **15,08%**), 2021-Q1 ghi 1,47% (đúng là **2,93%**). Không có phép sửa chung nào cứu được loại bảng đó.
- Số cuối năm không dính cả ba vấn đề: mốc luôn là 31/12 và NHNN công bố tại họp báo có tên người phát ngôn.
- Vài số có **hơn một dạng lưu hành**, `note` ghi rõ thay vì chọn thầm: 2018 báo chí giật tít làm tròn "14%"; 2022 công bố 14,5% nhưng bản quyết toán sau còn lưu 14,18%; 2025 có báo giật "19,1%" trong khi số chi tiết là 19,01%.
- `as_monthly_series()` trải số của năm ra 12 tháng để join với chuỗi tháng. **Đây không phải đường tăng trưởng trong năm** — không được lấy sai phân hay đọc như động thái từng tháng.
- **2018 và 2019 mới có nguồn thứ cấp** (bài tổng hợp dẫn số liệu NHNN), chưa phải công bố gốc — cần bổ sung trích dẫn Báo cáo thường niên NHNN trước khi đưa vào luận văn. Đã ghi trong `note`.
- **Đã đối chiếu nội dung cả 8 trích dẫn (24/08/2026)** — chạy lại bằng `python -m crawlers.credit_growth --check-sources`. Phép kiểm này **không chỉ xem status code**: nó bắt link phải không redirect đi nơi khác *và* trang phải thực sự chứa con số mà dòng đó khai. Ba trích dẫn đã phải sửa vì lý do đó:
  - **2020**: URL `hochiminhcity.gov.vn` cũ vẫn trả **200** nhưng bài đã bị gỡ và **redirect về trang chủ cổng thông tin** — một link checker chỉ đọc status code sẽ báo "khoẻ" trong khi trích dẫn đã thành vô giá trị. Nguồn mới (VnExpress) nêu rõ người phát ngôn, ngày họp báo và mốc chốt số.
  - **2023**: `tapchitaichinh.vn` redirect sang `tapchikinhtetaichinh.vn` (tạp chí đổi tên) — đã trỏ thẳng vào URL đích.
  - **2025**: Tuổi Trẻ đã sửa tít từ "đến 19,1%" thành "hơn 19%" và **đổi luôn slug** — đã trỏ vào URL đích.
  - Hiện **8/8 trích dẫn còn sống**, không link nào redirect, mỗi trang đều chứa đúng con số. Nên chạy lại lệnh trên trước khi nộp.

**Kiểm định tăng trưởng tín dụng** — chạy `python -m crawlers.credit_growth --validate`:

| Phép kiểm tra | Kết quả |
|---|---|
| Đủ năm, mỗi dòng có `source_url`, `as_of_date` đều là 31/12 | **8/8 năm, không thiếu năm nào** |
| Đối chiếu với tổng dư nợ 22 NH niêm yết (nguồn độc lập: BCTC qua vnstock) | **r = 0,8331** trên 7 năm |
| Chiều của chênh lệch | Nhóm niêm yết tăng nhanh hơn hệ thống **+1,32 điểm** (trung vị) — đúng kỳ vọng, nhóm niêm yết giành thị phần từ các TCTD nhỏ/yếu |

> Hai chuỗi này độc lập hoàn toàn: một bên chép từ công bố NHNN, một bên cộng dồn dư nợ từ báo cáo tài chính đã kiểm toán. Chúng không đo cùng một tập ngân hàng nên **mức** khác nhau là đương nhiên; bằng chứng nằm ở việc chúng cùng chiều.

**`data/macro/cpi.csv`**: `month, cpi_yoy_percent, cpi_mom_percent, source_url, note`
- **103 dòng, 2018-01 → 2026-07 — đủ mọi tháng, không còn ô trống nào.**
- Nguồn chính: `crawlers/cpi_nso.py` (REST API của NSO). Bù khuyết: `crawlers/cpi_vneconomy.py` (VnEconomy + một số ô chép tay có trích dẫn).
- `cpi_nso.backfill()` hợp nhất **theo từng ô và không bao giờ ghi đè** giá trị đã có — thay nguyên dòng sẽ xóa mất các ô lấy từ nguồn khác. Xung đột được báo ra, không tự áp dụng.
- Chạy `python -m crawlers.cpi_nso` rồi `python -m crawlers.cpi_vneconomy` để cập nhật (cả hai idempotent).

**Kiểm định dữ liệu CPI** (nên trích vào chương thu thập dữ liệu):

| Phép kiểm tra | Kết quả |
|---|---|
| So với biểu đồ chính thức `nso.gov.vn/chart/cpi/embed/` | **12/12 khớp chính xác** |
| Nội tại: tích lũy 12 tháng `mom` có tái tạo `yoy` không | **92/92 tháng trong ±0,5đ**; \|lệch\| trung vị **0,008 điểm %**, lệch lớn nhất **0,029đ** |
| Nội tại: có chuỗi tháng liên tiếp nào lệch cùng dấu > 0,2đ không | **0** (xem cảnh báo bên dưới) |
| Bình quân 12 tháng `yoy` vs lạm phát bình quân năm công bố | cả 8 năm lệch ≤0,011đ; 2018/2021/2024 và **2025** khớp gần như tuyệt đối (≤0,002đ) |
| Chéo nguồn VnEconomy vs NSO trên ô cả hai cùng có | 2/2 khớp tuyệt đối |

**Cạm bẫy khi parse bản công bố NSO** (đã xử lý trong `NOT_HEADLINE_CPI` / `CPI_SUBJECT`) — nhiều bản công bố **không nêu** số CPI cần tìm nhưng lại nêu các số dùng câu chữ y hệt. Nếu không chặn, parser sẽ trả về nhầm:

| Bẫy | Ví dụ thật |
|---|---|
| **Lạm phát cơ bản** | *"Lạm phát cơ bản tháng 10/2019 tăng 0,15% so với tháng trước"* — đã từng lọt vào 4 ô |
| Chỉ số giá vàng / đô la Mỹ | *"chỉ số giá vàng tháng 10/2019 giảm 0,57% so với tháng trước"* |
| Nhóm hàng hóa | *"nhóm giáo dục tăng 6,19% so với cùng kỳ năm trước"* |
| Bình quân lũy kế | *"Bình quân 5 tháng đầu năm 2026, CPI tăng 4,31%"* — nằm **cùng câu** với số của tháng |
| **"tháng năm" trong cụm lũy kế** | *"...tháng 9, quý III và **9 tháng năm 2025**"* — `năm` vừa là *tháng Năm* vừa là *year*, xem dưới |

**Bẫy nguy hiểm nhất, đã từng làm hỏng dữ liệu thật** (phát hiện 24/08/2026, đã vá): tiêu đề bản công bố **tháng 9/2025** viết tháng bằng **chữ số** (`"tháng 9, quý III và 9 tháng năm 2025"`), trong khi `parse_month` khớp dạng chữ trước — nó lướt qua `"tháng 9"` rồi bắt trúng `"tháng năm"` trong cụm lũy kế `"9 tháng năm 2025"` và xếp bài đó vào **2025-05**. Vì hợp nhất dedup theo `month`, bài tháng 9 **đè mất bài tháng 5 thật**, khiến ô 2025-05 mang số của tháng 9 (`0,42 / 3,38` thay vì `0,16 / 3,24`), và tháng 2025-09 thì *trông như* không có bài nên phải bù từ VnEconomy.

> Phép thử ±0,5đ **không bắt được** lỗi này: nó chỉ đẩy 11 tháng liên tiếp lệch **cùng dấu ~0,26đ** (đúng bằng 0,42 − 0,16). Dấu hiệu là **một chuỗi dài lệch đều**, không phải một tháng lệch to — nên bảng kiểm định ở trên đã thêm hẳn một dòng cho tiêu chí này. Sau khi sửa, lệch lớn nhất tụt từ 0,272 xuống **0,029đ**.
>
> `parse_month` nay đọc **dạng số trước**, và chặn dạng chữ đứng ngay sau chữ số (`(?<!\d\s)`). Đã quét lại toàn bộ **261 bài** trên REST API của NSO: **0 bài bị gán sai tháng**.
>
> Bằng chứng thứ ba, độc lập với cả hai phép trên: bình quân 12 tháng `yoy` của năm 2025 **trước** khi sửa là 3,3217 (lệch +0,012đ so với mức 3,31% NSO công bố — sai số lớn nhất trong 8 năm); **sau** khi sửa là **3,3100, khớp tuyệt đối**.

Bốn ô đã phải sửa vì dính bẫy lạm phát cơ bản: `2019-09` yoy, `2019-10` mom, `2019-12` yoy, `2020-07` yoy. Ba ô đầu có trích dẫn trực tiếp — đã **đối chiếu lại nguyên văn** vào 24/08/2026, trong đó `2019-09` phải đổi tên miền (`gso.gov.vn` không còn phân giải) và `2019-12` phải đổi hẳn nguồn (bài Vietstock cũ **không hề chứa con số 5,23**, chỉ có MoM 1,4 và bình quân năm 2,79). **`2020-07` yoy = 3,39 vẫn là giá trị SUY RA** (từ quan hệ liên tháng, kiểm chéo bằng bình quân năm 2020) — chưa có trích dẫn trực tiếp, cần xác minh trước khi đưa vào luận văn.

**`data/price/<TICKER>.csv`**: `time, open, high, low, close, volume`
- 22 file, tổng **47.074 phiên**, `time` dạng `YYYY-MM-DD 07:00:00`. Độ dài rất lệch: EIB/STB 2.724 phiên (từ 2015), SSB chỉ 1.352 (lên sàn 2021).
- Cập nhật: `python -m crawlers.price` (idempotent — ghi đè ngày trùng, sắp xếp theo `time`).
- **Giới hạn đã biết**: 19 dòng có OHLC không nhất quán (close nằm ngoài khoảng high-low), rải rác 2019-2024 — do vnstock điều chỉnh giá theo cổ tức không đồng nhất giữa các cột. Cần lọc hoặc xử lý khi build feature. Danh sách: BAB 2020-02-18; EIB 2019-07-15, 2019-08-07; HDB 2019-08-07, 2019-09-04; LPB 2020-02-18; MBB 2019-09-04; NVB 2020-12-07; PGB 2024-09-23, 2024-12-20; STB 2019-08-07; TCB 2019-07-18; TPB 2019-07-18, 2019-07-19, 2019-09-04; VCB 2019-07-19, 2019-08-30; VIB 2019-12-31, 2020-02-18.

**`data/external/vn_banking_system_2002_2021_data.csv`** (667 dòng, 45 ngân hàng x 2002-2022)
Các cột chính: `Bank Code, Year, Classification, Number of Employees, Number of Branches, Total Deposits, Total Loans, Total Assets, Interest Expenses, Interest Incomes, Non-performing Loans, Total Shareholder's Equity, ...` (49 cột — xem đầy đủ trong file hoặc sheet `Variables List` của `vn_banking_system_2002_2021.xlsx`). Cột `ticker` được thêm vào để join với dữ liệu vnstock/lãi suất theo mã 22 ngân hàng niêm yết.

**`data/interest_rates/bank_earning_asset_yield_quarterly.csv`** (540 dòng, 22 NH, 2018-Q1 → 2026-Q2)
`period, period_end, ticker, earning_asset_yield_ttm_percent, nim_ttm_percent, cof_ttm_percent, ibl_over_earning_assets, source, retrieved_at_utc`
- **Sinh ra để trả lời câu "lùi lãi suất cho vay về 2018".** Câu trả lời thẳng là **không lùi được** với số công bố (lý do ở mục giới hạn 1) — nên phía cho vay phải **suy ra từ BCTC**, đúng nước đi mà `cost_of_funds.py` đã làm cho phía huy động.
- **ĐÂY KHÔNG PHẢI LÃI SUẤT CHO VAY. Không được gọi tên như vậy trong luận văn.** Nó là lợi suất gộp trên **toàn bộ tài sản sinh lời** — gồm cả trái phiếu chính phủ, tiền gửi liên ngân hàng, chứng khoán kinh doanh, những thứ lợi suất thấp hơn hẳn cho vay khách hàng.
- **Cách dựng.** IS chỉ có `IS_NET_INTEREST_INCOME` (**thuần**) nên không có thu nhập lãi gộp để chia. Nhưng NIM và COF dùng chung tử số nên khôi phục được:
  - `NIM = (thu lãi − chi lãi) / tài sản sinh lời`, `COF = chi lãi / nợ chịu lãi`
  - ⇒ `chi lãi / TSSL = COF × (IBL/EA)` ⇒ **`lợi suất = NIM + COF × (IBL/EA)`**
  - `IBL` = tiền gửi KH + vay/tiền gửi TCTD + giấy tờ có giá. `EA` = tổng tài sản − tiền mặt − TSCĐ − tiền gửi tại NHNN (**trừ ra** chứ không cộng các cấu phần, vì vnstock không tách chứng khoán đầu tư — cộng vào sẽ thiếu hẳn phần lớn sổ trái phiếu của nhóm NHTM nhà nước).
  - `IBL/EA` ra trung vị **0,912** (5–95%: 0,83–0,97), đúng khoảng bảng cân đối ngân hàng thật — tức phép khôi phục không sinh ra số vô lý.
- **Cơ sở TRAILING 12 THÁNG.** Đã kiểm NIM bằng đúng phép mà `cost_of_funds.py` kiểm COF: Q4 khớp số cả năm (lệch trung vị **0,0000**, khớp tuyệt đối **139/160**), rồi trôi dần Q3 → Q2 → Q1. Hai đầu vào cùng TTM nên đầu ra cùng TTM — **không đọc chênh lệch quý này so quý trước như mức thay đổi lãi suất của quý đó**.
- **Kế thừa y nguyên độ phủ lệch của COF**: 540/748 ô, NVB chỉ 6 quý còn VCB 33.

**Kiểm định lợi suất tài sản** — chạy `python -m crawlers.lending_yield --validate`:

| Phép kiểm tra | Kết quả |
|---|---|
| Chéo nguồn với lãi suất cho vay **công bố** (2 chuỗi hoàn toàn độc lập: BCTC kiểm toán vs NH tự công bố qua báo) | 97 cặp bank-quarter, **r = 0,6705** |
| **Chiều** của chênh lệch — lợi suất phải THẤP hơn lãi suất cho vay | **83,5% số cặp**, trung vị **−0,91 điểm** — đúng kỳ vọng |
| **Tương quan chéo ngân hàng trong từng quý** (thứ TOPSIS thực sự cần) | **+0,68 … +0,90**, cả 6/6 quý chồng lấn |
| Cơ sở TTM của NIM | Q4 lệch trung vị 0,0000, khớp tuyệt đối 139/160 |

> **Chênh lệch KHÔNG phải hằng số — đừng bù offset để "quy về" lãi suất cho vay**: −2,48 điểm ở NVB, −1,62 ở TCB, −0,34 ở MBB, **+0,81 ở SHB**. Nó phản ánh cơ cấu tài sản từng ngân hàng (NH ôm nhiều trái phiếu thì lệch sâu hơn), nên bản thân độ lệch là thông tin, không phải nhiễu.

**`data/interest_rates/bank_cost_of_funds_quarterly.csv`**
`period, period_end, ticker, cof_ttm_percent, source, retrieved_at_utc`
- **525 dòng, 22 ngân hàng, 2018-Q1 → 2026-Q2** (thiếu 2021-Q2, xem dưới). Dựng bằng `python -m crawlers.cost_of_funds`. Trước 15/09/2026 là 540 dòng: 15 dòng 2021-Q4/2022-Q1 sai do ratio VCI lệch quý, xem `crawlers/vci_ratio.py`.
- `cof_ttm_percent`: chi phí vốn thực tế, **%/năm, số dương**. Khoảng thực tế 2,10%–8,71%.
- **Cơ sở là TRAILING 12 THÁNG, không phải riêng quý đó.** Hai quý liền nhau chồng lấn 9 tháng nên chuỗi tự thân đã rất tự tương quan; **không được đọc chênh lệch quý này so quý trước như mức thay đổi lãi suất của quý đó**, và khi dự báo bằng LSTM phải ý thức rằng cửa sổ trượt này làm bài toán dễ đi một cách giả tạo.
- **Bẫy trong dữ liệu thô:** trường gốc lưu **phân số ÂM** dù `unit` ghi `%` (−0,0252 = 2,52%/năm) — đọc thẳng là sai cả dấu lẫn 100 lần độ lớn. Và **114/654 ô bằng đúng 0.0**: không ngân hàng nào huy động vốn miễn phí — đây là placeholder thiếu dữ liệu, module loại bỏ chúng. Nạp thẳng file ratio vào mô hình sẽ có 114 quan sát giả "huy động vốn 0%".
- **Độ phủ rất lệch giữa các ngân hàng:** 11 NH có 32–33 quý (VCB, VPB, STB, HDB, MBB, SHB, BID, CTG, LPB, TPB, BAB), nhưng NVB chỉ có 6, PGB 8, VIB 10, BVB và EIB 11. TOPSIS cần chấm điểm mọi phương án — phải quyết định loại nhóm thiếu hay thu hẹp cửa sổ thời gian, không thể lờ đi.
- 2021-Q2 trống hoàn toàn: nguồn chỉ có NVB và giá trị là placeholder 0.0.

**Kiểm định dữ liệu COF** (nên trích vào chương thu thập dữ liệu) — chạy `python -m crawlers.cost_of_funds --validate`:

| Phép kiểm tra | Kết quả |
|---|---|
| **Cơ sở tính** (nội bộ): nếu là TTM thì Q4 phải bằng số cả năm | Q4 lệch trung vị **0,0000đ, khớp tuyệt đối 118/133 cặp**; Q3 0,20đ → Q2 0,39đ → Q1 0,49đ (càng xa Q4 càng lệch, đúng dạng cửa sổ trượt) |
| **Chéo vendor**: Harvard Dataverse (Interest Expenses / Total Deposits) vs COF, 55 bank-year | **r = 0,8716**; chênh lệch **dương ở 98,2%** số cặp, trung vị +1,29đ — đúng hướng vì mẫu số Harvard chỉ là tiền gửi còn COF tính cả liên NH + giấy tờ có giá |
| **Cấu trúc chênh lệch** (bằng chứng mạnh nhất): lệch lớn nhất phải rơi vào nhóm huy động nhiều ngoài tiền gửi | VPB +2,6→3,1đ, HDB +2,0→2,7đ, TPB +1,9→2,4đ; nhỏ nhất VCB +0,2→0,6đ, STB −0,1→+0,3đ. Hai bộ số độc lập tái tạo đúng cơ cấu vốn từng ngân hàng |
| **Chéo nguồn**: COF trung vị vs tiền gửi 6–12 tháng bình quân của SBV, cùng đưa về cơ sở TTM | **r = 0,9482** nhưng **chỉ trên n = 7 quý** (chuỗi SBV bắt đầu 2024-01, mất 12 tháng đầu cho cửa sổ TTM) — mẫu quá nhỏ để coi là bằng chứng mạnh, phải nêu n khi trích. COF **thấp hơn ở mọi quý**, khoảng cách ổn định −0,78đ — đúng mức pha loãng do CASA (0,1–0,2%/năm) |

> Ghi chú về phép kiểm tra cuối: nếu **không** đưa hai bên về cùng cơ sở TTM thì r chỉ còn 0,51 và COF có vẻ *cao hơn* lãi suất tiền gửi ở 2024-Q1/Q2. Đó không phải mâu thuẫn mà là hệ quả của chính cơ sở TTM: COF quý 2024-Q1 phản ánh 12 tháng của 2023 khi mặt bằng lãi suất còn cao.

**`data/app_reviews/{TICKER}.csv`** — đánh giá app ngân hàng số trên Google Play, **1 dòng = 1 đánh giá**
`ticker, app_id, app_role, review_id, at_utc, score, thumbs_up, app_version, content, replied, replied_at_utc, source, source_url, retrieved_at_utc`

Đây là nguồn **phía người dùng** duy nhất của đề tài — mọi file còn lại đều là phía cung (ngân hàng/SBV công bố gì). Cũng là chuỗi theo từng ngân hàng **dài thứ hai sau giá cổ phiếu**, và là chuỗi duy nhất không suy ra từ BCTC.

- `app_id` là khoá thật, **không phải `ticker`**. 5 ngân hàng có nhiều hơn một app và **không được nối thành một chuỗi** (`--validate` mục 8 liệt kê): STB (mBanking bán lẻ + SACOMBANK PAY ví điện tử), MSB và LPB (**app cũ + app kế nhiệm** — đúng loại đứt gãy đã xử lý cho VCBNEO/MBV ở `lending_rates_bank.py`), TPB (TPBank Mobile + Savy, app tiết kiệm riêng), BVB (digimi + Timo). Mặc định chỉ cào `app_role == "retail"`.
- **`userName` và `userImage` bị loại có chủ đích, không phải sót.** Nguồn trả về cả hai; module bỏ trước khi ghi (`DROPPED_PERSONAL_FIELDS`) vì đây là dữ liệu cá nhân theo Nghị định 13/2023/NĐ-CP, và luận văn chỉ công bố ở mức tổng hợp. `--validate` mục 9 kiểm lại rằng chúng không lọt vào file.
- **Endpoint chỉ trả về đánh giá CÓ nội dung.** Chênh lệch giữa `ratings` và `reviews_with_text` trong `app_catalog.csv` chính là phần chấm sao suông không lấy được (VCB: 185.758 lượt chấm nhưng chỉ 69.443 có chữ). Nghĩa là **`mean_score` tính từ file này là trung bình của người có viết nhận xét**, không phải trung bình toàn bộ người chấm — phải nói rõ khi trích, và dùng `app_catalog.score` khi cần con số của cả tập.
- `at_utc` là dấu thời gian **do nguồn trả về, dạng naive**; giữ nguyên, không quy đổi múi giờ.
- Đánh giá **sửa được**: người dùng sửa lại thì bản mới nổi lên đầu với cùng `review_id`. Dedup theo `(app_id, review_id)` với `keep="last"` nên bản mới ghi đè bản cũ; lần chạy tăng dần lùi thêm `OVERLAP_DAYS = 3` ngày để bắt được.
- `app_version` lấy `reviewCreatedVersion` trước, `appVersion` sau. Nhiều dòng để trống — không suy đoán.

**`data/app_reviews/app_catalog.csv`** — snapshot cấp app mỗi lần chạy
`date, ticker, app_id, app_role, app_name, title, developer, score, ratings, reviews_with_text, installs, min_installs, version, released, last_updated, source, source_url, retrieved_at_utc`
- Chạy hàng ngày thì đây tự thành **chuỗi thời gian của điểm hiển thị + số lượt cài** — rẻ hơn hẳn việc tính lại từ file đánh giá.
- **`score` ở đây khác `mean_score` lịch sử, và khoảng cách có ý nghĩa.** Google gia trọng đánh giá gần đây: PGBank hiển thị 4,74 trong khi trung bình toàn bộ lịch sử là 3,34. Đó là dấu vết app được làm lại, không phải lỗi số liệu — nhưng lấy nhầm cái này cho cái kia sẽ làm hỏng chuỗi.
- `released` là chuỗi ngày **theo định dạng tiếng Việt của nguồn** ("29 thg 10, 2018"), giữ nguyên như nguồn in ra.

**`data/app_reviews/app_reviews_monthly.csv`** — panel bank-month, đây là file đưa vào mô hình
`month, ticker, app_id, app_role, n_reviews, mean_score, median_score, pct_1star, pct_5star, pct_with_content, n_with_content, thumbs_up_sum, n_versions, reply_rate, bombing_days, usable`
- Khoá là `(month, ticker, app_id)` — **không gộp các app của cùng một ngân hàng**, đúng lý do ở trên.
- `usable = False` khi tháng có `< 10` đánh giá. Trung bình sao của một tháng 3 đánh giá không phải mặt bằng hài lòng; lọc trước khi vẽ chuỗi, cùng nguyên tắc với `dung_duoc` của `lending_rates_bank`.
- **`bombing_days` là cờ cảnh báo, không phải kết luận.** Đếm số ngày trong tháng vừa có `>= 20` đánh giá, vừa `>= 5x` trung vị ngày, vừa `>= 60%` một sao. Ngưỡng đặt tay và **có thể bắt nhầm** một đợt sập app thật — nhưng đó chính là thứ cần nhìn: cả review bombing lẫn sự cố hệ thống đều làm `mean_score` tháng đó không so được với tháng khác. `--validate` mục 6 in ra từng ngày bị gắn cờ để soát bằng mắt.
- Chiều ngược lại — **5 sao ảo** — nằm ở mục 7 của `--validate` (cụm đánh giá 5 sao không nội dung trong một ngày). Trên dữ liệu hiện có tỉ lệ này bằng 0 vì endpoint đã lọc sẵn đánh giá không có chữ; giữ phép kiểm để nếu nguồn đổi hành vi thì phát hiện được.

**`data/branch_network/branch_points.csv`** — mạng lưới điểm giao dịch + ATM, **1 dòng = 1 điểm trên bản đồ**
`osm_type, osm_id, kind, ticker, brand_label, wikidata, province, lat, lon, name, addr_city, addr_street, source, source_url, retrieved_at_utc`

Nguồn là **OpenStreetMap** qua Overpass API — miễn phí, không cần API key, giấy phép ODbL nên trích dẫn được trong luận văn. Đây là phương án thay cho Google Places API (cần thẻ thanh toán) và cho việc cào trang web từng ngân hàng (đã khảo sát, xem dưới).

- `kind` là `bank` (điểm có người) hoặc `atm`, lấy thẳng từ tag `amenity` của OSM.
- **Nhận diện ngân hàng theo hai bậc, ưu tiên bậc chắc chắn hơn**: khớp `brand:wikidata`/`operator:wikidata` trước (18/22 NH có mã Wikidata — chính xác tuyệt đối), không có mới rơi xuống khớp mẫu tên đã chuẩn hoá bỏ dấu (`NAME_PATTERNS`). Bốn ngân hàng chưa có mã Wikidata trong OSM: BAB, BVB, NVB, PGB.
- **Tên trong OSM hỗn loạn đúng như `lending_rates_bank.py`**: cùng một ngân hàng xuất hiện dưới "NCB", "NCB Bank", "Ncb", "Navibank", "Ngân hàng Quốc Dân", "NCB - National Citizen Bank"; hoặc "Techcombank" và "Techcombank - ATM". Chuẩn hoá bỏ dấu + bỏ token nhiễu (`ngan hang`, `atm`, `pos`, `cn`, `pgd`) rồi mới khớp mẫu.
- **Cố ý KHÔNG gộp các ngân hàng đã sáp nhập/đổi chủ**: "Southerbank" (Southern Bank, sáp nhập vào Sacombank 2015) và "Vikki Bank" (tên mới của DongA Bank) để nguyên không map — gộp sẽ nối hai chế độ sở hữu vào một chuỗi, cùng nguyên tắc với VCBNEO/MBV.
- **39,9% POI không map được và module không đoán.** Trong đó **539 điểm không có tên gì**, và **521 điểm là Agribank** — ngân hàng lớn nhất hệ thống nhưng **không niêm yết** nên không thuộc 22 mã. `--unmapped` liệt kê để mở rộng `NAME_PATTERNS` khi cần.
- `provinces.csv` lấy động từ OSM và hiện đã là **34 tỉnh/thành sau sáp nhập 01/07/2025** — không phải 63 như phần lớn tài liệu cũ. Nếu ghép với bất kỳ bảng nào theo tỉnh trước 2025 thì phải ánh xạ lại.

**Ba phép đối chiếu, và cả ba đều nói cùng một điều** — chạy `python -m crawlers.branch_network --validate`:

| Phép kiểm tra | Kết quả |
|---|---|
| **Chéo nguồn**: OSM `n_bank` vs `Number of Branches` của Harvard, 22 NH | **Spearman = 0,414 / Pearson = 0,452** — yếu. Đơn vị vốn đã khác nhau (Harvard đếm chi nhánh cấp 1, OSM đếm mọi điểm) nên chỉ đọc thứ hạng được, mà thứ hạng cũng không khớp |
| **Cấu trúc sai lệch** (bằng chứng quyết định): nếu OSM thiếu đều thì tỉ lệ OSM/Harvard phải xấp xỉ nhau | **Lệch 37 lần**: LPB 0,035 và SHB 0,035 ở một đầu, CTG 1,31 và VCB 1,31 ở đầu kia. LPBank có 568 chi nhánh (mạng lưới bưu điện) nhưng OSM chỉ có 20 điểm |
| **Chéo độc lập TPB** (bản ngân hàng tự công bố trên tpb.vn) | tpb.vn: **486 điểm** (159 chi nhánh + 327 LiveBank). OSM: **33 điểm giao dịch, 189 kể cả ATM** → tỉ lệ **0,39**, và riêng phía chi nhánh thiếu tới 5 lần |
| **Độ phủ địa lý** | Hà Nội 1.963 POI và TP.HCM 1.474, nhưng **Sơn La 2 và Cà Mau 4**. 14/22 ngân hàng có mặt ở **dưới 50% số tỉnh** |

**Khảo sát trang web từng ngân hàng (thực hiện 2026-08-28) — kết quả là bỏ**, ghi lại để không ai phải làm lại. Quét 12 ngân hàng lớn:
- **Chỉ TPBank nhúng dữ liệu server-side**: mảng JSON `danhSachLocation` ngay trong HTML, 486 điểm đầy đủ toạ độ + địa chỉ. Đây chính là nguồn cho `tpb_official_points.csv`.
- **BIDV** có dữ liệu nhưng nạp qua AJAX (HTML chỉ chứa JS dựng marker từ `a.Lat`/`a.Lon`/`a.BranchType`) — phải dò endpoint riêng.
- **VCB và CTG** render client-side hoàn toàn: trang 2,7 MB mà không có lấy một toạ độ nào trong HTML.
- **MBB, ACB, TCB, VPB, STB, VIB, HDB** không lộ cả link mạng lưới ở trang chủ; **SHB trả 403**.
- Tức là **1/12 cào được sạch**, đúng bằng tỉ lệ đã gặp ở khảo sát 14 trang IR ngân hàng tại giới hạn 6. Làm đủ 22 ngân hàng nghĩa là 22 parser riêng cho một biến duy nhất.

## Làm sạch → xử lý → đặc trưng → chọn lọc

Chạy theo thứ tự, mỗi bước chỉ đọc file đã có, không gọi mạng:

```
python -m crawlers.build_panel       # panel sạch + cổng validate (mã thoát 1 nếu còn ERROR)
python -m crawlers.inventory         # kiểm kê mọi CSV → data/model/data_inventory.csv
python -m crawlers.build_features    # 120 đặc trưng → features_quarterly.csv + feature_spec.csv
python -m crawlers.select_features   # quyết định Giữ/Loại → feature_catalog.csv, features_selected.csv, features_ranking_latest.csv
```

**Kiểm kê (15/09/2026):** 639 file, 2,16 triệu dòng. Bỏ 288 file lưu trữ và 261 file trùng (1,07 triệu dòng: `powerbi/`, `raw*/` theo mã, `deposit_raw/`, bản sao nhập tay). Giữ 60 file cho mô hình, 7 file cho xếp hạng/giao diện, 15 file tham khảo, 8 file trung gian.

**Đưa về NH-quý.** Dòng chảy KQKD/LCTT cộng 4 quý (TTM), mẫu số là số dư bình quân 5 mốc — số quý của vnstock là số **riêng từng quý**, không phải lũy kế (cộng 4 quý khớp số năm ở 76–97% NH-năm, phần lệch là số trình bày lại). Số năm và nửa năm gán **as-of** (năm Y dùng cho Q4/Y và Q1–Q3/Y+1) để không dùng số chưa công bố. Tháng lấy trung bình quý, ngày lấy lợi suất/biến động trong quý, sự kiện lấy giá trị có hiệu lực cuối quý, ảnh chụp (sở hữu, chi nhánh) lặp mọi quý và gắn cờ `tĩnh`.

**Làm sạch ở tầng tạo biến** (số ô ghi vào `crawl_log.txt`): mẫu số ≤ 0 → NaN; COF/lợi suất TSSL bằng 0 → NaN (3 + 8 ô sót trong panel); thuyết minh chi lương, trả lãi, phí BHTG bằng 0 hoặc âm → NaN (67 ô); trái phiếu Chính phủ vượt tổng chứng khoán đầu tư → NaN (4 ô); quý < 20 phiên → NaN (8); quý < 30 review → điểm app NaN (158). Tăng trưởng lợi nhuận dùng dạng đối xứng 200(a−b)/(|a|+|b|) — dạng thường cho ra −8,4 triệu % ở NVB. **Không** điền khuyết và **không** winsorize ở đây: hai việc đó phải fit trên tập train.

**Chọn lọc — tầng 1 (chất lượng):** mức tuyệt đối đồng → Loại; cùng khái niệm với biến khác → Loại; một giá trị ≥ 95% số ô → Loại; phủ < 70% hoặc < 20 NH → Loại, trừ biến có ≥ 20 NH trong 4 quý gần nhất → **Giữ cho xếp hạng**; |Spearman| ≥ 0,90 với biến ưu tiên hơn → Loại. Kết quả: **88 Giữ · 7 Giữ cho xếp hạng · 25 Loại**.

**Chọn lọc — tầng 2 (liên hệ dự báo, không loại biến):** Spearman giữa đặc trưng quý t (trừ trung bình từng NH) và **thay đổi** của 6 mục tiêu (NIM, COF, NPL, CASA, LDR, ROE) từ t sang t+1; đạt khi |ρ| ≥ 0,15 và cùng dấu, |ρ| ≥ 0,10 ở cả hai nửa (≤ 2022-Q2 và sau). 28 biến là **Lõi dự báo**, 60 biến là **Mô tả / xếp hạng**. Đáng chú ý: thay đổi COF đi theo lãi suất tái cấp vốn (ρ = +0,41) và tăng trưởng tín dụng hệ thống (+0,47) — nhân tố chung; NPL và LDR chỉ có động lượng của chính nó. Trung bình NH tính trên cả mẫu nên đây là số **mô tả**, không phải kiểm định ngoài mẫu.

### Thử nghiệm điền khuyết (`experiments/imputation_benchmark.py`)

Thử lại Jäger, Allhorn & Bießmann (2021), *A Benchmark for Data Imputation Methods*, Frontiers in Big Data 4:693674, trên `features_selected.csv` từ 2019-Q1 (660 dòng, 2,4% ô thiếu thật). Bỏ 2018 vì 89% ô thiếu nằm ở đầu chuỗi — ô chưa thể có số, không phải ô bị mất. Chạy ~25 phút: `python -m experiments.imputation_benchmark`.

**Phần 1 — chất lượng điền.** Che giả ô trên 68 biến theo NH-quý (bỏ biến chung và biến tĩnh vì điền từ NH khác cùng quý là chép đáp án), 4 kiểu thiếu (MCAR, MAR, MNAR như bài; thêm BLOCK = một đoạn quý liền nhau trong một NH) × 1/10/30/50% × 3 lần lặp. NRMSE tính theo độ lệch chuẩn của biến (trung bình ≈ 1):

| Cách điền | NRMSE trung vị | Hạng TB (1–9) | Giây / lần |
|---|---|---|---|
| RF + thông tin panel (quý trước/sau, trung vị NH) | 0,373 | 2,29 | 13,2 |
| Nội suy trong từng NH | 0,373 | 2,71 | 0,22 |
| Random forest như bài | 0,486 | 3,40 | 12,7 |
| Lấy số quý trước (không nhìn tương lai) | 0,500 | 4,48 | 0,04 |
| kNN (k = 5) | 0,600 | 4,87 | 0,23 |
| Trung vị NH | 0,705 | 6,08 | 0,04 |
| GAIN | 0,762 | 6,52 | 8,4 |
| VAE | 0,853 | 7,02 | 4,6 |
| Trung bình | 1,018 | 7,63 | 0,02 |

Số chạy lại ngày 15/09/2026 sau khi gỡ lỗi ratio VCI lệch quý. Thứ hạng giữ nguyên; riêng RF + panel và nội suy nay bằng nhau ở trung vị (trước là 0,370 so với 0,373).

Hai kết luận của bài lặp lại được:
- RF là tốt nhất trong các cách của bài: thắng kNN ở 80,1% trường hợp.
- DL không hơn cách đơn giản: GAIN thua kNN ở 77,6% trường hợp; ở mức che 50%, GAIN (1,20) và VAE (1,46) còn tệ hơn điền trung bình (1,03).

Điểm mới:
- Cách điền theo panel mà bài không xét tốt hơn RF của bài ~23%.
- RF + panel chỉ hơn nội suy ở 48,9% trường hợp nhưng chậm gấp 60 lần.
- Nội suy tốt ở biến chuyển động chậm (log tổng tài sản 0,05, cơ cấu ngành 0,10) và tệ ở biến thay đổi/lợi suất (thay đổi CASA 1,34, lợi suất cổ phiếu 1,30) — với nhóm này không nên điền.

**Phần 2 — ảnh hưởng lên dự báo** (kịch bản 2 của bài: train và test đều thiếu thật). LightGBM dự báo thay đổi quý sau của 6 mục tiêu, walk-forward 13 gốc 2023-Q1 → 2026-Q1 (286 dự báo/mục tiêu), mỗi cách điền chỉ fit trên train và không nhìn tương lai. Khoảng tin cậy 95% bootstrap theo khối quý gốc:
- **Đổi cách điền chỉ đổi MAE từ −3,5% đến +4,4%** so với để nguyên ô thiếu; 27/30 khoảng tin cậy chứa 0 — khớp kết luận "hiếm khi cải thiện quá 5%" của bài.
- **Nút thắt không phải ô thiếu mà là tính dự báo được.**
  - So với naive, LightGBM hơn ở COF (+19,4% [−13,3; +46,9]) và NIM (+4,2% [−3,5; +12,8]), nhưng đều chưa có ý nghĩa.
  - **Thua naive có ý nghĩa ở NPL (−11,9% [−23,5; −1,8])**; thua ở ROE (−6,3%) và LDR (−3,2%).
  - Chạy lại 15/09/2026 sau khi gỡ lỗi ratio VCI lệch quý. Bản trước: COF +18,1%, NIM +6,2%, NPL −11,3% [−22,7; −1,3], khoảng thay đổi −3,5% → +4,2%. Kết luận không đổi. Khoảng tin cậy tính bằng bootstrap 5.000 lần theo khối quý gốc trên `imputation_downstream_predictions.csv`.

**Áp dụng:** để nguyên NaN cho LightGBM; mô hình cần đủ ô (tuyến tính, GRU) dùng lấy số quý trước trong NH + cột cờ thiếu; không dùng GAIN/VAE để điền.

**Phần 3 — ảnh hưởng lên xếp hạng TOPSIS** (`python -m experiments.ranking_missing_sensitivity`, ~2 phút). 11 tiêu chí minh họa cho người gửi tiết kiệm, trọng số đều, chuẩn hóa min-max — **chưa phải bộ tiêu chí chốt**. Mô phỏng có đáp án: 14 quý 2023-Q1 → 2026-Q2, các NH đủ 11 tiêu chí, che 1 ô (1.958 trường hợp) rồi xử lý bằng từng cách:

| Cách xử lý ô thiếu | NH bị che dịch TB | NH bị che đổi hạng | Top-3 đổi | NH khác dịch TB |
|---|---|---|---|---|
| Số gần nhất của chính NH | 0,39 bậc | 25,6% | 2,6% | 0,05 |
| kNN / trung bình / trung vị các NH | 0,91–0,94 | ~50% | 6,4–6,8% | 0,08 |
| Bỏ tiêu chí đó cho mọi NH | 1,05 | 61,3% | 47,1% | 1,05 |
| Giá trị tệ nhất | 2,78 | 81,5% | 15,7% | 0,20 |
| Bỏ ngân hàng | — | — | 11,8% | 0,19 |

Đổi trọng số (Dirichlet α = 8, 300 bộ) trên cùng khung làm mỗi NH dịch trung bình **1,92 bậc** — một ô điền bằng trung bình tạo ra khoảng một nửa mức bất định đó cho NH bị thiếu. Điền trung bình **kéo về giữa**: NH hạng 16+ được đẩy lên +0,52 bậc, NH top 5 bị kéo xuống −0,48. Ảnh chụp thật 4 quý gần nhất thiếu đúng hai ô quan trọng: BAB thiếu điểm app (số gần nhất 1,38 sao, 2024-Q4) → hạng 16 nếu điền trung bình, 19 nếu dùng số gần nhất; NVB thiếu CAR (9,22%, 2024-Q1) → 20 hoặc 21. Mô phỏng dùng số của quý liền trước nên ưu thế của "số gần nhất" là lạc quan với ô đã cũ nhiều quý.

### EDA — các nhóm dữ liệu liên hệ với nhau thế nào (`experiments/eda.py`)

`python -m experiments.eda` (~2 phút) → `data/model/eda/*.csv`. Chín câu hỏi trên `features_quarterly.csv` 2019-Q1 → 2026-Q2 (660 NH-quý), Spearman, khoảng tin cậy bootstrap theo cụm NH:

1. **Phân rã phương sai** (NH / xu hướng chung theo quý / riêng NH-quý): CASA 92%, quy mô 88%, vốn chủ 87%, NIM 82% là khác biệt giữa NH; lợi suất TSSL 32%, chi phí vốn 28% là xu hướng chung; tăng trưởng dư nợ 58%, điểm app 65%, NPL 49% là phần riêng.
2. **Xu hướng**: chi phí vốn TTM đáy 3,56% (2022-Q2) → đỉnh 5,93% (2023-Q4); NPL 1,38% → 2,73% (2025-Q3); LDR 94,5% → 110,1%.
   - CASA vẽ bằng **trung bình 4 quý** (`casa_r4`). CASA quý 4 cao hơn quý 1 năm sau: trung vị chênh 0,6–2,4 điểm ở 6/7 năm (`casa_seasonality.csv`).
   - Trung vị thô còn che cú sốc 2022 ở NH CASA cao: TCB 47,0% → 34,3%, MBB 44,6% → 37,6% (2021-Q4 → 2022-Q4).
   - Nhóm hiệu quả thấp: NPL 1,80% → 3,08%, CASA 4 quý 9,9% → 8,2%; nhóm hiệu quả: CASA 4 quý 15,0% → 20,2%.
3. **Độ trễ truyền dẫn** (7 lần đổi lãi suất tái cấp vốn):
   - Trên số **riêng từng quý** (MAS `*_quarter_percent`): chi phí vốn phản ứng mạnh nhất sau 1–2 quý (ρ +0,44 và +0,45), lợi suất tài sản sau 1 quý (+0,31), NIM bị ép sau 2 quý (−0,25). Chuỗi chi phí vốn theo quý đạt đỉnh ở 2023-Q2.
   - Trên số **cộng 4 quý (TTM)**: đỉnh tương quan ở 3 quý (+0,54), NIM âm nhất sau 4 quý (−0,25), chuỗi đạt đỉnh ở 2023-Q4. Khoảng 2 quý trễ thêm là do cửa sổ cộng dồn.
   - Lãi suất niêm yết không đo được vì từ 2023 NHNN chỉ đổi một lần.
4. **Tương quan giữa NH vs trong NH** (trừ trung bình NH và trung bình quý): CASA–chi phí vốn −0,95 vs −0,08; NIM–tăng trưởng dư nợ +0,76 vs −0,16; ROE–ROA +0,80 vs +0,88. Quan hệ so sánh các NH phần lớn không dùng được cho mô hình chuỗi.
5. **PCA + k-means trên số gần nhất của từng NH** (2026-Q2; cùng ảnh chụp với `features_ranking_latest.csv`). Từ 16/09/2026 thay cho trung bình 4 quý, vì bản trung bình chậm so với hiện tại: STB NPL 5,83% thay vì 7,54%; NVB ROA −0,93% dù đã lãi trở lại.
   - PC1 sinh lời 33,8%, PC2 vốn rẻ – rủi ro tín dụng thấp 21,4%.
   - Ba nhóm: 7 NH **lớn, vốn rẻ, nợ xấu thấp** (ACB, BID, CTG, MBB, MSB, TCB, VCB; CASA 22,7%, NPL 1,20%); 13 NH **vốn đắt, sinh lời thấp** (chi phí vốn 5,04%, ROA 0,87%); HDB, VPB **tăng trưởng nhanh, biên cao**.
   - **Nhóm không ổn định**: silhouette chỉ 0,20. `cluster_stability.csv` phân nhóm lại trên ảnh chụp của từng quý trong 4 quý gần nhất và bootstrap 300 lần theo NH. 16/22 NH vững (≥ 3/4 quý và ≥ 50% bootstrap); LPB, OCB, SHB, SSB, TPB, VIB chỉ cùng nhóm 2/4 quý — với trung bình 4 quý chúng rơi vào nhóm lớn, với số gần nhất rơi vào nhóm vốn đắt. Trang báo cáo vẽ các NH này bằng chấm rỗng.
   - Mọi số về nhóm, tỷ lệ PCA và ngày lãi suất trong trang báo cáo tự tính trong `reports/eda/make_eda_report.py` (khóa `facts`); script in CẢNH BÁO nếu hồ sơ nhóm không còn khớp tên nhóm.
6. **Lãi suất 12 tháng online 15/09/2026** (24hmoney qua `deposit_tiers.read()`, 22 NH; khớp `deposit_daily.csv` lệch 0,017 điểm %): 5,0–7,2%; tương quan với CAR −0,41 [−0,71; 0,02] — không có ý nghĩa với n = 22.
7. **Điểm app vs tài chính**: trong NH mọi |ρ| ≤ 0,12 → chiều độc lập. Điểm app phản ứng với **quy định** (`app_monthly.csv`, `app_events.csv`, gộp 22 app theo số review):
   - Tháng 7/2024 (QĐ 2345/QĐ-NHNN, sinh trắc học cho giao dịch > 10 triệu): điểm 3,24 → 2,45 sao, 1 sao 38% → 56%, 13/16 NH cùng giảm.
   - Tháng 1/2025 (TT 17/2024/TT-NHNN dừng giao dịch online của tài khoản chưa đối chiếu sinh trắc học): 3,20 → 2,67, 12/18 NH cùng giảm.
   - Trung vị giữa các NH theo tháng không thấy rõ hai điểm rơi này vì nhiều app có ít review.
8. **Chính sách**: NH tham gia gói nông nghiệp có tỷ trọng nông nghiệp gấp ~9 lần (chọn lọc, không phải tác động); phơi nhiễm Yagi không đi kèm NPL tăng (ρ −0,30, bỏ NVB).
9. **Mùa vụ trong năm** (thêm 18/09/2026; `season_anova.csv`, `season_profile.csv`, `season_years.csv`, `season_forecast.csv`):
   - ANOVA lồng nhau: quý trong năm > quý > NH-quý. Kiểm định F lấy **quý** làm đơn vị (29–30 quý), vì các NH trong cùng quý chịu chung cú sốc. Biến số dư cuối quý (NPL, nợ nhóm 2, CASA, LDR) xét thay đổi so với quý trước; biến riêng từng quý (tăng trưởng dư nợ trong quý, CIR/ROE/chi phí vốn MAS) xét mức đã trừ trung bình NH; cắt p1/p99.
   - **Có mùa vụ:**
     - NPL giảm ở quý 4 trong 79% NH-quý (trung vị −0,22 điểm), cùng chiều 7/7 năm, rồi tăng lại quý 1; phần mùa vụ 7,8%, p < 0,001.
     - CASA giảm ở quý 1 trong 77% NH-quý; phần mùa vụ 19,4%, p < 0,001.
     - Tăng trưởng dư nợ trong quý: quý 4 cao hơn mức thường của NH 1,5 điểm, quý 3 thấp nhất; p = 0,010.
   - **Yếu hoặc không có:** nợ nhóm 2 yếu (p = 0,043, Kruskal-Wallis 0,064). LDR, CIR, ROE, chi phí vốn theo quý không có (p ≥ 0,22).
   - **Dự báo không mô hình, walk-forward từ 2023-Q1, 286 dự báo tầm 1 quý:** naive có mùa vụ (cộng trung vị thay đổi của đúng quý tới) thắng naive.
     - NPL +6,3% [1,8; 13,6], CASA +9,7% [1,0; 17,6].
     - So với drift vẫn giữ: NPL +6,4%, CASA +9,5% → đây là mùa vụ thật.
     - LDR thắng naive +2,1% nhưng so với drift chỉ +0,3% [−1,0; 2,0] → lợi thế của LDR là xu hướng, không phải mùa vụ.
   - **Hệ quả:** mốc so sánh của mô hình là naive có mùa vụ (NPL, CASA) hoặc drift (LDR); mô hình cần biến "quý trong năm". Mục tiêu TTM không cần.

### EDA định hướng mô hình (`experiments/eda_ml.py`)

`python -m experiments.eda_ml` (~3 phút) → `data/model/eda_ml/*.csv` + `facts.json`; trang báo cáo: `python reports/eda_ml/make_report.py <file_ra.html>`. Khác `eda.py` (câu hỏi nghiệp vụ), file này hỏi những gì bước mô hình cần: phân phối từng biến → biến đổi nào; mục tiêu (tự tương quan, nửa vòng đời, IPS với ngưỡng Monte Carlo, phần chung/riêng của thay đổi, độ nhọn) → dự báo mức hay thay đổi, mốc so sánh, hàm mất mát; đặc trưng ↔ mục tiêu ở tầm 1/2/4 quý (biến theo NH trừ trung bình **quá khứ**; kiểm chéo khối quý có **purge** h quý, TTM thêm 3; spline vs đường thẳng) → mức tín hiệu, tuyến tính hay cây; đặc trưng ↔ đặc trưng (giữa/trong NH, VIF, số chiều) → bỏ trùng; rolloff, giãn nợ, cỡ mẫu; thiếu; xu hướng co cụm (silhouette, Hopkins so với khối Gauss cùng hiệp phương sai); tiêu chí xếp hạng; văn bản review. Hai bẫy đã gặp khi dựng: trừ trung bình cả mẫu của NH làm lộ tương lai (mức đã trừ "biết" NH sẽ quay về đâu); MI k láng giềng coi biến vĩ mô (một giá trị mỗi quý) là phi tuyến vì nó nhận ra quý.

**Cờ trong catalog:** `leak:<mục tiêu>` = quan hệ định nghĩa cùng quý (dùng được khi trễ 1 quý); `ngoại lai` = > 2% ô ngoài [Q1 − 3 IQR, Q3 + 3 IQR]; `tĩnh`, `chung`, `as-of`, `mục tiêu dự báo`.

## Cổng chất lượng dữ liệu (`crawlers/validate.py`)

Chạy tự động ở cuối `build_panel`, hoặc gọi riêng:

```
python -m crawlers.validate                 # báo cáo đầy đủ
python -m crawlers.validate --scope panel   # chỉ phép kiểm chặn được mô hình hóa
python -m crawlers.validate --json          # cho CI
python -m crawlers.validate --quiet         # chỉ in ERROR
```

Mã thoát 1 nếu còn ERROR, nên `python -m crawlers.build_panel && <lệnh huấn luyện>` sẽ dừng lại thay vì học trên dữ liệu hỏng. Bỏ qua cổng bằng `python -m crawlers.build_panel --no-check`.

**Vì sao cần module riêng khi 19 crawler đã có `validate()`.** Mỗi `validate()` kia chỉ nhìn được file của chính nó. Ba loại lỗi đã từng cắn dự án đều nằm ngoài tầm nhìn đó: lỗi đơn vị/dấu im lặng (`financial_long.csv` ghi `unit='%'` nhưng lưu thập phân, COF/NPL-coverage/CIR lưu số âm — không exception nào được ném ra), mâu thuẫn giữa hai nguồn độc lập (một nguồn có thể tự nhất quán hoàn toàn mà vẫn sai), và biến suy dần theo thời gian (crawler mất dần dòng sau mỗi lần chạy).

**Ba mức nghiêm trọng — đây là phần quan trọng nhất.**

| Mức | Nghĩa | Ví dụ đang có |
|---|---|---|
| `ERROR` | Không thể đúng về mặt định nghĩa, hoặc hai nguồn mâu thuẫn **và chưa phân định được** | `high < low`; `open`/`close` lệch khỏi `[low, high]` quá 5%; BID 3 tháng tại quầy 4,45% so với 2,40% ở nguồn kia |
| `WARN` | Cực đoan nhưng **có thể có thật**, hoặc khiếm khuyết nguồn đã phân định | Toàn bộ chuỗi NVB — NPL 35%, ROE −92%, CIR 976% — là số thật của một ngân hàng đang tái cơ cấu (báo chí: NPL 29,76% đầu 2024 → 35,28% quý 2/2024, khớp đúng panel); 54 phiên `open`/`close` lệch dưới 2,5% do nhà cung cấp điều chỉnh một trường |
| `INFO` | Độ phủ và thống kê nền | tripwire xác nhận giả định chuẩn hóa của `build_panel` vẫn đúng |

Nhầm `WARN` thành `ERROR` sẽ khiến người dùng xóa mất dữ liệu thật; nhầm `ERROR` thành `WARN` sẽ khiến lỗi lọt vào mô hình. Vì vậy hai mức này tách nhau bằng **hai bộ ngưỡng riêng** (`HARD_BOUNDS` và `SOFT_BOUNDS`), không bằng một allowlist — allowlist phải sửa tay mỗi lần thêm dữ liệu, còn hai bộ ngưỡng thì không.

**Tripwire cho bẫy đơn vị/dấu.** `RATIO_SHAPE` không phải danh sách lỗi cần sửa — nó ghi lại *hình dạng đã đo* của file ratio (thập phân, phần lớn âm, CAR đa số bằng 0) mà `build_panel` đang dựa vào để chuẩn hóa. Nếu nguồn âm thầm đổi cách lưu, các giả định đó thành sai và tripwire báo `ERROR` ngay. Ngưỡng thang thập phân đặt **riêng cho từng chỉ tiêu**: NPL Coverage thật sự chạy tới 504% (= 5,04 thập phân) nên dùng chung một ngưỡng với NIM sẽ báo sai.

**Hai cái bẫy kỹ thuật đã xử lý, ghi lại để không ai vấp lại:**

- `pandas.merge` **ghép NaN với NaN**. Đối chứng hai file lãi suất mà không lọc `ticker.notna()` trước sẽ sinh **8.218 cặp giả** thay vì 1.274 cặp thật, và mọi thống kê sau đó đều vô nghĩa.
- Lọc cột ngày bằng `"date" in tên_cột` sẽ kéo cả `source_updated_at` vào (chuỗi `updated` có chứa `date`) — cột đó lưu dạng `HH:MM:SS DD/MM/YYYY` nên sinh cảnh báo parse. Dùng `_is_date_column()` khớp theo tên chính xác.

**Hai loại vi phạm OHLC không được gộp chung.** `high < low` là bất khả thi về cấu trúc → luôn `ERROR`. Còn `open`/`close` nằm ngoài `[low, high]` thường là dấu vết nhà cung cấp điều chỉnh một trường mà không điều chỉnh các trường còn lại (close đã điều chỉnh cổ tức còn OHL thì chưa; open lấy từ phiên ATO trong khi high/low lấy từ phiên liên tục) → `WARN`, trừ khi lệch quá `OHLC_MAX_DEVIATION_PERCENT` = 5%. Đo trên kho ngày 10/09/2026: 54 vi phạm, **không cái nào là `high < low`**, lệch trung vị 0,50% và lớn nhất 2,42%; vi phạm `open` dồn hết ở file chỉ số, vi phạm `close` dồn hết ở file cổ phiếu — hai dấu vân khác nhau của cùng một loại lỗi nhà cung cấp.

**`ZERO_MEANS_MISSING` — số 0 dùng làm ký hiệu thiếu.** Nguy hiểm hơn mẫu bằng 0, vì 0 trông hoàn toàn hợp lệ và trong mọi phép min-max lại rơi đúng vào đầu mút "tốt nhất" của thang đo. Nguồn MAS ghi `0` thay vì để trống khi ngân hàng **chưa niêm yết**: 68 ô `pe = 0` và 68 ô `pb = 0`, trong khi `eps_vnd` và `bvps_vnd` của chính những ô đó vẫn bình thường (11.000–32.000 đồng). Đã đối chiếu với phiên giao dịch đầu tiên trong `data/price` — **toàn bộ 68 ô đều nằm trước ngày lên sàn, không ô nào sau đó**: BVB đến 2020-Q2 (lên sàn 09/07/2020), SSB đến 2020-Q4 (24/03/2021), TCB và TPB chỉ 2018-Q1. `beta = 0` cùng bản chất: 68 ô trước niêm yết cộng 26 ô ngay sau khi lên sàn, khi chuỗi giá còn quá ngắn để ước lượng. `build_panel` đổi cả ba cột này thành `NaN`.

`dividend_yield` **cố ý không** nằm trong danh sách: 508 trong 576 ô bằng 0 của nó nằm sau ngày niêm yết và là sự thật — ngân hàng không trả cổ tức tiền mặt. Thêm nó vào sẽ xoá mất một sự thật thay vì vạch ra một lỗi.

**`XSOURCE_RESOLVED` — ô mâu thuẫn đã phân định bằng bằng chứng.** Khác với ngưỡng miền giá trị, mâu thuẫn giữa hai nguồn không có luật chung nào giải được: phải đối chiếu từng ô. Bảng này ghi ô nào đã phân định, chọn nguồn nào, và **căn cứ là gì**; ô đã phân định hạ xuống `WARN` kèm lý do, ô chưa phân định vẫn là `ERROR`. Bỏ một mục khỏi bảng thì ô đó quay lại `ERROR`.

**Năm phép kiểm thêm ngày 15/09/2026, sau khi đối chiếu với web ngân hàng và BCTC.** Bốn phép đầu bắt lỗi nguồn; `deposit.tier` canh bảng ghi đè bậc lãi suất. Các loại lỗi dưới đây đều có giá trị nằm gọn trong miền hợp lệ, nên ngưỡng miền giá trị không bao giờ thấy. Trước khi sửa dữ liệu, cả bốn đã được chạy trên kho cũ: bắt đúng và đủ các ô lỗi đã biết, không báo nhầm ô nào khác.

| Phép kiểm | Mức | Bắt được gì |
|---|---|---|
| `vci.stale` | ERROR | Dòng ratio có ≥ 3/4 tỷ lệ (NPL, bao phủ, LDR, NIM) trùng đúng quý trước. Là tripwire cho lớp sửa `vci_ratio`: trên dữ liệu cũ bắt 20 NH-quý 2021-Q4 |
| `note.identity` | ERROR | Tiền gửi VND lớn hơn tổng tiền gửi theo loại tiền. Dung sai phải sát 0: BAB 2022-Q1 chỉ vượt 0,12%, đúng bằng phần ngoại tệ bị cộng nhầm |
| `panel.jump` | WARN | Tỷ trọng cơ cấu (tiền gửi VND, CASA, kỳ hạn cho vay) nhảy > 10 điểm rồi quay về; quý cuối thì so với 4 quý trước. Không áp cho bao phủ nợ xấu, vì cột đó nhảy quý 2/quý 4 thật |
| `deposit.cap` | ERROR/WARN | Lãi suất kỳ hạn 1–<6 tháng vượt trần NHNN tại ngày của bảng (6,0 → 5,5 → 5,0 → 4,75%). Vượt ≤ 0,05 điểm là 24hmoney làm tròn 4,75 thành 4,8 (WARN); vượt hơn là ERROR, trừ ô đã xem xét trong `DEPOSIT_CAP_RESOLVED` |
| `deposit.tier` | WARN | Bảng ghi đè bậc lãi suất (`deposit_tiers.TIER_OVERRIDES`) không còn khớp số 24hmoney ngày mới nhất → ngân hàng đã đổi biểu, phải đối chiếu lại |

**`vnstock_note.CORRECTIONS` — ô VCI ghi sai, đã đối chiếu BCTC gốc.**
- Chỉ áp khi giá trị thô vẫn đúng bằng số sai đã ghi. Nếu VCI sửa nguồn thì bỏ qua và ghi log, không ghi đè số mới.
- **STB 2026-Q2**: thuyết minh 9 cho tổng tiền gửi 647.939.224 triệu, vàng và ngoại tệ 16.840.024 → tỷ trọng VND 97,40%. VCI ghi 2,67%.
- **BAB 2022-Q1**: thuyết minh 15 cho ngoại tệ 109.456 triệu → VND 94.921.961 (99,88%). VCI ghi 95.140.873 = tổng **cộng** ngoại tệ.
- **PGB 2022-Q3**: VCI ghi 49,46%, kẹp giữa hai quý ~98,6%. BCTC không có trên Vietstock nên lấy bản đính chính do PGBank đăng trên `pgbank.com.vn/nha-dau-tu/bao-cao-tai-chinh` (trang render bằng Vue, link nằm trong dữ liệu component). Thuyết minh 18 cho tổng 28.937.613 triệu, ngoại tệ và vàng 403.223 → 98,61%. Lỗi này do `panel.jump` bắt được, không phải tìm tay.

**Đã kiểm bằng bơm lỗi giả**: 15 lỗi tổng hợp (trùng khóa, lưới khuyết, dư nợ vượt tổng tài sản, tiền gửi âm, LDR sai, tỷ trọng kỳ hạn không cộng 100%, giá trị ngoài miền, mẫu bằng 0, tụt độ phủ, mất cột, mất cột khóa, `high < low`, lệch OHLC quá ngưỡng) — bắt được **15/15**, không crash lần nào, và không báo sai trên panel thật.

## Cách chạy

`run_daily_crawl.py` chạy các crawler hàng ngày (`deposit_rates`, `deposit_24hmoney`, `deposit_crosscheck`, `loan_rates`, `price`, `market_index` — thêm từ 01/10/2026) rồi xuất lại `data/serving/`; lỗi của cái này không chặn cái kia:

```
.venv\Scripts\python.exe run_daily_crawl.py
```

Chạy tự động bằng Windows Task Scheduler (khuyến nghị hơn vòng lặp `schedule` vì không cần giữ terminal mở liên tục 2+ tháng):

```
schtasks /create /tn "KLTN_DailyCrawl" /tr "cmd /c cd /d D:\KLTN && .venv\Scripts\python.exe run_daily_crawl.py >> crawl_task.log 2>&1" /sc daily /st 15:30 /it /f
```

**Đặt lịch SAU 15:00** (giờ đóng cửa). `crawlers/price.py` lưu đúng những gì thị trường đang hiển thị tại thời điểm chạy, nên chạy buổi sáng sẽ ghi vào một phiên chưa kết thúc — đó chính là cách các dòng 2026-08-20 bị lưu số giữa phiên. Chạy muộn cũng lấy được lãi suất tiết kiệm sau khi các ngân hàng cập nhật trong ngày. Chạy sớm không mất dữ liệu: `price` làm mới cửa sổ 7 ngày nên lần chạy sau sẽ tự sửa lại.

`cmd /c cd /d D:\KLTN` là **bắt buộc**, không phải trang trí: mọi crawler dùng đường dẫn tương đối (`data/macro`, `data/price`…), chạy thẳng `python.exe run_daily_crawl.py` sẽ lấy thư mục làm việc mặc định của Task Scheduler (`C:\Windows\system32`) và ghi dữ liệu sai chỗ. `/it` = chỉ chạy khi đã đăng nhập, nhờ đó **không phải lưu mật khẩu**.

Đổi giờ task đang có — phải truyền lại `/it`, nếu không `schtasks` sẽ hỏi mật khẩu:

```
schtasks /change /tn "KLTN_DailyCrawl" /st 15:30 /it
```

Kiểm tra task đã tạo đúng: `schtasks /query /tn "KLTN_DailyCrawl"`. Chạy thử ngay: `schtasks /run /tn "KLTN_DailyCrawl"`. Xóa nếu cần: `schtasks /delete /tn "KLTN_DailyCrawl" /f`.

Chạy riêng từng phần khi cần:

```
.venv\Scripts\python.exe -m crawlers.price
```

Các crawler không chạy hàng ngày (nguồn cập nhật theo tháng/năm/sự kiện):

```
python -m crawlers.cpi_nso            # CPI, hàng tháng
python -m crawlers.cpi_vneconomy      # bù ô CPI còn trống
python -m crawlers.lending_rates_bank # lãi suất cho vay bình quân theo từng NH, hàng tháng
python -m crawlers.credit             # tín dụng theo NH — dựng lại từ BCTC, không gọi mạng
python -m crawlers.policy_rate        # lãi suất điều hành SBV, bảng chép tay
python -m crawlers.credit_growth      # tăng trưởng tín dụng hệ thống, bảng chép tay
python -m crawlers.repricing_gap      # khe hở lãi suất: dựng lại bảng công việc + kiểm (giữ ô nhập tay)
python -m crawlers.repricing_gap --check           # chỉ kiểm, thoát mã 1 nếu có lỗi
python -m crawlers.repricing_gap --ratios 2025-Q4  # bảng tỷ lệ cho TOPSIS
python -m crawlers.repricing_gap --them-ky 2024-Q4 # thêm 22 dòng cho một quý (từ chối quý chưa kết thúc)
```

Đánh giá app (`crawlers/app_reviews.py`) — lần đầu phải backfill, sau đó chạy tăng dần:

```
python -m crawlers.app_reviews --backfill --max-reviews 200000   # lần đầu, ~45 phút
python -m crawlers.app_reviews                                   # các lần sau, chỉ lấy phần mới
python -m crawlers.app_reviews --validate
python -m crawlers.app_reviews --coverage
python -m crawlers.app_reviews --monthly     # dựng lại panel bank-month, không gọi mạng
python -m crawlers.app_reviews --discover    # dò lại app_id trên Play Store, chỉ in ra
```

Mạng lưới (`crawlers/branch_network.py`) — quét lại toàn bộ mỗi lần chạy, khoảng 5 phút:

```
python -m crawlers.branch_network              # quét 34 tỉnh, dựng branch_points + branch_by_province
python -m crawlers.branch_network --validate   # gồm cả 3 phép đối chiếu chéo
python -m crawlers.branch_network --summary    # bảng mạng lưới theo ngân hàng
python -m crawlers.branch_network --unmapped   # nhãn chưa map được, để mở rộng NAME_PATTERNS
python -m crawlers.branch_network --cross-check # chỉ phép đối chiếu Harvard
python -m crawlers.branch_network --tpb        # dựng lại bản TPBank tự công bố
```

`--refresh-provinces` lấy lại danh sách tỉnh từ OSM (cần khi có thay đổi địa giới). Overpass có lúc trả HTTP 500 — module tự chuyển sang endpoint dự phòng rồi mới retry, đã gặp 4/34 tỉnh trong lần chạy đầu và cả 4 đều qua ở lần thử lại.

`--tickers VCB,BID` giới hạn ngân hàng; `--roles retail,wallet,successor` mở rộng ngoài app bán lẻ mặc định. Chạy tăng dần dừng khi chạm mốc cũ trừ `OVERLAP_DAYS` (3 ngày) nên vẫn bắt được đánh giá bị sửa lại. **`--discover` nên chạy lại trước khi nộp**: ngân hàng đổi app thì `app_id` cũ vẫn tải được nhưng chuỗi sẽ chết dần mà không báo lỗi.

`crawlers.credit_growth --check-sources` mở lại cả 8 trích dẫn để kiểm link còn sống và trang còn chứa đúng con số (cần mạng, thoát mã 1 nếu có link hỏng) — nên chạy trước khi nộp luận văn.

Tất cả đều idempotent. Các module có `--validate` in ra bộ kiểm định đã trích trong tài liệu này: `credit`, `credit_growth`, `lending_rates_bank` (thêm `--coverage` cho module cuối), `cost_of_funds`, `lending_yield`, `deposit_rates`, `app_reviews` (thêm `--coverage`), và `branch_network` (thêm `--summary`, `--unmapped`, `--cross-check`); `loan_rates` dùng `--selfcheck`.

## Trực quan hóa bằng Power BI

`data/powerbi/` là **bản chụp cũ, không còn dựng lại được**. Script `export_powerbi.py` từng gộp `data/` thành mô hình sao đã bị xoá khỏi dự án. Thư mục `data/powerbi/` vẫn giữ lại để tham khảo nhưng đang trôi dần khỏi nguồn: `fact_price_daily` thiếu 66 dòng so với `price/`, `fact_deposit_rate` giữ 12.502 dòng 24hmoney trong khi nguồn đã lên 14.892, và không có bảng nào cho panel mới ở `data/model/`.

**Đừng dùng `data/powerbi/` làm đầu vào mô hình.** File dùng cho mô hình là `data/model/bank_panel_quarterly.csv`.

Mỗi lần chạy in ra một bộ soát khóa: bảng fact nào có `bank_key` không tồn tại bên `dim_bank`, hoặc ngày nằm ngoài `dim_date`. **Power BI không báo lỗi khi quan hệ hỏng** — nó lặng lẽ dồn các dòng không khớp vào một thành viên blank và biểu đồ vẫn vẽ ra, nên phải soát ở bước export.

### Các bảng xuất ra

| Bảng | Grain | Dòng | Cột ngày |
|---|---|---|---|
| `dim_bank` | 1 ngân hàng | 53 | — |
| `dim_date` | 1 ngày, 2012-01-01 → 2026-12-31 | 5.479 | `date` |
| `dim_metric` | 1 chỉ tiêu BCTC | 40 | — |
| `dim_province` | 1 tỉnh/thành | 34 | — |
| `fact_deposit_rate` | ngày × NH × kỳ hạn × kênh × **nguồn** | 17.719 | `date` |
| `fact_lending_rate_monthly` | tháng × NH | 375 | `month_date` |
| `fact_bank_quarterly` | quý × NH | 748 | `period_end` |
| `fact_price_daily` | ngày × NH | 47.206 | `date` |
| `fact_financial` | quý/năm × NH × chỉ tiêu | 35.556 | `period_end` |
| `fact_app_review_monthly` | tháng × NH | 2.093 | `month_date` |
| `fact_app_review` | 1 đánh giá | 532.007 | `date` |
| `fact_branch_by_province` | tỉnh × NH | 338 | — |
| `fact_branch_point` | 1 điểm giao dịch/ATM | 5.904 | — |
| `fact_macro_monthly` | 1 tháng (không có NH) | 109 | `month_date` |
| `fact_credit_growth_yearly` | 1 năm | 8 | `year_end` |
| `fact_policy_rate_event` | 1 sự kiện × loại lãi suất | 33 | `date_effective` |
| `meta_source` | truy nguồn, không dùng để vẽ | 233 | — |

Bốn bảng được **gộp mới**, không có sẵn trong `data/`:

- `fact_bank_quarterly` = `bank_credit_quarterly` + `bank_cost_of_funds_quarterly` + `bank_earning_asset_yield_quarterly`. Cả ba cùng khóa `(period, ticker)` và cùng dựng từ một bộ BCTC nên một bảng rộng dễ dùng hơn ba bảng nối chéo. Thêm cột `*_ty_vnd` (chia 1e9) để nhãn trục đọc được — số VND thô làm trục dài loằng ngoằng.
- `fact_deposit_rate` = cả ba nguồn lãi suất tiền gửi chồng lên nhau, phân biệt bằng cột `source`. Xem cảnh báo bên dưới.
- `fact_price_daily` = 22 file `price/*.csv`, `ticker` lấy từ tên file. Thêm `turnover_vnd = close × volume × 1000` (giá vnstock tính bằng nghìn đồng).
- `fact_macro_monthly` = CPI + lãi suất điều hành + bình quân ngành trên cùng trục tháng. `policy_rate.csv` là event log 11 sự kiện, ở đây trải ra theo tháng và forward-fill, vì biểu đồ đường cần giá trị của **mọi** tháng chứ không chỉ tháng có thay đổi.

### Nạp vào Power BI Desktop

1. **Trước khi nạp**: File → Options and settings → Options → **Current File → Data Load** → bỏ tick **Autodetect new relationships after data is loaded**. Nhiều bảng có chung tên cột (`ticker`, `province`, `month`, `period`) nên tính năng này sẽ tự nối lung tung giữa các bảng fact, gỡ ra mất công hơn tự tạo.
2. **Home → Excel workbook** → `D:\KLTN\data\powerbi\KLTN_PowerBI.xlsx`. Trong Navigator tick **Select multiple items** rồi tick cả 16 sheet → **Load** (không cần Transform Data, kiểu dữ liệu đã sạch sẵn). Cần bảng đánh giá chi tiết thì nạp thêm: **Get data → Text/CSV** → `fact_app_review.csv` (532k dòng, không nằm trong file Excel).
   - Dùng CSV cho tất cả cũng được — **Get data → Text/CSV**, lặp lại cho từng file. Đừng dùng **Folder** connector: nó gộp các file cùng khuôn, mà 16 bảng ở đây khác khuôn nhau hoàn toàn.
3. Tất cả CSV ghi bằng **utf-8-sig**, ngày dạng **ISO `YYYY-MM-DD`**, thập phân dùng **dấu chấm**. Nếu Power BI đọc `4.5` thành `45`, vào **File → Options → Current File → Regional Settings** đặt **English (United States)** rồi refresh.
4. **Model view** → tạo quan hệ **một-nhiều**, hướng lọc **một chiều**, từ dim sang fact:
   - `dim_bank[bank_key]` → cột `bank_key` của 9 bảng: `fact_deposit_rate`, `fact_lending_rate_monthly`, `fact_bank_quarterly`, `fact_price_daily`, `fact_financial`, `fact_app_review_monthly`, `fact_app_review`, `fact_branch_by_province`, `fact_branch_point`.
   - `dim_date[date]` → cột ngày ở cột cuối bảng trên: `date` / `month_date` / `period_end` / `year_end` / `date_effective`.
   - `dim_metric[metric_id]` → `fact_financial[metric_id]`.
   - `dim_province[province]` → `fact_branch_by_province[province]` và `fact_branch_point[province]`.
5. Chọn `dim_date` → **Table tools → Mark as date table** → cột `date`. Không làm bước này thì time intelligence (`SAMEPERIODLASTYEAR`, `DATESYTD`…) trả sai.
6. Ẩn mọi cột `bank_key`, `ticker`, `metric_id` ở phía **fact** (chuột phải → Hide in report view) để khi kéo thả chỉ còn một chỗ chọn ngân hàng.

### Bốn cái bẫy khi vẽ

1. **`fact_deposit_rate` chồng ba nguồn.** Kéo `rate_percent` vào biểu đồ mà không lọc `source` thì Power BI lấy trung bình của cả laisuattietkiem + 24hmoney + CafeF — ba nguồn đo cùng một ô và lệch nhau tới 2,1 điểm (xem mục "Ba nguồn, cùng một ô"). **Luôn đặt `source` vào slicer.** Muốn một chuỗi liền mạch thì dùng `24hmoney` (đủ 22/22 mã, lùi về 2023); `laisuattietkiem` chỉ có 17/22 mã và bắt đầu từ 2026-08.
2. **`fact_financial` có cả `freq = quarter` và `freq = year`.** Kỳ năm có `period_end` là 31/12, trùng với quý 4 — cộng mà không lọc `freq` là đếm hai lần. Đặt `freq` vào slicer, hoặc lọc sẵn ở cấp visual.
3. **`fact_bank_quarterly` và `fact_financial` cùng dựng từ một bộ BCTC.** Đừng cộng chỉ tiêu từ cả hai vào một biểu đồ.
4. **`dim_bank` có 53 dòng chứ không phải 22.** 31 dòng còn lại là ngân hàng ngoài sàn (Agribank, PVComBank, HSBC…) xuất hiện trong các bảng lãi suất, cộng một dòng `UNKNOWN` gom 2.354 điểm OSM không gắn thương hiệu. **Lọc `is_listed = True`** cho mọi biểu đồ về 22 mã của khóa luận.

### Dựng biểu đồ

Tạo trước 6 measure (Report view → **Modeling → New measure**), dán từng cái một. Đặt hết vào một bảng cho gọn.

```dax
LS tiền gửi gần nhất =
LASTNONBLANKVALUE( dim_date[date], AVERAGE( fact_deposit_rate[rate_percent] ) )

LS cho vay gần nhất =
LASTNONBLANKVALUE( dim_date[date], AVERAGE( fact_lending_rate_monthly[lending_avg_percent] ) )

Tháng công bố = MAX( fact_lending_rate_monthly[month] )

Chênh lệch lãi (điểm) =
AVERAGE( fact_bank_quarterly[earning_asset_yield_ttm_percent] )
    - AVERAGE( fact_bank_quarterly[cof_ttm_percent] )

Điểm app TB =
VAR Dùng = FILTER( fact_app_review_monthly, fact_app_review_monthly[usable] = TRUE() )
RETURN
DIVIDE(
    SUMX( Dùng, fact_app_review_monthly[n_reviews] * fact_app_review_monthly[mean_score] ),
    SUMX( Dùng, fact_app_review_monthly[n_reviews] )
)

Số điểm giao dịch = SUM( fact_branch_by_province[n_bank] )
```

`LASTNONBLANKVALUE` lấy giá trị ở **ngày gần nhất mà ngân hàng đó có số liệu**, không phải ngày gần nhất của cả bảng — đúng thứ cần khi độ đầy lệch nhau (VPB chỉ có 1 tháng lãi suất cho vay, BID có 15). Đổi lại, các cột trong cùng một biểu đồ có thể đến từ những tháng khác nhau, nên **luôn kèm measure `Tháng công bố`** vào tooltip để người đọc biết.

`Điểm app TB` có trọng số theo `n_reviews`: lấy trung bình của các `mean_score` hàng tháng sẽ cho tháng có 3 đánh giá cùng sức nặng với tháng có 3.000.

`Chênh lệch lãi (điểm)` là **chênh lệch gộp, KHÔNG phải NIM** — đừng ghi nhầm nhãn trong luận văn. Hiệu `lợi suất tài sản − COF` luôn thấp hơn NIM bình quân 0,44 điểm vì quan hệ thật là `lợi suất = NIM + COF × (IBL/tài sản sinh lời)`. Cần NIM thì dùng cột `nim_ttm_percent` có sẵn trong `fact_bank_quarterly`.

#### Biểu đồ đầu tiên, từng bước

Xếp hạng lãi suất tiết kiệm — chính là câu hỏi trung tâm của khóa luận:

1. **Clustered bar chart**. Y axis: `dim_bank[bank_name]`. X axis: measure `LS tiền gửi gần nhất`.
2. Filters pane → kéo `dim_bank[is_listed]` vào **Filters on this page**, chọn `True`. Bỏ bước này thì 31 ngân hàng ngoài sàn chen vào.
3. Thêm 3 slicer, **bắt buộc cả ba**: `fact_deposit_rate[source]`, `fact_deposit_rate[term_months]`, `fact_deposit_rate[channel]`. Đặt slicer `source` về **Single select** (Format → Slicer settings → Selection).
4. Chọn `source = laisuattietkiem`, `term_months = 12`, `channel = online`.
5. Menu `...` góc biểu đồ → **Sort axis → LS tiền gửi gần nhất → Descending**.

Thiếu bước 3 thì Power BI lấy trung bình cộng của cả ba nguồn × 9 kỳ hạn × 2 kênh — ra một con số vô nghĩa mà biểu đồ vẫn vẽ đẹp.

#### Các biểu đồ còn lại

| Câu hỏi | Visual | Trường | Bộ lọc bắt buộc |
|---|---|---|---|
| Ngân hàng nào trả cao nhất, ở kỳ hạn nào? | **Matrix** + nền màu gradient | Rows `dim_bank[bank_name]`, Columns `fact_deposit_rate[term_months]`, Values `LS tiền gửi gần nhất` | `source`, `channel`, `is_listed` |
| Lãi suất tiết kiệm diễn biến ra sao? | **Line chart**, trục X **Continuous** | X `dim_date[date]`, Y `Average of rate_percent`, Legend `bank_name` | `source = 24hmoney`, `term_months`, `channel`, `is_listed` |
| Lãi suất huy động so với lãi suất điều hành? | **Line chart** 2 trục | X `dim_date[month_start]`, Y `fact_macro_monthly[policy_tai_cap_von_percent]` + `cpi_yoy_percent` | không cần — bảng này không có chiều ngân hàng |
| Vay ở đâu rẻ nhất? | **Clustered bar** | Y `bank_name`, X `LS cho vay gần nhất`, Tooltip `Tháng công bố` | `is_listed` |
| Ngân hàng nào ăn dày nhất? | **Scatter** | X `LS cho vay gần nhất`, Y `Average of spread_vs_deposit_point`, Details `bank_name` | `is_listed` |
| Phía cho vay từ 2018 (chuỗi dài) | **Line chart** | X `dim_date[quarter_label]`, Y `Average of earning_asset_yield_ttm_percent`, Legend `bank_name` | `is_listed` |
| Rủi ro và sinh lời đi cùng nhau? | **Scatter** + **Play axis** | X `Average of npl_percent`, Y `Average of nim_ttm_percent`, Size `Sum of loans_ty_vnd`, Details `bank_name`, Play `dim_date[quarter_label]` | `is_listed` |
| Chi phí vốn so với lợi suất tài sản | **Line and clustered column** — đừng dùng bản *stacked*, COF không cộng với lợi suất | X `quarter_label`, Column **`Average of`** `cof_ttm_percent` + `earning_asset_yield_ttm_percent`, Line `Chênh lệch lãi (điểm)` | 1 ngân hàng (slicer, Single select) |
| Mạng lưới phủ tới đâu? | **Map** (bong bóng) | Latitude `fact_branch_point[lat]`, Longitude `[lon]`, Legend `bank_name`, Size `Count of osm_id` | `is_listed` — xem ghi chú bên dưới |
| Ngân hàng nào nhiều điểm nhất? | **Stacked bar** | Y `bank_name`, X `Số điểm giao dịch` + `Sum of n_atm` | `is_listed` |
| App ngân hàng số tốt tới đâu? | **Line chart** | X `dim_date[month_start]`, Y `Điểm app TB`, Legend `bank_name` | `is_listed` (measure đã tự lọc `usable`) |
| Vì sao điểm app tụt tháng đó? | **Table**, đặt làm **Drill-through** | `fact_app_review[date]`, `[score]`, `[app_version]`, `[content]` | drill-through theo `bank_name` |

#### Độ phủ quyết định loại biểu đồ

Bốn chỗ mà chọn sai loại biểu đồ sẽ ra hình sai chứ không phải hình xấu:

1. **Lãi suất tiền gửi không phải chuỗi ngày liền mạch.** `24hmoney` chỉ có **27 ngày** rải từ 2023-01-27 đến 2026-09-03 (ảnh chụp qua web.archive.org, không phải cào hàng ngày); `laisuattietkiem` có 12 ngày từ 2026-08-21; `cafef` có 58 ngày nhưng **chỉ đúng ô 12 tháng**. Nên để trục X là **Continuous** — để **Categorical** thì 27 mốc cách nhau hàng tháng bị vẽ đều nhau, nhìn như dữ liệu liên tục. Muốn so sánh giữa các ngân hàng thì dùng biểu đồ cột tại một thời điểm, đừng dùng đường.
2. **Đừng vẽ CAR.** `car_percent` chỉ có **88/748 dòng (11,8%)**. Biểu đồ sẽ ra vài cột lẻ trông như các ngân hàng khác có CAR bằng 0. Các cột dùng được: `loans_ty_vnd`/`deposits_ty_vnd` (100%), `npl_percent`/`ldr_percent`/`nim_percent` (~87%), `cof_ttm_percent`/`earning_asset_yield_ttm_percent` (72,2%).
3. **Lãi suất cho vay công bố là biểu đồ cột, không phải đường.** Mỗi ngân hàng chỉ có 1–15 tháng (VPB 1, HDB 2, NVB 3 — trong khi BID/ACB/LPB có 15). Vẽ đường thì phần lớn ngân hàng thành một chấm rời. Cần chuỗi dài để dự báo thì dùng `earning_asset_yield_ttm_percent` (2018-Q1 trở đi) và nhớ nó **không phải** lãi suất cho vay.
4. **Bản đồ dùng lat/lon, đừng dùng tên tỉnh.** `dim_province` là 34 tỉnh **sau sáp nhập 2025**, kèm tiền tố `Thành phố`/`Tỉnh` và đủ dấu tiếng Việt — Bing geocoding của Filled map hay trả sai hoặc bỏ trống. `fact_branch_point` có **lat/lon đủ 5.904/5.904 dòng** nên bản đồ bong bóng không cần geocode. Chọn cột `lat` → **Column tools → Data category → Latitude** (và `lon` → Longitude), đặt Summarization = **Don't summarize**. Lọc `is_listed = True` để bỏ **2.354 điểm `UNKNOWN`** — OSM không gắn thương hiệu cho chúng, để nguyên thì chúng át hết 3.550 điểm của 22 ngân hàng.

Nếu Map bị chặn: **File → Options → Global → Security → Map and filled map visuals**.

### Chỗ khớp tên còn chưa sạch

22 mã niêm yết gộp bằng `ticker` nên chắc chắn không trùng — kể cả khi nguồn bỏ trống ô ticker (24hmoney bỏ trống 3.844 dòng, CafeF 468 dòng), `backfill_ticker()` tra ngược tên → ticker trong chính bảng đó nên `HDBank`, `SeABank`, `PGBank`, `NCB`, `BVBank` vẫn về đúng một thành viên. Tên hiển thị lấy theo **ngày mới nhất**, nên bắt được các vụ đổi tên (BVB từng là `VietCapitalBank`, LPB từng là `LienVietPostBank`).

Nhóm **ngoài** 22 mã thì không có khóa chung nào để gộp tự động mà không đoán: các nguồn có khi chỉ ghi chữ cái đầu. Còn 4 cặp gần chắc là trùng — `ABBANK`/`An Binh Bank`, `KLB`/`Kiên Long Bank`, `IVB`/`Indovina`, `SGB`/`Saigonbank`. Chưa gộp vì việc gộp cần một bảng ánh xạ chép tay, mà nhóm này nằm ngoài phạm vi khóa luận. Lọc `is_listed = True` là hết ảnh hưởng; nếu cần dùng nhóm ngoài sàn thì phải xử lý 4 cặp này trước.

## Giới hạn đã biết (để dùng cho chương phương pháp luận / thu thập dữ liệu của khóa luận)

1. **Lãi suất vay theo từng ngân hàng**: ~~không có nguồn công khai đáng tin cậy~~ — **đã giải quyết một phần**, xem `data/interest_rates/bank_lending_rates_monthly.csv`. Từ Công điện 18/CĐ-TTg (05/03/2024) mỗi NH phải tự công bố lãi suất cho vay bình quân hàng tháng. Ràng buộc còn lại là **độ dài và độ đầy**: 19 tháng liên tục (2025-01 → 2026-07, không thiếu tháng nào sau khi đọc được bảng "công bố gần nhất" theo từng dòng), nhưng **chỉ 14/19 tháng là khảo sát tháng thật** (`coverage().dung_duoc`) — 4 tháng còn lại toàn dòng cắt ngang, 1 tháng chỉ có 1 NH. Độ đầy theo NH cũng rất lệch: mỗi NH có từ 1 đến 15 tháng, **VPB chỉ 1 tháng** (2025-10, 8,01%). Đây là giới hạn của nguồn chứ không phải của cách cào — VPB chỉ xuất hiện trong 1 trên 15 bảng gốc. Đủ để xếp hạng tại một thời điểm, **chưa đủ để dự báo chuỗi thời gian theo từng NH**.
   - Bình quân ngành (SBV) vẫn giữ nguyên vai trò cũ: **giống nhau ở mọi ngân hàng** tại cùng thời điểm, nên chỉ dùng như biến vĩ mô chung, không đóng góp cho TOPSIS/AHP. Giờ nó thêm một việc nữa là **mốc đối chiếu** cho chuỗi theo từng NH (khớp 14/15 tháng).
   - **2024-03 → 2024-12 trống**: các NH đã công bố từ 03/2024 nhưng báo chí khi đó đăng dạng văn xuôi/ảnh infographic, không có bảng HTML để đọc máy. Muốn lùi về 2024 thì phải nhập tay (đã kiểm cạn — xem mục schema).
   - **Trước 03/2024 thì KHÔNG PHẢI vấn đề crawl, mà là số liệu không tồn tại.** Nghĩa vụ công bố lãi suất cho vay bình quân do **Công điện 18/CĐ-TTg ngày 05/03/2024** tạo ra; trước đó không ngân hàng nào công bố chỉ tiêu này. Đã kiểm bằng cách quét toàn bộ sitemap VietnamNet **74 tháng 2018-01 → 2024-02**: chỉ **199 bài** có slug liên quan lãi suất cho vay trong cả 6 năm (2018: 12 bài/năm, 2019: 30, 2020: 29, 2021: 42, 2022: 24) so với **1.082 bài trong 11 tháng** ngay sau Công điện — và mở hết 199 bài (0 lỗi mạng) thì **không có lấy một bảng lãi suất cho vay theo từng ngân hàng nào**. Đúng 1 bảng lọt bộ lọc hình dạng, và nó là bảng *dư nợ + thu nhập lãi cho vay* tính bằng **nghìn tỷ đồng**, không phải %. Chênh lệch ~50 lần về mật độ tin bài chính là dấu vết của việc trước 2024 không có gì để đưa tin.
   - *Ghi chú kỹ thuật rút ra từ đúng bài đó*: **thu nhập lãi cho vay khách hàng theo từng NH có tồn tại** — nằm trong thuyết minh BCTC. Nếu có nó thì tính được **lãi suất cho vay thực thu đúng nghĩa** (`thu lãi cho vay / dư nợ bình quân`), sạch hơn hẳn lợi suất tài sản sinh lời. Nhưng vnstock chỉ phơi ra `IS_NET_INTEREST_INCOME` (**thuần**), nên muốn có thì phải đọc PDF thuyết minh — cùng lý do đã bỏ qua ở giới hạn 6.
   - **Hệ quả cho luận văn**: chuỗi phía cho vay muốn lùi về 2018 thì bắt buộc phải **suy ra từ BCTC** — đó là `data/interest_rates/bank_earning_asset_yield_quarterly.csv`. Nhưng phải nói rõ nó đo **lợi suất tài sản sinh lời**, không phải lãi suất cho vay khách hàng.

1b. **Tăng trưởng tín dụng toàn hệ thống**: **đã có ở mức theo năm** — `data/macro/credit_growth.csv`, 8 năm 2018-2025, mỗi dòng kèm ngày chốt + cơ quan công bố + `source_url`. **Chỉ theo năm, không theo quý** (lý do ở mục schema). Không tự động hoá được: NSO đã bỏ mục ngân hàng khỏi báo cáo tháng (bản 07/2026 không nhắc "tín dụng" lần nào), sbv.gov.vn thì bị WAF chặn, báo chí đưa rời rạc không thành bảng — nên đây là bảng chép tay như `policy_rate.py`. Quan trọng hơn cả: đây là **một chuỗi vĩ mô giống hệt nhau ở mọi ngân hàng**, nên cùng loại hạn chế với bình quân ngành — chỉ dùng được làm biến ngoại sinh cho LSTM, không dùng được cho xếp hạng. Thứ dùng được cho xếp hạng là **tăng trưởng tín dụng theo từng NH** trong `data/credit/bank_credit_quarterly.csv` (660 quan sát theo quý).
   - *Cảnh báo*: các bảng "tăng trưởng tín dụng theo quý 2018-2024" trôi nổi trên mạng đã được kiểm và **có sai số thật** (2019 cả năm là 13,65% chứ không phải 13,89%; 2024 là **15,08%** chứ không phải 14,05%; 2021-Q1 là 2,93% chứ không phải 1,47%). Sai rải rác, không theo quy luật nào. Ngoài ra NHNN chốt số ở những ngày khác nhau (21/3, 24/3, 29/9, 30/6…) và NHNN vs Tổng cục Thống kê không khớp nhau (2024-Q3: 9,00% vs 8,53%), nên mỗi ô bắt buộc phải kèm **ngày chốt + cơ quan công bố**.

1c. **Phân loại nợ nhóm 1-5**: không có. vnstock chỉ cho NPL tổng. Chi tiết nhóm nợ **có thật** trong Thuyết minh 9.1 của BCTC, và **bóc được sạch khi PDF có lớp text** — đã kiểm. Nhưng phần lớn ngân hàng phát hành bản scan nên phải OCR; xem khảo sát đầy đủ ở mục 6.
2. **Lãi suất tiết kiệm niêm yết theo ngân hàng gần như không có lịch sử** — *đã gỡ được một phần, 03/09/2026*. `deposit_daily.csv` vẫn chỉ tích lũy từ 2026-08-21, và Wayback vẫn **không có snapshot nào** của `laisuattietkiem.vn` (đã kiểm cả CDX API lẫn availability API). **Nhưng chưa ai kiểm 24hmoney.vn — và nó có**: 39 snapshot HTTP 200 của `/lai-suat-gui-ngan-hang`, cho ra **27 bảng phân biệt trải 2023-01-27 → 2026-09-03**, đầy đủ 7 kỳ hạn x 2 kênh x **22/22 ticker**, nằm ở `deposit_24hmoney_daily.csv`.
   - **Đây KHÔNG phải chuỗi ngày.** 27 điểm trong 3,5 năm, thưa và không đều (~mỗi quý một bảng, có quãng trống 4 tháng). Dùng được cho phân tích mức và xu hướng theo quý, **không** dùng được cho biến động ngắn hạn.
   - Chuỗi này **khớp bối cảnh vĩ mô** — đỉnh 8-9% đầu 2023, hạ về ~4,6% giữa 2024, đi ngang suốt 2025, bật lên từ 12/2025 — nên đối chiếu chéo được với `policy_rate.csv` và `loan_industry_avg.csv` sẵn có. Đó là phép kiểm mà giới hạn này trước đây nói là không có.
   - Vẫn giữ nguyên cảnh báo: số của 24hmoney **lệch với hai nguồn kia tới 2,1 điểm** ở vài ngân hàng (xem mục schema). Có lịch sử không có nghĩa là có sự thật.
   - Phần dưới đây (khảo sát CafeF) viết trước phát hiện này, giữ lại vì kết luận về **CafeF** vẫn đúng nguyên: biến trung tâm của bài toán “chọn ngân hàng gửi tiết kiệm” lại là chuỗi ngắn nhất. `bank_cost_of_funds_quarterly.csv` là phương án thay thế đã kiểm định — khác biệt theo ngân hàng và có lịch sử từ 2018 — nhưng nó đo **chi phí vốn thực trả**, không phải lãi suất niêm yết mà người gửi nhìn thấy; phải nói rõ khác biệt này trong luận văn.
   - **CafeF đã kiểm và loại (25/08/2026)** — đây là nguồn cuối cùng còn khả năng lùi lịch sử, nên ghi lại để không ai phải làm lại. CafeF có sitemap đầy đủ tới 2016 (chunk 5 ngày), quét 7 tháng mẫu trải 2023-2026 được **141 bài** có slug lãi suất + tên ngân hàng. Nhưng **chỉ 12 bài (8,5%) có bảng HTML**, và chúng thuộc đúng **4 ngân hàng: Agribank, BIDV, Vietcombank, Sacombank** — mà Agribank không niêm yết, nên còn **3/22 ticker**. Đã kiểm phản chứng: các bài còn lại thực sự có `<table>` = 0, không phải lỗi bộ dò.
     - Loạt bài **hàng ngày** ("Lãi suất ngân hàng 11/8 tại Agribank, Vietcombank...") nhắc tới 25+ NH nhưng **toàn văn xuôi**, không bảng — đúng dạng đã chặn đường 2024 ở giới hạn 1.
     - Văn xuôi *có* số (SHB 35 lần "x,y%/năm") nhưng cắt nhau theo **bốn chiều**: kênh × bậc số tiền × **phương thức trả lãi** (cuối kỳ / trả trước / định kỳ) × kỳ hạn ghi dạng khoảng ("1-2 tháng", "6-11 tháng"). Riêng SHB đã là tới 12 mặt lãi suất cho cùng một kỳ hạn, và mỗi NH diễn đạt một kiểu.
     - **Lý do quyết định là không có gì để kiểm chéo.** Mọi chuỗi khác của đề tài đều qua một phép chéo độc lập (COF vs Harvard r=0,87; lãi suất cho vay vs SBV r=0,82; CPI vs tích lũy 12 tháng MoM). Với lãi suất tiết kiệm lùi lịch sử thì đối chứng duy nhất là chính `deposit_daily.csv` — 5 ngày. Một parser văn xuôi sẽ **không kiểm định được** đúng chỗ nó dễ sai nhất.
     - *Phần dùng được*: **VCB và BID** có bảng 2 cột (`Kỳ hạn | Lãi suất`) đều đặn hàng tháng, định dạng không đổi từ 2024-04 tới nay. Không đủ để mô hình hóa (2/22 NH) nhưng đủ làm **nguồn đối chứng độc lập** cho laisuattietkiem.vn — thứ dự án hiện không có, và là lý do ô Sacombank 0,5% phải phát hiện bằng tay.
   - Phương án thứ ba mới có: cột `deposit_avg_implied_percent` trong `bank_lending_rates_monthly.csv` — suy ra từ `chênh lệch lãi suất` mà chính NH công bố, 312 dòng trên 19 tháng theo từng NH, trung vị 5,42%. Nó là **lãi suất huy động bình quân thực tế trên toàn bộ số dư**, nên vẫn không phải lãi suất niêm yết; và là **số suy ra**, không trích dẫn trực tiếp được. Nhưng nó gần với thứ người gửi quan tâm hơn COF và có cùng độ phủ ngân hàng.
3. **Độ phủ ngân hàng của nguồn lãi suất tiết kiệm**: 17/22 ticker khớp trực tiếp; thiếu HDB, SSB, BVB, NVB, PGB. **Đã bù được (03/09/2026)**: `deposit_24hmoney_daily.csv` có đúng cả 5 mã này, nâng độ phủ lên **22/22** — nhưng là số của nguồn khác, phải đọc kèm cảnh báo **lệch nguồn** ở mục schema `deposit_24hmoney_daily.csv`.
   - **Độ phủ KÊNH cũng thủng, và đây không phải lỗi crawler**: 7/23 NH thiếu hẳn một kênh — Sacombank/Vietinbank/Eximbank/Bắc Á/Agribank/VP Bank không có `online`, SHB không có `quay`. Snapshot thô cho thấy nguồn **vẫn trả về dòng của kênh đó nhưng bỏ trống toàn bộ ô** (`-`), nên crawler loại đúng. Đáng lưu ý vì `online` thường **cao hơn** `quay` khá nhiều (Sacombank 12 tháng: 7,00% online vs 6,10% quầy theo bảng CafeF 08/2026) — thiếu kênh online sẽ kéo tụt các NH đó nếu đưa thẳng vào xếp hạng.
4. **CPI**: đã đủ 103/103 tháng (2018-01 → 2026-07), không còn ô trống. Nguồn chính là REST API của NSO, bù khuyết từ VnEconomy và một số ô chép tay. Bản công bố viết tay nên cách diễn đạt đổi theo năm — xem bảng "Cạm bẫy khi parse" ở mục schema: đã có 4 ô từng bị lấy nhầm số **lạm phát cơ bản**, chỉ phát hiện được nhờ phép thử tích lũy 12 tháng MoM.
4. **Lãi suất điều hành SBV**: không scrape được — `sbv.gov.vn` đứng sau WAF F5 BIG-IP, trả `Request Rejected` với request tự động. Thay vào đó là bảng tra cứu 11 sự kiện trong `crawlers/policy_rate.py`, mỗi dòng kèm số Quyết định và `source_url`.
   - **Đã đối chiếu nội dung toàn bộ 11 trích dẫn (24/08/2026)**, không chỉ mã HTTP: mỗi trang phải thật sự chứa **số Quyết định + cả ba mức lãi suất**. Ba URL phải thay vì trả 200 mà nội dung sai: QĐ 1809 (`hieuluat.vn` bị Cloudflare chặn 403), QĐ 950 (bài `thuvienphapluat/47487` đã bị biên tập lại tại chỗ, giờ nói về QĐ 1123), và mức nền 2017 — QĐ 1424 nay đã có **trích dẫn trực tiếp** cả ba mức 6,25 / 4,25 / 7,25, thay cho lời "xác nhận gián tiếp qua QĐ 1870" vốn **không đúng** (toàn văn QĐ 1870 chỉ nêu mức mới 6,0/4,0/7,0 và câu "thay thế QĐ 1424", không hề chứa 6,25 hay 4,25).
   - Bài học chung cho chương thu thập dữ liệu: **HTTP 200 không phải bằng chứng**. Trong 164 URL của đề tài, có trang trả 200 nhưng redirect về trang chủ, trang trả 200 là thử thách Cloudflare, và trang trả 200 nhưng đã bị viết lại thành văn bản khác.
5. **Độ phủ thời gian giữa các nguồn**: BCTC 2018-2026 và dataset Harvard 2002-2022 chỉ giao nhau ở **2018-2022** (~110 bank-year). Cân nhắc dùng cho hai bài toán tách biệt thay vì ghép làm một bảng feature.
6. **BCTC dạng PDF (thuyết minh)**: đã **khảo sát thực tế 24/08/2026** rồi mới quyết định bỏ, không phải bỏ theo cảm tính. Kết luận: **về nguyên tắc làm được, nhưng nút thắt là OCR chứ không phải parse** — và chi phí không xứng.

   **Thuyết minh có đúng thứ đề tài đang thiếu.** Khi PDF có lớp text, bóc bằng PyMuPDF ra sạch:
   - *Thuyết minh 9.1 — Phân tích chất lượng nợ cho vay*: đủ **nhóm 1-5 kèm số tiền và %**, hai kỳ cạnh nhau → giải quyết đúng giới hạn 1c.
   - *Thuyết minh 24 — Thu nhập lãi*: tách `Thu nhập lãi tiền gửi` / **`Thu nhập lãi cho vay`** / `Thu lãi từ đầu tư chứng khoán nợ` → tính được **lãi suất cho vay thực thu đúng nghĩa**, thứ mà `IS_NET_INTEREST_INCOME` (thuần) của vnstock không cho phép.
   - *Thuyết minh 25 — Chi phí lãi*: tách theo nguồn → dựng được COF tự tính thay vì lấy của vendor.
   - **Báo cáo QUÝ cũng có đủ hai thuyết minh này** (đã kiểm TCB 1Q25/3Q25/4Q25), không bị rút gọn mất.

   Kiểm chứng giá trị: TCB 2025, `53.445.735 / dư nợ bình quân 699.671.046` = **7,64%/năm**. Xếp đúng thứ tự với ba con số độc lập khác — COF 3,34% < lợi suất tài sản suy ra 6,75% < công bố 7,25% < **thực thu 7,64%**. Đây là con số tốt nhất trong bốn.

   **Nhưng phần lớn PDF là bản scan:**

   | Ngân hàng | Tài liệu | Dung lượng | Trang | Ký tự text | Kết quả |
   |---|---|---|---|---|---|
   | TCB | 1Q25 *(searchable)* | 1,1 MB | 74 | 174.984 | ✅ TEXT |
   | TCB | 3Q25 *(searchable)* | 1,2 MB | 82 | 194.855 | ✅ TEXT |
   | TCB | 4Q25 *(searchable)* | 1,3 MB | 87 | 204.303 | ✅ TEXT |
   | TCB | 1Q25 *(bản thường)* | 4,2 MB | 74 | **73** | ❌ SCAN |
   | **BID** | BCTC HN 2024 | 19,5 MB | 90 | **89** | ❌ SCAN |
   | **VCB** | BCTC HN 2022 | 15,1 MB | 84 | **83** | ❌ SCAN |
   | **CTG** | BCTC HN | 6,7 MB | 60 | **59** | ❌ SCAN |

   - Đây là **chính sách công bố ở cấp NGÂN HÀNG, không phải ngẫu nhiên theo kỳ**: Techcombank phát hành bản `-searchable` cho gần như mọi quý 2Q24→4Q25 (đặt tên file rõ ràng `-scan` / `-searchable`); còn VCB/BID/CTG thì scan.
   - **Ba ngân hàng scan lại đúng là ba NH có dư nợ lớn nhất hệ thống** — tức là trường hợp xấu nhất: quan trọng nhất với đề tài, mà cũng là nhóm phải OCR.
   - **Dung lượng file là chỉ báo rẻ và chính xác**: bản text 1,1-1,3 MB, bản scan 6,7-19,5 MB.

   **Nút thắt thứ hai — không có nguồn liệt kê PDF đồng nhất.** vnstock không có API tài liệu (`Company` chỉ có `overview/officers/shareholders/news/...`). Thử 14 trang IR ngân hàng: **12 trang trả về 0 link `.pdf`** vì render client-side, 3 trang trả 403/404/504. Chỉ VietinBank lộ 76 link server-side, mà các link Liferay đó lại đòi session (tải về ra 117 KB không phải PDF). CafeF nạp danh sách qua JS `LoadDocument()` không dò ra endpoint; Vietstock render client-side; cổng UBCKNN/HOSE/HNX đều không có API mở dùng được.

   **Vì sao vẫn bỏ:** 22 NH × 34 quý ≈ 748 tài liệu, ~3/4 phải OCR bảng tài chính tiếng Việt — dấu chấm phân cách nghìn, cột lệch, số âm trong ngoặc. Đó **đúng loại rủi ro đã cắn đề tài này hai lần** (lỗi `8.19 → 819` ở lãi suất cho vay, lỗi COF lưu phân số âm): sai kiểu im lặng, không crash, chỉ lộ ra khi có phép kiểm chéo. Cộng thêm việc phải dò URL riêng cho từng ngân hàng, chi phí không xứng với phần biên mà nó thêm vào so với `bank_earning_asset_yield_quarterly.csv` đã có.

   **Nếu sau này muốn mở lại**, hướng hẹp và khả thi nhất: chỉ lấy các ngân hàng phát hành bản searchable (dò bằng dung lượng file), chấp nhận độ phủ từng phần và ghi rõ — nhưng phải ý thức rằng **xếp hạng TOPSIS cần chấm điểm đủ 22 NH**, nên độ phủ từng phần sẽ tái lập đúng vấn đề mà COF đang gặp.

   *Bẫy đã phát hiện sẵn, ghi lại cho ai làm tiếp*: chuỗi `"Nợ đủ tiêu chuẩn"` xuất hiện **8 lần** trong một báo cáo; lần đầu tiên thuộc **Thuyết minh 7 (tiền gửi và cấp tín dụng cho TCTD khác)**, không phải Thuyết minh 9 (cho vay khách hàng) — lấy nhầm sẽ được ~70 nghìn tỷ thay vì ~700 nghìn tỷ. Và số trong báo cáo quý là **lũy kế từ đầu năm**, phải lấy sai phân mới ra số của riêng quý (TCB: 1Q25 = 11.721.049; 2Q25 = 24.470.058).
7. **Chuỗi thời gian lãi suất tiết kiệm** chỉ bắt đầu từ ngày crawl đầu tiên (không có API lịch sử miễn phí). Tính đến **2026-09-02 có 11 ngày (3.267 dòng, 297 dòng/ngày, 23 NH)**, dedup đúng (0 dòng trùng khoá) nhưng **thủng 2 ngày 29-30/08**. Quan trọng hơn số ngày: 11 ngày đó chỉ chứa **2 trạng thái phân biệt** (xem mục schema) — kéo dài thời gian crawl KHÔNG tự động làm chuỗi giàu thông tin hơn.
   - **Lỗ hổng ngày không còn tuyệt đối "mất vĩnh viễn"**: loạt bài CafeF hàng ngày có cả 29/08 và 30/08, và `deposit_crosscheck_daily.csv` đã lấy về. Chỉ vá được **ô 12 tháng/online**, không vá được 7 kỳ hạn x 2 kênh của nguồn chính — nên `--validate` vẫn kiểm lỗ hổng ngày ở mục đầu tiên.

8. **Đánh giá app ngân hàng số** (`crawlers/app_reviews.py`) — nguồn phía người dùng đầu tiên của đề tài, và cũng là nguồn có **độ phủ ngân hàng tốt nhất: 22/22 ticker**. Nhưng có bốn ràng buộc phải nêu rõ trước khi dùng làm tiêu chí xếp hạng:
   - **Đo hài lòng với APP, không phải hài lòng với NGÂN HÀNG.** Một ngân hàng dịch vụ quầy tốt nhưng app kém sẽ bị chấm thấp, và ngược lại. Với người gửi tiết kiệm — nhóm còn giao dịch tại quầy nhiều — đây là sai lệch có hướng, không phải nhiễu ngẫu nhiên. Phải đặt cạnh chỉ số mạng lưới chi nhánh nếu muốn nói về "chất lượng phục vụ" nói chung.
   - **Chỉ lấy được đánh giá có nội dung.** Người viết nhận xét lệch hẳn về hai cực: phân bố sao trên mẫu đã cào là ~38% một sao và ~52% năm sao, gần như không có 2-4 sao. `app_catalog.score` (điểm Google hiển thị, tính trên toàn bộ lượt chấm) mới là số đại diện cho tất cả người dùng — hai con số này **không thay thế cho nhau được**.
   - **Không so ngang được giữa các ngân hàng nếu không chuẩn hoá theo quy mô.** MBB có hơn 170 nghìn đánh giá còn PGB có 363; cùng một `mean_score` nhưng sai số chuẩn khác nhau hàng chục lần. Với TOPSIS nên dùng khoảng tin cậy hoặc thu nhỏ về trung bình chung (shrinkage) thay vì lấy thẳng trung bình thô.
   - **Đổi app là đứt chuỗi, và đứt một cách im lặng.** MSB và LPB đang có app cũ lẫn app kế nhiệm cùng tồn tại; app cũ vẫn tải được đánh giá nhưng lưu lượng dịch dần sang app mới. Không có tín hiệu lỗi nào báo việc này — chỉ có `--discover` chạy định kỳ và cột `n_reviews` tụt dần mới thấy. Cùng loại rủi ro với các vụ đổi tên VCBNEO/MBV ở giới hạn 1.
   - *Về mặt pháp lý*: `userName`/`userImage` được loại ngay khi ghi (Nghị định 13/2023/NĐ-CP), luận văn chỉ công bố ở mức tổng hợp bank-month. Nội dung đánh giá vẫn được lưu vì cần cho phân tích văn bản, nhưng **không trích nguyên văn kèm bất kỳ định danh nào**.

9. **Mạng lưới chi nhánh/ATM**: có dữ liệu, nhưng **KHÔNG dùng được làm tiêu chí quy mô mạng lưới trong TOPSIS** — đây là kết luận từ ba phép đối chiếu độc lập, không phải phỏng đoán.
   - **Cái dùng được**: `branch_points.csv` cho **vị trí thật, có toạ độ, của 3.550 điểm thuộc 22 ngân hàng**. Đủ để trả lời "chi nhánh nào gần tôi nhất" trong bản demo, và đủ để so **mật độ ATM ở đô thị lớn** (Hà Nội và TP.HCM chiếm hơn một nửa toàn bộ POI).
   - **Cái KHÔNG dùng được**: đếm số điểm rồi coi đó là quy mô mạng lưới. OSM là dữ liệu cộng đồng đóng góp nên thiếu **không đều theo ngân hàng**: tỉ lệ OSM/số công bố chạy từ 0,035 (LPB, SHB) tới 1,31 (CTG, VCB) — chênh **37 lần**. Xếp hạng bằng con số này sẽ dìm LPBank xuống đáy trong khi thực tế LPBank có mạng lưới lớn thứ ba hệ thống nhờ hệ thống bưu điện.
   - **Thiếu không đều theo tỉnh cũng nghiêm trọng tương tự**: Sơn La 2 POI, Cà Mau 4 POI cho *toàn bộ* ngành ngân hàng. Đó là lỗ hổng của người vẽ bản đồ, không phải của thị trường. Nên **không được đọc `branch_by_province` như thị phần địa lý**.
   - **Nguồn duy nhất còn lại cho quy mô mạng lưới** là cột `Number of Branches` của dataset Harvard: 468/667 dòng có số, khoảng 28 ngân hàng mỗi năm giai đoạn 2018-2022. Nhược điểm là **dừng ở 2022** và **không có chiều địa lý** — nhưng nó là số cấp ngân hàng đáng tin, và cho phép làm biến quy mô trong mô hình bảng theo năm. Đây là chỗ dùng đúng của nó.
   - *Lưu ý về đơn vị khi trích*: Harvard đếm **chi nhánh cấp 1** (VCB = 122 năm 2022), còn OSM đếm mọi điểm vật lý kể cả phòng giao dịch. Hai con số **không so mức được với nhau**, chỉ so thứ hạng — và ngay cả thứ hạng cũng chỉ Spearman 0,414.
   - *Vì sao không dùng Google Places*: cho được cả sao lẫn mạng lưới với độ phủ tốt hơn hẳn, nhưng bắt buộc có API key + bật thanh toán, và các trường `rating`/`userRatingCount` nằm ở bậc SKU tính phí cao hơn. Một lượt quét đầy đủ ước tính khoảng 4.000 request. Để ngỏ nếu sau này có kinh phí.
