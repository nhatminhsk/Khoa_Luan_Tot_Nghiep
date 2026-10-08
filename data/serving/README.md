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
| `banks.csv` | ticker | ticker, short_name, full_name, app_name |
| `indicators.csv` | code | code, name, camels_group (C/A/M/E/L/G), unit (PERCENT/VND), direction (HIGHER_BETTER/LOWER_BETTER/NEUTRAL), description, display_order |
| `bank_quarterly.csv` | ticker, period, indicator | ticker, period, period_end, indicator, value |
| `deposit_rates.csv` | rate_date, ticker, term_months, channel | rate_date, ticker, term_months, channel (ONLINE/COUNTER), rate_percent, source |
| `deposit_rate_tiers.csv` | ticker, term_months, channel, min_amount_vnd | ticker, term_months, channel, min_amount_vnd, rate_percent, base_rate_percent, tier_label, valid_from, source — bậc trên bậc thấp nhất theo số tiền gửi, cho ngày mới nhất của `deposit_rates`; chỉ áp khi lãi trong `deposit_rates` bằng `base_rate_percent` |
| `lending_rates.csv` | month, ticker | month, ticker, lending_avg_percent, deposit_avg_percent, segment (INDIVIDUAL/ALL/UNSPECIFIED), basis (NEW_LOANS/OUTSTANDING/trống), source (BANK/VIETNAMNET), source_url — mỗi ngân hàng × tháng một số: số khách hàng cá nhân ngân hàng công bố trên web, không có thì số chung, cuối cùng là số VietnamNet (UNSPECIFIED); deposit_avg_percent = lãi vay − chênh lệch ngân hàng công bố |
| `app_store.csv` | ticker, store | ticker, store (GOOGLE_PLAY/APP_STORE), snapshot_date, app_name, score, ratings |
| `app_reviews_monthly.csv` | ticker, month | ticker, month, n_reviews, mean_score, pct_1star, pct_5star, usable |
| `programs.csv` | program_code | program_code, program_name, category (HOUSING/AGRICULTURE/BUSINESS/INFRASTRUCTURE/OTHER) |
| `program_participation.csv` | program_code, ticker | program_code, ticker, participates (0/1), list_as_of, source_url |
| `program_rates.csv` | — | program_code, borrower_group, valid_from, valid_to, rate_pct_year, spread_below_avg_min_pct, spread_below_avg_max_pct, source_url |
| `macro_cpi.csv` | month | month, cpi_yoy_percent (lạm phát so cùng kỳ, %), cpi_mom_percent, source_url — từ 2019-01; web tính lãi suất thực = lãi niêm yết − cpi_yoy_percent |
| `bank_ownership.csv` | ticker | ticker, as_of_date, state_own_percent, foreign_own_percent, foreign_room_percent, source — ảnh chụp mới nhất của từng ngân hàng |
| `datasets.csv` | dataset | dataset, name, source, frequency, last_updated, row_count, coverage_note |

## File kết quả thuật toán (chưa sinh — sẽ do bước mô hình ghi)

Khi chưa có các file này, giao diện hiện "chưa có kết quả" ở đúng chỗ. Ghi file đúng schema dưới đây là đủ: không cần sửa backend hay giao diện.

### `rankings.csv` — xếp hạng mặc định

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| as_of_period | `YYYY-Qn` | Quý dữ liệu dùng để xếp |
| purpose | SAVINGS / LOAN | Mục đích |
| ticker | text | Mã ngân hàng |
| rank | int | Hạng (1 = tốt nhất) |
| rank_low, rank_high | int | Khoảng hạng (tốt nhất, tệ nhất) |
| score | số 0–1 | Điểm tổng hợp (ví dụ độ gần nghiệm lý tưởng của TOPSIS) |
| group_label | text, có thể trống | Nhóm ngân hàng, chỉ ghi cho ngân hàng có nhóm ổn định |
| top_positive, top_negative | text, có thể trống | Mã chỉ tiêu kéo hạng lên / xuống nhiều nhất |
| method_version | text | Phiên bản bộ tiêu chí và trọng số |

### `forecasts.csv` — dự báo 1–4 quý

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| ticker | text | Mã ngân hàng |
| indicator | text | Mã chỉ tiêu trong `indicators.csv` (nim, cof, npl, casa, ldr, roe) |
| origin_period | `YYYY-Qn` | Quý cuối cùng có số thật lúc dự báo |
| target_period | `YYYY-Qn` | Quý được dự báo |
| horizon | int 1–4 | Tầm dự báo |
| value | số | Giá trị dự báo |
| lower, upper | số | Biên dưới, biên trên của khoảng dự báo |
| naive_value | số | Mốc so sánh (giữ nguyên quý trước, hoặc naive có mùa vụ / drift theo chỉ tiêu) |
| method | text | Tên mô hình |

### `app_aspects.csv` — điểm review theo khía cạnh (NLP)

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| ticker | text | Mã ngân hàng |
| period | `YYYY-Qn` | Quý |
| aspect | TRANSACTION_ERROR / LOGIN_OTP / UPDATE_UI / SPEED / CUSTOMER_CARE / CARD_ATM / FEE / SAVINGS | Khía cạnh |
| score | số −1…1 | Điểm cảm xúc trung bình |
| n_reviews | int | Số review nhắc tới khía cạnh |
