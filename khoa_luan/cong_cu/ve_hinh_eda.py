import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
RA = REPO / "figures" / "khoa_luan" / "eda"
RA.mkdir(parents=True, exist_ok=True)
XANH, CAM, NGOC, XAM, CHU, CHU2 = "#2a78d6", "#eb6834", "#1baf7a", "#c3c2b7", "#0b0b0b", "#52514e"
plt.rcParams.update({
    "font.family": "Times New Roman", "font.size": 10.5, "axes.edgecolor": XAM, "axes.labelcolor": CHU,
    "xtick.color": CHU2, "ytick.color": CHU2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e1e0d9", "grid.linewidth": 0.6, "axes.axisbelow": True,
    "legend.frameon": False, "savefig.dpi": 300, "savefig.bbox": "tight", "figure.facecolor": "white",
})
PHAY = FuncFormatter(lambda v, _: f"{v:g}".replace(".", ","))
CHI_TIEU = {"npl_percent": "NPL (%)", "casa_percent": "CASA (%)", "ldr_computed_percent": "LDR (%)"}


def _panel() -> pd.DataFrame:
    p = pd.read_csv(REPO / "data/model/bank_panel_quarterly.csv", encoding="utf-8-sig")
    p["q"] = p.period.str[-1].astype(int)
    p["nam"] = p.period.str[:4].astype(int)
    return p.sort_values(["ticker", "period"])


def _luu(fig, ten):
    fig.savefig(RA / ten, facecolor="white")
    plt.close(fig)
    print("ghi", RA / ten)


def do_phu(p):
    cot = {"npl_percent": "NPL", "loans_g2_percent": "Nợ nhóm 2", "casa_percent": "CASA", "ldr_computed_percent": "LDR",
           "car_percent": "CAR", "nim_ttm_percent": "NIM", "cof_ttm_percent": "COF", "roa_ttm_percent": "ROA",
           "roe_ttm_percent": "ROE", "earning_asset_yield_ttm_percent": "Lợi suất TSSL", "pb": "P/B"}
    m = p.groupby("nam")[list(cot)].apply(lambda g: g.notna().mean()).T
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    im = ax.imshow(m.values * 100, cmap="Blues", vmin=0, vmax=100, aspect="auto")
    ax.set_yticks(range(len(cot)), list(cot.values()))
    ax.set_xticks(range(m.shape[1]), m.columns)
    ax.grid(False)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m.values[i, j] * 100
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8, color="white" if v > 60 else CHU)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("Tỷ lệ ô có dữ liệu (%)")
    _luu(fig, "h_do_phu.png")


def phan_phoi(p):
    d = p[p.period >= "2019-Q1"]
    fig, axs = plt.subplots(1, 3, figsize=(7.0, 2.6))
    for ax, (c, ten) in zip(axs, CHI_TIEU.items()):
        x = d[c].dropna()
        hi = x.quantile(0.99)
        ax.hist(x.clip(upper=hi), bins=30, color=XANH, edgecolor="white", linewidth=0.6)
        ax.axvline(x.median(), color=CAM, lw=1.5)
        ax.set_xlabel(ten)
        ax.text(0.97, 0.93, f"trung vị {x.median():.2f}".replace(".", ","), transform=ax.transAxes, ha="right",
                fontsize=8.5, color=CHU2)
        ax.xaxis.set_major_formatter(PHAY)
    axs[0].set_ylabel("Số ngân hàng–quý")
    fig.tight_layout()
    _luu(fig, "h_phan_phoi.png")


def xu_huong(p):
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.7), sharex=True)
    ky = sorted(p.period.unique())
    x = np.arange(len(ky))
    for ax, (c, ten) in zip(axs, CHI_TIEU.items()):
        g = p.groupby("period")[c]
        ax.fill_between(x, g.quantile(0.25).reindex(ky), g.quantile(0.75).reindex(ky), color=XANH, alpha=0.18, lw=0)
        ax.plot(x, g.median().reindex(ky), color=XANH, lw=2)
        ax.set_title(ten, fontsize=10.5, color=CHU)
        ax.set_xticks(x[::8], [k[:4] for k in ky[::8]])
        ax.yaxis.set_major_formatter(PHAY)
    fig.tight_layout()
    _luu(fig, "h_xu_huong.png")


def npl_theo_nh(p):
    d = p[p.period >= "2018-Q1"].pivot(index="period", columns="ticker", values="npl_percent")
    x = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    noi = {"STB": CAM, "VCB": XANH, "NVB": NGOC}
    for tk in d.columns:
        if tk not in noi:
            ax.plot(x, d[tk], color=XAM, lw=0.8)
    for tk, mau in noi.items():
        ax.plot(x, d[tk], color=mau, lw=2, label=tk)
    ax.set_ylim(0, 12)
    ax.set_xticks(x[::4], [k[:4] for k in d.index[::4]])
    ax.set_ylabel("NPL (%)")
    ax.yaxis.set_major_formatter(PHAY)
    ax.legend(loc="upper left", ncol=3, fontsize=9)
    ax.text(len(x) - 1, 11.6, "NVB vượt 12% ở một số quý (bị cắt trục)", ha="right", fontsize=8, color=CHU2)
    _luu(fig, "h_npl_theo_nh.png")


def mua_vu(p):
    d = p[p.period >= "2019-Q1"].copy()
    fig, axs = plt.subplots(1, 2, figsize=(6.8, 2.8))
    for ax, (c, ten) in zip(axs, (("npl_percent", "Thay đổi NPL so với quý trước (điểm %)"),
                                  ("casa_percent", "Thay đổi CASA so với quý trước (điểm %)"))):
        d["d"] = d.groupby("ticker")[c].diff()
        nhom = [d.loc[d.q == q, "d"].dropna().clip(-3 if c == "npl_percent" else -8, 3 if c == "npl_percent" else 8)
                for q in (1, 2, 3, 4)]
        bp = ax.boxplot(nhom, tick_labels=["Quý 1", "Quý 2", "Quý 3", "Quý 4"], patch_artist=True, widths=0.55,
                        medianprops=dict(color=CAM, lw=1.6), flierprops=dict(marker=".", ms=3, mec=XAM))
        for b in bp["boxes"]:
            b.set(facecolor="#d6e2f0", edgecolor=XANH)
        ax.axhline(0, color=CHU2, lw=0.8)
        ax.set_ylabel(ten, fontsize=9.5)
        ax.yaxis.set_major_formatter(PHAY)
    fig.tight_layout()
    _luu(fig, "h_mua_vu.png")


def tuong_quan(p):
    cot = {"npl_percent": "NPL", "loans_g2_percent": "Nợ nhóm 2", "casa_percent": "CASA", "ldr_computed_percent": "LDR",
           "car_percent": "CAR", "nim_ttm_percent": "NIM", "cof_ttm_percent": "COF", "roa_ttm_percent": "ROA",
           "loans_yoy_percent": "Tăng dư nợ"}
    d = p[p.period >= "2019-Q1"][list(cot)].rename(columns=cot)
    r = d.corr(method="spearman")
    fig, ax = plt.subplots(figsize=(5.6, 4.6))
    from matplotlib.colors import LinearSegmentedColormap
    cm = LinearSegmentedColormap.from_list("phan_ky", ["#e34948", "#f0efec", XANH])
    im = ax.imshow(r.values, cmap=cm, vmin=-1, vmax=1)
    ax.set_xticks(range(len(r)), r.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(r)), r.columns)
    ax.grid(False)
    for i in range(len(r)):
        for j in range(len(r)):
            ax.text(j, i, f"{r.values[i, j]:.2f}".replace(".", ","), ha="center", va="center", fontsize=7.5,
                    color="white" if abs(r.values[i, j]) > 0.6 else CHU)
    fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02, label="Hệ số Spearman")
    _luu(fig, "h_tuong_quan.png")


def ben_vung(p):
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.6))
    d = p[p.period >= "2019-Q1"].copy()
    for ax, (c, ten) in zip(axs, CHI_TIEU.items()):
        d["sau"] = d.groupby("ticker")[c].shift(-1)
        m = d[[c, "sau"]].dropna()
        lo, hi = m.quantile(0.005).min(), m.quantile(0.995).max()
        ax.scatter(m[c], m.sau, s=5, color=XANH, alpha=0.45, lw=0)
        ax.plot([lo, hi], [lo, hi], color=CAM, lw=1)
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_xlabel(f"{ten} quý t")
        ax.set_ylabel(f"{ten} quý t + 1")
        rho = m[[c, "sau"]].corr().iloc[0, 1]
        ax.text(0.05, 0.9, f"r = {rho:.2f}".replace(".", ","), transform=ax.transAxes, fontsize=9, color=CHU)
        ax.xaxis.set_major_formatter(PHAY)
        ax.yaxis.set_major_formatter(PHAY)
    fig.tight_layout()
    _luu(fig, "h_ben_vung.png")


def lai_suat_theo_thoi_gian():
    d = pd.read_csv(REPO / "data/model/ranking_daily.csv", encoding="utf-8-sig", parse_dates=["date"])
    d = d[d.date <= "2026-10-29"].dropna(subset=["dep12_online_pct"])
    g = d.groupby("date").dep12_online_pct
    s = pd.DataFrame({"min": g.min(), "med": g.median(), "max": g.max(), "n": g.size()})
    s = s[s.n >= 15]
    fig, ax = plt.subplots(figsize=(6.6, 2.9))
    ax.fill_between(s.index, s["min"], s["max"], color=XANH, alpha=0.16, lw=0, label="Thấp nhất – cao nhất")
    ax.plot(s.index, s["med"], color=XANH, lw=2, marker="o", ms=3, label="Trung vị 22 ngân hàng")
    ax.axvline(pd.Timestamp("2026-10-18"), color=CAM, lw=1, ls=(0, (4, 3)))
    ax.text(pd.Timestamp("2026-10-10"), s["max"].max() + 0.1, "CV 9608\n18/10/2026", ha="right", fontsize=8,
            color=CHU2)
    ax.set_xlim(s.index.min() - pd.Timedelta(days=20), s.index.max() + pd.Timedelta(days=20))
    ax.set_ylabel("Lãi suất 12 tháng trực tuyến (%/năm)")
    ax.yaxis.set_major_formatter(PHAY)
    ax.legend(loc="upper center", ncol=2, fontsize=9)
    _luu(fig, "h_lai_suat_12t.png")


def lai_vs_an_toan():
    f = pd.read_csv(REPO / "data/model/experiments/inputs/features_ranking_2026-11-06.csv", encoding="utf-8-sig")
    spec = pd.read_csv(REPO / "data/model/ranking_spec.csv", encoding="utf-8-sig")
    spec = spec[(spec.freq == "quý") & (spec.deposit_group == "an toàn")]
    tru = {}
    for _, s in spec.iterrows():
        x = f[s.feature].astype(float).fillna(f[s.feature].median())
        r = (x - x.min()) / (x.max() - x.min())
        tru.setdefault(s.pillar, []).append(r if s.direction == 1 else 1 - r)
    an_toan = pd.DataFrame({k: pd.concat(v, axis=1).mean(axis=1) for k, v in tru.items()}).mean(axis=1)
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    ax.scatter(an_toan, f.dep12_online_pct, s=36, color=XANH, edgecolor="white", lw=0.8, zorder=3)
    for tk, a, l in zip(f.ticker, an_toan, f.dep12_online_pct):
        ax.annotate(tk, (a, l), xytext=(4, 3), textcoords="offset points", fontsize=7.5, color=CHU2)
    from scipy.stats import spearmanr
    rho, pv = spearmanr(an_toan, f.dep12_online_pct)
    ax.text(0.02, 0.95, f"ρ = {rho:.2f}; p = {pv:.2f}".replace(".", ","), transform=ax.transAxes, fontsize=9)
    ax.set_xlabel("Điểm an toàn tổng hợp (0 = kém nhất, 1 = tốt nhất)")
    ax.set_ylabel("Lãi 12 tháng trực tuyến (%/năm)")
    ax.xaxis.set_major_formatter(PHAY)
    ax.yaxis.set_major_formatter(PHAY)
    _luu(fig, "h_lai_vs_an_toan.png")
    print(f"rho lai-an toan {rho:.3f} p {pv:.3f}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    p = _panel()
    for fn in (do_phu, phan_phoi, xu_huong, npl_theo_nh, mua_vu, tuong_quan, ben_vung):
        fn(p)
    lai_suat_theo_thoi_gian()
    lai_vs_an_toan()
