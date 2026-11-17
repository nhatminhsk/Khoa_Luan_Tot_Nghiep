import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ve_hinh_mo_hinh as vh  # noqa: E402  (dùng chung kiểu chữ, màu, hàm lưu)

plt = vh.plt
REPO = vh.REPO
DG = REPO / "data/model/experiments/danh_gia_co_dinh"
DN = REPO / "data/model/experiments/do_nhay_xep_hang"
RA4 = REPO / "figures/khoa_luan/chuong4"
RA4.mkdir(parents=True, exist_ok=True)
TEN_CT = {"npl_percent": "NPL", "casa_percent": "CASA", "ldr_computed_percent": "LDR"}
THU_TU = ["NPL", "CASA", "LDR"]


def _tom_tat() -> pd.DataFrame:
    return pd.read_csv(DG / "tom_tat.csv", encoding="utf-8-sig")


def hinh_so_sanh_h1(S: pd.DataFrame):
    d = S[S.h == 1].pivot_table(index="indicator", columns="method", values="mae").loc[THU_TU]
    fig, ax = plt.subplots(figsize=(6.8, 3.1))
    w = 0.16
    cot = (("base", "Mô hình cơ sở", vh.XAM), ("ridge", "Ridge", vh.NGOC), ("lgbm_res", "LightGBM", vh.VANG),
           ("rf_2019", "Random Forest", vh.XANH), ("lai_A", "Mô hình lai (quy tắc chọn)", "#0d366b"))
    for k, (c, ten, mau) in enumerate(cot):
        g = (1 - d[c] / d["naive"]) * 100
        ax.bar(np.arange(len(d)) + (k - 2) * w, g, width=w * 0.95, color=mau, label=ten)
    ax.axhline(0, color=vh.CHU2, lw=0.8)
    ax.set_xticks(range(len(d)), d.index)
    ax.set_ylabel("Giảm MAE so với giữ nguyên (%)")
    from matplotlib.ticker import MultipleLocator
    ax.yaxis.set_major_locator(MultipleLocator(2))
    ax.yaxis.set_major_formatter(vh.PHAN_TRAM)
    ax.legend(ncol=3, fontsize=8.3, loc="lower center", bbox_to_anchor=(0.5, 1.0), frameon=False)
    vh._luu(fig, "h_so_sanh_mo_hinh.png")


def hinh_theo_tam(S: pd.DataFrame):
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 3.0), sharey=False)
    for ax, ct in zip(axs, THU_TU):
        x = np.arange(1, 5)
        for k, (m, ten, mau) in enumerate((("rf_2019", "RF học từ 2019", vh.XANH),
                                           ("rf_2013", "RF học từ 2013", "#0d366b"))):
            g = S[(S.indicator == ct) & (S.method == m)].sort_values("h")
            xx = x + (k - 0.5) * 0.28
            ax.bar(xx, g.gain_vs_base * 100, width=0.26, color=mau, label=ten if ct == "NPL" else None)
            ax.errorbar(xx, g.gain_vs_base * 100, yerr=[(g.gain_vs_base - g.lo) * 100, (g.hi - g.gain_vs_base) * 100],
                        fmt="none", color=vh.CHU2, lw=0.7, capsize=1.8)
        a = S[(S.indicator == ct) & (S.method == "lai_A")].sort_values("h")
        b = S[(S.indicator == ct) & (S.method == "lai_B")].sort_values("h")
        ax.scatter(x, a.gain_vs_base * 100, marker="D", s=22, color=vh.CAM, zorder=5,
                   label="Quy tắc chọn, tập chọn 2021–2022" if ct == "NPL" else None)
        ax.scatter(x, b.gain_vs_base * 100, marker="o", s=26, facecolor="none", edgecolor=vh.CHU, zorder=6, lw=0.9,
                   label="Quy tắc chọn, tập chọn mở rộng về 2019" if ct == "NPL" else None)
        ax.axhline(0, color=vh.CHU2, lw=0.8)
        ax.set_xticks(x, [f"{h}" for h in x])
        ax.set_xlabel("Tầm dự báo (quý)")
        ax.set_title(ct, fontsize=10.5, color=vh.CHU)
        ax.yaxis.set_major_formatter(vh.PHAN_TRAM)
        lo = min(-20, (S[(S.indicator == ct) & S.method.isin(["rf_2019", "rf_2013"])].lo * 100).min() - 2)
        ax.set_ylim(max(lo, -60), 22)
    axs[0].set_ylabel("Giảm MAE so với mô hình cơ sở (%)")
    fig.legend(ncol=2, fontsize=8.2, loc="lower center", bbox_to_anchor=(0.5, 0.98), frameon=False)
    fig.tight_layout()
    vh._luu(fig, "h_rf_theo_tam.png")


def _du_doan_rf(P: pd.DataFrame, t: str, h: int, p: pd.DataFrame, method: str = "rf_2019") -> pd.DataFrame:
    g = P[(P.indicator == t) & (P.h == h) & (P.method == method) & (P.origin >= vh.TEST_FROM)].copy()
    g["thuc_te"] = g.x0 + g.y
    g["du_bao"] = g.x0 + g.pred
    return g.dropna(subset=["thuc_te", "du_bao"])


def hinh_thuc_te(P: pd.DataFrame, p: pd.DataFrame):
    fig, axs = plt.subplots(1, 2, figsize=(6.8, 3.2))
    for ax, t in zip(axs, ("npl_percent", "casa_percent")):
        g = _du_doan_rf(P, t, 1, p)
        mae = (g.thuc_te - g.du_bao).abs().mean()
        hi = g[["thuc_te", "du_bao"]].quantile(0.99).max()
        lo = g[["thuc_te", "du_bao"]].quantile(0.0).min()
        ngoai = 0
        if t == "npl_percent":
            ngoai = int(((g.thuc_te > 8) | (g.du_bao > 8)).sum())
            g = g[(g.thuc_te <= 8) & (g.du_bao <= 8)]
            hi = 8
        ax.scatter(g.thuc_te, g.du_bao, s=9, color=vh.XANH, alpha=0.55, lw=0)
        ax.plot([lo, hi], [lo, hi], color=vh.CAM, lw=1)
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_xlabel(f"{TEN_CT[t]} thực tế quý t + 1 (%)")
        ax.set_ylabel(f"{TEN_CT[t]} dự báo (%)")
        ax.text(0.05, 0.9, f"MAE = {mae:.2f} điểm %".replace(".", ","), transform=ax.transAxes, fontsize=9)
        if ngoai:
            ax.text(0.95, 0.05, f"{ngoai} điểm nằm ngoài trục", ha="right", transform=ax.transAxes, fontsize=8,
                    color=vh.CHU2)
        ax.xaxis.set_major_formatter(vh.PHAY)
        ax.yaxis.set_major_formatter(vh.PHAY)
        print(f"  {TEN_CT[t]} h1 RF 2019: MAE {mae:.3f}, ngoài trục {ngoai}")
    fig.tight_layout()
    vh._luu(fig, "h_thuc_te_du_bao.png")


def hinh_chuoi(P: pd.DataFrame, p: pd.DataFrame):
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.7))
    t = "casa_percent"
    g = _du_doan_rf(P, t, 1, p)
    for ax, tk in zip(axs, ("TCB", "MBB", "VPB")):
        a = p.loc[tk][t]
        a = a[a.index >= "2021-Q1"]
        x = {k: i for i, k in enumerate(a.index)}
        ax.plot([x[k] for k in a.index], a.values, color=vh.XANH, lw=2, marker="o", ms=3, label="Thực tế")
        d = g[g.ticker == tk].sort_values("target_period")
        d = d[d.target_period.isin(x)]
        ax.plot([x[k] for k in d.target_period], d.du_bao, color=vh.CAM, lw=1.5, marker="s", ms=3, ls="--",
                label="Dự báo trước 1 quý")
        ax.set_title(tk, fontsize=10.5, color=vh.CHU)
        ticks = [k for k in a.index if k.endswith("Q1") and int(k[:4]) % 2 == 1]
        ax.set_xticks([x[k] for k in ticks], [k[:4] for k in ticks])
        ax.yaxis.set_major_formatter(vh.PHAY)
    axs[0].set_ylabel("CASA (%)")
    axs[1].legend(fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    fig.tight_layout()
    vh._luu(fig, "h_chuoi_du_bao_casa.png")


def hinh_quan_trong():
    from sklearn.ensemble import RandomForestRegressor

    from experiments import longer_history as lh
    ten_dt = {"_d1": "Thay đổi ở quý gần nhất", "_d1_l1": "Thay đổi ở quý trước đó",
              "_dev": "Chênh lệch so với trung bình lịch sử", "refi_d1": "Thay đổi lãi tái cấp vốn (quý t)",
              "refi_d1_l1": "Thay đổi lãi tái cấp vốn (trễ 1 quý)", "refi_d1_l2": "Thay đổi lãi tái cấp vốn (trễ 2 quý)",
              "refi_d1_l3": "Thay đổi lãi tái cấp vốn (trễ 3 quý)", "tq": "Quý trong năm của kỳ dự báo"}
    f = lh.load(True)
    out = []
    for t in ("npl_percent", "casa_percent"):
        h = 1
        y = f.groupby("ticker")[t].shift(-h) - f[t]
        X = f.assign(tq=((f.q + h - 1) % 4 + 1).astype(float))[lh.core(t)]
        m = (f.period >= "2019-Q1") & y.notna()
        rf = RandomForestRegressor(**{**lh.RF_PARAMS, "n_jobs": -1}).fit(X[m].to_numpy(np.float32), y[m])
        imp = pd.Series(rf.feature_importances_, index=[c.replace(t, "y") for c in X.columns])
        out.append(imp.rename(TEN_CT[t]))
    bang = pd.concat(out, axis=1)
    bang = bang.loc[bang.mean(axis=1).sort_values().index]
    lab = []
    for c in bang.index:
        key = next((k for k in ten_dt if c.endswith(k) and (k.startswith("refi") == c.startswith("refi"))), c)
        lab.append(ten_dt.get(key, c))
    fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.0), sharey=True)
    for ax, ten in zip(axs, bang.columns):
        ax.barh(range(len(bang)), bang[ten].values * 100, color=vh.XANH, height=0.6)
        ax.set_yticks(range(len(bang)), lab, fontsize=9)
        ax.set_title(f"{ten}, tầm 1 quý", fontsize=10.5, color=vh.CHU)
        ax.set_xlabel("Độ quan trọng (%)")
        for k, v in enumerate(bang[ten].values * 100):
            ax.text(v + 0.4, k, f"{v:.0f}", va="center", fontsize=7.5, color=vh.CHU2)
    fig.tight_layout()
    vh._luu(fig, "h_quan_trong.png")
    bang.to_csv(vh.BANG / "quan_trong.csv", encoding="utf-8-sig")
    print((bang * 100).round(1).to_string())


def hinh_do_nhay():
    R = pd.read_csv(DN / "do_nhay.csv", encoding="utf-8-sig")
    q = R[(R.phan == "gui") & (R.phep_thu == "trong_so_lai")].sort_values("gia_tri")
    M = pd.read_csv(DN / "on_dinh_monte_carlo.csv", encoding="utf-8-sig")
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0))
    ax = axs[0]
    ax.plot(q.gia_tri * 100, q.ty_le_dung_dau * 100, color=vh.XANH, marker="o", ms=4, label="Tỷ lệ đứng đầu của VPB")
    ax.plot(q.gia_tri * 100, q.ty_le_thu_hai * 100, color=vh.CAM, marker="s", ms=3.5, ls="--",
            label="Tỷ lệ đứng đầu của ngân hàng thứ hai")
    ax2 = ax.twinx()
    ax2.plot(q.gia_tri * 100, q.rho, color=vh.NGOC, marker="^", ms=4, lw=1.2, label="ρ so với mặc định")
    ax2.set_ylim(0.6, 1.02)
    ax2.set_ylabel("ρ Spearman", color=vh.NGOC)
    ax2.spines["right"].set_visible(True)
    ax2.grid(False)
    ax.axvline(62.5, color=vh.CHU2, lw=0.8, ls=":")
    ax.text(61.5, 104, "mặc định", fontsize=7.5, color=vh.CHU2, ha="right", va="bottom")
    ax.set_xlabel("Trọng số nhóm lãi (%)")
    ax.set_ylabel("Tỷ lệ đứng đầu (%)")
    ax.set_ylim(0, 110)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7.4, loc="upper center", bbox_to_anchor=(0.5, -0.27), ncol=1, frameon=False)
    ax = axs[1]
    g = M.groupby("N").VPB.agg(["mean", "min", "max"]) * 100
    ax.fill_between(g.index, g["min"], g["max"], color="#9ec5f4", alpha=0.7, label="Khoảng của 5 hạt giống")
    ax.plot(g.index, g["mean"], color=vh.XANH, marker="o", ms=4, label="Trung bình")
    ax.set_xscale("log")
    ax.set_xticks([1000, 2000, 5000, 10000, 20000], ["1.000", "2.000", "5.000", "10.000", "20.000"])
    ax.minorticks_off()
    ax.set_xlabel("Số vòng mô phỏng N")
    ax.set_ylabel("Tỷ lệ đứng đầu của VPB (%)")
    ax.set_ylim(90, 94)
    ax.yaxis.set_major_formatter(vh.PHAY)
    ax.legend(fontsize=7.4, loc="upper center", bbox_to_anchor=(0.5, -0.27), ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(RA4 / "h_do_nhay_trong_so.png", facecolor="white")
    plt.close(fig)
    print("ghi", RA4 / "h_do_nhay_trong_so.png")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    S = _tom_tat()
    P = pd.read_csv(DG / "sai_so_tung_dong.csv", encoding="utf-8-sig")
    p = vh._panel()
    hinh_so_sanh_h1(S)
    hinh_theo_tam(S)
    hinh_thuc_te(P, p)
    hinh_chuoi(P, p)
    hinh_quan_trong()
    hinh_do_nhay()
    if "--co-du-bao" in sys.argv:  # sau khi chạy lại python -m serving.forecast với tập chọn đặt trước
        vh.hinh_do_phu()
        vh.hinh_du_bao_q4()
