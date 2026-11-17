# data/serving — hợp đồng dữ liệu giữa pipeline và web app

Pipeline Python ghi các file CSV ở đây. Backend Java (`webapp/backend`) nạp các file này vào cơ sở dữ liệu của nó: khi khởi động, hoặc khi quản trị viên bấm "Nạp lại dữ liệu". Giao diện chỉ đọc từ backend và **không chạy mô hình** khi người dùng mở trang.

Quy ước chung:

- UTF-8 không BOM, dấu phân cách `,`, dấu thập phân `.`, ngày `YYYY-MM-DD`, tháng `YYYY-MM`, quý `YYYY-Qn`.
- Ô trống nghĩa là thiếu số. Backend không điền và không sửa số.
- Mỗi file thay **toàn bộ** bảng tương ứng. Backend nạp lại một file khi checksum của nó đổi.
- Mã ngân hàng là mã niêm yết (22 mã, xem `banks.csv`). Mã khác bị bỏ qua.

Sinh lại các file dữ liệu:

```
python -m serving.export
```

## File do `serving.export` sinh ra

| File | Khóa | Cột |
|---|---|---|
| `banks.csv` | ticker | ticker, short_name, full_name |
| `indicators.csv` | code | code, name, camels_group (C/A/M/E/L/G), unit (PERCENT/VND), direction (HIGHER_BETTER/LOWER_BETTER/NEUTRAL), description, display_order |
| `bank_quarterly.csv` | ticker, period, indicator | ticker, period, period_end, indicator, value |
| `deposit_rates.csv` | rate_date, ticker, term_months, channel | rate_date, ticker, term_months, channel (ONLINE/COUNTER), rate_percent, source |
| `deposit_rate_tiers.csv` | ticker, term_months, channel, min_amount_vnd | ticker, term_months, channel, min_amount_vnd, rate_percent, base_rate_percent, tier_label, valid_from, source — bậc trên bậc thấp nhất theo số tiền gửi, cho ngày mới nhất của `deposit_rates`; chỉ áp khi lãi trong `deposit_rates` bằng `base_rate_percent` |
| `lending_rates.csv` | month, ticker | month, ticker, lending_avg_percent, deposit_avg_percent, segment (INDIVIDUAL/ALL/INDIV_MID_LONG/CONSUMER_SHORT/UNSPECIFIED, ≤ 16 ký tự), basis (NEW_LOANS/OUTSTANDING/trống), source (BANK/VIETNAMNET), source_url — mỗi ngân hàng × tháng một số: số khách hàng cá nhân ngân hàng công bố trên web, không có thì số chung, rồi nhóm hẹp ngân hàng chỉ công bố riêng (SSB cá nhân trung dài hạn = INDIV_MID_LONG, SHB tiêu dùng ngắn hạn = CONSUMER_SHORT; deposit_avg_percent trống), cuối cùng là số VietnamNet (UNSPECIFIED); deposit_avg_percent = lãi vay − chênh lệch ngân hàng công bố |
| `programs.csv` | program_code | program_code, program_name, category (HOUSING/AGRICULTURE/BUSINESS/INFRASTRUCTURE/OTHER) |
| `program_participation.csv` | program_code, ticker | program_code, ticker, participates (0/1), list_as_of, source_url |
| `program_rates.csv` | — | program_code, borrower_group, valid_from, valid_to, rate_pct_year, spread_below_avg_min_pct, spread_below_avg_max_pct, source_url |
| `macro_cpi.csv` | month | month, cpi_yoy_percent (lạm phát so cùng kỳ, %), cpi_mom_percent, source_url — từ 2019-01; web tính lãi suất thực = lãi niêm yết − cpi_yoy_percent |
| `bank_ownership.csv` | ticker | ticker, as_of_date, state_own_percent, foreign_own_percent, foreign_room_percent, source — ảnh chụp mới nhất của từng ngân hàng |
| `datasets.csv` | dataset | dataset, name, source, frequency, last_updated, row_count, coverage_note |

## File chưa nạp vào web

Backend chỉ nạp các file có trong `ServingDatasets.java`; file dưới đây nằm ở thư mục này nhưng backend bỏ qua, không có dòng trong `datasets.csv`.

### `bank_health.csv` — điểm tài chính tương đối tham khảo các nhóm chỉ tiêu Moody's

Sinh bằng `python -m serving.bank_health [--ranking <ảnh chụp>]`. Là nhóm **tùy chọn** của bài toán vay: hiển thị riêng, chỉ gộp vào điểm vay khi người dùng tự chọn trọng số (mặc định 0%; `experiments.montecarlo_ranking --suc-khoe-vay W`). Điểm là phân vị cắt ngang 22 ngân hàng, không phải lưới ngưỡng của Moody's, không phải hạng tín nhiệm và không suy ra khả năng được vay hay mức lãi. Phép kiểm trước khi gộp: `reports/kiem_suc_khoe_vay_2026-10-27.md`.

| Cột | Ý nghĩa |
|---|---|
| ticker, ky_BCTC | Mã ngân hàng, quý BCTC của ảnh chụp |
| problem_loans_pct | Nợ xấu + nợ nhóm 2, % dư nợ (nhóm tài sản, thấp tốt) |
| car_asof_percent, ky_CAR, CAR_thong_tu | CAR hợp nhất, kỳ nửa năm của số CAR, thông tư tính (nhóm vốn, đại diện chính) |
| equity_to_assets_pct | Vốn chủ / tổng tài sản, % (đại diện vốn thay thế, phép kiểm độ nhạy) |
| roa_ttm_percent | ROA 4 quý gần nhất (nhóm sinh lời) |
| deposits_to_assets_pct | Tiền gửi khách hàng / tổng tài sản, % ở quý BCTC (nhóm huy động) |
| liquid_assets_pct | Tài sản thanh khoản / tổng tài sản theo định nghĩa rộng của bộ dữ liệu (nhóm thanh khoản) |
| pv_tai_san, pv_von, pv_sinh_loi, pv_huy_dong, pv_thanh_khoan | Phân vị trong 22 ngân hàng (1 = tốt nhất), dùng CAR |
| diem_car, hang_car | Điểm tổng 0–1 (trọng số nhóm 25/25/15/20/15) và hạng, dùng CAR |
| diem_von_chu, hang_von_chu, dich_hang_doi_von | Như trên nhưng dùng vốn chủ/TTS; độ dịch hạng khi đổi đại diện vốn |
| o_thieu_dien_trung_vi | Chỉ tiêu thiếu, đã điền trung vị 22 ngân hàng (hiện chỉ CAR của NVB) |
| ten_bang | Tên bảng phải hiện kèm số |

## File kết quả thuật toán

### `rankings.csv` — xếp hạng tổng hợp (MCDM × Monte Carlo)

Sinh bằng `python -m serving.rankings --ranking <ảnh chụp>` sau `experiments.montecarlo_ranking --ranking <ảnh chụp>` (bảng mặc định, thêm `--so-tien 100e6,500e6,1e9,2e9,5e9` cho các mốc tiền). Quy trình và kiểm lỗi: `reports/xep_hang_2026-11-03.md`. Không có file thì giao diện hiện "chưa có kết quả" ở đúng chỗ.

Mỗi lần chạy ghi nhiều bảng: gửi — một bảng mỗi kỳ hạn × kênh ở trọng số mặc định (`amount_vnd` trống) và ở từng mốc tiền; vay — một bảng (`term_months`, `channel`, `amount_vnd` trống). Trang Gửi tiết kiệm lấy mốc tiền lớn nhất không vượt số tiền người gửi; Tổng quan lấy bảng 12 tháng trực tuyến ở trọng số mặc định.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| as_of_period | `YYYY-Qn` | Quý BCTC mới nhất của ảnh chụp |
| purpose | SAVINGS / LOAN | Mục đích |
| term_months, channel | int, ONLINE / COUNTER | Kỳ hạn × kênh của bảng gửi (trống với vay) |
| amount_vnd | int, có thể trống | Mốc tiền gửi; trống = trọng số mặc định (lãi 62,5 / an toàn 37,5) |
| rates_as_of | text | Ngày lãi gửi (YYYY-MM-DD) hoặc tháng lãi vay mới nhất (YYYY-MM) của ảnh chụp |
| uninsured_share | số 0–1 | Phần tiền (gốc + lãi đến hạn) vượt hạn mức bảo hiểm tiền gửi 350 triệu, ở mốc tiền đó |
| safety_weight | số 0–1 | Trọng số nhóm an toàn tại tâm sau khi nhân `uninsured_share` |
| ticker | text | Mã ngân hàng |
| rank | int | Hạng: trung bình 4 hạng điểm (SAW, TOPSIS, VIKOR, PROMETHEE II) tại trọng số mặc định, rồi theo p_top3 |
| rank_low, rank_high | int | p05 nhỏ nhất .. p95 lớn nhất của 4 thuật toán qua 10.000 lần rút trọng số (bao ngoài, không phải khoảng tin cậy) |
| p_top1, p_top3 | số 0–1 | Tần suất đứng đầu / lọt top 3 trong mô phỏng, trung bình 4 thuật toán. Không phải xác suất NH tốt nhất |
| score, group_label | trống | Giữ chỗ (không có điểm chung cho 4 thuật toán; không hiển thị nhóm k-means) |
| top_positive, top_negative | text | Tiêu chí đóng góp nhiều nhất (dương / âm) vào điểm SAW tại trọng số mặc định so với NH trung bình; ghi tên hiển thị |
| method_version | text | Bộ thuật toán |

Điểm/đánh giá ứng dụng (`app_store.csv`, `app_reviews_monthly.csv`, `app_aspects.csv`) và dự báo chỉ tiêu (`forecasts.csv`)
đã bỏ khỏi web ngày 29/10/2026 (migration V8): CSDL web chỉ giữ thứ hệ thống gợi ý dùng. `serving.export` không xuất các file đó
nữa; `serving/forecast.py --publish` nếu chạy vẫn ghi `forecasts.csv` nhưng backend không nạp.
