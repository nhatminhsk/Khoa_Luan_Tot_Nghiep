"""Biểu đồ CAR từ data/credit/bank_car_halfyear.csv.

CAR chưa từng được vẽ trong dự án: bieu_do_kltn.ipynb ghi rõ bản vnstock
(fact_bank_quarterly.car_percent) chỉ đầy 11,8% nên "vẽ lên sẽ trông như phần lớn
ngân hàng có CAR = 0". Bộ dữ liệu nửa năm hiện tại đầy 88,2% (291/330 ô) nên đã vẽ được.

Ba hình, mỗi hình trả lời một câu hỏi khác nhau:
  fig_37  xu hướng ngành   -> CAR toàn ngành đi lên hay xuống?
  fig_38  xếp hạng một kỳ  -> kỳ mới nhất đủ dữ liệu, ai cao ai thấp?
  fig_37b ma trận từng ngân hàng -> tách riêng 22 ô, ô nào thiếu kỳ nào?
  fig_39  ma trận đầy đủ   -> ô nào có số, ô nào trống, ô nào ngân hàng không công bố?

Chỉ dùng MỘT sắc nhấn. Danh tính ngân hàng đến từ nhãn chữ chứ không từ màu, nhờ vậy
không có cặp màu nào có thể bị đọc nhầm, kể cả với người mù màu.

Chạy:  python bieu_do_car.py
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
SRC = ROOT / "data" / "credit" / "bank_car_halfyear.csv"
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

# --- bảng màu nhà, giữ nguyên từ bieu_do_kltn.ipynb ---
SURFACE, INK, INK_2, INK_3 = "#fcfcfb", "#0b0b0b", "#52514e", "#7b7a75"
GRID, AXIS, MUTED = "#e8e7e3", "#d8d7d2", "#c9c8c3"
ACCENT = "#2a78d6"
ACCENT_FILL = "#cde2fb"
SEQ = LinearSegmentedColormap.from_list(
    "seq_blue",
    ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"],
)
KHONG_CONG_BO = "#ebe9e4"   # ô ghi "NA" -- đã tra, ngân hàng không công bố
CHUA_CO = SURFACE           # ô trống -- chưa đi tìm

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


def tach_nhan(diem, khoang_toi_thieu):
    """Đẩy các nhãn quá sát nhau ra xa theo trục dọc.

    Ở kỳ cuối, STB (9,20) và BID (9,18) chỉ cách nhau 0,02 điểm nên hai nhãn chồng
    khít lên nhau thành một đống chữ không đọc được. Hàm này giữ nguyên thứ tự nhưng
    ép khoảng cách tối thiểu giữa hai nhãn liền kề.
    """
    ra, truoc = [], -np.inf
    for y, ten in sorted(diem):
        y_moi = max(y, truoc + khoang_toi_thieu)
        ra.append((y, y_moi, ten))
        truoc = y_moi
    return ra


# ---------------------------------------------------------------------------
# Đọc dữ liệu. Đọc HAI lần: một lần giữ nguyên chuỗi để phân biệt ô ghi "NA"
# (đã tra, ngân hàng không công bố) với ô trống (chưa đi tìm) -- hai trạng thái này
# khác nhau về ý nghĩa và hình 39 vẽ chúng khác nhau.
# ---------------------------------------------------------------------------
raw = pd.read_csv(SRC, keep_default_na=False)
df = pd.read_csv(SRC)
df["la_NA"] = raw["car_percent"].str.strip().str.upper() == "NA"

TICKERS = sorted(df.ticker.unique())
PERIODS = sorted(df.period.unique())
pv = df.pivot(index="ticker", columns="period", values="car_percent")
na = df.pivot(index="ticker", columns="period", values="la_NA")

n_o, n_co = len(df), int(df.car_percent.notna().sum())
NGUON_CHUNG = (
    f"Nguồn: bảng CAR nửa năm tự hợp ({SRC.relative_to(ROOT).as_posix()}) — "
    f"bản ngân hàng tự công bố (Trụ cột 3) gộp với vnstock; {n_co}/{n_o} ô có số ({n_co/n_o:.1%}). "
    "CAR hợp nhất, cơ sở Thông tư 41/2016."
)
LUU_Y_TT14 = (
    "Thông tư 14/2025 thay TT41 từ 15/09/2025 và thường cho CAR cao hơn, nhưng kiểm tra bước "
    "2025-H1 → 2025-H2 không thấy lệch hệ thống giữa nhóm đang chuyển Basel III (trung vị −0,14 điểm) "
    "và nhóm còn lại (−0,08), nên chuỗi không bị gãy cơ sở."
)

# ===========================================================================
# Hình 37 -- xu hướng ngành, trên BẢNG CÂN ĐỐI
# ===========================================================================
# Trung vị tính trên toàn bộ 22 ngân hàng sẽ bị bóp méo vì số ngân hàng có số thay
# đổi từng kỳ (11 đến 22). Nên chỉ lấy các ngân hàng có ĐỦ mọi kỳ trong khung lõi ->
# thành phần mẫu cố định, mọi thay đổi của đường trung vị là thay đổi thật.
CORE = [p for p in PERIODS if "2019-H2" <= p <= "2025-H2"]
bal = pv[CORE].dropna()
x = np.arange(len(CORE))

fig, ax = plt.subplots(figsize=(11, 5.6))
for t in bal.index:                                   # 14 đường nền, không nhấn
    ax.plot(x, bal.loc[t], color=MUTED, lw=0.9, zorder=1)

p25, med, p75 = bal.quantile(.25), bal.median(), bal.quantile(.75)
ax.fill_between(x, p25, p75, color=ACCENT_FILL, alpha=.85, lw=0, zorder=2,
                label="Khoảng từ phân vị 25 đến 75")
ax.plot(x, med, color=ACCENT, lw=2.2, marker="o", ms=5,
        mfc=SURFACE, mew=1.8, zorder=4, label="Trung vị 14 ngân hàng")
ax.axhline(8, color=INK_3, lw=1.1, ls="--", zorder=3)
ax.text(len(CORE) - .5, 8.12, "Ngưỡng tối thiểu 8% (TT41)", fontsize=8.5,
        color=INK_3, ha="right", va="bottom")

# Nhãn chữ cho 2 ngân hàng cao nhất và 2 thấp nhất ở kỳ cuối — danh tính bằng CHỮ.
# Nhãn nào bị đẩy khỏi vị trí thật thì nối lại bằng một nét mảnh để không hiểu sai.
cuoi = bal[CORE[-1]].sort_values()
chon = list(cuoi.index[:2]) + list(cuoi.index[-2:])
for y_that, y_ve, ten in tach_nhan([(bal.loc[t, CORE[-1]], t) for t in chon], .55):
    if abs(y_ve - y_that) > .02:
        ax.plot([x[-1], x[-1] + .16], [y_that, y_ve], color=MUTED, lw=.7, zorder=4)
    ax.annotate(f" {ten}", (x[-1] + .16, y_ve), fontsize=8.5,
                color=INK_2, va="center", ha="left", zorder=5)

ax.set_xticks(x)
ax.set_xticklabels([p.replace("-", "\n") for p in CORE], fontsize=8.5)
ax.set_xlim(-.4, len(CORE) - .1 + .9)
ax.set_ylim(7.5, 18)
ax.set_ylabel("CAR hợp nhất (%)")
ax.legend(loc="upper left", bbox_to_anchor=(0, .99))
frame(ax, "Hệ số an toàn vốn của 14 ngân hàng, 2019-H2 đến 2025-H2",
      "Đường xám là từng ngân hàng; dải xanh là nửa giữa của phân bố",
      "Chỉ lấy 14/22 ngân hàng có ĐỦ cả 13 kỳ, nên mọi thay đổi của đường trung vị là thay đổi "
      "thật chứ không phải do số ngân hàng trong mẫu thay đổi. Đã bỏ hai kỳ đầu và cuối khung "
      "(2019-H1 còn 12 ngân hàng, 2026-H1 còn 11) vì quá mỏng. " + NGUON_CHUNG + " " + LUU_Y_TT14)
save(fig, "fig_37_car_xu_huong")

# ===========================================================================
# Hình 37b -- lưới small multiples, tách riêng cả 22 ngân hàng
# ===========================================================================
# Theo khuôn luoi_nho/ten_o của bieu_do_theo_doc.ipynb (xem doc_03a_du_no_22nh):
# 6 cột, tiêu đề ô là mã, số góc phải, nền tô nhạt dưới đường.
#
# Khác bản dư nợ ở MỘT điểm, và là điểm cố ý: bản đó cho mỗi ô một thang y riêng
# (set_ylim(0, max*1.2)) vì dư nợ chênh nhau tới hai bậc độ lớn -- 48 nghìn tỷ so với
# 2.467 nghìn tỷ thì chung thang là ô nhỏ bẹp dí. CAR thì ngược lại: cả 291 quan sát
# nằm gọn trong 8,2%-17,1%, nên thang riêng từng ô sẽ khiến BID dao động 8,6-9,6 trông
# y hệt TCB dao động 13,8-16,9 -- người đọc sẽ hiểu ngược về sức mạnh vốn. Vì vậy dùng
# THANG CHUNG, đúng nguyên tắc mà chính fig_13b_luoi_roe đã ghi: "thang đo chung cho
# cả 22 ô nên so ngang được".
#
# Đáy vùng tô đặt ở 8% chứ không phải 0: phần tô là ĐỆM VỐN TRÊN NGƯỠNG tối thiểu,
# một mốc có nghĩa thật. Tô từ 0 thì 8 điểm dưới cùng là phần không ngân hàng nào được
# phép chạm tới, chiếm nửa hình mà không mang thông tin gì.
NCOT, NGUONG = 6, 8.0
nhang = int(np.ceil(len(TICKERS) / NCOT))
fig, axes = plt.subplots(nhang, NCOT, figsize=(NCOT * 2.3, nhang * 1.5),
                         sharex=True, sharey=True)
axes = np.atleast_1d(axes).ravel()
for ax in axes[len(TICKERS):]:
    ax.set_visible(False)

xa = np.arange(len(PERIODS))
for ax, ma in zip(axes, TICKERS):          # TICKERS đã sắp theo abc như NH22
    v = pv.loc[ma, PERIODS].to_numpy(dtype=float)
    co = int(np.isfinite(v).sum())
    ax.fill_between(xa, NGUONG, v, where=np.isfinite(v), color=ACCENT, alpha=.15)
    ax.plot(xa, v, lw=1.4, color=ACCENT, marker="o", ms=2.4, mec=SURFACE, mew=.5)
    ax.axhline(NGUONG, color=INK_3, lw=.8, ls="--", zorder=1)
    moi_nhat = v[np.isfinite(v)]
    # Ô quá thưa thì tên mã để xám, đúng cách doc_12b đánh dấu ngân hàng thiếu số
    ax.set_title(ma, fontsize=9.5, fontweight="600", pad=3, loc="left",
                 color=INK if co >= 10 else MUTED)
    ax.text(1.0, 1.02, f"{moi_nhat[-1]:.2f}" if len(moi_nhat) else "—",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=7.6, color=INK_3)
    ax.set_xticks([0, 4, 8, 12])
    ax.set_xticklabels(["2019", "2021", "2023", "2025"], fontsize=7.5)
    ax.tick_params(labelsize=7.5, length=2)

axes[0].set_ylim(NGUONG, 17.6)
axes[0].set_yticks([8, 11, 14, 17])
for ax in axes[:len(TICKERS)]:
    ax.label_outer()

cao = fig.get_figheight()
fig.tight_layout(rect=(0, 0, 1, 1 - .80 / cao))
fig.text(.008, 1 - .10 / cao, "CAR theo nửa năm — 22 ngân hàng", fontsize=14.5,
         fontweight="600", color=INK, ha="left", va="top")
fig.text(.008, 1 - .44 / cao,
         f"% · {PERIODS[0]} → {PERIODS[-1]} · {n_co} quan sát · "
         "số góc phải mỗi ô là CAR kỳ gần nhất",
         fontsize=10.2, color=INK_2, ha="left", va="top")
fig.text(.008, -.10 / cao, textwrap.fill(
    "Thang đo chung cho cả 22 ô nên so ngang được — CAR là tỷ lệ, không phải quy mô, nên "
    "để mỗi ô một thang riêng sẽ làm ngân hàng vốn mỏng trông y như ngân hàng vốn dày. "
    "Nét đứt và đáy vùng tô là ngưỡng tối thiểu 8%, nên phần tô chính là đệm vốn trên ngưỡng. "
    "Đường đứt đoạn là kỳ không có số, không nối liền qua chỗ trống; mã để xám là ngân hàng "
    "có dưới 10/15 kỳ (NVB). " + NGUON_CHUNG, 145),
    fontsize=8.4, color=INK_3, ha="left", va="top")
save(fig, "fig_37b_luoi_car")

# ===========================================================================
# Hình 38 -- xếp hạng tại kỳ mới nhất còn đủ dữ liệu
# ===========================================================================
# Không dùng 2026-H1: kỳ đó mới có 11/22 ngân hàng, xếp hạng trên nửa bảng là sai lệch.
KY = "2025-H2"
s = pv[KY].dropna().sort_values()

fig, ax = plt.subplots(figsize=(9, 7.4))
ax.barh(np.arange(len(s)), s.values, color=ACCENT, height=.62, zorder=3)
ax.axvline(8, color=INK_3, lw=1.1, ls="--", zorder=4)
for i, (t, v) in enumerate(s.items()):
    ax.text(v + .12, i, f"{v:.2f}", va="center", ha="left", fontsize=8.6, color=INK_2)
ax.set_yticks(np.arange(len(s)))
ax.set_yticklabels(s.index, fontsize=9)
ax.set_ylim(-.8, len(s) - .1)
ax.set_xlim(0, 18.6)
ax.set_xlabel("CAR hợp nhất (%)")
ax.grid(axis="y", visible=False)
# Nhãn ngưỡng đặt DƯỚI đáy cột thấp nhất để không đè lên cột nào.
ax.text(8.1, -.72, "Ngưỡng 8%", fontsize=8.5, color=INK_3, ha="left", va="bottom")
frame(ax, f"Xếp hạng CAR tại {KY} (chốt 31/12/2025)",
      f"{len(s)}/22 ngân hàng có số; mọi ngân hàng đều vượt ngưỡng tối thiểu",
      f"Lấy {KY} làm kỳ đối chiếu chứ không lấy 2026-H1 vì kỳ mới nhất mặc dù mới hơn "
      f"nhưng chỉ có 11/22 ngân hàng công bố, xếp hạng trên nửa bảng sẽ sai lệch. "
      f"Thiếu {22 - len(s)} ngân hàng: {', '.join(sorted(set(TICKERS) - set(s.index)))}. "
      + NGUON_CHUNG)
save(fig, "fig_38_car_xep_hang")

# ===========================================================================
# Hình 39 -- ma trận đầy đủ, thấy rõ ô nào thiếu
# ===========================================================================
fig, ax = plt.subplots(figsize=(12, 8))
M = pv.loc[TICKERS, PERIODS].values.astype(float)
lo, hi = np.nanpercentile(M, 2), np.nanpercentile(M, 98)
im = ax.imshow(M, cmap=SEQ, aspect="auto", vmin=lo, vmax=hi)

for i, t in enumerate(TICKERS):
    for j, p in enumerate(PERIODS):
        v = pv.loc[t, p]
        if pd.notna(v):
            # Chữ đen hay trắng tuỳ ô nhạt hay đậm. Ngưỡng 0,50 chứ không phải 0,62:
            # ở 0,62 các ô xanh tầm giữa vẫn nhận chữ đen và bị chìm.
            dam = (min(max(v, lo), hi) - lo) / max(hi - lo, 1e-9)
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7.6,
                    color="white" if dam > .50 else INK)
        else:
            ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1,
                         facecolor=KHONG_CONG_BO if na.loc[t, p] else CHUA_CO,
                         edgecolor=AXIS, lw=.6, zorder=2))
            if na.loc[t, p]:
                ax.text(j, i, "NA", ha="center", va="center", fontsize=7,
                        color=INK_3, zorder=3)

ax.set_xticks(np.arange(len(PERIODS)))
ax.set_xticklabels([p.replace("-", "\n") for p in PERIODS], fontsize=8.4)
ax.set_yticks(np.arange(len(TICKERS)))
ax.set_yticklabels(TICKERS, fontsize=9)
ax.set_xticks(np.arange(-.5, len(PERIODS), 1), minor=True)
ax.set_yticks(np.arange(-.5, len(TICKERS), 1), minor=True)
ax.grid(which="minor", color=SURFACE, lw=1.4)
ax.grid(which="major", visible=False)
ax.tick_params(which="minor", length=0)

cb = fig.colorbar(im, ax=ax, pad=.015, fraction=.026)
cb.set_label("CAR hợp nhất (%)", fontsize=9, color=INK_2)
cb.outline.set_visible(False)
ax.legend(handles=[
    Patch(facecolor=KHONG_CONG_BO, edgecolor=AXIS, label='Ghi "NA" — ngân hàng không công bố'),
    Patch(facecolor=CHUA_CO, edgecolor=AXIS, label="Trống — chưa tra được số"),
], loc="upper left", bbox_to_anchor=(0, -.075), ncol=2)

n_na, n_trong = int(na.values.sum()), int(pv.isna().values.sum() - na.values.sum())
frame(ax, "Ma trận CAR: 22 ngân hàng × 15 kỳ nửa năm",
      f"{n_co}/{n_o} ô có số ({n_co/n_o:.1%}); {n_na} ô ghi NA; {n_trong} ô còn trống",
      'Hai loại ô rỗng không đồng nghĩa: ô "NA" là đã tra và ngân hàng không công bố, '
      "ô trống là chưa tìm ra số. Hai đầu khung thưa nhất (2019-H1 và 2026-H1) vì các kỳ này "
      "ngân hàng công bố ít hơn hẳn. " + NGUON_CHUNG)
save(fig, "fig_39_car_ma_tran")

print(f"\nxong 3 hình | bảng cân đối {len(bal)} NH × {len(CORE)} kỳ | "
      f"xếp hạng {KY} {len(s)} NH | lưới {n_co}/{n_o} ô")
