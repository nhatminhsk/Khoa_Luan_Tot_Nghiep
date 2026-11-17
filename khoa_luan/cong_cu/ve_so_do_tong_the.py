from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

RA = Path(__file__).resolve().parents[2] / "figures" / "khoa_luan" / "so_do"
RA.mkdir(parents=True, exist_ok=True)
plt.rcParams["font.family"] = "Times New Roman"
VIEN, NEN, NEN2, CAM = "#1f3b63", "#e8eef6", "#d6e2f0", "#b4532a"
H, G = 0.9, 0.6  # chiều cao một khối, khoảng cách giữa hai tầng (chỗ cho mũi tên)


def hop(ax, x, y, w, h, tieu_de, nen=NEN, vien=VIEN, net="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.10", lw=1.0,
                                edgecolor=vien, facecolor=nen, linestyle=net))
    ax.text(x + w / 2, y + h / 2, tieu_de, ha="center", va="center", fontsize=10, fontweight="bold", color=vien)


def mui(ax, a, b, mau=VIEN, net="-", rad=0.0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=10, lw=1.0, color=mau, linestyle=net,
                                 connectionstyle=f"arc3,rad={rad}"))


def ve():
    # tọa độ y (mép dưới) của từng tầng, tính từ dưới lên
    y_web = 0.1
    y_xh = y_web + H + G                 # bộ máy xếp hạng / đầu ra dự báo
    y_ts = y_xh + H + G                  # trọng số giả định
    y_bt = y_ts + H + 0.25               # bài toán gửi / vay
    y_bang = y_bt + H + G                # bảng ngân hàng–quý / ảnh chụp
    y_vao = y_bang + H + G               # dữ liệu đầu vào
    tran = y_vao + H + 0.15
    fig, ax = plt.subplots(figsize=(6.6, tran * 0.5), dpi=300)
    ax.set_xlim(0, 13.2)
    ax.set_ylim(0, tran)
    ax.axis("off")
    # tầng 1: dữ liệu đầu vào
    hop(ax, 0.2, y_vao, 12.8, H, "Dữ liệu đầu vào (nguồn công khai)")
    # tầng 2: bảng dữ liệu
    hop(ax, 0.2, y_bang, 6.2, H, "Bảng ngân hàng–quý")
    hop(ax, 6.8, y_bang, 6.2, H, "Ảnh chụp dữ liệu đóng băng")
    mui(ax, (3.3, y_vao), (3.3, y_bang + H))
    mui(ax, (9.9, y_vao), (9.9, y_bang + H))
    mui(ax, (6.4, y_bang + H / 2), (6.8, y_bang + H / 2))
    # tầng 3: mô hình dự báo (bên trái, cao bằng hai khối bên phải) và bộ tiêu chí (bên phải)
    hop(ax, 0.2, y_ts, 6.2, y_bt + H - y_ts, "Mô hình dự báo (học máy)", nen=NEN2)
    mui(ax, (3.3, y_bang), (3.3, y_bt + H))
    hop(ax, 6.8, y_bt, 2.95, H, "Bài toán gửi")
    hop(ax, 10.05, y_bt, 2.95, H, "Bài toán vay")
    hop(ax, 6.8, y_ts, 6.2, H, "Trọng số giả định")
    mui(ax, (8.27, y_bang), (8.27, y_bt + H))
    mui(ax, (11.52, y_bang), (11.52, y_bt + H))
    # tầng 4: bộ máy xếp hạng
    hop(ax, 6.8, y_xh, 6.2, H, "Bộ máy xếp hạng")
    mui(ax, (9.9, y_ts), (9.9, y_xh + H))
    # nhánh dự báo: nét đứt
    hop(ax, 0.2, y_xh, 6.2, H, "Đầu ra của dự báo", nen="white", vien=CAM, net="--")
    mui(ax, (3.3, y_ts), (3.3, y_xh + H), mau=CAM, net="--")
    # tầng 5: hệ thống web
    hop(ax, 0.2, y_web, 12.8, H, "Ứng dụng web BankAdvisor (Spring Boot + PostgreSQL + Next.js)")
    mui(ax, (9.9, y_xh), (9.9, y_web + H))
    fig.savefig(RA / "h1_so_do_tong_the.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("ghi", RA / "h1_so_do_tong_the.png")


if __name__ == "__main__":
    ve()
