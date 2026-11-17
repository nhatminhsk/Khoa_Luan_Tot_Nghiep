from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

RA = Path(__file__).resolve().parents[2] / "figures" / "khoa_luan" / "h1_1_khung_nghien_cuu.png"

plt.rcParams["font.family"] = "Times New Roman"

BUOC = [
    ("1. Dữ liệu công khai",
     "BCTC quý của 22 ngân hàng niêm yết (2018-Q1 đến 2026-Q3) · biểu lãi suất tiền gửi theo ngày\n"
     "lãi suất cho vay bình quân theo tháng · giá cổ phiếu · chỉ số vĩ mô"),
    ("2. Thu thập, làm sạch, kiểm chéo",
     "Bảng ngân hàng–quý 22 × 35 = 770 quan sát · bảng lãi suất theo ngày và theo tháng\n"
     "đối chiếu giữa các nguồn · cổng kiểm tra chất lượng trước khi dùng"),
    ("3. Phân tích bằng học máy (CH1–CH6)",
     "Dự báo chỉ tiêu · đoán ngân hàng xấu đi · phân nhóm và chế độ thị trường · xếp hạng bằng ML\n"
     "mọi mô hình so với mô hình cơ sở · kiểm định theo thời gian · khoảng tin cậy bootstrap"),
    ("4. Hàm ý và khuyến nghị",
     "Người gửi tiền · người vay · ngân hàng thương mại · cơ quan quản lý\n"
     "mỗi khuyến nghị ghi rõ căn cứ ở kết quả phân tích"),
    ("5. Hệ thống gợi ý trên web",
     "Lọc ngân hàng theo nhu cầu → tổng hợp bằng SAW, TOPSIS, VIKOR, PROMETHEE II\n"
     "với trọng số rút ngẫu nhiên → xác suất đứng đầu, khoảng hạng, tiền lãi ước tính"),
]

fig, ax = plt.subplots(figsize=(7.2, 7.6), dpi=200)
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis("off")

h, gap = 1.55, 0.42
top = 9.9
mau_vien = "#1f3b63"
mau_nen = ["#e8eef6", "#e8eef6", "#d6e2f0", "#e8eef6", "#d6e2f0"]
for k, (tieu_de, chi_tiet) in enumerate(BUOC):
    y = top - k * (h + gap) - h
    box = FancyBboxPatch((0.25, y), 9.5, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                         linewidth=1.2, edgecolor=mau_vien, facecolor=mau_nen[k])
    ax.add_patch(box)
    ax.text(5, y + h - 0.38, tieu_de, ha="center", va="center", fontsize=12, fontweight="bold", color=mau_vien)
    ax.text(5, y + 0.58, chi_tiet, ha="center", va="center", fontsize=9.2, color="#222222", linespacing=1.45)
    if k < len(BUOC) - 1:
        ax.add_patch(FancyArrowPatch((5, y - 0.02), (5, y - gap + 0.02), arrowstyle="-|>", mutation_scale=14,
                                     linewidth=1.3, color=mau_vien))

RA.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(RA, bbox_inches="tight", facecolor="white")
print(RA)
