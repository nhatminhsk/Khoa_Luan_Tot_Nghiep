import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
RA = REPO / "figures" / "khoa_luan"
RA.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "Times New Roman", "font.size": 10, "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b",
    "xtick.color": "#52514e", "ytick.color": "#0b0b0b", "axes.spines.top": False, "axes.spines.right": False,
})
XANH, CAM, NGOC = "#2a78d6", "#eb6834", "#1baf7a"
CHU, CHU2 = "#0b0b0b", "#52514e"


def phan_ra_phuong_sai() -> None:
    v = pd.read_csv(REPO / "data" / "model" / "eda" / "variance.csv")
    bo = ["pb", "app_mean_score", "noii_share_ttm_pct", "invsec_to_assets_pct"]
    v = v[~v.feature.isin(bo)].sort_values("bank_share")
    fig, ax = plt.subplots(figsize=(6.3, 4.6), dpi=300)
    y = list(range(len(v)))
    trai = [0.0] * len(v)
    phan = [("bank_share", "Khác biệt giữa các ngân hàng", XANH, None),
            ("quarter_share", "Biến động chung theo quý", CAM, "////"),
            ("resid_share", "Phần riêng ngân hàng–quý", NGOC, "...")]
    for cot, ten, mau, van in phan:
        ax.barh(y, v[cot], left=trai, color=mau, edgecolor="white", linewidth=1.2, height=0.72, label=ten, hatch=van)
        trai = [a + b for a, b in zip(trai, v[cot])]
    for i, (_, r) in enumerate(v.iterrows()):
        ax.text(r.bank_share - 0.012, i, f"{r.bank_share * 100:.0f}%", ha="right", va="center",
                fontsize=8, color="white", fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels(v["label"], fontsize=9)
    ax.set_xlim(0, 1)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("Tỷ trọng trong tổng phương sai")
    ax.legend(loc="lower center", bbox_to_anchor=(0.42, 1.0), ncol=3, frameon=False, fontsize=8.5,
              handlelength=1.6, columnspacing=1.2)
    fig.tight_layout()
    fig.savefig(RA / "h3_phan_ra_phuong_sai.png", facecolor="white")
    plt.close(fig)


def walk_forward() -> None:
    quy = [f"{y}-Q{q}" for y in range(2019, 2027) for q in range(1, 5)]   # 2019-Q1 .. 2026-Q4
    idx = {q: i for i, q in enumerate(quy)}
    fig, ax = plt.subplots(figsize=(6.3, 3.1), dpi=300)
    h = 4
    hang = [("2023-Q1", 4.0), ("2023-Q2", 3.0), ("2023-Q3", 2.0), ("2025-Q2", 0.6)]
    for g, yy in hang:
        t = idx[g]
        ax.add_patch(Rectangle((0, yy - 0.3), t - h + 1, 0.6, color=XANH, lw=0))
        ax.add_patch(Rectangle((t - h + 1, yy - 0.3), h, 0.6, facecolor="#e8e8e6", edgecolor=CHU2, lw=0.6,
                               hatch="////"))
        ax.plot([t + 1, t + 1], [yy - 0.42, yy + 0.42], color=CHU, lw=1.2)
        for hh, mk in ((1, "o"), (2, "s"), (4, "D")):
            ax.plot(t + hh + 0.5, yy, marker=mk, color=CAM, ms=5, mec="white", mew=0.6)
        ax.text(-0.6, yy, f"Gốc {g}", ha="right", va="center", fontsize=8.5, color=CHU)
    ax.text(-0.6, 1.3, "…", ha="right", va="center", fontsize=11, color=CHU2)
    tach = idx["2023-Q1"]
    ax.axvspan(-0.5, tach, color="#f0efec", zorder=-2)
    ax.text(tach / 2, 4.75, "Tập chọn cấu hình: quý đích ≤ 2022-Q4", ha="center", fontsize=8.5, color=CHU2)
    ax.text(tach + (len(quy) - tach) / 2, 4.75, "Tập kiểm tra: gốc từ 2023-Q1", ha="center", fontsize=8.5,
            color=CHU2)
    ax.set_xlim(-0.5, len(quy) + 0.3)
    ax.set_ylim(0.1, 5.1)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.set_xticks([idx[f"{y}-Q1"] for y in range(2019, 2027)])
    ax.set_xticklabels([str(y) for y in range(2019, 2027)])
    chu_giai = [Rectangle((0, 0), 1, 1, color=XANH),
                Rectangle((0, 0), 1, 1, facecolor="#e8e8e6", edgecolor=CHU2, hatch="////"),
                Line2D([], [], color=CHU, lw=1.2),
                Line2D([], [], marker="o", color=CAM, lw=0, ms=5), Line2D([], [], marker="s", color=CAM, lw=0, ms=5),
                Line2D([], [], marker="D", color=CAM, lw=0, ms=5)]
    ax.legend(chu_giai, ["Huấn luyện", "Loại vì nhãn chưa biết (h = 4)", "Gốc t",
                         "Đích t + 1", "Đích t + 2", "Đích t + 4"],
              loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=6, frameon=False, fontsize=7.5,
              handlelength=1.3, columnspacing=0.8)
    fig.tight_layout()
    fig.savefig(RA / "h3_walk_forward.png", facecolor="white")
    plt.close(fig)


def erd() -> None:
    from matplotlib.patches import Circle

    W, RH, HH, PAD = 15.0, 0.34, 0.50, 0.08        # rộng hình, cao dòng, cao tiêu đề, đệm đáy (cm)
    TW, GUT, GAP, VG = 3.05, 0.66, 0.70, 0.62       # rộng bảng, cột khóa, khe giữa cột, khe dọc
    X = [0.60 + i * (TW + GAP) for i in range(4)]
    # Đen trắng (07/11/2026, theo yêu cầu bỏ màu): tiêu đề nền trắng, mọi nét và chữ màu đen.
    NET, VIEN, TIEU_DE = "#000000", "#000000", "#000000"
    ND = DL = KQ = "white"

    def cot(*hang):
        return [h if isinstance(h, tuple) else ("", h) for h in hang]

    BANG = {
        # cột 1: người dùng
        "app_user": (0, ND, cot(("PK", "id"), "email", "password_hash", "role, status", "token_version",
                                "notify_channel")),
        "saved_need": (0, ND, cot(("PK", "id"), ("FK", "user_id"), "purpose, label", "amount, term_months",
                                  "channel, repayment", "loan_purpose")),
        "notification": (0, ND, cot(("PK", "id"), ("FK", "user_id"), "type, ticker", "title, body", "email_status",
                                    "created_at, read_at")),
        "admin_audit": (0, ND, cot(("PK", "id"), "actor_id, actor_email", "action", "target_id", "created_at")),
        # cột 2
        "watch_item": (1, ND, cot(("PK", "id"), ("FK", "user_id"), ("FK", "ticker"), "rate_threshold", "created_at")),
        "ranking_result": (1, KQ, cot(("PK", "id"), ("FK", "ticker"), "purpose, as_of_period", "term_months, channel",
                                      "amount_vnd", "rank_value", "rank_low, rank_high", "p_top1, p_top3",
                                      "rates_as_of")),
        "dataset_info": (1, KQ, cot(("PK", "dataset"), "name, source", "frequency", "last_updated", "row_count")),
        "import_run": (1, KQ, cot(("PK", "id"), "dataset", "file_name, checksum", "status, row_count", "started_at")),
        "macro_cpi": (1, DL, cot(("PK", "cpi_month"), "cpi_yoy_percent", "cpi_mom_percent")),
        # cột 3
        "bank": (2, DL, cot(("PK", "ticker"), "short_name", "full_name")),
        "bank_ownership": (2, DL, cot(("PK FK", "ticker"), "as_of_date", "state_own_percent",
                                      "foreign_own_percent")),
        "program_participation": (2, DL, cot(("PK", "id"), ("FK", "program_code"), ("FK", "ticker"), "participates",
                                             "list_as_of")),
        "policy_program": (2, DL, cot(("PK", "code"), "name", "category")),
        "program_rate": (2, DL, cot(("PK", "id"), ("FK", "program_code"), "borrower_group", "rate_percent",
                                    "valid_from, valid_to")),
        # cột 4
        "deposit_rate": (3, DL, cot(("PK", "id"), ("FK", "ticker"), "rate_date", "term_months, channel",
                                    "rate_percent")),
        "deposit_rate_tier": (3, DL, cot(("PK", "id"), ("FK", "ticker"), "term_months, channel", "min_amount_vnd",
                                         "rate_percent")),
        "lending_rate": (3, DL, cot(("PK", "id"), ("FK", "ticker"), "rate_month", "lending_avg_percent",
                                    "segment, basis")),
        "bank_quarter_value": (3, DL, cot(("PK", "id"), ("FK", "ticker"), ("FK", "indicator_code"),
                                          "period, period_end", "val")),
        "indicator": (3, DL, cot(("PK", "code"), "name, unit", "camels_group", "direction", "display_order")),
    }
    assert len(BANG) == 19

    def cao(ten):
        return HH + RH * len(BANG[ten][2]) + PAD

    # Xếp chồng từng cột; đỉnh lệch nhau một vài dòng để các đường nối chính đi thẳng hàng.
    THU_TU = [(["app_user", "saved_need", "notification", "admin_audit"], -RH),
              (["watch_item", "ranking_result", "dataset_info", "import_run", "macro_cpi"], 0.0),
              (["bank", "bank_ownership", "program_participation", "policy_program", "program_rate"],
               -2 * RH),
              (["deposit_rate", "deposit_rate_tier", "lending_rate", "bank_quarter_value", "indicator"], -RH)]
    DINH = {}
    for ds, y in THU_TU:
        for ten in ds:
            DINH[ten] = y
            y -= cao(ten) + VG
    day = min(DINH[t] - cao(t) for t in BANG)
    CHU_GIAI = 1.0
    H = -day + CHU_GIAI + 0.35
    fig = plt.figure(figsize=(W / 2.54, H / 2.54), dpi=300)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, W)
    ax.set_ylim(day - CHU_GIAI - 0.1, 0.25)
    ax.axis("off")

    def trai(t):
        return X[BANG[t][0]]

    def phai(t):
        return X[BANG[t][0]] + TW

    def dong(t, ten_cot):
        for k, (_, c) in enumerate(BANG[t][2]):
            if ten_cot in [s.strip() for s in c.split(",")]:
                return DINH[t] - HH - RH * (k + 0.5)
        raise KeyError((t, ten_cot))

    chu = []
    for ten, (ci, mau, hang) in BANG.items():
        x, y, h = X[ci], DINH[ten], cao(ten)
        ax.add_patch(Rectangle((x, y - h), TW, h, facecolor="white", edgecolor=VIEN, lw=0.8, zorder=2))
        ax.add_patch(Rectangle((x, y - HH), TW, HH, facecolor=mau, edgecolor=VIEN, lw=0.8, zorder=3))
        ax.text(x + TW / 2, y - HH / 2, ten, ha="center", va="center", fontsize=7.6, fontweight="bold",
                color=TIEU_DE, zorder=4)
        ax.plot([x + GUT, x + GUT], [y - HH, y - h], color=NET, lw=0.4, zorder=3)
        for k, (khoa, c) in enumerate(hang):
            yy = y - HH - RH * (k + 0.5)
            if khoa:
                ax.text(x + GUT / 2, yy, khoa, ha="center", va="center", fontsize=5.3, fontweight="bold",
                        color=VIEN, zorder=4)
            chu.append((ten, ax.text(x + GUT + 0.1, yy, c, ha="left", va="center", fontsize=7, color=CHU,
                                     fontweight="bold" if khoa.startswith("PK") else "normal", zorder=4)))

    def ky_hieu(P, d, loai):
        nx, ny = -d[1], d[0]

        def at(t, s=0.0):
            return P[0] + d[0] * t + nx * s, P[1] + d[1] * t + ny * s

        kw = dict(color=NET, lw=0.75, zorder=6, solid_capstyle="butt")

        def vach(t):
            a, b = at(t, -0.085), at(t, 0.085)
            ax.plot([a[0], b[0]], [a[1], b[1]], **kw)

        if loai == "1":                       # đúng một
            vach(0.07)
            vach(0.13)
            return
        if loai == "0n":                      # không hoặc nhiều
            dinh = at(0.15)
            for s in (-0.09, 0.0, 0.09):
                e = at(0.0, s)
                ax.plot([dinh[0], e[0]], [dinh[1], e[1]], **kw)
        else:                                 # "01": không hoặc một
            vach(0.09)
        ax.add_patch(Circle(at(0.22), 0.045, facecolor="white", edgecolor=NET, lw=0.75, zorder=7))

    def huong(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = (dx * dx + dy * dy) ** 0.5
        return dx / n, dy / n

    def noi(pts, dau="1", cuoi="0n", logic=False):
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=NET, lw=0.75, zorder=1,
                ls=(0, (1.2, 1.4)) if logic else "-")
        if dau:
            ky_hieu(pts[0], huong(pts[0], pts[1]), dau)
        if cuoi:
            ky_hieu(pts[-1], huong(pts[-1], pts[-2]), cuoi)

    def truc(cha, x_cha, y_cha, xb, con):
        for xc, yc in con:
            noi([(x_cha, y_cha), (xb, y_cha), (xb, yc), (xc, yc)] if abs(yc - y_cha) > 1e-6
                else [(x_cha, y_cha), (xc, yc)])
        ys = [y_cha] + [yc for _, yc in con]
        tren, duoi = max(ys), min(ys)
        for y in sorted(set(ys)):
            bac = sum(1 for v in ys if abs(v - y) < 1e-6) + (y < tren - 1e-6) + (y > duoi + 1e-6)
            if bac >= 3:
                ax.add_patch(Circle((xb, y), 0.04, color=NET, zorder=5))

    # app_user — saved_need, notification (lề trái), watch_item (thẳng sang phải)
    yb = dong("app_user", "id")
    truc("app_user", trai("app_user"), yb, X[0] / 2,
         [(trai(t), dong(t, "user_id")) for t in ("saved_need", "notification")])
    noi([(phai("app_user"), yb), (trai("watch_item"), dong("watch_item", "user_id"))])
    # bank — các bảng con qua trục ở khe trái và khe phải
    yb = dong("bank", "ticker")
    truc("bank", trai("bank"), yb, X[2] - GAP / 2,
         [(phai("watch_item"), dong("watch_item", "ticker")), (phai("ranking_result"), dong("ranking_result", "ticker")),
          (trai("program_participation"), dong("program_participation", "ticker"))])
    truc("bank", phai("bank"), yb, X[3] - GAP / 2,
         [(trai(t), dong(t, "ticker")) for t in ("deposit_rate", "deposit_rate_tier", "lending_rate",
                                                  "bank_quarter_value")])
    xg = X[2] + TW / 2
    noi([(xg, DINH["bank"] - cao("bank")), (xg, DINH["bank_ownership"])], "1", "01")
    # policy_program ở giữa hai bảng con; indicator dưới bank_quarter_value
    noi([(xg, DINH["policy_program"]), (xg, DINH["program_participation"] - cao("program_participation"))])
    noi([(xg, DINH["policy_program"] - cao("policy_program")), (xg, DINH["program_rate"])])
    xg = X[3] + TW / 2
    noi([(xg, DINH["indicator"]), (xg, DINH["bank_quarter_value"] - cao("bank_quarter_value"))])
    # Tham chiếu logic, không đặt khóa ngoại
    xl = X[1] - GAP / 2
    y1 = DINH["app_user"] - HH - RH * 1.5
    noi([(phai("admin_audit"), dong("admin_audit", "actor_id")), (xl, dong("admin_audit", "actor_id")), (xl, y1),
         (phai("app_user"), y1)], None, None, logic=True)
    xg = X[1] + TW / 2
    noi([(xg, DINH["import_run"]), (xg, DINH["dataset_info"] - cao("dataset_info"))], None, None, logic=True)

    # Chú giải: đặt nối tiếp theo độ rộng chữ đo được
    r = fig.canvas.get_renderer()

    def het(t):
        return ax.transData.inverted().transform((t.get_window_extent(r).x1, 0))[0]

    y0 = day - 0.55
    x = X[0]
    for dau, cuoi, logic, ten in (("1", "0n", False, "Một – không hoặc nhiều"), ("1", "01", False, "Một – không hoặc một"),
                                  (None, None, True, "Tham chiếu logic, không có khóa ngoại")):
        noi([(x, y0), (x + 0.95, y0)], dau, cuoi, logic)
        x = het(ax.text(x + 1.1, y0 - 0.09, ten, va="baseline", fontsize=7.4, color=CHU)) + 0.6
    assert x - 0.6 < W - 0.05, f"chú giải tràn: {x - 0.6:.2f} cm"

    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    tran = []
    for ten, t in chu:
        x1 = ax.transData.inverted().transform((t.get_window_extent(r).x1, 0))[0]
        if x1 > phai(ten) - 0.05:
            tran.append((ten, t.get_text(), round(x1 - phai(ten), 2)))
    if tran:
        print("Chữ tràn khỏi bảng:", tran)
    fig.savefig(RA / "h3_erd.png", facecolor="white")
    plt.close(fig)


def quy_trinh_xep_hang() -> None:
    from matplotlib.patches import FancyArrowPatch
    buoc = [
        ("1. Nhu cầu người dùng", "Gửi: số tiền, kỳ hạn, kênh · Vay: mục đích, số tiền, thời hạn, cách trả"),
        ("2. Lọc phương án", "Bỏ ngân hàng không có sản phẩm đúng kỳ hạn và kênh · áp bậc lãi theo số tiền"),
        ("3. Ma trận tiêu chí, chuẩn hóa", "Lãi suất mới nhất, BCTC gần nhất trong 4 quý · min-max, đảo chiều tiêu chí chi phí"),
        ("4. Trọng số mặc định ba tầng", "Nhóm → trụ → tiêu chí · nhóm an toàn nhân tỷ trọng vượt hạn mức BHTG (4.1)"),
        ("5. Monte Carlo, 10.000 vòng", "Rút trọng số Dirichlet → chạy SAW, TOPSIS, VIKOR, PROMETHEE II → ghi hạng"),
        ("6. Tổng hợp và hiển thị", "Tỷ lệ đứng đầu, vào top 3, khoảng hạng, mức đồng thuận · ngày dữ liệu"),
    ]
    fig, ax = plt.subplots(figsize=(6.3, 5.6), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    h, gap, top = 1.18, 0.38, 9.9
    for k, (tieu_de, chi_tiet) in enumerate(buoc):
        y = top - k * (h + gap) - h
        nen = "#d6e2f0" if k == 4 else "#e8eef6"
        ax.add_patch(FancyBboxPatch((0.2, y), 9.6, h, boxstyle="round,pad=0.02,rounding_size=0.12", lw=1.1,
                                    edgecolor="#1f3b63", facecolor=nen))
        ax.text(5, y + h - 0.36, tieu_de, ha="center", va="center", fontsize=11, fontweight="bold", color="#1f3b63")
        ax.text(5, y + 0.36, chi_tiet, ha="center", va="center", fontsize=8.6, color="#222222")
        if k < len(buoc) - 1:
            ax.add_patch(FancyArrowPatch((5, y - 0.02), (5, y - gap + 0.02), arrowstyle="-|>", mutation_scale=12,
                                         lw=1.2, color="#1f3b63"))
    fig.savefig(RA / "h3_quy_trinh_xep_hang.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    HINH = {"quy_trinh": quy_trinh_xep_hang, "phan_ra": phan_ra_phuong_sai, "walk_forward": walk_forward, "erd": erd}
    chon = sys.argv[1:] or list(HINH)
    for ten in chon:
        HINH[ten]()
    print("Đã vẽ", ", ".join(chon), "vào", RA)
