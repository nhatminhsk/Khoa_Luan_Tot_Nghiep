"""Biểu đồ cho các chỉ số LẦN ĐẦU có trong dự án.

Chỉ vẽ chiều dữ liệu trước đây hoàn toàn không có. Những thứ chỉ là nguồn tốt hơn
cho chỉ tiêu đã vẽ rồi (NPL từ thuyết minh, COF/NIM từ MAS, lợi suất tài sản sinh
lãi công bố, điểm app iOS) thì KHÔNG vẽ lại ở đây — chúng thuộc về phần đối chiếu
nguồn, không phải phần chỉ tiêu mới.

  fig_40  CASA xếp hạng            -> ngân hàng nào giữ được tiền gửi không kỳ hạn?
  fig_41  CASA vs chi phí vốn      -> vì sao CASA đáng quan tâm (r = -0,86)
  fig_42  CASA lưới 22 ngân hàng   -> ai đang cải thiện, ai đang mất dần?
  fig_43  Cơ cấu kỳ hạn cho vay    -> ngân hàng cho vay ngắn hay dài?
  fig_44  Sở hữu nhà nước & room ngoại -> hai cụm tách rời, không có ở giữa
  fig_45  Chỉ số giá USD và vàng   -> hai kênh cạnh tranh với tiền gửi
  fig_46  Ngành ngân hàng vs VN-Index -> tách biến động chung khỏi phần riêng

Giữ nguyên quy ước của bieu_do_car.py: một sắc nhấn duy nhất, danh tính ngân hàng
đến từ nhãn chữ chứ không từ màu. Riêng hình 43 dùng ba bậc đậm nhạt CÙNG một màu
vì kỳ hạn ngắn/trung/dài là thang có thứ tự, không phải ba loại ngang hàng.

Chạy:  python bieu_do_chi_so_moi.py
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parent
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

NOTE_SRC = ROOT / "data" / "credit" / "bank_asset_quality_quarterly.csv"
PANEL_SRC = ROOT / "data" / "model" / "bank_panel_quarterly.csv"
OWN_SRC = ROOT / "data" / "ownership" / "bank_ownership.csv"
PX_SRC = ROOT / "data" / "macro" / "price_indices.csv"
CPI_SRC = ROOT / "data" / "macro" / "cpi.csv"
IDX_SRC = ROOT / "data" / "market" / "VNINDEX.csv"
PRICE_DIR = ROOT / "data" / "price"

# --- bảng màu nhà, giữ nguyên từ bieu_do_car.py ---
SURFACE, INK, INK_2, INK_3 = "#fcfcfb", "#0b0b0b", "#52514e", "#7b7a75"
GRID, AXIS, MUTED = "#e8e7e3", "#d8d7d2", "#c9c8c3"
ACCENT = "#2a78d6"
ACCENT_FILL = "#cde2fb"
SEQ = LinearSegmentedColormap.from_list(
    "seq_blue",
    ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"],
)
# Ba bậc cho thang kỳ hạn: nhạt = ngắn hạn, đậm = dài hạn.
TENOR = ["#cde2fb", "#6da7ec", "#184f95"]

mpl.rcParams.update({
    "figure.facecolor": SURFACE, "figure.dpi": 110,
    "savefig.dpi": 200, "savefig.facecolor": SURFACE, "savefig.bbox": "tight",
    "axes.facecolor": SURFACE, "axes.edgecolor": AXIS, "axes.linewidth": 0.8,
    "axes.labelcolor": INK_2, "axes.titlecolor": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.axisbelow": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "grid.linestyle": "-",
    "xtick.color": INK_2, "ytick.color": INK_2,
    "xtick.labelsize": 9, "ytick.labelsize": 9,
    "text.color": INK, "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "Tahoma", "DejaVu Sans", "Arial"],
    "font.size": 10, "legend.frameon": False, "legend.fontsize": 9,
})


def ghi_chan(fig, note, y=-0.02):
    rong = max(60, int(fig.get_figwidth() * 15))
    fig.text(0.005, y, textwrap.fill(note, rong), fontsize=8.2,
             color=INK_3, va="top", ha="left")


def frame(ax, title, subtitle=None, note=None):
    ax.set_title(title, fontsize=13, fontweight="600", loc="left",
                 pad=18 if subtitle else 10)
    if subtitle:
        ax.text(0, 1.015, subtitle, transform=ax.transAxes, fontsize=9.5,
                color=INK_2, va="bottom", ha="left")
    if note:
        ghi_chan(ax.figure, note)
    return ax


def save(fig, name):
    out = FIGDIR / f"{name}.png"
    fig.savefig(out)
    print("đã lưu →", out.relative_to(ROOT))
    plt.close(fig)


def q_to_num(period):
    return int(period[:4]) + (int(period[-1]) - 1) / 4


def nhan_khong_dam(ax, diem, dy=9):
    """Đặt nhãn cho scatter, đẩy ra xa khi hai điểm quá sát nhau.

    Ở 2026-Q2 có nhiều cụm sát khít: SHB với BVB cách nhau 0,07 điểm chi phí vốn,
    TCB với MBB cách nhau 0,09. Để mặc thì hai nhãn chồng khít thành đống chữ.
    Hàm này đo khoảng cách trong hệ toạ độ màn hình rồi lật hướng nhãn xuống dưới
    khi phát hiện va chạm, thay vì dịch ngang làm lệch điểm neo.
    """
    tr = ax.transData.transform
    xy = np.array([tr((x, y)) for x, y, _ in diem])
    huong = np.ones(len(diem))
    for i in range(len(diem)):
        for j in range(i):
            if huong[j] != huong[i]:
                continue
            if abs(xy[i, 0] - xy[j, 0]) < 34 and abs(xy[i, 1] - xy[j, 1]) < 15:
                huong[i] = -1
    for (x, y, ten), h in zip(diem, huong):
        ax.annotate(ten, (x, y), textcoords="offset points",
                    xytext=(0, dy if h > 0 else -dy - 5),
                    ha="center", fontsize=8.2, color=INK_2)


# ---------------------------------------------------------------------------
# Đọc dữ liệu
# ---------------------------------------------------------------------------
note = pd.read_csv(NOTE_SRC, encoding="utf-8-sig")
panel = pd.read_csv(PANEL_SRC, encoding="utf-8-sig")
own = pd.read_csv(OWN_SRC, encoding="utf-8-sig")
own = own[own.date == own.date.max()]

KY = note.period.max()
TICKERS = sorted(note.ticker.unique())
PERIODS = sorted(note.period.unique())

NGUON_NOTE = (
    f"Nguồn: thuyết minh báo cáo tài chính qua vnstock ({NOTE_SRC.relative_to(ROOT).as_posix()}) — "
    f"{note.casa_percent.notna().sum()}/{22*len(PERIODS)} ô có số. "
    "CASA = tiền gửi không kỳ hạn / tổng tiền gửi khách hàng."
)

# ---------------------------------------------------------------------------
# fig_40 — CASA xếp hạng
# ---------------------------------------------------------------------------
s = note[note.period == KY][["ticker", "casa_percent"]].dropna()
s = s.sort_values("casa_percent")

fig, ax = plt.subplots(figsize=(9.2, 7.4))
y = np.arange(len(s))
ax.barh(y, s.casa_percent, height=0.72, color=ACCENT_FILL,
        edgecolor=ACCENT, linewidth=0.9)
for yi, (val, ten) in enumerate(zip(s.casa_percent, s.ticker)):
    ax.text(val + 0.45, yi, f"{val:.1f}", va="center", ha="left",
            fontsize=8.8, color=INK_2)
ax.set_yticks(y)
ax.set_yticklabels(s.ticker, fontsize=9)
ax.set_xlabel("CASA (%)")
ax.set_xlim(0, s.casa_percent.max() * 1.14)
ax.grid(axis="y", visible=False)

trung_vi = s.casa_percent.median()
ax.axvline(trung_vi, color=MUTED, lw=1, ls="--", zorder=0)
ax.text(trung_vi, len(s) - 0.3, f" trung vị {trung_vi:.1f}%", fontsize=8.5,
        color=INK_3, va="top", ha="left")

frame(ax, f"CASA theo ngân hàng, {KY}",
      f"Chênh {s.casa_percent.max()/s.casa_percent.min():.0f} lần giữa cao nhất và thấp nhất",
      "CASA là phần tiền gửi ngân hàng gần như không phải trả lãi, nên quyết định giá vốn. "
      "Đây là chỉ tiêu lần đầu có trong dự án — trước đây không nguồn nào trong kho tách được "
      "tiền gửi không kỳ hạn khỏi tiền gửi có kỳ hạn. " + NGUON_NOTE)
save(fig, "fig_40_casa_xep_hang")

# ---------------------------------------------------------------------------
# fig_41 — CASA vs chi phí vốn
# ---------------------------------------------------------------------------
j = panel[panel.period == KY][["ticker", "casa_percent", "cof_ttm_percent"]].dropna()
r = float(j.casa_percent.corr(j.cof_ttm_percent))

fig, ax = plt.subplots(figsize=(8.6, 6.4))
ax.scatter(j.casa_percent, j.cof_ttm_percent, s=62, color=ACCENT_FILL,
           edgecolor=ACCENT, linewidth=1.1, zorder=3)
slope, intercept = np.polyfit(j.casa_percent, j.cof_ttm_percent, 1)
xs = np.linspace(j.casa_percent.min() - 1, j.casa_percent.max() + 1, 50)
ax.plot(xs, slope * xs + intercept, color=MUTED, lw=1.4, ls="--", zorder=2)

nhan_khong_dam(ax, list(zip(j.casa_percent, j.cof_ttm_percent, j.ticker)))
ax.set_xlabel("CASA (%)")
ax.set_ylabel("Chi phí vốn, trượt 12 tháng (%)")

frame(ax, "CASA càng cao, huy động càng rẻ",
      f"{KY} · hệ số tương quan r = {r:.3f} trên {len(j)} ngân hàng",
      "Mỗi điểm phần trăm CASA tăng thêm đi kèm chi phí vốn giảm "
      f"{abs(slope):.3f} điểm. Đây là lý do CASA đáng đưa vào bộ tiêu chí: nó giải thích "
      "phần lớn chênh lệch giá vốn giữa các ngân hàng, thứ mà quy mô hay thị phần không "
      "giải thích được. " + NGUON_NOTE)
save(fig, "fig_41_casa_vs_chi_phi_von")

# ---------------------------------------------------------------------------
# fig_42 — CASA lưới 22 ngân hàng
# ---------------------------------------------------------------------------
pv = note.pivot(index="period", columns="ticker", values="casa_percent")
pv = pv.reindex(PERIODS)
x = np.array([q_to_num(p) for p in PERIODS])
thu_tu = pv.iloc[-1].sort_values(ascending=False).index.tolist()
ymax = float(np.nanmax(pv.values)) * 1.08

fig, axes = plt.subplots(4, 6, figsize=(14.6, 9.2), sharex=True, sharey=True)
for ax_i, ten in zip(axes.flat, thu_tu):
    chuoi = pv[ten].values
    ax_i.fill_between(x, 0, chuoi, color=ACCENT_FILL, alpha=0.85, zorder=2)
    ax_i.plot(x, chuoi, color=ACCENT, lw=1.5, zorder=3)
    cuoi = chuoi[~np.isnan(chuoi)]
    nhan = f"{ten}  {cuoi[-1]:.0f}%" if len(cuoi) else ten
    ax_i.text(0.04, 0.9, nhan, transform=ax_i.transAxes, fontsize=9,
              fontweight="600", color=INK, va="top", ha="left")
    ax_i.set_ylim(0, ymax)
    ax_i.grid(axis="x", visible=False)
    ax_i.tick_params(labelsize=8)
for ax_i in axes.flat[len(thu_tu):]:
    ax_i.set_visible(False)
for ax_i in axes[-1]:
    ax_i.set_xticks([2018, 2020, 2022, 2024, 2026])
    ax_i.set_xticklabels(["2018", "2020", "2022", "2024", "2026"], fontsize=8)

sut = (pv.loc["2023-Q1"] - pv.loc["2021-Q4"]).dropna()
ca_ky = (pv.loc[KY] - pv.loc["2018-Q1"]).dropna()

fig.suptitle("CASA từng ngân hàng, 2018-Q1 → " + KY, x=0.005, y=1.0,
             ha="left", fontsize=13, fontweight="600", color=INK)
fig.text(0.005, 0.966, "Cùng một thang dọc 0–%.0f%% nên so sánh trực tiếp được; "
         "xếp theo mức mới nhất" % ymax, ha="left", fontsize=9.5, color=INK_2)
ghi_chan(fig, "Giai đoạn lãi suất huy động tăng vọt cuối 2022 kéo CASA xuống ở "
              f"{int((sut < 0).sum())}/{len(sut)} ngân hàng — từ 2021-Q4 đến 2023-Q1 trung vị giảm "
              f"{abs(sut.median()):.1f} điểm, sâu nhất là {sut.idxmin()} {sut.min():.1f} điểm — vì người gửi "
              "chuyển tiền từ tài khoản thanh toán sang tiền gửi có kỳ hạn. Nhóm ngân hàng "
              "quốc doanh giảm nhẹ hơn hẳn nên nhìn qua tưởng phẳng. Tính cả kỳ thì "
              f"{int((ca_ky > 0).sum())} ngân hàng tăng và {int((ca_ky < 0).sum())} giảm; "
              f"{ca_ky.idxmin()} mất nhiều nhất, {abs(ca_ky.min()):.1f} điểm. " + NGUON_NOTE, y=0.028)
fig.subplots_adjust(top=0.93, hspace=0.22, wspace=0.12)
save(fig, "fig_42_casa_luoi")

# ---------------------------------------------------------------------------
# fig_43 — cơ cấu kỳ hạn cho vay
# ---------------------------------------------------------------------------
cols = ["loans_short_share_percent", "loans_medium_share_percent",
        "loans_long_share_percent"]
t = note[note.period == KY][["ticker"] + cols].dropna()
t = t.sort_values("loans_short_share_percent")

fig, ax = plt.subplots(figsize=(9.6, 7.4))
y = np.arange(len(t))
trai = np.zeros(len(t))
nhan_ky = ["Ngắn hạn", "Trung hạn", "Dài hạn"]
for col, mau, ten_ky in zip(cols, TENOR, nhan_ky):
    gia_tri = t[col].values
    ax.barh(y, gia_tri, left=trai, height=0.72, color=mau,
            edgecolor=SURFACE, linewidth=1.6, label=ten_ky)
    for yi, (v, l) in enumerate(zip(gia_tri, trai)):
        if v >= 9:
            ax.text(l + v / 2, yi, f"{v:.0f}", va="center", ha="center",
                    fontsize=8.2, color=INK if col != cols[2] else SURFACE)
    trai = trai + gia_tri
ax.set_yticks(y)
ax.set_yticklabels(t.ticker, fontsize=9)
ax.set_xlabel("Tỷ trọng dư nợ (%)")
ax.set_xlim(0, 100)
ax.grid(axis="y", visible=False)
ax.legend(loc="upper left", bbox_to_anchor=(0, -0.075), ncol=3)

frame(ax, f"Cơ cấu kỳ hạn dư nợ cho vay, {KY}",
      "Xếp theo tỷ trọng ngắn hạn — trên cùng là ngân hàng cho vay ngắn hạn nhiều nhất",
      "Ba bậc đậm nhạt cùng một màu vì kỳ hạn là thang có thứ tự, không phải ba loại "
      "ngang hàng. Cơ cấu kỳ hạn quyết định mức độ lệch kỳ hạn giữa huy động và cho vay — "
      "ngân hàng cho vay dài bằng vốn huy động ngắn chịu rủi ro thanh khoản cao hơn. "
      "Chỉ tiêu này lần đầu có trong dự án. "
      f"Nguồn: thuyết minh báo cáo tài chính qua vnstock ({NOTE_SRC.relative_to(ROOT).as_posix()}).")
save(fig, "fig_43_co_cau_ky_han_cho_vay")

# ---------------------------------------------------------------------------
# fig_44 — sở hữu nhà nước & room ngoại
# ---------------------------------------------------------------------------
o = own[["ticker", "state_own_percent", "foreign_own_percent",
         "foreign_room_percent"]].dropna(subset=["state_own_percent"])
o = o.sort_values("state_own_percent")

fig, axes = plt.subplots(1, 2, figsize=(13.4, 7.2), sharey=True)
y = np.arange(len(o))

ax = axes[0]
ax.barh(y, o.state_own_percent, height=0.72, color=ACCENT_FILL,
        edgecolor=ACCENT, linewidth=0.9)
for yi, v in enumerate(o.state_own_percent):
    if v > 0.5:
        ax.text(v + 1.2, yi, f"{v:.1f}", va="center", ha="left",
                fontsize=8.6, color=INK_2)
ax.set_yticks(y)
ax.set_yticklabels(o.ticker, fontsize=9)
ax.set_xlabel("Sở hữu nhà nước (%)")
ax.set_xlim(0, 92)
ax.grid(axis="y", visible=False)

gia_tri = o.state_own_percent.tolist()
khoang = [(gia_tri[i + 1] - gia_tri[i], i) for i in range(len(gia_tri) - 1)]
rong_nhat, vi_tri = max(khoang)
# Kẻ MỘT đường mảnh thay vì dải nền: dải nền chạy hết bề ngang trông như một
# thanh giá trị của ngân hàng ngay bên cạnh, đọc nhầm thành OCB có cột rất dài.
ax.axhline(vi_tri + 0.5, color=INK_3, lw=1, ls=(0, (4, 3)), zorder=4)
ax.text(91, vi_tri + 0.5, f"khoảng trống {rong_nhat:.1f} điểm  ",
        fontsize=8.6, color=INK_3, va="bottom", ha="right")
ax.set_title("Sở hữu nhà nước", fontsize=11, fontweight="600", loc="left", pad=10)

ax = axes[1]
ax.barh(y, o.foreign_room_percent, height=0.72, color=GRID,
        edgecolor=AXIS, linewidth=0.8, label="Room tối đa")
ax.barh(y, o.foreign_own_percent, height=0.44, color=ACCENT,
        label="Đã sở hữu")
for yi, (da, room) in enumerate(zip(o.foreign_own_percent, o.foreign_room_percent)):
    ax.text(room + 0.7, yi, f"{da:.1f}/{room:.0f}", va="center", ha="left",
            fontsize=8.2, color=INK_2)
ax.set_xlabel("Sở hữu nước ngoài (%)")
ax.set_xlim(0, 40)
ax.grid(axis="y", visible=False)
ax.tick_params(axis="y", length=0)
# Chú giải đặt DƯỚI trục: để trong khung thì nó đè lên nhãn của ngân hàng cuối bảng.
ax.legend(loc="upper left", bbox_to_anchor=(0, -0.055), ncol=2)
ax.set_title("Room ngoại: đã dùng bao nhiêu", fontsize=11, fontweight="600",
             loc="left", pad=10)

fig.suptitle("Cơ cấu sở hữu 22 ngân hàng niêm yết", x=0.005, y=1.075,
             ha="left", fontsize=13, fontweight="600", color=INK)
fig.text(0.005, 1.028, f"Ảnh chụp {own.date.max()} — không phải chuỗi thời gian",
         ha="left", fontsize=9.5, color=INK_2)
ghi_chan(fig, "Nhóm Nhà nước chi phối tách hẳn thành một cụm riêng: không ngân hàng nào "
              f"nằm giữa {gia_tri[vi_tri]:.1f}% và {gia_tri[vi_tri+1]:.1f}%. Với xếp hạng đa tiêu chí, "
              "đây gần như biến nhị phân chứ không phải thang liên tục, nên cân nhắc mã hoá "
              "thành nhóm. Room ngoại thấp (BVB, LPB, VIB ở 5%) là ràng buộc pháp lý riêng "
              "của từng ngân hàng, không phải thiếu quan tâm từ nhà đầu tư. "
              f"Nguồn: vnstock Company.overview ({OWN_SRC.relative_to(ROOT).as_posix()}).",
         y=-0.055)
fig.subplots_adjust(top=0.95, wspace=0.05)
save(fig, "fig_44_so_huu_nha_nuoc")

# ---------------------------------------------------------------------------
# fig_45 — chỉ số giá USD và vàng
# ---------------------------------------------------------------------------
px = pd.read_csv(PX_SRC, encoding="utf-8-sig", dtype={"month": str})
cpi = pd.read_csv(CPI_SRC, encoding="utf-8-sig", dtype={"month": str})
mac = cpi[["month", "cpi_yoy_percent"]].merge(
    px[["month", "usd_index_yoy_percent", "gold_index_yoy_percent"]],
    on="month", how="outer").sort_values("month")
mac = mac[mac.month >= "2018-01"]
mx = pd.to_datetime(mac.month + "-01")

fig, axes = plt.subplots(2, 1, figsize=(11.6, 7.8), sharex=True,
                         gridspec_kw={"height_ratios": [1, 1]})

ax = axes[0]
ax.axhline(0, color=AXIS, lw=1)
ax.plot(mx, mac.cpi_yoy_percent, color=INK_2, lw=1.6, label="CPI")
ax.plot(mx, mac.usd_index_yoy_percent, color=ACCENT, lw=2.0,
        label="Chỉ số giá đô la Mỹ")
ax.set_ylabel("Thay đổi so cùng kỳ (%)")
ax.legend(loc="upper left", ncol=2)
ax.set_title("CPI và chỉ số giá đô la Mỹ", fontsize=11, fontweight="600",
             loc="left")

ax = axes[1]
ax.axhline(0, color=AXIS, lw=1)
# KHÔNG dropna: giữ nguyên NaN để matplotlib NGẮT đường tại chỗ trống. Nếu bỏ
# NaN đi thì đoạn 2022-2023 sẽ nối thẳng qua 15 tháng không có số, vẽ ra một xu
# hướng không hề tồn tại trong dữ liệu.
n_vang = int(mac.gold_index_yoy_percent.notna().sum())
ax.plot(mx, mac.gold_index_yoy_percent,
        color=ACCENT, lw=2.0, marker="o", ms=3.2,
        markerfacecolor=SURFACE, markeredgewidth=1.1)
ax.set_ylabel("Thay đổi so cùng kỳ (%)")
ax.set_title(f"Chỉ số giá vàng — thang riêng, {n_vang}/{len(mac)} tháng có số",
             fontsize=11, fontweight="600", loc="left")

fig.suptitle("Hai kênh cạnh tranh với tiền gửi ngân hàng", x=0.005, y=1.0,
             ha="left", fontsize=13, fontweight="600", color=INK)
fig.text(0.005, 0.968, "Chỉ số giá theo tháng, 2018-01 → " + mac.month.max(),
         ha="left", fontsize=9.5, color=INK_2)
ghi_chan(fig, "Vàng vẽ ở thang riêng vì biên độ lớn gấp nhiều lần CPI và USD — ép chung "
              "một trục sẽ làm hai đường kia bẹp thành đường thẳng. Người gửi tiết kiệm so "
              "lãi suất với chính hai đường này, nên chúng là mốc tham chiếu chứ không phải "
              "biến vĩ mô nền. Đường vàng ĐỨT ĐOẠN ở chỗ nguồn không có số — từ 2021 bản công bố "
              "bỏ dần phần so cùng kỳ — chứ không nối thẳng qua khoảng trống. "
              f"Nguồn: NSO qua {PX_SRC.relative_to(ROOT).as_posix()} và {CPI_SRC.relative_to(ROOT).as_posix()}.",
         y=0.0)
fig.subplots_adjust(top=0.9, hspace=0.28)
save(fig, "fig_45_usd_vang_vs_cpi")

# ---------------------------------------------------------------------------
# fig_46 — ngành ngân hàng so với VN-Index
# ---------------------------------------------------------------------------
idx = pd.read_csv(IDX_SRC)
idx["date"] = pd.to_datetime(idx.time).dt.normalize()
idx = idx[idx.date >= "2018-01-01"][["date", "close"]].rename(
    columns={"close": "vnindex"})

chuoi = {}
for path in sorted(PRICE_DIR.glob("*.csv")):
    ten = path.stem
    if ten not in TICKERS:
        continue
    d = pd.read_csv(path)
    d["date"] = pd.to_datetime(d.time).dt.normalize()
    d = d[d.date >= "2018-01-01"][["date", "close"]]
    chuoi[ten] = d.set_index("date")["close"]

banks = pd.DataFrame(chuoi).sort_index()
base = idx.set_index("date")["vnindex"]
chung = banks.index.intersection(base.index)
banks, base = banks.loc[chung], base.loc[chung]

# Chỉ số ngành dựng từ TRUNG VỊ LỢI SUẤT NGÀY rồi tích luỹ, không phải chuẩn hoá
# từng chuỗi về 100 tại phiên đầu của riêng nó. Cách chuẩn hoá kia sai khi thành
# phần thay đổi: OCB lên sàn 01/2021, SSB 03/2021 — lấy mốc 100 tại ngày niêm yết
# của chính chúng rồi trộn chung sẽ thổi phồng đường trung vị, vì các mã lên sàn
# giữa sóng tăng xuất phát từ 100 đúng lúc thị trường đang đi lên.
# fill_method=None: mặc định pandas forward-fill giá trước khi tính, sinh ra lợi
# suất 0 giả ở những phiên ngân hàng không có dữ liệu. Để NaN thì phiên đó ngân
# hàng chỉ đơn giản không đóng góp vào trung vị.
loi_suat = banks.pct_change(fill_method=None)
so_ngan_hang = loi_suat.notna().sum(axis=1)
# TRUNG BÌNH chứ không phải trung vị. Trung bình lợi suất ngày qua các mã chính là
# lợi suất của danh mục đều tái cân bằng hằng ngày, nên tích luỹ lại ra một chỉ số
# có nghĩa. Tích luỹ TRUNG VỊ thì không: chuỗi lợi suất lệch phải nên trung vị luôn
# thấp hơn trung bình, nhân dồn 2.166 phiên sẽ kéo chỉ số ngành về 18 trong khi
# từng ngân hàng đều tăng nhiều lần -- đã kiểm và loại cách đó.
binh_quan_ngay = loi_suat.mean(axis=1, skipna=True).fillna(0)
nganh = (1 + binh_quan_ngay).cumprod() * 100
thi_truong = base / base.iloc[0] * 100

fig, axes = plt.subplots(2, 1, figsize=(11.6, 7.6), sharex=True,
                         gridspec_kw={"height_ratios": [4, 1]})

ax = axes[0]
ax.plot(thi_truong.index, thi_truong, color=INK_2, lw=2.0, zorder=3,
        label="VN-Index")
ax.plot(nganh.index, nganh, color=ACCENT, lw=2.4, zorder=4,
        label="Ngành ngân hàng (danh mục đều)")
ax.axhline(100, color=AXIS, lw=1, zorder=0)
ax.set_ylabel("Chỉ số, phiên đầu = 100")
ax.legend(loc="upper left", ncol=2)

cuoi_nganh, cuoi_tt = float(nganh.iloc[-1]), float(thi_truong.iloc[-1])
ax.annotate(f"{cuoi_nganh:.0f}", (nganh.index[-1], cuoi_nganh),
            textcoords="offset points", xytext=(6, 0), fontsize=9,
            color=ACCENT, va="center", fontweight="600")
ax.annotate(f"{cuoi_tt:.0f}", (thi_truong.index[-1], cuoi_tt),
            textcoords="offset points", xytext=(6, 0), fontsize=9,
            color=INK_2, va="center", fontweight="600")
ax.set_title("Ngành ngân hàng so với thị trường chung", fontsize=13,
             fontweight="600", loc="left", pad=18)
ax.text(0, 1.015, f"Chuẩn hoá từ 2018-01, {len(chung)} phiên",
        transform=ax.transAxes, fontsize=9.5, color=INK_2, va="bottom",
        ha="left")

ax = axes[1]
ax.fill_between(so_ngan_hang.index, 0, so_ngan_hang, color=ACCENT_FILL,
                alpha=0.9, zorder=2)
ax.plot(so_ngan_hang.index, so_ngan_hang, color=ACCENT, lw=1.2, zorder=3)
ax.set_ylim(0, 23)
ax.set_yticks([0, 11, 22])
ax.set_ylabel("Số NH", fontsize=9)
ax.grid(axis="x", visible=False)
ax.text(0.005, 0.86, "Số ngân hàng đóng góp vào chỉ số mỗi phiên",
        transform=ax.transAxes, fontsize=8.6, color=INK_2, va="top", ha="left")

ghi_chan(fig, "Trước đây kho không có chỉ số thị trường nào, nên mọi so sánh lợi suất cổ "
              "phiếu giữa các ngân hàng đều lẫn với xu thế chung. Có VN-Index rồi thì tách "
              "được phần biến động riêng của từng ngân hàng khỏi phần chung — điều kiện cần "
              "để tính beta và lợi suất điều chỉnh theo thị trường. Chỉ số ngành dựng từ trung "
              "vị lợi suất ngày chứ không chuẩn hoá từng chuỗi về 100, vì thành phần thay đổi "
              f"theo thời gian (panel dưới): từ {int(so_ngan_hang.iloc[1])} mã đầu 2018 lên đủ 22 mã. "
              f"Nguồn: {IDX_SRC.relative_to(ROOT).as_posix()} và data/price/.", y=0.0)
fig.subplots_adjust(top=0.9, hspace=0.12)
save(fig, "fig_46_nganh_vs_vnindex")

print(f"\nxong 7 hình | CASA {note.casa_percent.notna().sum()} ô | "
      f"sở hữu {len(o)} NH | vĩ mô {len(mac)} tháng | thị trường {len(chung)} phiên")
