# EDA — khám phá dữ liệu theo quy trình của kênh Gà AI

Thư mục này làm EDA cho đề tài theo ba video:

| Video | Nội dung chính | Làm ở đâu |
|---|---|---|
| [EDA là gì? Hiểu EDA trong 4 phút](https://youtu.be/42WzSAD7KAY) | EDA có hai mức. **Sơ bộ**: dữ liệu có đủ sạch để dựng baseline chưa. **Chi tiết**: phân phối, ngoại lai, tương quan, tương tác, để cải thiện dữ liệu (tạo đặc trưng, làm sạch, xử lý lệch, encode, phát hiện rò rỉ) | Sơ bộ: `01`, `02` · Chi tiết: `03` |
| [Tại Sao Cần EDA Sơ Bộ? 6 Bước Trước Khi Visualization](https://youtu.be/k3Xvapm3QZk) | 6 bước: đọc file (`shape`, `head`), `info()`, `describe()`, trùng lặp, giá trị thiếu, phân phối nhãn. Gói cả 6 bước trong một hàm | `eda_utils.read_and_explore_data` |
| [EDA Nhanh: 7 Phút Mổ Xẻ Dataset Telco Churn](https://youtu.be/LaivB1LgVvs) | Chạy hàm (Lần 1: dữ liệu, Lần 2: target, `show=False`), bảng ý nghĩa đặc trưng theo nhóm (*Cột · Ý nghĩa · Ghi chú điều tra*), insight ban đầu, bước tiếp theo | `01`, `02` |

EDA ở đây theo nghĩa AI/ML mà anh hướng dẫn nêu: tìm liên hệ giữa các trường dữ liệu để chọn **hướng đi, thuật toán và feature engineering**. Vì vậy mỗi mục của EDA chi tiết đều kết thúc bằng "→ Hành động".

## Các file

| File | Nội dung |
|---|---|
| `eda_utils.py` | Hàm `read_and_explore_data`, giữ tham số và thứ tự bước như video, thêm: đọc cả thư mục, kiểm trùng khóa, cảnh báo sai kiểu và giá trị viết không thống nhất, mục tiêu liên tục. Thêm `quick_profile` để kiểm nhanh nhiều file |
| `01_EDA_so_bo_panel.ipynb` | EDA sơ bộ cho panel 22 NH × 34 quý (`data/model/features_selected.csv`) và kiểm nhanh các file còn lại; bảng ý nghĩa 88 đặc trưng theo nhóm CAMELS; insight |
| `02_EDA_so_bo_review.ipynb` | EDA sơ bộ cho 532.007 review app (`data/app_reviews/`), nhãn `score`; vì sao thiếu, vì sao trùng; ý nghĩa từng cột; insight |
| `03_EDA_chi_tiet.ipynb` | EDA chi tiết: phân phối, ngoại lai, tương quan (giữa NH / trong NH), liên hệ với mục tiêu (mùa vụ, rolloff, độ trễ), rò rỉ, phân cụm, độ dài review, khía cạnh; bảng tổng hợp phát hiện → hành động |
| `tu_dien.py` | Sinh bảng ý nghĩa đặc trưng (ký hiệu 🎯 ★ ⚠️ 🔍) từ `feature_catalog.csv` và kết quả EDA |
| `tu_dien_dac_trung.csv` | Bảng ý nghĩa đặc trưng đầy đủ (88 dòng) để dán vào khóa luận |

## Chạy lại

1. Nếu dữ liệu mô hình vừa đổi, chạy lại chuỗi dựng dữ liệu, rồi tính phần EDA nặng (~3 phút):
   ```
   python -m crawlers.build_features
   python -m crawlers.select_features
   python -m experiments.eda_ml
   ```
2. Mở notebook trong VS Code, chọn kernel `.venv`, bấm **Run All**. Thứ tự: `01` → `02` → `03`.

Notebook tự tìm thư mục gốc dự án (thư mục có `data/model`). Muốn chạy trên Colab thì tải cả `EDA/` và `data/` lên cùng một thư mục.

Các đoạn *Insight* và *Nhận xét* là chữ viết tay dựa trên output ngày 23/09/2026 (dữ liệu tới 2026-Q2). Khi có BCTC quý mới, chạy lại rồi đối chiếu số trong các đoạn đó.
