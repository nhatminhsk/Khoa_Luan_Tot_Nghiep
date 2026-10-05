"""Kiem ke toan bo file CSV trong data/ -> vai tro va quyet dinh giu/bo cho tung file.

Buoc dau cua chuoi lam sach -> xu ly -> dac trung: truoc khi tao bien phai biet file
nao la NGUON GOC, file nao la TRUNG GIAN dung lai duoc, file nao TRUNG hoac LUU TRU.
Doc toan bo file de dem dong/cot, do khoa (ma NH, cot thoi gian), khoang thoi gian;
vai tro va quyet dinh lay tu bang RULES ben duoi (khop theo duong dan, quy tac dau
tien khop thang).

Ket qua: data/model/data_inventory.csv

Chay:
    python -m crawlers.inventory
"""
from __future__ import annotations

import glob
import os
import re

import pandas as pd

OUT = "data/model/data_inventory.csv"

USE_MODEL = "Dùng cho mô hình"
USE_RANK = "Dùng cho xếp hạng / giao diện"
REFERENCE = "Tham khảo / kiểm chéo"
INTERMEDIATE = "Trung gian (dựng lại được)"
DROP_DUP = "Bỏ — trùng"
DROP_ARCHIVE = "Bỏ — lưu trữ"
OUTPUT = "Sản phẩm của bước đặc trưng"

# (mau duong dan, vai tro, quyet dinh, ly do / dung o dau)
RULES = [
    (r"^data/_archive/", "Lưu trữ", DROP_ARCHIVE, "Bản cũ trước khi tải BCTC đầy đủ; 44 file BCTC cũ rỗng"),
    (r"^data/powerbi/", "Dẫn xuất cho Power BI", DROP_DUP, "Dựng lại từ các thư mục khác; fact_app_review trùng app_reviews/"),
    (r"^data/vnstock_financial/raw(_mas|_note)?/", "Bản thô theo mã", DROP_DUP, "Đã gộp nguyên vẹn vào *_long.csv (cùng số dòng)"),
    (r"^data/interest_rates/deposit_raw/", "Bản thô theo ngày", DROP_DUP, "Đã gộp vào deposit_daily.csv"),
    (r"agri_loans_annual_nhap_tay\.csv$", "Bản sao người dùng", DROP_DUP, "Đã gộp 16 ô vào agri_loans_fill_template.csv ngày 15/09/2026"),
    (r"^data/model/(features_quarterly|feature_spec|feature_catalog|features_selected|features_ranking_latest|data_inventory)\.csv$", "Kết quả", OUTPUT, "Sinh bởi crawlers.inventory / build_features / select_features"),
    (r"^data/model/experiments/", "Kết quả thử nghiệm", OUTPUT, "Sinh bởi experiments/*.py"),
    (r"^data/model/eda/", "Kết quả EDA", OUTPUT, "Sinh bởi experiments/eda.py"),
    (r"^data/model/bank_panel_quarterly\.csv$", "Panel sạch NH-quý", USE_MODEL, "Đầu vào chính của build_features (đã qua cổng validate)"),
    (r"^data/vnstock_financial/financial_long\.csv$", "Nguồn gốc BCTC quý/năm", USE_MODEL, "Tạo tỷ số CAMELS từ bảng cân đối, KQKD, lưu chuyển tiền"),
    (r"^data/vnstock_financial/note_long\.csv$", "Nguồn gốc thuyết minh", USE_MODEL, "Cơ cấu tiền gửi, nhóm nợ, chứng khoán đầu tư, chi lương, trả lãi tiền gửi"),
    (r"^data/vnstock_financial/ratio_mas_long\.csv$", "Nguồn gốc chỉ số MAS", INTERMEDIATE, "Dựng ratio_mas_ttm.csv"),
    (r"^data/vnstock_financial/ratio_mas_ttm\.csv$", "Trung gian", INTERMEDIATE, "Đã vào panel (NIM/COF dự phòng, ROE, ROA, P/E, P/B, beta)"),
    (r"^data/vnstock_financial/availability", "Nhật ký tải", REFERENCE, "Ghi lại kỳ nào tải được"),
    (r"^data/credit/bank_(credit|asset_quality)_quarterly\.csv$", "Trung gian", INTERMEDIATE, "Đã vào panel"),
    (r"^data/credit/bank_car_halfyear\.csv$", "Nguồn nửa năm (có nhập tay)", USE_MODEL, "CAR, gán as-of cho quý"),
    (r"^data/credit/bank_repricing_gap\.csv$", "Nhập tay", USE_RANK, "Chỉ vài kỳ gần nhất → không đủ cho panel lịch sử"),
    (r"^data/credit/loans_by_industry_group_wide\.csv$", "Trung gian năm", USE_MODEL, "Tỷ trọng dư nợ theo nhóm ngành, gán as-of"),
    (r"^data/credit/loans_by_industry_annual\.csv$", "Nguồn chép tay", INTERMEDIATE, "Dựng bản rộng"),
    (r"^data/credit/loans_by_industry_all_versions\.csv$", "Trung gian", REFERENCE, "Xem số trình bày lại giữa hai BCTC"),
    (r"^data/credit/loans_by_industry_manual/", "Nguồn gốc chép tay", REFERENCE, "Link BCTC và trang PDF"),
    (r"^data/interest_rates/bank_(cost_of_funds|earning_asset_yield)_quarterly\.csv$", "Trung gian", INTERMEDIATE, "Đã vào panel"),
    (r"^data/interest_rates/deposit_24hmoney_daily\.csv$", "Nguồn lịch sử lãi suất huy động", USE_RANK, "38 ngày từ 2023 → phủ 14/34 quý; dùng cho xếp hạng gửi tiết kiệm"),
    (r"^data/interest_rates/deposit_daily\.csv$", "Nguồn hàng ngày", USE_RANK, "Lãi suất hiện tại cho giao diện và thông báo"),
    (r"^data/interest_rates/deposit_crosscheck_daily\.csv$", "Nguồn đối chứng", REFERENCE, "Kiểm chéo lãi suất huy động"),
    (r"^data/interest_rates/bank_lending_rates_monthly\.csv$", "Nguồn báo chí tháng", USE_RANK, "Chỉ 2025-01 → 2026-07; dùng cho xếp hạng vay"),
    (r"^data/loan_rates/", "Mức toàn ngành (NHNN)", USE_RANK, "Chỉ từ 2024; khung tham chiếu lãi suất trên giao diện"),
    (r"^data/macro/world_bank_annual\.csv$", "Nguồn năm, trễ", REFERENCE, "Hết 2023–2024; kiểm chéo COF/NPL hệ thống"),
    (r"^data/macro/", "Nguồn vĩ mô", USE_MODEL, "Biến chung cho mọi ngân hàng"),
    (r"^data/market/VNINDEX\.csv$", "Nguồn thị trường", USE_MODEL, "Lợi suất thị trường theo quý"),
    (r"^data/market/VN30\.csv$", "Nguồn thị trường", REFERENCE, "Cùng vai trò với VN-Index"),
    (r"^data/price/", "Nguồn giá cổ phiếu ngày", USE_MODEL, "Lợi suất, biến động, thanh khoản theo quý"),
    (r"^data/app_reviews/[A-Z]{3}\.csv$", "Nguồn gốc review", USE_MODEL, "NLP review (tầng B) và điểm app theo quý"),
    (r"^data/app_reviews/app_reviews_monthly\.csv$", "Trung gian tháng", USE_MODEL, "Tổng hợp quý cho đặc trưng khách hàng"),
    (r"^data/app_reviews/app_catalog_ios\.csv$", "Ảnh chụp iOS", REFERENCE, "Đối chứng Play Store"),
    (r"^data/app_reviews/app_catalog\.csv$", "Ảnh chụp Play Store", USE_RANK, "Điểm store và lượt cài hiện tại"),
    (r"^data/branch_network/branch_by_province\.csv$", "Trung gian ảnh chụp", USE_MODEL, "Biến tĩnh mạng lưới, phơi nhiễm thiên tai"),
    (r"^data/branch_network/branch_points\.csv$", "Nguồn gốc OSM", USE_RANK, "Bản đồ chi nhánh"),
    (r"^data/branch_network/", "Danh mục / đối chứng", REFERENCE, "Danh mục tỉnh, điểm TPB tự công bố"),
    (r"^data/ownership/bank_ownership\.csv$", "Ảnh chụp 09/09/2026", USE_MODEL, "Biến tĩnh sở hữu nhà nước, nước ngoài"),
    (r"^data/ownership/", "Chi tiết cổ đông", REFERENCE, "Không đổi theo quý"),
    (r"^data/external/", "Bộ dữ liệu ngoài 2002–2022", REFERENCE, "Hết 2022 → không phủ 2023–2026"),
    (r"^data/policy_credit/(program_participation|agri_loans_annual|disaster_provinces)\.csv$", "Nguồn nhập tay", USE_MODEL, "Biến giả chương trình, tỷ trọng nông nghiệp, phơi nhiễm thiên tai"),
    (r"^data/policy_credit/agri_loans_fill_template\.csv$", "Nguồn sự thật nhập tay", INTERMEDIATE, "Dựng agri_loans_annual.csv"),
    (r"^data/policy_credit/", "Nguồn nhập tay", REFERENCE, "Số tổng / lãi suất chương trình / số NH tự công bố — không theo NH-quý"),
]

# (mau duong dan, noi dung file) -- quy tac dau tien khop thang
CONTENT = [
    (r"^data/_archive/", "Bản BCTC tóm tắt cũ theo mã (trước 14/09/2026); nhiều file rỗng"),
    (r"^data/powerbi/dim_", "Bảng danh mục (dim) cho Power BI"),
    (r"^data/powerbi/", "Bảng dữ kiện (fact) cho Power BI, dựng từ các thư mục khác"),
    (r"^data/vnstock_financial/raw_mas/", "Chỉ số MAS của một NH theo quý, trước khi gộp"),
    (r"^data/vnstock_financial/raw_note/", "Thuyết minh BCTC của một NH theo quý, trước khi gộp"),
    (r"^data/vnstock_financial/raw/", "Một loại BCTC (CĐKT/KQKD/LCTT/chỉ số) của một NH, trước khi gộp"),
    (r"^data/interest_rates/deposit_raw/", "Bảng lãi suất tiết kiệm thô của một ngày: NH × kênh × kỳ hạn 1–36 tháng"),
    (r"agri_loans_annual_nhap_tay\.csv$", "Bản Save As của agri_loans_annual.csv có 16 ô người dùng nhập (đã gộp)"),
    (r"^data/model/experiments/imputation_quality\.csv$", "Sai số điền (NRMSE) theo lần che × kiểu thiếu × mức × cách điền × biến"),
    (r"^data/model/experiments/imputation_quality_summary\.csv$", "NRMSE và hạng trung bình theo kiểu thiếu × mức × cách điền"),
    (r"^data/model/experiments/imputation_downstream\.csv$", "MAE dự báo thay đổi quý sau theo mục tiêu × cách điền, so với naive"),
    (r"^data/model/experiments/imputation_downstream_predictions\.csv$", "Từng dự báo walk-forward: quý gốc, cách điền, mục tiêu, NH, thật, dự báo"),
    (r"^data/model/experiments/ranking_missing_snapshot\.csv$", "Hạng TOPSIS của 22 NH theo từng cách xử lý ô thiếu (ảnh chụp hiện tại)"),
    (r"^data/model/experiments/ranking_missing_simulation\.csv$", "Mô phỏng che ô: quý, NH, tiêu chí, cách xử lý, số bậc dịch hạng"),
    (r"^data/model/experiments/ranking_weight_perturbation\.csv$", "Số bậc dịch hạng trung bình khi đổi trọng số ngẫu nhiên"),
    (r"^data/model/eda/variance\.csv$", "Phân rã phương sai 20 chỉ số: phần giữa NH, xu hướng chung theo quý, phần riêng NH-quý"),
    (r"^data/model/eda/trends\.csv$", "Trung vị, tứ phân vị theo quý của 10 chỉ số cho 22 NH và từng nhóm"),
    (r"^data/model/eda/macro\.csv$", "Lãi suất tái cấp vốn, tăng trưởng tín dụng, CPI, lợi suất VN-Index theo quý"),
    (r"^data/model/eda/leadlag\.csv$", "Tương quan thay đổi lãi suất tái cấp vốn quý t−k với thay đổi COF, NIM, lợi suất TSSL, lãi niêm yết"),
    (r"^data/model/eda/corr_pairs\.csv$", "190 cặp chỉ số: tương quan giữa NH và trong NH (trừ trung bình NH và quý)"),
    (r"^data/model/eda/pca_banks\.csv$", "Tọa độ PC1–PC3 và nhóm k-means của 22 NH (4 quý gần nhất)"),
    (r"^data/model/eda/pca_loadings\.csv$", "Trọng số của 14 tiêu chí trên PC1–PC3"),
    (r"^data/model/eda/cluster_profile\.csv$", "Trung vị 14 tiêu chí theo 3 nhóm ngân hàng"),
    (r"^data/model/eda/deposit_today\.csv$", "22 NH: lãi suất 12 tháng online/quầy ngày mới nhất + chỉ số tài chính 4 quý gần nhất"),
    (r"^data/model/eda/deposit_corr\.csv$", "Tương quan lãi suất 12 tháng online với chỉ số an toàn, KTC 95%"),
    (r"^data/model/eda/app_links\.csv$", "Tương quan điểm app với chỉ số tài chính: giữa NH và trong NH, KTC 95%"),
    (r"^data/model/eda/policy_agri\.csv$", "Tỷ trọng dư nợ nông nghiệp 2025 theo việc tham gia gói nông nghiệp"),
    (r"^data/model/eda/policy_yagi\.csv$", "% chi nhánh ở tỉnh bị bão Yagi và thay đổi NPL 2024-Q2 → 2025-Q2"),
    (r"^data/model/features_quarterly\.csv$", "120 đặc trưng ứng viên × 748 NH-quý, đã làm sạch, chưa điền khuyết"),
    (r"^data/model/features_selected\.csv$", "88 đặc trưng được Giữ × 748 NH-quý — đầu vào mô hình dự báo"),
    (r"^data/model/features_ranking_latest\.csv$", "22 NH × số gần nhất trong 4 quý cuối của 87 đặc trưng — đầu vào xếp hạng"),
    (r"^data/model/feature_catalog\.csv$", "Mỗi đặc trưng: nhóm, công thức, độ phủ, ICC, cờ, quyết định Giữ/Loại và lý do"),
    (r"^data/model/feature_spec\.csv$", "Mỗi đặc trưng: nhóm CAMELS, nguồn, công thức, đơn vị, cách quy về quý"),
    (r"^data/model/data_inventory\.csv$", "Bảng này: mỗi file CSV, nội dung, vai trò, quyết định giữ/bỏ"),
    (r"^data/model/bank_panel_quarterly\.csv$", "22 NH × 34 quý: dư nợ, tiền gửi, tổng tài sản, NPL, nợ nhóm 2, CASA, cơ cấu kỳ hạn, NIM, COF, "
                                                  "lợi suất TSSL, ROE, ROA, CIR, P/E, P/B, EPS, BVPS, beta, cổ tức, CAR; cột *_src ghi nguồn"),
    (r"^data/vnstock_financial/financial_long\.csv$", "BCTC quý và năm dạng dài (NH, loại báo cáo, kỳ, chỉ tiêu, giá trị): 80 chỉ tiêu CĐKT, "
                                                        "25 KQKD, 49 LCTT, 47 chỉ số; đơn vị đồng, chỉ số lưu thập phân"),
    (r"^data/vnstock_financial/note_long\.csv$", "Thuyết minh BCTC quý dạng dài, 205 chỉ tiêu: tiền gửi theo loại/tiền tệ/khách hàng, dư nợ theo "
                                                   "nhóm nợ/kỳ hạn/ngành, chứng khoán đầu tư, thu–chi lãi, chi lương, CAR"),
    (r"^data/vnstock_financial/ratio_mas_long\.csv$", "12 chỉ số MAS theo NH-quý dạng dài từ 2012: NIM, COF, YIEA, ROE, ROA, CIR, P/E, P/B, EPS, BVPS, beta, cổ tức"),
    (r"^data/vnstock_financial/ratio_mas_ttm\.csv$", "Chỉ số MAS đã cộng 4 quý (TTM) dạng rộng theo NH-quý, 2012-Q1 → 2026-Q2"),
    (r"^data/vnstock_financial/availability", "Nhật ký tải BCTC: mã, loại báo cáo, kỳ yêu cầu, trạng thái, số dòng"),
    (r"^data/credit/bank_credit_quarterly\.csv$", "NH-quý từ BCTC: dư nợ, tiền gửi, tổng tài sản, tăng trưởng dư nợ, LDR, dự phòng, NPL, NIM"),
    (r"^data/credit/bank_asset_quality_quarterly\.csv$", "NH-quý từ thuyết minh: NPL, nợ nhóm 2, CASA, cơ cấu kỳ hạn cho vay, tiền gửi VNĐ, chi phí trả lãi tiền gửi"),
    (r"^data/credit/bank_car_halfyear\.csv$", "CAR hợp nhất (riêng lẻ, Tier 1 nếu có) theo nửa năm 2019-H1 → 2026-H1, thông tư áp dụng, nguồn, độ tin cậy"),
    (r"^data/credit/bank_repricing_gap\.csv$", "Khe hở định lại lãi suất nội bảng theo kỳ (quá hạn, ≤1 tháng … >5 năm), tổng tài sản, nợ — nhập tay từ thuyết minh"),
    (r"^data/credit/loans_by_industry_group_wide\.csv$", "Tỷ trọng % dư nợ theo nhóm ngành VSIC (A, C, F, G, L…) mỗi NH-năm 2018–2025"),
    (r"^data/credit/loans_by_industry_annual\.csv$", "Từng dòng ngành trong bảng dư nợ theo ngành của BCTC kiểm toán, một bản cho mỗi NH-năm"),
    (r"^data/credit/loans_by_industry_all_versions\.csv$", "Như loans_by_industry_annual nhưng giữ cả cột cuối năm và đầu năm của mọi BCTC"),
    (r"^data/credit/loans_by_industry_manual/sources\.csv$", "Link BCTC và trang PDF của 81 bảng dư nợ theo ngành chép tay"),
    (r"^data/credit/loans_by_industry_manual/", "Bảng dư nợ theo ngành chép tay: dòng ngành, mã nhóm, số cuối năm, số đầu năm"),
    (r"^data/interest_rates/bank_cost_of_funds_quarterly\.csv$", "Chi phí vốn TTM theo NH-quý (VCI)"),
    (r"^data/interest_rates/bank_earning_asset_yield_quarterly\.csv$", "Lợi suất tài sản sinh lãi, NIM, COF TTM theo NH-quý (suy ra từ BCTC)"),
    (r"^data/interest_rates/deposit_24hmoney_daily\.csv$", "Lãi suất tiết kiệm niêm yết: NH × kỳ hạn 1–36 tháng × kênh (quầy/online), 38 ngày quan sát từ 2023"),
    (r"^data/interest_rates/deposit_daily\.csv$", "Lãi suất tiết kiệm niêm yết hàng ngày: NH × kỳ hạn × kênh, kèm mức hôm trước, từ 21/08/2026"),
    (r"^data/interest_rates/deposit_crosscheck_daily\.csv$", "Lãi suất online từ nguồn thứ hai (CafeF) để đối chiếu, có kiểm checksum"),
    (r"^data/interest_rates/bank_lending_rates_monthly\.csv$", "Lãi suất cho vay và huy động bình quân từng NH công bố theo tháng (báo chí), 2025-01 → 2026-07"),
    (r"^data/loan_rates/", "Khung lãi suất huy động theo kỳ hạn và cho vay bình quân toàn ngành NHNN công bố, theo tháng từ 2024"),
    (r"^data/macro/cpi\.csv$", "CPI so cùng kỳ và so tháng trước, theo tháng từ 2018-01 (NSO), kèm link"),
    (r"^data/macro/price_indices\.csv$", "Chỉ số giá USD, vàng, lạm phát cơ bản so tháng trước và so cùng kỳ, theo tháng (NSO)"),
    (r"^data/macro/policy_rate\.csv$", "Lãi suất tái cấp vốn, tái chiết khấu, cho vay qua đêm của NHNN theo ngày hiệu lực, kèm quyết định"),
    (r"^data/macro/credit_growth\.csv$", "Tăng trưởng tín dụng toàn hệ thống theo năm 2018–2025 (NHNN), kèm nguồn"),
    (r"^data/macro/world_bank_annual\.csv$", "Chuỗi năm World Bank: lãi suất tiền gửi, cho vay, chênh lệch, lãi thực, NPL, vốn/tài sản, tín dụng/GDP"),
    (r"^data/market/VNINDEX\.csv$", "VN-Index theo ngày: mở, cao, thấp, đóng, khối lượng từ 2015"),
    (r"^data/market/VN30\.csv$", "VN30 theo ngày: mở, cao, thấp, đóng, khối lượng từ 2015"),
    (r"^data/price/", "Giá cổ phiếu một NH theo ngày: mở, cao, thấp, đóng (nghìn đồng), khối lượng"),
    (r"^data/app_reviews/[A-Z]{3}\.csv$", "Từng review Google Play app của một NH: mã review, thời gian, số sao, lượt thích, phiên bản, nội dung, phản hồi"),
    (r"^data/app_reviews/app_reviews_monthly\.csv$", "NH-tháng: số review, sao trung bình/trung vị, % 1 sao, % 5 sao, % có nội dung, tỷ lệ phản hồi, ngày bị spam, cờ dùng được"),
    (r"^data/app_reviews/app_catalog_ios\.csv$", "Ảnh chụp app App Store: điểm, lượt đánh giá, phiên bản, app Play tương ứng"),
    (r"^data/app_reviews/app_catalog\.csv$", "Ảnh chụp app Play Store: tên, nhà phát triển, điểm, lượt đánh giá, số review có chữ, lượt cài"),
    (r"^data/branch_network/branch_by_province\.csv$", "Số chi nhánh/PGD và ATM của từng NH theo 34 tỉnh (OSM)"),
    (r"^data/branch_network/branch_points\.csv$", "Từng điểm chi nhánh/PGD/ATM trên OpenStreetMap: loại, NH, tỉnh, tọa độ"),
    (r"^data/branch_network/provinces\.csv$", "Danh mục 34 tỉnh mới và mã vùng OSM"),
    (r"^data/branch_network/tpb_official_points\.csv$", "Điểm giao dịch TPBank tự công bố để đối chiếu OSM"),
    (r"^data/ownership/bank_ownership\.csv$", "Ảnh chụp 09/09/2026: sở hữu nhà nước, nước ngoài, room ngoại, vốn hóa, giá, thanh khoản 1 tháng"),
    (r"^data/ownership/bank_shareholders\.csv$", "Cổ đông lớn từng NH: tên, loại, số cổ phần, tỷ lệ"),
    (r"^data/external/.*banks_list", "Danh sách 45 NH của bộ dữ liệu ngoài: mã, loại sở hữu, niêm yết"),
    (r"^data/external/", "Bộ dữ liệu ngoài 45 NH × năm 2002–2022: nhân viên, chi nhánh, tiền gửi, cho vay, chi phí, thu nhập, tỷ số"),
    (r"^data/policy_credit/agri_loans_annual\.csv$", "22 NH × 2018–2025: dư nợ nông, lâm, thủy sản, tổng dư nợ theo ngành, tỷ trọng %, nguồn, link"),
    (r"^data/policy_credit/agri_loans_fill_template\.csv$", "File nhập tay dư nợ nông nghiệp: trạng thái, số, dòng BCTC, cột đọc, trang, link"),
    (r"^data/policy_credit/program_participation\.csv$", "22 NH × 8 chương trình tín dụng chính sách: tham gia 0/1, cam kết (tỷ đồng), ngày danh sách, văn bản"),
    (r"^data/policy_credit/program_rates\.csv$", "Lãi suất / mức ưu đãi của từng chương trình theo giai đoạn và nhóm người vay"),
    (r"^data/policy_credit/program_aggregates\.csv$", "Số tổng NHNN công bố theo chương trình: giải ngân lũy kế, dư nợ, số khách hàng"),
    (r"^data/policy_credit/disaster_provinces\.csv$", "Tỉnh trong TT 53/2024 (bão Yagi) và CV 9651/2025 (bão 10–12): tên tỉnh cũ → tỉnh mới 2025"),
    (r"^data/policy_credit/bank_reported_items\.csv$", "Số NH tự công bố về hỗ trợ lãi suất và thiên tai (VCB, BID, EIB, CTG): BCTC, báo cáo thường niên, báo chí"),
]

TICKER_COLS = ("ticker", "symbol", "Bank Code")
TIME_COLS = ("period", "date", "month", "year", "time", "as_of_date", "date_effective", "valid_from", "as_of", "Year")


def _classify(path: str):
    for pattern, role, decision, reason in RULES:
        if re.search(pattern, path):
            return role, decision, reason
    return "Chưa phân loại", "Cần xem", ""


def _content(path: str) -> str:
    return next((text for pattern, text in CONTENT if re.search(pattern, path)), "")


def build() -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob("data/**/*.csv", recursive=True)):
        path = f.replace(os.sep, "/")
        role, decision, reason = _classify(path)
        rec = dict(file=path, content=_content(path), folder=path.split("/")[1], size_kb=round(os.path.getsize(f) / 1024, 1),
                   rows=0, cols=0, ticker_col="", n_tickers=None, time_col="", time_min="", time_max="",
                   role=role, decision=decision, reason=reason)
        try:
            d = pd.read_csv(f, encoding="utf-8-sig", low_memory=False)
        except pd.errors.EmptyDataError:
            rec["reason"] = (reason + "; file rỗng").strip("; ")
            rows.append(rec)
            continue
        rec.update(rows=len(d), cols=d.shape[1])
        tcol = next((c for c in TICKER_COLS if c in d.columns), None)
        if tcol is None and re.search(r"/[A-Z]{3}(_(bs|cf|is|ratio|note|mas))?\.csv$", path):
            rec.update(ticker_col="(tên file)", n_tickers=1)
        elif tcol:
            rec.update(ticker_col=tcol, n_tickers=int(d[tcol].nunique()))
        time_col = next((c for c in TIME_COLS if c in d.columns), None)
        if time_col:
            s = d[time_col].dropna().astype(str).str[:10]
            rec.update(time_col=time_col, time_min=s.min() if len(s) else "", time_max=s.max() if len(s) else "")
        rows.append(rec)
    inv = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    inv.to_csv(OUT, index=False, encoding="utf-8-sig")
    return inv


def summary(inv: pd.DataFrame) -> dict:
    g = inv.groupby("decision").agg(files=("file", "size"), rows=("rows", "sum"))
    return {
        "files": len(inv),
        "rows": int(inv.rows.sum()),
        "by_decision": {k: {"files": int(v.files), "rows": int(v.rows)} for k, v in g.iterrows()},
        "unclassified": inv.loc[inv.decision == "Cần xem", "file"].tolist(),
        "no_content": inv.loc[inv.content == "", "file"].tolist(),
        "path": OUT,
    }


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(summary(build()), indent=2, ensure_ascii=False))
