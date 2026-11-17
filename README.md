# Hệ thống hỗ trợ lựa chọn ngân hàng gửi tiết kiệm và vay vốn

Mã nguồn và dữ liệu đã xử lý của khóa luận tốt nghiệp *Xây dựng hệ thống hỗ trợ ra quyết định lựa chọn ngân hàng vay/gửi tiền dựa trên phân tích dữ liệu tài chính bằng Machine Learning*. Phạm vi: 22 ngân hàng thương mại niêm yết tại Việt Nam.

Hệ thống có ba phần:

1. **Dữ liệu** (`crawlers/`): thu thập lãi suất tiền gửi hằng ngày từ biểu lãi của từng ngân hàng, lãi cho vay bình quân, báo cáo tài chính theo quý, CAR, CPI, lãi suất điều hành; làm sạch, dựng bảng ngân hàng–quý và kiểm tra chất lượng.
2. **Mô hình** (`serving/`, `experiments/`): mô hình lai (mô hình cơ sở + rừng ngẫu nhiên học phần dư) dự báo NPL, CASA, LDR; xếp hạng gợi ý bằng SAW, TOPSIS, VIKOR, PROMETHEE II kết hợp mô phỏng Monte Carlo trên trọng số.
3. **Ứng dụng web** (`webapp/`): backend Spring Boot, giao diện Next.js, nạp dữ liệu từ `data/serving/`.

## Cấu trúc thư mục

```
crawlers/            thu thập, làm sạch, đối chiếu, dựng bảng, cổng kiểm tra chất lượng (validate.py)
serving/             forecast.py (dự báo), rankings.py (xếp hạng), export.py (xuất CSV cho web)
experiments/         các thực nghiệm dùng trong khóa luận
data/
  interest_rates/    lãi suất tiền gửi theo ngày, lãi cho vay bình quân
  credit/            nợ xấu, CASA, tín dụng, CAR theo ngân hàng
  macro/, market/    CPI, lãi điều hành, chỉ số giá, VN-Index
  model/             bảng ngân hàng–quý, đặc trưng, tiêu chí xếp hạng, kết quả thực nghiệm
  serving/           các tệp CSV ứng dụng web nạp vào cơ sở dữ liệu
webapp/
  backend/           Spring Boot 4.1 (Java 25), Flyway V1–V11
  frontend/          Next.js 16, React 19, MUI 9
  deploy/            nginx, sao lưu, chứng chỉ, cài đặt VPS
  kiem_thu/          kiểm thử bổ sung API và giao diện
  docker-compose*.yml
pipeline/            ảnh Docker chạy thu thập hằng ngày
khoa_luan/cong_cu/   chương trình vẽ hình và ráp báo cáo
run_daily_crawl.py   chạy các bước thu thập hằng ngày rồi xuất data/serving
```

## Cài đặt

Cần Python 3.11, Java 25 trở lên, Node.js 24 và Docker Desktop nếu chạy bằng Docker.

```
git clone https://github.com/nhatminhsk/Khoa_Luan_Tot_Nghiep.git
cd Khoa_Luan_Tot_Nghiep
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Gói `vnstock_data` (báo cáo tài chính, giá cổ phiếu) không có trên PyPI, phải cài theo hướng dẫn của Vnstock. Một số trang biểu lãi suất chỉ hiện bằng JavaScript nên `crawlers/deposit_official.py` và `crawlers/lending_rates_official.py` cần Microsoft Edge để đọc trang ở chế độ headless.

## Chạy

Cập nhật dữ liệu (tùy chọn, dữ liệu đã xử lý có sẵn trong `data/`):

```
python run_daily_crawl.py
python -m crawlers.build_panel
python -m crawlers.build_long_panel
python -m serving.forecast
python -m experiments.montecarlo_ranking
python -m serving.rankings
python -m serving.export
```

`serving.rankings` đọc kết quả Monte Carlo, nên `experiments.montecarlo_ranking` phải chạy trước trên cùng ảnh chụp dữ liệu (thêm `--so-tien 100e6,500e6,1e9,2e9,5e9` nếu cần xếp hạng theo số tiền gửi). `run_daily_crawl.py` nên đặt lịch sau 15 giờ (giờ đóng cửa thị trường), từ thư mục gốc của dự án vì các chương trình dùng đường dẫn tương đối. Kiểm tra chất lượng dữ liệu: `python -m crawlers.validate`.

Máy chủ (trong `webapp/backend`): sao chép `.env.example` thành `.env`, điền khóa ký JWT (tối thiểu 32 ký tự) rồi chạy `mvnw spring-boot:run`. Máy chủ nghe ở cổng 8080 và tự nạp dữ liệu từ `data/serving` lúc khởi động và 16 giờ mỗi ngày.

Giao diện (trong `webapp/frontend`): `npm install`, `npm run dev`, mở http://localhost:3000.

Docker (trong `webapp`): tạo `.env` theo `.env.example` (ít nhất `APP_DB_PASSWORD`, `APP_JWT_SECRET`) rồi `docker compose up -d --build`; ghép thêm `docker-compose.https.yml` để chạy qua HTTPS. Chi tiết ở `webapp/README.md`.

Kiểm thử: `mvnw test` trong `webapp/backend`; `python webapp/kiem_thu/kiem_thu_api.py <địa chỉ máy chủ>` và `node webapp/kiem_thu/kiem_thu_giao_dien.mjs <địa chỉ giao diện>`.

## Thực nghiệm trong khóa luận

| Lệnh | Nội dung | Kết quả ghi vào |
|---|---|---|
| `python -m experiments.danh_gia_co_dinh` | Đánh giá mô hình dự báo theo thiết kế cố định (huấn luyện từ 2019, tập chọn 2021–2022, tập kiểm tra từ 2023) | `data/model/experiments/danh_gia_co_dinh/` |
| `python -m experiments.montecarlo_ranking --ranking data/model/experiments/inputs/features_ranking_2026-11-06.csv` | Xếp hạng MCDM kết hợp Monte Carlo trên trọng số | `data/model/experiments/montecarlo_*.csv` |
| `python -m experiments.do_nhay_xep_hang` | Độ nhạy của bảng xếp hạng theo trọng số và giả định dữ liệu | `data/model/experiments/do_nhay_xep_hang/` |
| `python -m experiments.xep_hang_voi_du_bao` | Thay NPL, CASA, LDR bằng giá trị dự báo rồi xếp hạng lại | `data/model/experiments/xep_hang_voi_du_bao.csv` |
| `python -m experiments.hyperparam_tuning`, `python -m experiments.hyperparam_search` | Tìm tham số bằng lưới, ngẫu nhiên, Hyperband, Bayes (Optuna) | `data/model/experiments/hyperparam_*.csv` |
| `python -m experiments.eda` | Phân tích khám phá, phân rã phương sai giữa và trong ngân hàng | `data/model/eda/` |

Tham số cố định (rừng ngẫu nhiên 300 cây, tối thiểu 10 mẫu mỗi lá, 33% đặc trưng mỗi lần tách, hạt giống 20261013; bootstrap 2.000 lần theo ngân hàng) được ghi vào `danh_gia_co_dinh/config.json` trước mỗi lần chạy, kèm phiên bản thư viện và mã băm của tệp dữ liệu.

## Nguồn dữ liệu

| Dữ liệu | Nguồn | Tần suất, phạm vi |
|---|---|---|
| BCTC quý (cân đối, kết quả kinh doanh, thuyết minh) | Thư viện vnstock, nguồn VCI | Quý, 2018-Q1 đến 2026-Q3 |
| Chỉ số tài chính theo quý | vnstock, nguồn MAS | Quý, 2012-Q1 đến 2026-Q3 |
| BCTC 2012–2017 bản quét (NPL, CASA, LDR) | Vietstock, trang web ngân hàng; đọc bằng RapidOCR | Quý, 528 ngân hàng–quý |
| Tỷ lệ an toàn vốn (CAR) | Báo cáo công bố của ngân hàng | Nửa năm, 2019 đến 2026-H1 |
| Lãi suất tiền gửi niêm yết | Biểu lãi chính thức của từng ngân hàng, 24HMoney | Ngày, 7 kỳ hạn × 2 kênh × 22 ngân hàng |
| Lãi cho vay bình quân | Trang web ngân hàng, NHNN | Tháng, từ 03/2024 |
| Lãi suất điều hành, CPI | NHNN, Cục Thống kê | Theo quyết định; tháng |
| Đối chiếu bên ngoài | World Bank, bộ dữ liệu Harvard Dataverse (Thanh Ngo, 2002–2021) | Năm |

Không đưa lên repo: dữ liệu BCTC thô (`data/vnstock_financial/`, tải lại bằng crawler), PDF BCTC dùng cho OCR, tệp `.env` và bản sao lưu cơ sở dữ liệu.
