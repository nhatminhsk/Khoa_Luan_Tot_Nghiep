"""O thieu anh huong the nao den XEP HANG TOPSIS -- noi tiep imputation_benchmark.py.

TOPSIS can ma tran quyet dinh DU O (NH x tieu chi). Moi o thieu buoc phai chon mot trong:
bo NH, bo tieu chi, hoac dien. Script do ba cai:

  1. Anh chup that 4 quy gan nhat: o thieu nam o dau, moi cach xu ly dua NH do len hang may.
  2. Mo phong co dap an: o cac quy 2023-Q1 -> 2026-Q2, lay cac NH du 11 tieu chi, xep hang
     that; che 1 o (va 2 o cung NH), xu ly bang tung cach, do so bac dich hang.
  3. Doi chieu do lon: cung khung do, doi trong so (Dirichlet alpha = 8, 300 bo) lam hang
     dich bao nhieu bac -- de biet o thieu la nguon bat dinh lon hay nho.

Tieu chi va trong so DEU la minh hoa (xep hang cho nguoi gui tiet kiem, trong so bang
nhau), CHUA phai bo tieu chi chot cua khoa luan. Chuan hoa min-max theo quy (ROA co gia
tri am nen khong dung chuan hoa vector).

Chay:
    python -m experiments.ranking_missing_sensitivity
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

FEATURES = "data/model/features_quarterly.csv"
SNAPSHOT = "data/model/features_ranking_latest.csv"
OUT_DIR = "data/model/experiments"
SEED = 20260915
QUARTERS = ("2023-Q1", "2026-Q2")

# tieu chi -> (chieu, nhom): +1 cang cao cang tot, -1 cang thap cang tot
CRITERIA = {
    "car_asof_percent": (+1, "C"), "equity_to_assets_pct": (+1, "C"),
    "npl_percent": (-1, "A"), "loans_g2_percent": (-1, "A"), "credit_cost_ttm_pct": (-1, "A"),
    "roa_ttm_percent": (+1, "E"), "cir_ttm_pct": (-1, "E"),
    "ldr_computed_percent": (-1, "L"), "liquid_assets_pct": (+1, "L"),
    "app_mean_score": (+1, "K"), "dep12_online_pct": (+1, "R"),
}
COLS = list(CRITERIA)
DIRS = np.array([CRITERIA[c][0] for c in COLS], dtype=float)
LABEL = {
    "true": "Đủ số (đáp án)", "mean": "Trung bình các NH", "median": "Trung vị các NH",
    "worst": "Giá trị tệ nhất", "locf": "Số gần nhất của chính NH", "knn": "kNN theo các tiêu chí khác",
    "drop_criterion": "Bỏ tiêu chí đó cho mọi NH", "drop_bank": "Bỏ ngân hàng",
}


def topsis(X: pd.DataFrame, w: np.ndarray | None = None) -> pd.Series:
    """Tra ve hang (1 = tot nhat). Chuan hoa min-max, dao chieu tieu chi chi phi."""
    cols = list(X.columns)
    d = np.array([CRITERIA[c][0] for c in cols])
    w = np.full(len(cols), 1 / len(cols)) if w is None else w / w.sum()
    lo, hi = X.min(), X.max()
    span = (hi - lo).replace(0, 1)
    N = (X - lo) / span
    N = N.where(np.broadcast_to(d > 0, N.shape), 1 - N)
    V = N * w
    dp = np.sqrt(((V - V.max()) ** 2).sum(axis=1))
    dm = np.sqrt(((V - V.min()) ** 2).sum(axis=1))
    score = dm / (dp + dm)
    return score.rank(ascending=False, method="min").astype(int)


def fill(X: pd.DataFrame, method: str, history: pd.DataFrame | None = None, period: str | None = None) -> pd.DataFrame:
    """Xu ly o thieu trong ma tran mot quy. Tra ve ma tran de dua vao TOPSIS."""
    X = X.copy()
    if method == "mean":
        return X.fillna(X.mean())
    if method == "median":
        return X.fillna(X.median())
    if method == "worst":
        worst = pd.Series({c: (X[c].min() if CRITERIA[c][0] > 0 else X[c].max()) for c in X.columns})
        return X.fillna(worst)
    if method == "locf":
        prev = history[history.period < period].sort_values("period").groupby("ticker")[list(X.columns)].last()
        return X.fillna(prev.reindex(X.index)).fillna(X.mean())
    if method == "knn":
        from sklearn.impute import KNNImputer
        mu, sd = X.mean(), X.std().replace(0, 1)
        Z = KNNImputer(n_neighbors=5).fit_transform((X - mu) / sd)
        return pd.DataFrame(Z, index=X.index, columns=X.columns) * sd + mu
    if method == "drop_criterion":
        return X.dropna(axis=1)
    if method == "drop_bank":
        return X.dropna(axis=0)
    raise ValueError(method)


def snapshot_real(f: pd.DataFrame) -> pd.DataFrame:
    snap = pd.read_csv(SNAPSHOT, encoding="utf-8-sig").set_index("ticker")[COLS]
    missing = {t: [c for c in COLS if pd.isna(snap.loc[t, c])] for t in snap.index}
    missing = {t: v for t, v in missing.items() if v}
    last = f.sort_values("period").groupby("ticker")
    rows = {}
    for m in ["mean", "median", "worst", "locf", "knn", "drop_criterion", "drop_bank"]:
        X = fill(snap, m, history=f, period="2025-Q3")  # locf: so truoc cua so 4 quy
        rows[m] = topsis(X).reindex(snap.index)
    R = pd.DataFrame(rows)
    stale = {}
    for t, cs in missing.items():
        for c in cs:
            s = f[(f.ticker == t) & f[c].notna()].sort_values("period")
            stale[f"{t}.{c}"] = (s.period.iloc[-1], float(s[c].iloc[-1])) if len(s) else (None, None)
    return R, missing, stale


def simulate(f: pd.DataFrame, rng) -> tuple[pd.DataFrame, pd.DataFrame]:
    periods = sorted(p for p in f.period.unique() if QUARTERS[0] <= p <= QUARTERS[1])
    methods = ["mean", "median", "worst", "locf", "knn", "drop_criterion"]
    rows, wrows = [], []
    for p in periods:
        X = f[f.period == p].set_index("ticker")[COLS].dropna()
        if len(X) < 12:
            continue
        true = topsis(X)
        # 3. trong so ngau nhien tren cung ma tran day du
        for _ in range(300):
            w = rng.dirichlet(np.full(len(COLS), 8.0))
            wrows.append(dict(period=p, mean_abs_shift=float((topsis(X, w) - true).abs().mean())))
        for b in X.index:
            for k in (1, 2):
                combos = [[c] for c in COLS] if k == 1 else [list(rng.choice(COLS, 2, replace=False)) for _ in range(len(COLS))]
                for cs in combos:
                    Xm = X.copy()
                    Xm.loc[b, cs] = np.nan
                    for m in methods:
                        R = topsis(fill(Xm, m, history=f, period=p))
                        others = [t for t in X.index if t != b]
                        rows.append(dict(period=p, n_banks=len(X), bank=b, n_masked=k, criteria="+".join(cs), method=m,
                                         shift_bank=abs(int(R[b]) - int(true[b])),
                                         shift_others=float((R[others] - true[others]).abs().mean()),
                                         top3_changed=set(R[R <= 3].index) != set(true[true <= 3].index),
                                         true_rank=int(true[b]), direction=int(true[b]) - int(R[b])))
                    # bo NH: chi do duoc cac NH con lai dich hang the nao
                    others = [t for t in X.index if t != b]
                    R = topsis(X.loc[others])
                    ref = true[others].rank(method="min").astype(int)
                    rows.append(dict(period=p, n_banks=len(X), bank=b, n_masked=k, criteria="+".join(cs), method="drop_bank",
                                     shift_bank=np.nan, shift_others=float((R - ref).abs().mean()),
                                     top3_changed=set(R[R <= 3].index) != set(ref[ref <= 3].index),
                                     true_rank=int(true[b]), direction=np.nan))
    return pd.DataFrame(rows), pd.DataFrame(wrows)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pd.set_option("display.width", 220)
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(SEED)
    f = pd.read_csv(FEATURES, encoding="utf-8-sig")

    R, missing, stale = snapshot_real(f)
    R.to_csv(f"{OUT_DIR}/ranking_missing_snapshot.csv", encoding="utf-8-sig")
    print("1. ANH CHUP THAT (4 quy gan nhat) - o thieu trong 11 tieu chi:", missing)
    print("   so gan nhat da biet:", stale)
    print(R.loc[list(missing)].to_string())
    print("   Spearman giua cac cach (22 NH, bo NH tinh tren NH con lai):")
    print(R.drop(columns="drop_bank").corr(method="spearman").round(3).to_string())

    S, W = simulate(f, rng)
    S.to_csv(f"{OUT_DIR}/ranking_missing_simulation.csv", index=False, encoding="utf-8-sig")
    W.to_csv(f"{OUT_DIR}/ranking_weight_perturbation.csv", index=False, encoding="utf-8-sig")
    g = S.groupby(["n_masked", "method"]).agg(
        cases=("bank", "size"), shift_bank_mean=("shift_bank", "mean"), shift_bank_p90=("shift_bank", lambda s: s.quantile(0.9)),
        pct_bank_moved=("shift_bank", lambda s: (s > 0).mean() * 100), shift_others=("shift_others", "mean"),
        pct_top3_changed=("top3_changed", lambda s: s.mean() * 100)).round(2)
    print("\n2. MO PHONG CO DAP AN (che o cua NH dang du so):")
    print(g.to_string())
    bias = S[S.method.isin(["mean", "worst", "locf", "knn"]) & (S.n_masked == 1)].copy()
    bias["tier"] = pd.cut(bias.true_rank, [0, 5, 15, 30], labels=["hạng 1–5", "hạng 6–15", "hạng 16+"])
    print("   dich hang theo vi tri that (duong = duoc day len, am = bi keo xuong):")
    print(bias.groupby(["method", "tier"]).direction.mean().unstack().round(2).to_string())
    by_crit = S[(S.n_masked == 1) & (S.method == "mean")].groupby("criteria").shift_bank.mean().sort_values(ascending=False).round(2)
    print("   tieu chi nhay nhat khi dien trung binh:", by_crit.head(5).to_dict())
    print(f"\n3. DOI TRONG SO (Dirichlet alpha=8): trung binh moi NH dich {W.mean_abs_shift.mean():.2f} bac")


if __name__ == "__main__":
    main()
