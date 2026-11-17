from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

RA = Path(__file__).resolve().parents[2] / "figures" / "khoa_luan" / "so_do"
RA.mkdir(parents=True, exist_ok=True)
plt.rcParams["font.family"] = "Times New Roman"
VIEN, NEN, NEN2, CAM, CHU = "#1f3b63", "#e8eef6", "#d6e2f0", "#eb6834", "#222222"


def hop(ax, x, y, w, h, tieu_de, chi_tiet="", nen=NEN, co=10, co2=8.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", lw=1.0,
                                edgecolor=VIEN, facecolor=nen))
    if chi_tiet:
        ax.text(x + w / 2, y + h * 0.76, tieu_de, ha="center", va="center", fontsize=co, fontweight="bold", color=VIEN)
        ax.text(x + w / 2, y + h * 0.36, chi_tiet, ha="center", va="center", fontsize=co2, color=CHU, linespacing=1.25)
    else:
        ax.text(x + w / 2, y + h / 2, tieu_de, ha="center", va="center", fontsize=co, fontweight="bold", color=VIEN,
                linespacing=1.25)


def mui_ten(ax, a, b, mau=VIEN):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=11, lw=1.1, color=mau))


def _khung(w, h, y0=0):
    fig, ax = plt.subplots(figsize=(w, h), dpi=300)
    ax.set_xlim(0, w * 10)
    ax.set_ylim(y0, y0 + h * 10)
    ax.axis("off")
    return fig, ax


def quy_trinh_ml():
    fig, ax = _khung(6.6, 1.9, y0=-5)
    buoc = ["Thu thập\ndữ liệu", "Tiền xử lý\nlàm sạch", "Phân tích\nkhám phá", "Tạo\nđặc trưng", "Huấn luyện\nmô hình",
            "Đánh giá\nmô hình", "Triển khai\nsử dụng"]
    w, gap = 8.4, 1.0
    for k, b in enumerate(buoc):
        x = 0.4 + k * (w + gap)
        hop(ax, x, 3, w, 9, b, nen=NEN2 if k in (4, 5) else NEN, co=8.4)
        if k < len(buoc) - 1:
            mui_ten(ax, (x + w + 0.05, 7.5), (x + w + gap - 0.05, 7.5))
    x4, x5 = 0.4 + 4 * (w + gap) + w / 2, 0.4 + 5 * (w + gap) + w / 2
    ax.annotate("", xy=(x4, 2.8), xytext=(x5, 2.8),
                arrowprops=dict(arrowstyle="-|>", color=CAM, lw=1.1, connectionstyle="arc3,rad=-0.5"))
    ax.text((x4 + x5) / 2, -3.6, "điều chỉnh, chọn lại (chỉ theo tập chọn)", ha="center", fontsize=8, color=CAM)
    fig.savefig(RA / "h2_quy_trinh_ml.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def cay(ax, cx, cy, s=1.0):
    nut = [(cx, cy), (cx - 2.2 * s, cy - 2.6 * s), (cx + 2.2 * s, cy - 2.6 * s), (cx - 3.3 * s, cy - 5.2 * s),
           (cx - 1.1 * s, cy - 5.2 * s), (cx + 1.1 * s, cy - 5.2 * s), (cx + 3.3 * s, cy - 5.2 * s)]
    for a, b in ((0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (2, 6)):
        ax.plot([nut[a][0], nut[b][0]], [nut[a][1], nut[b][1]], color=VIEN, lw=0.9)
    for k, (x, y) in enumerate(nut):
        ax.add_patch(plt.Circle((x, y), 0.55 * s, color="#2a78d6" if k < 3 else "#9ec5f4", zorder=3))


def random_forest():
    fig, ax = _khung(6.6, 3.6, y0=-2)
    hop(ax, 0.3, 12.5, 13, 9, "Tập huấn luyện", "n quan sát,\np đặc trưng", co=9.5)
    for k in range(3):
        y = 26 - k * 10.5
        hop(ax, 18, y, 13, 6.5, f"Mẫu bootstrap {k + 1}" if k < 2 else "Mẫu bootstrap B", co=8.6)
        mui_ten(ax, (13.5, 17), (17.8, y + 3.2))
        cay(ax, 39, y + 5.8, 0.9)
        mui_ten(ax, (31.3, y + 3.2), (34.6, y + 3.2))
        ax.text(39, y - 0.7, f"Cây {k + 1}" if k < 2 else "Cây B", ha="center", fontsize=8.5, color=CHU)
        mui_ten(ax, (43.5, y + 3.2), (48.6, 17))
    ax.plot([24.5] * 3, [12.4, 13.4, 14.4], "o", color=VIEN, ms=1.6)
    hop(ax, 49, 12.5, 12, 9, "Trung bình", "dự báo\ncủa B cây", nen=NEN2, co=9.5)
    mui_ten(ax, (61.2, 17), (63.4, 17))
    ax.text(64, 17, "ŷ", fontsize=14, va="center", color=CAM, fontweight="bold")
    ax.text(33, 0.2, "Mỗi lần tách nút, cây chỉ xét một tập con ngẫu nhiên các đặc trưng.", fontsize=8.2, color=CAM,
            ha="center")
    fig.savefig(RA / "h2_random_forest.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def mo_hinh_lai():
    fig, ax = _khung(6.6, 3.0)
    hop(ax, 0.3, 17, 15, 11, "Lịch sử chỉ tiêu", "giá trị của ngân hàng\nđến quý t", co=9.5)
    hop(ax, 0.3, 2, 15, 11, "Đặc trưng", "thay đổi gần đây,\nlãi tái cấp vốn,\nquý trong năm", co=9.5)
    hop(ax, 20.5, 17, 17, 11, "Mô hình cơ sở", "giữ nguyên, mùa vụ,\nxu hướng hoặc rolloff", co=9.5)
    hop(ax, 20.5, 2, 17, 11, "Random Forest", "học phần dư:\nthực tế − mô hình cơ sở", nen=NEN2, co=9.5)
    mui_ten(ax, (15.5, 22.5), (20.3, 22.5))
    mui_ten(ax, (15.5, 7.5), (20.3, 7.5))
    mui_ten(ax, (29, 16.8), (29, 13.2), CAM)
    ax.text(29.8, 15, "phần dư", fontsize=7.8, color=CAM, va="center")
    ax.add_patch(plt.Circle((44, 15), 2.2, facecolor="white", edgecolor=VIEN, lw=1.1))
    ax.text(44, 15, "+", ha="center", va="center", fontsize=15, color=VIEN)
    mui_ten(ax, (37.7, 22.5), (42.4, 16.6))
    mui_ten(ax, (37.7, 7.5), (42.4, 13.4))
    hop(ax, 49.5, 9.5, 16, 11, "Dự báo quý t + h", "= cơ sở + phần dư\nkèm khoảng 90%", nen=NEN2, co=9.5)
    mui_ten(ax, (46.3, 15), (49.3, 15))
    fig.savefig(RA / "h2_mo_hinh_lai.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def giai_doan():
    buoc = [
        ("Giai đoạn I. Thu thập và tiền xử lý dữ liệu", "BCTC quý của 22 ngân hàng, lãi suất theo ngày · đối chiếu nguồn, kiểm tra tự động"),
        ("Giai đoạn II. Phân tích khám phá dữ liệu", "Phân phối, xu hướng, mùa vụ, tương quan → chọn mô hình và đặc trưng"),
        ("Giai đoạn III. Mô hình dự báo chỉ tiêu tài chính", "Mô hình cơ sở + Random Forest học phần dư · kiểm định theo thời gian"),
        ("Giai đoạn IV. Xếp hạng gợi ý ngân hàng", "Bốn phương pháp MCDM · trọng số rút ngẫu nhiên · hạn mức BHTG"),
        ("Giai đoạn V. Xây dựng hệ thống web", "Next.js, Spring Boot, PostgreSQL, Docker · gợi ý gửi và vay, hồ sơ ngân hàng"),
    ]
    fig, ax = plt.subplots(figsize=(6.2, 5.2), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    h, gap, top = 1.45, 0.42, 9.9
    for k, (t, c) in enumerate(buoc):
        y = top - k * (h + gap) - h
        ax.add_patch(FancyBboxPatch((0.2, y), 9.6, h, boxstyle="round,pad=0.02,rounding_size=0.12", lw=1.1,
                                    edgecolor=VIEN, facecolor=NEN2 if k == 2 else NEN))
        ax.text(5, y + h - 0.45, t, ha="center", va="center", fontsize=10.5, fontweight="bold", color=VIEN)
        ax.text(5, y + 0.45, c, ha="center", va="center", fontsize=8.4, color=CHU)
        if k < len(buoc) - 1:
            ax.add_patch(FancyArrowPatch((5, y - 0.02), (5, y - gap + 0.02), arrowstyle="-|>", mutation_scale=12,
                                         lw=1.2, color=VIEN))
    fig.savefig(RA / "h3_giai_doan.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    quy_trinh_ml()
    random_forest()
    mo_hinh_lai()
    giai_doan()
    print("xong", RA)
