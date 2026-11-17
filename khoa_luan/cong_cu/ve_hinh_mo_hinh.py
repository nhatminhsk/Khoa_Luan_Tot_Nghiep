import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
EXP = REPO / "data/model/experiments"
RA = REPO / "figures/khoa_luan/mo_hinh"
BANG = REPO / "khoa_luan/bang"
RA.mkdir(parents=True, exist_ok=True)
BANG.mkdir(parents=True, exist_ok=True)
XANH, CAM, NGOC, XAM, CHU, CHU2 = "#2a78d6", "#eb6834", "#1baf7a", "#c3c2b7", "#0b0b0b", "#52514e"
VANG = "#eda100"
plt.rcParams.update({
    "font.family": "Times New Roman", "font.size": 10.5, "axes.edgecolor": XAM, "axes.labelcolor": CHU,
    "xtick.color": CHU2, "ytick.color": CHU2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e1e0d9", "grid.linewidth": 0.6, "axes.axisbelow": True,
    "legend.frameon": False, "savefig.dpi": 300, "savefig.bbox": "tight", "figure.facecolor": "white",
})
PHAY = FuncFormatter(lambda v, _: f"{v:g}".replace(".", ","))
PHAN_TRAM = FuncFormatter(lambda v, _: f"{v:.0f}%")
TEN = {"npl_percent": "NPL", "casa_percent": "CASA", "ldr_computed_percent": "LDR", "cof_ttm_percent": "COF",
       "nim_ttm_percent": "NIM", "roe_ttm_percent": "ROE"}
THU_TU = ["npl_percent", "casa_percent", "ldr_computed_percent"]
TEST_FROM = "2023-Q1"
rng = np.random.default_rng(20261104)


def _luu(fig, ten):
    fig.savefig(RA / ten, facecolor="white")
    plt.close(fig)
    print("ghi", RA / ten)


def _oof() -> pd.DataFrame:
    o = pd.read_csv(EXP / "forecast_oof_errors.csv", encoding="utf-8-sig")
    return o[o.origin >= TEST_FROM]


def _bootstrap(e_m: pd.Series, e_b: pd.Series, bank: pd.Series, n=2000):
    d = pd.DataFrame({"m": e_m.abs().values, "b": e_b.abs().values, "bank": bank.values})
    g = d.groupby("bank")[["m", "b"]].sum()
    gain = 1 - g.m.sum() / g.b.sum()
    idx = rng.integers(0, len(g), size=(n, len(g)))
    m, b = g.m.values[idx].sum(1), g.b.values[idx].sum(1)
    lo, hi = np.percentile(1 - m / b, [2.5, 97.5])
    return gain, lo, hi


def bang_rf_theo_tam(o: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (t, h), g in o.groupby(["indicator", "h"]):
        pick = g.chosen.iloc[0]
        base_name = g.base.iloc[0]
        w = g.pivot_table(index=["origin", "ticker"], columns="method", values="err")
        meth = pick if pick != "base" else "base"
        rf_cols = [c for c in w.columns if c.startswith("rf")]
        # RF được chọn; nếu ô chọn mô hình cơ sở thì vẫn báo RF tốt nhất trên tập chọn để thấy mức chênh
        rf = pick if pick != "base" else None
        w = w.dropna(subset=["base"] + ([rf] if rf else []))
        n = len(w)
        if rf:
            gain, lo, hi = _bootstrap(w[rf], w["base"], pd.Series(w.index.get_level_values("ticker")))
        else:
            gain, lo, hi = 0.0, 0.0, 0.0
        rows.append(dict(indicator=t, h=h, base=base_name, chon=meth, n=n, mae_base=w["base"].abs().mean(),
                         mae_chon=(w[rf].abs().mean() if rf else w["base"].abs().mean()), gain=gain, lo=lo, hi=hi,
                         rf_cols=",".join(rf_cols)))
    r = pd.DataFrame(rows)
    r.to_csv(BANG / "rf_theo_tam.csv", index=False, encoding="utf-8-sig")
    return r


def hinh_rf_theo_tam(r: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(6.6, 3.2))
    w = 0.13
    mau = {1: "#9ec5f4", 2: "#5598e7", 3: XANH, 4: "#0d366b"}
    for k, t in enumerate(THU_TU):
        for h in (1, 2, 3, 4):
            s = r[(r.indicator == t) & (r.h == h)].iloc[0]
            x = k + (h - 2.5) * w * 1.15
            ax.bar(x, s.gain * 100, width=w, color=mau[h], label=f"Tầm {h} quý" if k == 0 else None)
            if s.chon != "base":
                ax.errorbar(x, s.gain * 100, yerr=[[(s.gain - s.lo) * 100], [(s.hi - s.gain) * 100]], color=CHU2,
                            lw=0.8, capsize=2)
            else:
                ax.text(x, 0.6, "cs", ha="center", fontsize=6.5, color=CHU2)
    ax.axhline(0, color=CHU2, lw=0.8)
    ax.set_xticks(range(len(THU_TU)), [TEN[t] for t in THU_TU])
    ax.set_ylabel("Giảm sai số so với mô hình cơ sở (%)")
    ax.yaxis.set_major_formatter(PHAN_TRAM)
    ax.legend(ncol=4, loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=8.5, frameon=False)
    _luu(fig, "h_rf_theo_tam.png")


def _panel():
    p = pd.read_csv(REPO / "data/model/bank_panel_quarterly.csv", encoding="utf-8-sig")
    return p.set_index(["ticker", "period"])


def _du_doan(o, t, h, p):
    g = o[(o.indicator == t) & (o.h == h)]
    pick = g.chosen.iloc[0]
    g = g[g.method == pick].copy()
    g["thuc_te"] = [p[t].get((tk, tp), np.nan) for tk, tp in zip(g.ticker, g.target_period)]
    g["du_bao"] = g.thuc_te - g.err
    g["hien_tai"] = [p[t].get((tk, op), np.nan) for tk, op in zip(g.ticker, g.origin)]
    return g.dropna(subset=["thuc_te", "du_bao"])


def hinh_thuc_te(o, p):
    fig, axs = plt.subplots(1, 2, figsize=(6.8, 3.2))
    for ax, t in zip(axs, ("npl_percent", "casa_percent")):
        g = _du_doan(o, t, 1, p)
        g = g[g.origin >= "2023-Q1"]
        mae = (g.thuc_te - g.du_bao).abs().mean()
        ngoai = 0
        hi = g[["thuc_te", "du_bao"]].quantile(0.99).max()
        lo = g[["thuc_te", "du_bao"]].quantile(0.0).min()
        if t == "npl_percent":
            ngoai = int((g.thuc_te > 8).sum() + ((g.thuc_te <= 8) & (g.du_bao > 8)).sum())
            g = g[(g.thuc_te <= 8) & (g.du_bao <= 8)]
            hi = 8
        ax.scatter(g.thuc_te, g.du_bao, s=9, color=XANH, alpha=0.55, lw=0)
        ax.plot([lo, hi], [lo, hi], color=CAM, lw=1)
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)
        ax.set_xlabel(f"{TEN[t]} thực tế quý t + 1 (%)")
        ax.set_ylabel(f"{TEN[t]} dự báo (%)")
        ax.text(0.05, 0.9, f"MAE = {mae:.2f} điểm %".replace(".", ","), transform=ax.transAxes, fontsize=9)
        if ngoai:
            ax.text(0.95, 0.05, f"{ngoai} điểm nằm ngoài trục", ha="right", transform=ax.transAxes, fontsize=8,
                    color=CHU2)
        ax.xaxis.set_major_formatter(PHAY)
        ax.yaxis.set_major_formatter(PHAY)
    fig.tight_layout()
    _luu(fig, "h_thuc_te_du_bao.png")


def hinh_chuoi(o, p):
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.7), sharey=False)
    t = "casa_percent"
    g = _du_doan(o, t, 1, p)
    for ax, tk in zip(axs, ("TCB", "MBB", "VPB")):
        a = p.loc[tk][t]
        a = a[a.index >= "2021-Q1"]
        x = {k: i for i, k in enumerate(a.index)}
        ax.plot([x[k] for k in a.index], a.values, color=XANH, lw=2, marker="o", ms=3, label="Thực tế")
        d = g[g.ticker == tk].sort_values("target_period")
        d = d[d.target_period.isin(x)]
        ax.plot([x[k] for k in d.target_period], d.du_bao, color=CAM, lw=1.5, marker="s", ms=3, ls="--",
                label="Dự báo trước 1 quý")
        ax.set_title(tk, fontsize=10.5, color=CHU)
        ticks = [k for k in a.index if k.endswith("Q1") and int(k[:4]) % 2 == 1]
        ax.set_xticks([x[k] for k in ticks], [k[:4] for k in ticks])
        ax.yaxis.set_major_formatter(PHAY)
    axs[0].set_ylabel("CASA (%)")
    axs[1].legend(fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    fig.tight_layout()
    _luu(fig, "h_chuoi_du_bao_casa.png")


def hinh_quan_trong():
    from experiments import longer_history as lh
    ten_dt = {"_d1": "Thay đổi ở quý gần nhất", "_d1_l1": "Thay đổi ở quý trước đó",
              "_dev": "Chênh lệch so với trung bình lịch sử", "refi_d1": "Thay đổi lãi tái cấp vốn (quý t)",
              "refi_d1_l1": "Thay đổi lãi tái cấp vốn (trễ 1 quý)", "refi_d1_l2": "Thay đổi lãi tái cấp vốn (trễ 2 quý)",
              "refi_d1_l3": "Thay đổi lãi tái cấp vốn (trễ 3 quý)", "tq": "Quý trong năm của kỳ dự báo"}
    from sklearn.ensemble import RandomForestRegressor
    f = lh.load(True)
    out = []
    for t in ("npl_percent", "casa_percent"):
        h = 1
        y = (f.groupby("ticker")[t].shift(-h) - f[t])
        X = f.assign(tq=((f.q + h - 1) % 4 + 1).astype(float))[lh.core(t)]
        m = (f.period >= "2013-Q1") & y.notna() & X.notna().all(axis=1)
        w = np.where(f.period < lh.BASE_FROM, 0.5 if t == "npl_percent" else 1.0, 1.0)
        rf = RandomForestRegressor(**{**lh.RF_PARAMS, "n_jobs": -1}).fit(X[m], y[m], sample_weight=w[m])
        imp = pd.Series(rf.feature_importances_, index=[c.replace(t, "y") for c in X.columns])
        out.append(imp.rename(TEN[t]))
    bang = pd.concat(out, axis=1)
    bang = bang.loc[bang.mean(axis=1).sort_values().index]
    lab = []
    for c in bang.index:
        key = next((k for k in ten_dt if c.endswith(k) and (k.startswith("refi") == c.startswith("refi"))), c)
        lab.append(ten_dt.get(key, c))
    fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.0), sharey=True)
    for ax, ten in zip(axs, bang.columns):
        ax.barh(range(len(bang)), bang[ten].values * 100, color=XANH, height=0.6)
        ax.set_yticks(range(len(bang)), lab, fontsize=9)
        ax.set_title(f"{ten}, tầm 1 quý", fontsize=10.5, color=CHU)
        ax.set_xlabel("Độ quan trọng (%)")
        for k, v in enumerate(bang[ten].values * 100):
            ax.text(v + 0.4, k, f"{v:.0f}", va="center", fontsize=7.5, color=CHU2)
    fig.tight_layout()
    _luu(fig, "h_quan_trong.png")
    bang.to_csv(BANG / "quan_trong.csv", encoding="utf-8-sig")


def hinh_do_phu():
    s = pd.read_csv(EXP / "forecast_selection.csv", encoding="utf-8-sig")
    fig, ax = plt.subplots(figsize=(6.6, 2.8))
    w = 0.18
    for k, t in enumerate(THU_TU):
        for h in (1, 2, 3, 4):
            v = s[(s.indicator == t) & (s.h == h)].coverage_test.iloc[0] * 100
            ax.bar(k + (h - 2.5) * w, v, width=w * 0.95, color=["#9ec5f4", "#5598e7", XANH, "#0d366b"][h - 1],
                   label=f"Tầm {h} quý" if k == 0 else None)
    ax.axhline(90, color=CAM, lw=1.2, ls=(0, (4, 3)))
    ax.text(-0.42, 90.6, "mức danh nghĩa 90%", ha="left", va="bottom", fontsize=8, color=CAM,
            bbox=dict(facecolor="white", edgecolor="none", pad=0.6))
    ax.set_ylim(70, 102)
    ax.set_xticks(range(len(THU_TU)), [TEN[t] for t in THU_TU])
    ax.set_ylabel("Tỷ lệ giá trị thực nằm trong khoảng (%)")
    ax.yaxis.set_major_formatter(PHAN_TRAM)
    ax.legend(ncol=4, loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=8.5)
    _luu(fig, "h_do_phu_khoang.png")


def hinh_du_bao_q4():
    f = pd.read_csv(EXP / "forecasts_de_xuat.csv")
    p = _panel()
    fig, axs = plt.subplots(1, 2, figsize=(7.0, 4.6), sharey=True)
    for ax, (code, t) in zip(axs, (("npl", "npl_percent"), ("casa", "casa_percent"))):
        d = f[(f.indicator == code) & (f.horizon == 1)].copy()
        d["hien_tai"] = [p[t].get((tk, op), np.nan) for tk, op in zip(d.ticker, d.origin_period)]
        d = d.sort_values("ticker", ascending=False).reset_index(drop=True)
        y = np.arange(len(d))
        ax.hlines(y, d.lower, d.upper, color="#9ec5f4", lw=4)
        ax.scatter(d.hien_tai, y, marker="|", s=80, color=CHU2, label="Quý 3/2026 (thực tế)", zorder=3)
        ax.scatter(d.value, y, s=22, color=CAM, zorder=4, label="Dự báo quý 4/2026")
        ax.set_yticks(y, d.ticker, fontsize=8.5)
        ax.set_xlabel(f"{TEN[t]} (%)")
        ax.xaxis.set_major_formatter(PHAY)
        if code == "npl":
            ax.set_xlim(0, max(10, d.upper.quantile(0.9)))
    axs[0].legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    _luu(fig, "h_du_bao_q4_2026.png")


def bang_so_sanh(r_rf: pd.DataFrame):
    s = pd.read_csv(EXP / "algorithm_benchmark_summary.csv", encoding="utf-8-sig")
    ten_ab = {"NPL": "npl_percent", "CASA": "casa_percent", "LDR": "ldr_computed_percent", "COF": "cof_ttm_percent",
              "NIM": "nim_ttm_percent", "ROE": "roe_ttm_percent"}
    rows = []
    for ab_t, t in ten_ab.items():
        for h in (1, 2, 4):
            g = s[(s.target == ab_t) & (s.h == h)].set_index("method")
            if g.empty:
                continue
            mae_naive = g.loc["naive", "mae"]
            rf = r_rf[(r_rf.indicator == t) & (r_rf.h == h)].iloc[0]
            # mô hình cơ sở và mô hình lai lấy đúng của module dự báo (serving.forecast), cùng tập kiểm tra từ 2023-Q1
            rows.append(dict(chi_tieu=ab_t, h=h, naive=mae_naive, mae_co_so=rf.mae_base, mae_rf=rf.mae_chon,
                             mae_ridge=g.loc["ridge", "mae"], mae_lgbm=g.loc["lgbm", "mae"],
                             co_so=1 - rf.mae_base / mae_naive, ridge=1 - g.loc["ridge", "mae"] / mae_naive,
                             lgbm=1 - g.loc["lgbm", "mae"] / mae_naive, rf=1 - rf.mae_chon / mae_naive,
                             rf_vs_base=rf.gain, rf_lo=rf.lo, rf_hi=rf.hi, rf_chon=rf.chon, base_ten=rf.base,
                             n_rf=rf.n, n_ab=g.loc["naive", "n"]))
    b = pd.DataFrame(rows)
    b.to_csv(BANG / "so_sanh_mo_hinh.csv", index=False, encoding="utf-8-sig")
    d = b[b.h == 1].set_index("chi_tieu").loc[["NPL", "CASA", "LDR"]]
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    w = 0.2
    for k, (c, ten, mau) in enumerate((("co_so", "Mô hình cơ sở tốt nhất", XAM), ("ridge", "Ridge", NGOC),
                                       ("lgbm", "LightGBM", VANG), ("rf", "Cơ sở + RF học phần dư", XANH))):
        ax.bar(np.arange(len(d)) + (k - 1.5) * w, d[c] * 100, width=w * 0.95, color=mau, label=ten)
    ax.axhline(0, color=CHU2, lw=0.8)
    ax.set_xticks(range(len(d)), d.index)
    ax.set_ylabel("Giảm MAE so với giữ nguyên (%)")
    ax.yaxis.set_major_formatter(PHAN_TRAM)
    ax.legend(ncol=4, fontsize=8.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), frameon=False)
    _luu(fig, "h_so_sanh_mo_hinh.png")
    return b


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    o = _oof()
    r = bang_rf_theo_tam(o)
    print(r[["indicator", "h", "base", "chon", "n", "mae_base", "mae_chon", "gain", "lo", "hi"]].round(3).to_string())
    hinh_rf_theo_tam(r)
    p = _panel()
    hinh_thuc_te(o, p)
    hinh_chuoi(o, p)
    hinh_do_phu()
    hinh_du_bao_q4()
    hinh_quan_trong()
    if "--bo-so-sanh" not in sys.argv:
        b = bang_so_sanh(r)
        print(b.round(3).to_string())
