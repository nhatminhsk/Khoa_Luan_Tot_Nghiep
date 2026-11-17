from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyArrowPatch, Polygon, Rectangle

GOC = Path(__file__).resolve().parents[2]
RA = GOC / "figures" / "khoa_luan"
DEN = "#111111"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 8})


def _canvas(w_in: float, h_in: float, w_u: float):
    fig = plt.figure(figsize=(w_in, h_in))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w_u)
    ax.set_ylim(0, w_u * h_in / w_in)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def _luu(fig, ten: str) -> None:
    RA.mkdir(parents=True, exist_ok=True)
    fig.savefig(RA / ten, dpi=300, facecolor="white")
    plt.close(fig)
    print("đã ghi", RA / ten)


# ---------------------------------------------------------------- use case
def _tac_nhan(ax, x, y, ten):
    ax.add_patch(plt.Circle((x, y + 0.62), 0.17, fill=False, lw=0.9, ec=DEN))
    ax.plot([x, x], [y + 0.45, y], color=DEN, lw=0.9)
    ax.plot([x - 0.3, x + 0.3], [y + 0.3, y + 0.3], color=DEN, lw=0.9)
    ax.plot([x, x - 0.24], [y, y - 0.42], color=DEN, lw=0.9)
    ax.plot([x, x + 0.24], [y, y - 0.42], color=DEN, lw=0.9)
    ax.text(x, y - 0.55, ten, ha="center", va="top", fontsize=8, linespacing=1.1)
    return {"phai": (x + 0.34, y + 0.3), "trai": (x - 0.34, y + 0.3),
            "tren": (x, y + 0.82), "duoi": (x, y - 0.55 - 0.22 * (ten.count("\n") + 1))}


class UC:
    W, H = 3.25, 0.9

    def __init__(self, ax, x, y, ten):
        self.x, self.y = x, y
        ax.add_patch(Ellipse((x, y), self.W, self.H, fill=True, fc="white", ec=DEN, lw=0.9, zorder=3))
        ax.text(x, y, ten, ha="center", va="center", fontsize=8, linespacing=1.05, zorder=4)

    def bien(self, tx, ty):
        dx, dy = tx - self.x, ty - self.y
        t = 1 / ((dx / (self.W / 2)) ** 2 + (dy / (self.H / 2)) ** 2) ** 0.5
        return self.x + t * dx, self.y + t * dy

    @property
    def trai(self):
        return self.x - self.W / 2, self.y

    @property
    def phai(self):
        return self.x + self.W / 2, self.y

    @property
    def tren(self):
        return self.x, self.y + self.H / 2

    @property
    def duoi(self):
        return self.x, self.y - self.H / 2


def _lien_ket(ax, p, q):
    ax.plot([p[0], q[0]], [p[1], q[1]], color=DEN, lw=0.75, zorder=2)


def _mui_ten_dut(ax, diem, nhan, vt_nhan, ha="left"):
    xs, ys = zip(*diem)
    ax.plot(xs[:-1] + (xs[-1],), ys[:-1] + (ys[-1],), color=DEN, lw=0.75, ls=(0, (4, 2.5)), zorder=2)
    ax.add_patch(FancyArrowPatch(diem[-2], diem[-1], arrowstyle="->,head_length=4,head_width=2.6",
                                 color=DEN, lw=0.75, shrinkA=0, shrinkB=0, zorder=2,
                                 linestyle=(0, (4, 2.5))))
    ax.text(*vt_nhan, nhan, ha=ha, va="center", fontsize=7.5, zorder=4,
            bbox=dict(fc="white", ec="none", pad=0.4))


def _ke_thua(ax, p, q):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>,head_length=7,head_width=4.5", fc="white",
                                 ec=DEN, lw=0.8, shrinkA=0, shrinkB=0, zorder=2))


def _kiem_cat(lien_ket, ucs) -> None:
    for p, q, dich, *nguon in lien_ket:
        for u in ucs:
            if u is dich or u in nguon:
                continue
            for k in range(1, 200):
                t = k / 200
                x, y = p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])
                if ((x - u.x) / (u.W / 2 + 0.06)) ** 2 + ((y - u.y) / (u.H / 2 + 0.06)) ** 2 < 1:
                    print(f"  CẮT: đường tới '{dich.ten}' đi qua '{u.ten}'")
                    break


def use_case() -> None:
    fig, ax = _canvas(6.3, 5.25, 16.0)
    # khung hệ thống
    ax.add_patch(Rectangle((2.55, 0.35), 10.9, 12.55, fill=False, ec=DEN, lw=1.0))
    ax.text(8.0, 12.55, "Hệ thống gợi ý ngân hàng BankAdvisor", ha="center", va="center",
            fontsize=9, fontweight="bold")

    xl, xr = 4.95, 11.55
    uc1 = UC(ax, xl, 11.55, "Xem tổng quan thị trường")
    uc4 = UC(ax, xl, 10.5, "Tra cứu, so sánh\nngân hàng")
    uc5 = UC(ax, xl, 9.45, "Xem phương pháp\nvà nguồn dữ liệu")
    uc6 = UC(ax, xl, 8.4, "Đăng ký, đăng nhập")
    uc2 = UC(ax, xl, 7.35, "Nhận gợi ý\ngửi tiết kiệm")
    uc3 = UC(ax, xl, 6.3, "Nhận gợi ý vay")
    # cột giữa: use case riêng của người dùng
    uc7 = UC(ax, 8.35, 4.6, "Lưu nhu cầu")
    uc8 = UC(ax, 6.6, 2.55, "Theo dõi ngân hàng,\nnhận thông báo")
    # cột phải
    uc9 = UC(ax, xr, 11.55, "Quản lý dữ liệu, nạp lại")
    uc10 = UC(ax, xr, 10.5, "Quản lý người dùng,\nxem nhật ký")
    uc11 = UC(ax, xr, 9.45, "Quản lý hàng đợi thư")
    uc12 = UC(ax, xr, 7.55, "Nạp dữ liệu hằng ngày")
    uc13 = UC(ax, xr - 0.6, 6.05, "Tạo thông báo\ncho người theo dõi")
    uc15 = UC(ax, xr - 0.6, 3.25, "Sao lưu cơ sở dữ liệu")
    uc14 = UC(ax, xr, 1.55, "Gửi thư thông báo")
    ucs = [uc1, uc4, uc5, uc6, uc2, uc3, uc7, uc8, uc9, uc10, uc11, uc12, uc13, uc15, uc14]
    for u, t in zip(ucs, ["tổng quan", "tra cứu", "phương pháp", "đăng ký", "gửi", "vay", "lưu nhu cầu",
                          "theo dõi", "dữ liệu", "người dùng", "hàng đợi", "nạp", "tạo thông báo", "sao lưu",
                          "gửi thư"]):
        u.ten = t

    khach = _tac_nhan(ax, 1.15, 8.6, "Khách")
    nd = _tac_nhan(ax, 1.15, 2.9, "Người dùng\nđã đăng nhập")
    qtv = _tac_nhan(ax, 14.75, 10.2, "Quản trị viên")
    cttt = _tac_nhan(ax, 14.75, 7.6, "Chương trình\nthu thập dữ liệu")
    bll = _tac_nhan(ax, 14.75, 4.3, "Bộ lập lịch")
    mct = _tac_nhan(ax, 14.75, 1.3, "Máy chủ thư")

    lk = []
    for a, us in ((khach["phai"], (uc1, uc4, uc5, uc6, uc2, uc3)), (nd["phai"], (uc7, uc8)),
                  (qtv["trai"], (uc9, uc10, uc11)), (cttt["trai"], (uc12,)),
                  (bll["trai"], (uc12, uc15, uc14)), (mct["trai"], (uc14,))):
        for u in us:
            q = u.trai if a[0] < u.x else u.phai  # nối vào đầu elip phía tác nhân
            _lien_ket(ax, a, q)
            lk.append((a, q, u))

    # người dùng kế thừa khách
    _ke_thua(ax, (1.15, nd["tren"][1] + 0.05), (1.15, khach["duoi"][1] - 0.08))
    # lưu nhu cầu mở rộng hai use case nhận gợi ý
    p3 = uc7.bien(uc3.phai[0], uc3.y)
    q3 = uc3.bien(*p3)
    _mui_ten_dut(ax, [p3, q3], "«extend»", (p3[0] + 0.62 * (q3[0] - p3[0]) - 0.1,
                                            p3[1] + 0.62 * (q3[1] - p3[1]) - 0.22), ha="center")
    p2 = uc7.bien(uc7.x - 0.15, uc7.y + 1)
    q2 = uc2.bien(uc2.x + 1.7, uc2.y + 0.1)
    _mui_ten_dut(ax, [p2, q2], "«extend»", (p2[0] + 0.62 * (q2[0] - p2[0]) + 0.05,
                                            p2[1] + 0.62 * (q2[1] - p2[1])), ha="center")
    # nạp dữ liệu bao gồm tạo thông báo
    a13 = uc12.bien(uc13.x, uc13.y)
    b13 = uc13.bien(*a13)
    _mui_ten_dut(ax, [a13, b13], "«include»", ((a13[0] + b13[0]) / 2 + 0.15, (a13[1] + b13[1]) / 2))
    _kiem_cat(lk + [(p3, q3, uc3, uc7), (p2, q2, uc2, uc7), (a13, b13, uc13, uc12)], ucs)
    _luu(fig, "h4_use_case_uml.png")


# ---------------------------------------------------------------- triển khai
def _nut(ax, x, y, w, h, khuon, ten, d=0.25, lw=0.9, cn=None, tren=True, co_khuon=7.2):
    ax.add_patch(Rectangle((x, y), w, h, fc="white", ec=DEN, lw=lw, zorder=1))
    ax.add_patch(Polygon([(x, y + h), (x + d, y + h + d), (x + w + d, y + h + d), (x + w, y + h)],
                         closed=True, fc="white", ec=DEN, lw=lw, zorder=1))
    ax.add_patch(Polygon([(x + w, y), (x + w + d, y + d), (x + w + d, y + h + d), (x + w, y + h)],
                         closed=True, fc="white", ec=DEN, lw=lw, zorder=1))
    yy = y + h - 0.3 if tren else y + h / 2 + 0.35
    ax.text(x + w / 2, yy, khuon, ha="center", va="center", fontsize=co_khuon, zorder=4)
    ax.text(x + w / 2, yy - 0.36, ten, ha="center", va="center", fontsize=8, fontweight="bold", zorder=4)
    for i, c in enumerate(cn or []):
        ax.text(x + w / 2, yy - 0.76 - 0.34 * i, c, ha="center", va="center", fontsize=7.5, zorder=4)


def _artifact(ax, x, y, w, h, ten, chi_tiet=None):
    ax.add_patch(Rectangle((x, y), w, h, fc="white", ec=DEN, lw=0.85, zorder=3))
    # biểu tượng tài liệu gấp góc
    ix, iy, s = x + w - 0.42, y + h - 0.5, 0.3
    ax.add_patch(Polygon([(ix, iy), (ix, iy + s), (ix + s * 0.65, iy + s), (ix + s * 0.9, iy + s * 0.75),
                          (ix + s * 0.9, iy)], closed=True, fc="white", ec=DEN, lw=0.6, zorder=4))
    ax.plot([ix + s * 0.65, ix + s * 0.65, ix + s * 0.9], [iy + s, iy + s * 0.75, iy + s * 0.75],
            color=DEN, lw=0.6, zorder=4)
    ax.text(x + w / 2 - 0.15, y + h - 0.32, "«artifact»", ha="center", va="center", fontsize=7.2, zorder=4)
    ax.text(x + w / 2 - 0.15, y + h - 0.68, ten, ha="center", va="center", fontsize=8, fontweight="bold",
            zorder=4)
    if chi_tiet:
        ax.text(x + w / 2 - 0.15, y + h - 1.02, chi_tiet, ha="center", va="center", fontsize=7.5, zorder=4)


def _duong(ax, diem, nhan=None, vt=None, mui_ten=False, dut=False, ha="center", va="center"):
    ls = (0, (4, 2.5)) if dut else "-"
    xs, ys = zip(*diem)
    ax.plot(xs, ys, color=DEN, lw=0.8, ls=ls, zorder=2)
    if mui_ten:
        ax.add_patch(FancyArrowPatch(diem[-2], diem[-1], arrowstyle="->,head_length=4,head_width=2.6",
                                     color=DEN, lw=0.8, shrinkA=0, shrinkB=0, zorder=2, linestyle=ls))
    if nhan:
        ax.text(*vt, nhan, ha=ha, va=va, fontsize=7.3, zorder=5, bbox=dict(fc="white", ec="none", pad=0.5))


def trien_khai() -> None:
    fig, ax = _canvas(6.3, 5.75, 16.0)
    # máy người dùng và máy chủ thư (bên ngoài)
    _nut(ax, 0.1, 10.35, 3.45, 2.85, "«device»", "Máy tính, điện thoại")
    _nut(ax, 0.3, 10.6, 2.9, 1.35, "«execution environment»", "Trình duyệt web", d=0.18, tren=False,
         co_khuon=6.6)
    _nut(ax, 0.1, 6.55, 3.45, 1.6, "«device»", "Máy chủ thư", cn=["dịch vụ bên ngoài"])

    # máy chủ và Docker
    _nut(ax, 4.05, 0.25, 11.6, 13.35, "«device»", "Máy chủ (1–2 GB bộ nhớ)", lw=1.0)
    _nut(ax, 4.3, 2.65, 11.1, 9.95, "«execution environment»", "Docker Engine, Docker Compose", d=0.2)

    W, H, D = 2.9, 1.95, 0.18
    A, B, C = 4.6, 8.45, 12.25
    R1, R2, R3 = 9.35, 6.2, 3.05
    nut = dict(d=D, lw=0.85, tren=False)
    _nut(ax, B, R1, W, H, "«container»", "nginx", cn=["nginx 1.27 · 64 MB"], **nut)
    _nut(ax, A, R2, W, H, "«container»", "api", cn=["Spring Boot 4.1 · 512 MB"], **nut)
    _nut(ax, B, R2, W, H, "«container»", "web", cn=["Next.js 16 · 256 MB"], **nut)
    _nut(ax, C, R2, W, H, "«container»", "pipeline", cn=["Python · 1 GB · 15:30"], **nut)
    _nut(ax, A, R3, W, H, "«container»", "db", cn=["PostgreSQL 17 · 256 MB"], **nut)
    _nut(ax, B, R3, W, H, "«container»", "backup", cn=["pg_dump · 64 MB · 02:00"], **nut)
    _artifact(ax, B + 0.1, 0.55, W - 0.2, 1.45, "backups/", "bản sao lưu")
    _artifact(ax, C + 0.1, 0.55, W - 0.2, 1.45, "data/serving/", "tệp CSV")

    cx = lambda c: c + W / 2  # noqa: E731
    # trình duyệt → nginx
    _duong(ax, [(3.55 + 0.25, 11.15), (B, R1 + H * 0.55)], "«HTTPS» cổng 443", (6.15, 10.93))
    # nginx → web, nginx → api
    _duong(ax, [(cx(B), R1), (cx(B), R2 + H + D)], "«HTTP»", (cx(B) + 0.15, R1 - 0.42), ha="left")
    _duong(ax, [(B, R1 + 0.35), (cx(A) + 0.4, R2 + H + D)], "«HTTP» /api", (7.0, R1 - 0.22))
    # web → api (kết xuất phía máy chủ)
    _duong(ax, [(B, R2 + H * 0.5), (A + W + D, R2 + H * 0.5)], "SSR", (8.24, R2 + H * 0.5 + 0.32))
    # api → db, backup → db
    _duong(ax, [(cx(A), R2), (cx(A), R3 + H + D)], "«JDBC»", (cx(A) - 0.12, R2 - 0.5), ha="right")
    _duong(ax, [(B, R3 + H * 0.5), (A + W + D, R3 + H * 0.5)])
    # api → máy chủ thư
    _duong(ax, [(A, R2 + H * 0.55), (3.55 + 0.25, R2 + H * 0.55)], "«SMTP»", (4.2, R2 + H * 0.55 + 0.3))
    # backup ghi bản sao lưu; pipeline ghi CSV; api đọc CSV
    _duong(ax, [(cx(B), R3), (cx(B), 2.0)], "ghi", (cx(B) + 0.12, 2.35), mui_ten=True, dut=True, ha="left")
    _duong(ax, [(cx(C) + 0.5, R2), (cx(C) + 0.5, 2.0)], "ghi", (cx(C) + 0.62, 4.0), mui_ten=True, dut=True,
           ha="left")
    yg = R2 - 0.5
    _duong(ax, [(A + W * 0.8, R2), (A + W * 0.8, yg), (cx(C) - 0.5, yg), (cx(C) - 0.5, 2.0)],
           "đọc lúc 16:00", (cx(B), yg), mui_ten=True, dut=True)
    _luu(fig, "h4_trien_khai_uml.png")


# ---------------------------------------------------------------- tuần tự
def _icon(ax, loai, x, y, ten):
    r = 0.28
    if loai == "actor":
        ax.add_patch(plt.Circle((x, y + 0.36), 0.14, fill=False, lw=0.85, ec=DEN))
        ax.plot([x, x], [y + 0.22, y - 0.14], color=DEN, lw=0.85)
        ax.plot([x - 0.24, x + 0.24], [y + 0.1, y + 0.1], color=DEN, lw=0.85)
        ax.plot([x, x - 0.2], [y - 0.14, y - 0.46], color=DEN, lw=0.85)
        ax.plot([x, x + 0.2], [y - 0.14, y - 0.46], color=DEN, lw=0.85)
        y_nhan = y - 0.56
    else:
        ax.add_patch(plt.Circle((x, y), r, fc="white", ec=DEN, lw=0.85, zorder=3))
        if loai == "boundary":
            ax.plot([x - r - 0.16, x - r - 0.16], [y - r, y + r], color=DEN, lw=0.85)
            ax.plot([x - r - 0.16, x - r], [y, y], color=DEN, lw=0.85)
        elif loai == "control":
            ax.plot([x + 0.02, x - 0.1, x + 0.04], [y + r + 0.08, y + r, y + r - 0.09], color=DEN, lw=0.85,
                    zorder=4)
        elif loai == "entity":
            ax.plot([x - r, x + r], [y - r - 0.02, y - r - 0.02], color=DEN, lw=0.85)
        y_nhan = y - r - 0.12
    t = ax.text(x, y_nhan, ten, ha="center", va="top", fontsize=7.4, linespacing=1.05)
    return y_nhan - 0.24 * (ten.count("\n") + 1) - 0.08


def tuan_tu(ten_tep: str, lanes, buoc) -> None:
    import textwrap

    n = len(lanes)
    W_U = 16.0
    le = 1.25
    xs = [le + i * (W_U - 2 * le) / (n - 1) for i in range(n)]
    cao = {"m": 0.56, "r": 0.56, "r-": 0.56, "s": 0.78, "alt": 0.62, "opt": 0.62, "loop": 0.62,
           "else": 0.5, "end": 0.32}
    # ngắt dòng chữ thông điệp cho vừa khoảng giữa hai làn (≈ 0.105 đơn vị mỗi ký tự ở cỡ 7,1);
    # chữ được phép tràn nhẹ qua đường sống hai bên (nền trắng che nét đứt)
    so_tam = 0
    buoc2 = []
    for b in buoc:
        if b[0] in ("m", "r", "r-"):
            so_tam += 1
            nhip = abs(xs[b[2]] - xs[b[1]]) - 0.3
            rong_dong = max(int(nhip / 0.105), 16, max(len(w) for w in b[3].split()) + 4)
            s = textwrap.fill(f"{so_tam}. {b[3]}", rong_dong, break_long_words=False, break_on_hyphens=False)
            buoc2.append((b[0], b[1], b[2], s, s.count("\n")))
        elif b[0] == "s":
            so_tam += 1
            buoc2.append(("s", b[1], f"{so_tam}. {b[2]}"))
        else:
            buoc2.append(b)
    buoc = buoc2
    cao["x"] = 0.0
    h = lambda b: cao[b[0]] + (0.28 * b[4] if b[0] in ("m", "r", "r-") else 0)  # noqa: E731
    tong = 2.25 + sum(h(b) for b in buoc) + 0.45
    fig, ax = _canvas(6.3, tong / 2.54, W_U)
    y_icon = tong - 0.62
    y_day = min(_icon(ax, loai, x, y_icon, ten) for (loai, ten), x in zip(lanes, xs))
    y = y_day - 0.2
    bar = [[] for _ in lanes]           # chồng thanh kích hoạt: y bắt đầu
    ve_bar = []                         # (làn, y0, y1, độ sâu)
    khung = []                          # khung alt/opt/loop đang mở
    pass
    BW = 0.085

    def xl(i, phia):
        if lanes[i][0] == "actor" or not bar[i]:
            return xs[i]
        return xs[i] + (len(bar[i]) - 1) * 0.1 + phia * BW

    def rong(s):
        return max(len(d) for d in s.split("\n")) * 0.105

    def chu(x, yy, s, ha="center"):
        nua = rong(s) / 2
        x = min(max(x, 0.15 + nua), W_U - 0.15 - nua)   # không tràn khỏi khung hình
        ax.text(x, yy + 0.1, s, ha=ha, va="bottom", fontsize=7.1, zorder=6, linespacing=1.15,
                bbox=dict(fc="white", ec="none", pad=0.15, alpha=0.9))

    for b in buoc:
        k = b[0]
        if k == "x":  # kết thúc thanh kích hoạt trên cùng của một làn
            if bar[b[1]]:
                y0 = bar[b[1]].pop()
                ve_bar.append((b[1], y0, y - 0.25, len(bar[b[1]])))
            continue
        if k in ("m", "r", "r-"):
            y -= h(b)
            a, c, s = b[1], b[2], b[3]
            phai = c > a
            x0 = xl(a, 1 if phai else -1)
            if k == "m":
                if lanes[c][0] != "actor":
                    bar[c].append(y)
                x1 = xl(c, -1 if phai else 1)
                ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="-|>,head_length=4.5,head_width=2.4",
                                             color=DEN, lw=0.75, shrinkA=0, shrinkB=0, zorder=5))
            else:
                if k == "r" and bar[a]:
                    y0 = bar[a].pop()
                    ve_bar.append((a, y0, y, len(bar[a])))
                x1 = xl(c, -1 if phai else 1)
                ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="->,head_length=4,head_width=2.4",
                                             color=DEN, lw=0.7, ls=(0, (3.5, 2.2)), shrinkA=0, shrinkB=0,
                                             zorder=5))
            chu((x0 + x1) / 2, y, s)
        elif k == "s":
            y -= cao[k]
            a, s = b[1], b[2]
            x0 = xl(a, 1)
            y_tren = y + 0.32
            ax.plot([x0, x0 + 0.42, x0 + 0.42], [y_tren, y_tren, y], color=DEN, lw=0.75, zorder=5)
            ax.add_patch(FancyArrowPatch((x0 + 0.42, y), (x0 + 0.1, y),
                                         arrowstyle="-|>,head_length=4.5,head_width=2.4", color=DEN, lw=0.75,
                                         shrinkA=0, shrinkB=0, zorder=5))
            d = len(bar[a])
            ve_bar.append((a, y - 0.12, y + 0.06, d))
            if x0 + 0.52 + rong(s) < W_U - 0.1:
                ax.text(x0 + 0.52, y + 0.16, s, ha="left", va="center", fontsize=7.1, zorder=6,
                        bbox=dict(fc="white", ec="none", pad=0.15, alpha=0.9))
            else:  # làn sát mép phải: ghi chữ sang trái đường sống
                ax.text(xl(a, -1) - 0.12, y + 0.16, s, ha="right", va="center", fontsize=7.1, zorder=6,
                        bbox=dict(fc="white", ec="none", pad=0.15, alpha=0.9))
        elif k in ("alt", "opt", "loop"):
            y -= cao[k]
            khung.append({"loai": k, "a": b[2], "b": b[3], "y0": y + 0.42, "re": [], "dk": b[1]})
        elif k == "else":
            y -= cao[k]
            khung[-1]["re"].append((y + 0.22, b[1]))
        elif k == "end":
            y -= cao[k]
            f = khung.pop()
            sau = len(khung)
            x0 = xs[f["a"]] - 0.78 + 0.14 * sau   # khung lồng trong hẹp hơn khung ngoài
            x1 = xs[f["b"]] + 0.78 - 0.14 * sau
            y0, y1 = f["y0"], y + 0.12
            ax.add_patch(Rectangle((x0, y1), x1 - x0, y0 - y1, fill=False, ec=DEN, lw=0.75, zorder=4))
            tw = 0.42 + 0.12 * len(f["loai"])
            ax.add_patch(Polygon([(x0, y0), (x0 + tw, y0), (x0 + tw, y0 - 0.2), (x0 + tw - 0.12, y0 - 0.32),
                                  (x0, y0 - 0.32)], closed=True, fc="white", ec=DEN, lw=0.75, zorder=5))
            ax.text(x0 + 0.06, y0 - 0.16, f["loai"], ha="left", va="center", fontsize=7.2, fontweight="bold",
                    zorder=6)
            ax.text(x0 + tw + 0.12, y0 - 0.16, f["dk"], ha="left", va="center", fontsize=7.1, zorder=6, bbox=dict(fc="white", ec="none", pad=0.1))
            for yy, dk in f["re"]:
                ax.plot([x0, x1], [yy, yy], color=DEN, lw=0.7, ls=(0, (4, 2.5)), zorder=4)
                ax.text(x0 + 0.1, yy - 0.16, dk, ha="left", va="center", fontsize=7.1, zorder=6, bbox=dict(fc="white", ec="none", pad=0.1))
    y_cuoi = y - 0.3
    for i, st in enumerate(bar):
        while st:
            ve_bar.append((i, st.pop(), y_cuoi + 0.1, len(st)))
    for i, x in enumerate(xs):
        ax.plot([x, x], [y_day - 0.05, y_cuoi], color=DEN, lw=0.6, ls=(0, (4, 3)), zorder=1)
    for i, y0, y1, d in ve_bar:
        lo, hi = min(y0, y1), max(y0, y1)
        ax.add_patch(Rectangle((xs[i] + d * 0.1 - BW, lo - 0.06), 2 * BW, hi - lo + 0.12, fc="white", ec=DEN,
                               lw=0.75, zorder=2 + d))
    _luu(fig, ten_tep)


A, B, C, D, E, F = range(6)
TUAN_TU = {
    "tt_tong_quan": (
        [("actor", "Khách"), ("boundary", "Trang tổng quan"), ("control", "OverviewController"),
         ("control", "OverviewService"), ("entity", "CSDL")],
        [("m", A, B, "Mở trang Tổng quan"),
         ("m", B, C, "GET /api/v1/overview"),
         ("m", C, D, "overview()"),
         ("m", D, E, "Lãi gửi ngày mới nhất (deposit_rate)"),
         ("r", E, D, "Bảng lãi suất"),
         ("m", D, E, "Chỉ tiêu quý mới nhất (bank_quarter_value)"),
         ("r", E, D, "Giá trị chỉ tiêu"),
         ("m", D, E, "Xếp hạng, ngày cập nhật (ranking_result, dataset_info)"),
         ("r", E, D, "Xếp hạng, ngày dữ liệu"),
         ("r", D, C, "OverviewResponse"),
         ("r", C, B, "JSON"),
         ("s", B, "Hiển thị thẻ KPI, biểu đồ, bảng chỉ tiêu")]),
    "tt_gui": (
        [("actor", "Khách"), ("boundary", "Trang gửi tiết kiệm"), ("control", "AdvisorController"),
         ("control", "SavingsAdvisorService"), ("entity", "CSDL")],
        [("m", A, B, "Nhập số tiền, kỳ hạn, kênh"),
         ("m", B, C, "POST /api/v1/advisor/savings"),
         ("alt", "[dữ liệu vào không hợp lệ]", B, E),
         ("r-", C, B, "400, lỗi từng trường"),
         ("else", "[hợp lệ]"),
         ("m", C, D, "advise(request)"),
         ("m", D, E, "Lãi ngày mới nhất (deposit_rate, bank)"),
         ("r", E, D, "Lãi suất 22 ngân hàng"),
         ("m", D, E, "Bậc lãi theo số tiền (deposit_rate_tier)"),
         ("r", E, D, "Các bậc lãi"),
         ("s", D, "Chọn bậc, tính tiền lãi, sắp theo lãi"),
         ("m", D, E, "Xếp hạng theo kỳ hạn, kênh, mốc tiền (ranking_result)"),
         ("r", E, D, "Thứ hạng, tỷ lệ đứng đầu, khoảng hạng"),
         ("r", D, C, "SavingsAdviceResponse"),
         ("r", C, B, "JSON"),
         ("end",),
         ("s", B, "Hiển thị bảng lãi, tiền lãi, xếp hạng")]),
    "tt_vay": (
        [("actor", "Khách"), ("boundary", "Trang gợi ý vay"), ("control", "AdvisorController"),
         ("control", "LoanAdvisorService"), ("entity", "CSDL")],
        [("m", A, B, "Nhập mục đích, số tiền, thời hạn, cách trả"),
         ("m", B, C, "POST /api/v1/advisor/loans"),
         ("m", C, D, "advise(request)"),
         ("m", D, E, "Lãi cho vay bình quân mới nhất (lending_rate)"),
         ("r", E, D, "Lãi vay 22 ngân hàng"),
         ("m", D, E, "Ngân hàng tham gia chương trình (program_participation)"),
         ("r", E, D, "Danh sách tham gia"),
         ("s", D, "Tính tiền trả mỗi kỳ, tổng lãi"),
         ("m", D, E, "Chương trình theo mục đích vay (policy_program, program_rate)"),
         ("r", E, D, "Chương trình ưu đãi"),
         ("m", D, E, "Xếp hạng phía vay (ranking_result)"),
         ("r", E, D, "Thứ hạng, tỷ lệ đứng đầu"),
         ("r", D, C, "LoanAdviceResponse"),
         ("r", C, B, "JSON"),
         ("s", B, "Hiển thị tiền trả mỗi kỳ, xếp hạng")]),
    "tt_so_sanh": (
        [("actor", "Khách"), ("boundary", "Trang so sánh"), ("control", "IndicatorController"),
         ("control", "IndicatorService"), ("entity", "CSDL")],
        [("m", A, B, "Mở trang So sánh"),
         ("m", B, C, "GET /api/v1/indicators/snapshot"),
         ("m", C, D, "snapshot()"),
         ("m", D, E, "Chỉ tiêu quý mới nhất (indicator, bank_quarter_value)"),
         ("r", E, D, "Giá trị của 22 ngân hàng"),
         ("r", D, C, "IndicatorSnapshotResponse"),
         ("r", C, B, "JSON"),
         ("s", B, "Hiển thị bảng chỉ tiêu"),
         ("x", B),
         ("m", A, B, "Chọn ngân hàng và chỉ tiêu"),
         ("m", B, C, "GET /api/v1/indicators/{code}/comparison"),
         ("m", C, D, "compare(code, tickers)"),
         ("m", D, E, "Chuỗi theo quý của các ngân hàng đã chọn"),
         ("r", E, D, "Giá trị theo quý"),
         ("r", D, C, "IndicatorComparisonResponse"),
         ("r", C, B, "JSON"),
         ("s", B, "Vẽ biểu đồ so sánh theo quý")]),
    "tt_dang_nhap": (
        [("actor", "Khách"), ("boundary", "Trang đăng nhập"), ("control", "AuthController"),
         ("control", "AuthService"), ("entity", "CSDL")],
        [("m", A, B, "Nhập email, mật khẩu"),
         ("m", B, C, "POST /api/v1/auth/login"),
         ("m", C, D, "login(request, IP)"),
         ("s", D, "Kiểm tra số lần đăng nhập sai"),
         ("m", D, E, "Tìm tài khoản theo email (app_user)"),
         ("r", E, D, "Tài khoản"),
         ("s", D, "So khớp mật khẩu (BCrypt)"),
         ("alt", "[sai email hoặc mật khẩu]", B, E),
         ("s", D, "Ghi một lần đăng nhập sai"),
         ("r-", D, C, "INVALID_CREDENTIALS"),
         ("r-", C, B, "401, báo sai thông tin"),
         ("else", "[đúng mật khẩu nhưng tài khoản bị khóa]"),
         ("r-", D, C, "ACCOUNT_LOCKED"),
         ("r-", C, B, "Báo tài khoản bị khóa"),
         ("else", "[hợp lệ]"),
         ("m", D, E, "Ghi thời điểm đăng nhập"),
         ("r", E, D, "Đã lưu"),
         ("s", D, "Cấp mã JWT"),
         ("r", D, C, "Session(user, token)"),
         ("s", C, "Ghi cookie phiên HttpOnly"),
         ("r", C, B, "Thông tin người dùng"),
         ("end",),
         ("s", B, "Chuyển về trang trước")]),
    "tt_luu_nhu_cau": (
        [("actor", "Người dùng"), ("boundary", "Trang gửi tiết kiệm"), ("control", "Spring Security"),
         ("control", "SavedNeedController"), ("control", "SavedNeedService"), ("entity", "CSDL")],
        [("m", A, B, "Bấm Lưu nhu cầu, đặt tên"),
         ("m", B, C, "POST /api/v1/me/needs"),
         ("s", C, "Kiểm tra mã CSRF, giải mã JWT"),
         ("m", C, F, "Đọc tài khoản trong JWT (app_user)"),
         ("r", F, C, "Trạng thái, token_version"),
         ("alt", "[phiên không hợp lệ hoặc tài khoản bị khóa]", B, F),
         ("r-", C, B, "401, yêu cầu đăng nhập"),
         ("else", "[hợp lệ]"),
         ("m", C, D, "Chuyển yêu cầu kèm người dùng"),
         ("m", D, E, "create(userId, request)"),
         ("m", E, F, "Đếm nhu cầu đã lưu (saved_need)"),
         ("r", F, E, "Số nhu cầu"),
         ("s", E, "Kiểm tra giới hạn nhu cầu"),
         ("m", E, F, "Lưu nhu cầu mới (saved_need)"),
         ("r", F, E, "Bản ghi đã lưu"),
         ("r", E, D, "SavedNeedResponse"),
         ("r", D, B, "JSON"),
         ("x", C),
         ("end",),
         ("s", B, "Báo đã lưu nhu cầu")]),
    "tt_theo_doi": (
        [("actor", "Người dùng"), ("boundary", "Trang hồ sơ ngân hàng"), ("control", "WatchlistController"),
         ("control", "WatchlistService"), ("entity", "CSDL")],
        [("m", A, B, "Bấm Theo dõi, nhập ngưỡng thay đổi lãi"),
         ("m", B, C, "POST /api/v1/me/watchlist"),
         ("m", C, D, "add(userId, request)"),
         ("m", D, E, "Kiểm tra mã ngân hàng (bank)"),
         ("r", E, D, "Ngân hàng"),
         ("m", D, E, "Đã theo dõi chưa? (watch_item)"),
         ("r", E, D, "Kết quả"),
         ("alt", "[đã theo dõi]", B, E),
         ("r-", D, C, "ALREADY_WATCHED"),
         ("r-", C, B, "Báo đã theo dõi"),
         ("else", "[chưa theo dõi]"),
         ("m", D, E, "Lưu mục theo dõi, ngưỡng (watch_item)"),
         ("r", E, D, "Đã lưu"),
         ("m", D, E, "Lãi suất hiện tại (deposit_rate)"),
         ("r", E, D, "Lãi suất"),
         ("r", D, C, "WatchItemResponse"),
         ("r", C, B, "JSON"),
         ("end",),
         ("s", B, "Hiện ngân hàng trong danh sách theo dõi")]),
    "tt_nap_du_lieu": (
        [("actor", "Bộ lập lịch"), ("control", "DataImportJobs"), ("control", "DataImportService"),
         ("entity", "Tệp CSV\n(data/serving)"), ("entity", "CSDL"), ("control", "NotificationService")],
        [("m", A, B, "Kích hoạt lúc 16:00"),
         ("m", B, C, "importAll(force = false)"),
         ("loop", "[mỗi bộ dữ liệu]", C, F),
         ("m", C, D, "Tính SHA-256 của tệp"),
         ("r", D, C, "Checksum"),
         ("m", C, E, "Checksum lần nạp thành công gần nhất (import_run)"),
         ("r", E, C, "Checksum cũ"),
         ("alt", "[checksum khác]", C, F),
         ("m", C, E, "Ghi lần nạp đang chạy (import_run)"),
         ("r", E, C, "Mã lần nạp"),
         ("m", C, D, "Đọc các dòng"),
         ("r", D, C, "Dữ liệu"),
         ("m", C, E, "Thay dữ liệu bảng trong một giao dịch"),
         ("r", E, C, "Số dòng, mốc dữ liệu mới"),
         ("m", C, F, "DatasetImportedEvent"),
         ("m", F, E, "Tạo thông báo cho người theo dõi (notification)"),
         ("r", E, F, "Đã tạo"),
         ("r", F, C, "Xong"),
         ("else", "[checksum không đổi]"),
         ("s", C, "Bỏ qua bộ dữ liệu"),
         ("end",),
         ("end",),
         ("r", C, B, "ImportSummary")]),
    "tt_gui_thu": (
        [("actor", "Bộ lập lịch"), ("control", "NotificationEmailDispatcher"), ("entity", "CSDL"),
         ("actor", "Máy chủ thư")],
        [("m", A, B, "Quét hàng đợi mỗi 60 giây"),
         ("opt", "[hệ thống đã bật gửi thư]", B, D),
         ("m", B, C, "Thông báo chờ gửi thư (notification)"),
         ("r", C, B, "Danh sách, gom theo người nhận"),
         ("loop", "[mỗi người nhận]", B, D),
         ("m", B, D, "Gửi thư tóm tắt (SMTP)"),
         ("r-", D, B, "Kết quả gửi"),
         ("m", B, C, "Đánh dấu đã gửi hoặc ghi lỗi"),
         ("r", C, B, "Đã cập nhật"),
         ("end",),
         ("end",)]),
    "tt_khoa_tai_khoan": (
        [("actor", "Quản trị viên"), ("boundary", "Trang quản lý người dùng"), ("control", "AdminUserController"),
         ("control", "UserAdminService"), ("entity", "CSDL")],
        [("m", A, B, "Chọn tài khoản, bấm Khóa, nhập lý do"),
         ("m", B, C, "PATCH /api/v1/admin/users/{id}"),
         ("m", C, D, "update(actor, id, request)"),
         ("m", D, E, "Tìm tài khoản (app_user)"),
         ("r", E, D, "Tài khoản"),
         ("s", D, "Kiểm tra: không tự khóa, có lý do"),
         ("m", D, E, "Đếm quản trị viên đang hoạt động"),
         ("r", E, D, "Số quản trị viên"),
         ("alt", "[vi phạm điều kiện]", B, E),
         ("r-", D, C, "Lỗi nghiệp vụ"),
         ("r-", C, B, "Báo lỗi"),
         ("else", "[hợp lệ]"),
         ("m", D, E, "Đặt LOCKED, tăng token_version"),
         ("r", E, D, "Đã cập nhật"),
         ("m", D, E, "Ghi nhật ký quản trị (admin_audit)"),
         ("r", E, D, "Đã ghi"),
         ("r", D, C, "UserSummary"),
         ("r", C, B, "JSON"),
         ("end",),
         ("s", B, "Cập nhật danh sách tài khoản")]),
}


def tuan_tu_tat_ca() -> None:
    for ten, (lanes, buoc) in TUAN_TU.items():
        tuan_tu(f"h4_{ten}.png", lanes, buoc)


if __name__ == "__main__":
    viec = {"use_case": use_case, "trien_khai": trien_khai, "tuan_tu": tuan_tu_tat_ca}
    viec.update({k: (lambda k=k: tuan_tu(f"h4_{k}.png", *TUAN_TU[k])) for k in TUAN_TU})
    for ten in sys.argv[1:] or ["use_case", "trien_khai", "tuan_tu"]:
        viec[ten]()
