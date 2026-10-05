"""Thu lai Jager, Allhorn & Biessmann (2021) "A Benchmark for Data Imputation Methods"
(Frontiers in Big Data 4:693674) tren panel 22 NH x 30 quy.

Bai goc: 69 bang OpenML (3.000-100.000 dong), tao o thieu gia MCAR/MAR/MNAR o 1/10/30/50%,
so sanh trung binh, kNN, random forest, DL phan biet, VAE, GAIN theo RMSE va theo anh
huong len mo hinh phia sau. Ket luan: RF tot nhat, DL khong hon; khi tap train cung
thieu thi hau nhu khong cai thien qua 5%.

Dieu chinh cho du lieu nay (ly do trong README muc "Thu nghiem dien khuyet"):
  * Bat dau 2019-Q1: 89% o thieu cua features_selected.csv nam o DAU chuoi (bien TTM chua
    du 4 quy, so nam 2017 khong co) -> la o chua the co so, khong phai o bi mat.
  * Che o tren NHIEU cot cung luc (bai goc che mot cot) -- dung voi du lieu that, 57/88 cot
    co o thieu -- va them kieu thieu BLOCK: mot doan quy lien tiep trong mot NH.
  * Chi cham cot theo NH-quy lien tuc. Bien chung moi NH (vi mo) va bien tinh bi loai khoi
    phan cham vi dien tu NH khac cung quy la chep dap an.
  * Them cach dien theo panel ma bai goc khong co: trung vi NH, lay so quy truoc, noi suy.
  * Phan anh huong (kich ban 2 cua bai: train va test deu thieu that): LightGBM du bao thay
    doi 6 muc tieu quy sau, walk-forward goc 2023-Q1 -> 2026-Q1; moi cach dien chi fit tren
    phan train, va chi dung cach khong nhin tuong lai (khong noi suy, khong bfill).

Ket qua: data/model/experiments/imputation_*.csv

Chay:
    python -m experiments.imputation_benchmark              # day du
    python -m experiments.imputation_benchmark --quick      # 1 lan lap, 10/30%, de do thoi gian
    python -m experiments.imputation_benchmark --skip-dl    # bo GAIN/VAE
    python -m experiments.imputation_benchmark --downstream-only
"""
from __future__ import annotations

import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

FEATURES = "data/model/features_selected.csv"
SPEC = "data/model/feature_catalog.csv"
OUT_DIR = "data/model/experiments"
START = "2019-Q1"
TARGETS = ["nim_ttm_percent", "cof_ttm_percent", "npl_percent", "casa_percent", "ldr_computed_percent", "roe_ttm_percent"]
PATTERNS = ["MCAR", "MAR", "MNAR", "BLOCK"]
FRACTIONS = [0.01, 0.10, 0.30, 0.50]
REPS = 3
TEST_ORIGINS = ("2023-Q1", "2026-Q1")
SEED = 20260915


# --------------------------------------------------------------------------- du lieu
def load():
    f = pd.read_csv(FEATURES, encoding="utf-8-sig")
    f = f[f.period >= START].sort_values(["ticker", "period"]).reset_index(drop=True)
    cat = pd.read_csv(SPEC, encoding="utf-8-sig").set_index("feature")
    feats = [c for c in f.columns if c not in ("period", "period_end", "ticker")]
    binary = [c for c in feats if set(f[c].dropna().unique()) <= {0, 1} or c == "n_programs_active"]
    scored = [c for c in feats if cat.loc[c, "kind"] == "theo NH-quý" and c not in binary]
    return f, feats, scored


# --------------------------------------------------------------------------- kieu thieu
def make_mask(f: pd.DataFrame, cols, pattern, frac, rng) -> pd.DataFrame:
    """True = o dang co so bi che de cham diem."""
    mask = pd.DataFrame(False, index=f.index, columns=cols)
    for c in cols:
        obs = f.index[f[c].notna()].to_numpy()
        k = int(round(frac * len(obs)))
        if k == 0:
            continue
        if pattern == "MCAR":
            pick = rng.choice(obs, k, replace=False)
        elif pattern in ("MAR", "MNAR"):
            if pattern == "MAR":  # phu thuoc mot cot khac chon ngau nhien
                other = rng.choice([x for x in cols if x != c])
                driver = f.loc[obs, other]
                driver = driver.fillna(driver.median())
            else:  # phu thuoc chinh gia tri cua cot
                driver = f.loc[obs, c]
            r = driver.rank(pct=True).to_numpy()
            if rng.random() < 0.5:
                r = 1 - r
            w = r ** 3 + 1e-9
            pick = rng.choice(obs, k, replace=False, p=w / w.sum())
        else:  # BLOCK: doan quy lien tiep trong mot NH
            chosen: set[int] = set()
            by_bank = {t: g.index[g[c].notna()].to_numpy() for t, g in f.groupby("ticker")}
            banks = [t for t, v in by_bank.items() if len(v) >= 3]
            while len(chosen) < k:
                idx = by_bank[rng.choice(banks)]
                L = int(rng.integers(2, 7))
                s = int(rng.integers(0, max(1, len(idx) - L + 1)))
                chosen.update(idx[s:s + L].tolist())
            pick = rng.choice(sorted(chosen), k, replace=False)
        mask.loc[pick, c] = True
    return mask


# --------------------------------------------------------------------------- cach dien
def _std(X):
    mu, sd = X.mean(), X.std().replace(0, 1)
    return mu, sd


def imp_mean(X, f, **_):
    return X.fillna(X.mean())


def imp_bank_median(X, f, **_):
    return X.fillna(X.groupby(f.ticker).transform("median")).fillna(X.median())


def imp_locf(X, f, **_):
    return X.groupby(f.ticker).ffill().fillna(X.groupby(f.ticker).bfill()).fillna(X.median())


def imp_interp(X, f, **_):
    out = X.groupby(f.ticker, group_keys=False).apply(lambda g: g.interpolate(limit_direction="both"))
    return out.fillna(X.median())


def imp_knn(X, f, **_):
    from sklearn.impute import KNNImputer
    mu, sd = _std(X)
    Z = KNNImputer(n_neighbors=5, weights="distance").fit_transform((X - mu) / sd)
    return pd.DataFrame(Z, index=X.index, columns=X.columns) * sd + mu


def _rf_columnwise(X, f, target_cols, panel=False, seed=0):
    """Nhu bai goc: moi cot can dien -> mot RF hoc tu cac cot con lai (cot khac dien trung binh)."""
    from sklearn.ensemble import RandomForestRegressor
    out = X.copy()
    base = X.fillna(X.mean())
    for c in target_cols:
        miss = X[c].isna()
        if not miss.any() or miss.all():
            continue
        feats = base.drop(columns=c)
        if panel:  # them thong tin cung cot trong NH: quy truoc, quy sau (sau khi noi suy) va trung vi NH
            s = X[c].groupby(f.ticker, group_keys=False).apply(lambda g: g.interpolate(limit_direction="both"))
            feats = feats.assign(_lag=s.groupby(f.ticker).shift(1), _lead=s.groupby(f.ticker).shift(-1),
                                 _bank_med=X[c].groupby(f.ticker).transform("median")).fillna(X[c].median())
        m = RandomForestRegressor(n_estimators=60, min_samples_leaf=2, max_features=0.5, n_jobs=-1, random_state=seed)
        m.fit(feats[~miss], X.loc[~miss, c])
        out.loc[miss, c] = m.predict(feats[miss])
    return out.fillna(X.mean())


def imp_rf(X, f, target_cols=None, seed=0, **_):
    return _rf_columnwise(X, f, target_cols or list(X.columns), panel=False, seed=seed)


def imp_rf_panel(X, f, target_cols=None, seed=0, **_):
    return _rf_columnwise(X, f, target_cols or list(X.columns), panel=True, seed=seed)


def imp_vae(X, f, seed=0, **_):
    import tensorflow as tf
    tf.random.set_seed(seed)
    mu, sd = _std(X)
    Z = ((X - mu) / sd).to_numpy("float32")
    M = (~np.isnan(Z)).astype("float32")
    Z0 = np.nan_to_num(Z)
    d, h, z = Z.shape[1], 64, 8
    enc = tf.keras.Sequential([tf.keras.layers.Dense(h, activation="relu"), tf.keras.layers.Dense(2 * z)])
    dec = tf.keras.Sequential([tf.keras.layers.Dense(h, activation="relu"), tf.keras.layers.Dense(d)])
    opt = tf.keras.optimizers.Adam(1e-3)
    ds = tf.data.Dataset.from_tensor_slices((Z0, M)).shuffle(len(Z0), seed=seed).batch(64).repeat()

    @tf.function
    def step(x, m):
        with tf.GradientTape() as tape:
            p = enc(x * m)
            zm, lv = tf.split(p, 2, axis=1)
            eps = tf.random.normal(tf.shape(zm))
            xr = dec(zm + tf.exp(0.5 * lv) * eps)
            rec = tf.reduce_sum(m * tf.square(x - xr)) / tf.reduce_sum(m)
            kl = -0.5 * tf.reduce_mean(tf.reduce_sum(1 + lv - tf.square(zm) - tf.exp(lv), axis=1)) / d
            loss = rec + 0.1 * kl
        v = enc.trainable_variables + dec.trainable_variables
        opt.apply_gradients(zip(tape.gradient(loss, v), v))

    for i, (x, m) in enumerate(ds):
        step(x, m)
        if i >= 2000:
            break
    cur = Z0.copy()
    for _ in range(3):  # lap thay o thieu bang ban dung lai
        p = enc(cur * 1.0)
        zm, _lv = tf.split(p, 2, axis=1)
        rec = dec(zm).numpy()
        cur = M * Z0 + (1 - M) * rec
    return pd.DataFrame(cur, index=X.index, columns=X.columns) * sd + mu


def imp_gain(X, f, seed=0, **_):
    """Yoon, Jordon & van der Schaar (2018): hint rate 0,9, alpha 100, batch 128, 2000 vong."""
    import tensorflow as tf
    tf.random.set_seed(seed)
    rng = np.random.default_rng(seed)
    lo, hi = X.min(), X.max()
    span = (hi - lo).replace(0, 1)
    N = ((X - lo) / span).to_numpy("float32")
    M = (~np.isnan(N)).astype("float32")
    N0 = np.nan_to_num(N)
    n, d = N.shape

    def mlp(out_act):
        return tf.keras.Sequential([tf.keras.layers.Dense(d, activation="relu"), tf.keras.layers.Dense(d, activation="relu"),
                                    tf.keras.layers.Dense(d, activation=out_act)])
    G, D = mlp("sigmoid"), mlp("sigmoid")
    og, od = tf.keras.optimizers.Adam(1e-3), tf.keras.optimizers.Adam(1e-3)

    @tf.function
    def step(x, m, z, h):
        xin = m * x + (1 - m) * z
        with tf.GradientTape() as td, tf.GradientTape() as tg:
            g = G(tf.concat([xin, m], 1))
            xhat = m * x + (1 - m) * g
            dp = D(tf.concat([xhat, h], 1))
            ld = -tf.reduce_mean(m * tf.math.log(dp + 1e-8) + (1 - m) * tf.math.log(1 - dp + 1e-8))
            lg = -tf.reduce_mean((1 - m) * tf.math.log(dp + 1e-8)) + 100 * tf.reduce_sum(tf.square(m * x - m * g)) / tf.reduce_sum(m)
        od.apply_gradients(zip(td.gradient(ld, D.trainable_variables), D.trainable_variables))
        og.apply_gradients(zip(tg.gradient(lg, G.trainable_variables), G.trainable_variables))

    for _ in range(2000):
        idx = rng.choice(n, min(128, n), replace=False)
        x, m = N0[idx], M[idx]
        z = rng.uniform(0, 0.01, x.shape).astype("float32")
        b = (rng.uniform(size=x.shape) < 0.9).astype("float32")
        step(x, m, z, m * b + 0.5 * (1 - b))
    z = rng.uniform(0, 0.01, N0.shape).astype("float32")
    g = G(tf.concat([M * N0 + (1 - M) * z, M], 1)).numpy()
    out = M * N0 + (1 - M) * g
    return pd.DataFrame(out, index=X.index, columns=X.columns) * span + lo


METHODS = {"mean": imp_mean, "bank_median": imp_bank_median, "locf_bank": imp_locf, "interp_bank": imp_interp,
           "knn": imp_knn, "rf": imp_rf, "rf_panel": imp_rf_panel, "vae": imp_vae, "gain": imp_gain}
DL = {"vae", "gain"}


# --------------------------------------------------------------------------- phan 1: chat luong dien
def quality(f, feats, scored, reps, fractions, methods):
    rng = np.random.default_rng(SEED)
    X_true = f[feats]
    sd = X_true[scored].std()
    rows, timing = [], {m: 0.0 for m in methods}
    total = len(PATTERNS) * len(fractions) * reps
    run = 0
    for pattern in PATTERNS:
        for frac in fractions:
            for rep in range(reps):
                run += 1
                mask = make_mask(f, scored, pattern, frac, rng)
                X = X_true.copy()
                X[scored] = X[scored].mask(mask)
                for name in methods:
                    t0 = time.time()
                    Xi = METHODS[name](X, f, target_cols=scored, seed=SEED + rep)
                    timing[name] += time.time() - t0
                    for c in scored:
                        m = mask[c]
                        if m.sum() == 0:
                            continue
                        err = (Xi.loc[m, c] - X_true.loc[m, c]) / sd[c]
                        rows.append(dict(pattern=pattern, frac=frac, rep=rep, method=name, column=c,
                                         n_masked=int(m.sum()), nrmse=float(np.sqrt(np.mean(err ** 2)))))
                print(f"  chat luong {run}/{total}: {pattern} {frac:.0%} lan {rep + 1}", flush=True)
    q = pd.DataFrame(rows)
    q["rank"] = q.groupby(["pattern", "frac", "rep", "column"]).nrmse.rank(method="average")
    return q, {k: round(v / total, 2) for k, v in timing.items()}


# --------------------------------------------------------------------------- phan 2: anh huong len du bao
DOWN_METHODS = ["native_nan", "mean", "bank_median", "locf_bank", "knn", "rf"]


def _fit_transform(name, Xtr, ftr, Xte, fte, seed):
    """Dien khuyet chi dung thong tin train (va qua khu cua chinh dong test)."""
    if name == "native_nan":
        return Xtr, Xte
    if name == "mean":
        mu = Xtr.mean()
        return Xtr.fillna(mu), Xte.fillna(mu)
    if name == "bank_median":
        med = Xtr.groupby(ftr.ticker).median()
        fill = lambda X, ff: X.fillna(med.reindex(ff.ticker).set_index(X.index)).fillna(Xtr.median())  # noqa: E731
        return fill(Xtr, ftr), fill(Xte, fte)
    if name == "locf_bank":
        both = pd.concat([Xtr, Xte])
        fb = pd.concat([ftr, fte])
        order = fb.sort_values(["ticker", "period"]).index
        filled = both.loc[order].groupby(fb.loc[order, "ticker"]).ffill().reindex(both.index).fillna(Xtr.median())
        return filled.loc[Xtr.index], filled.loc[Xte.index]
    if name == "knn":
        from sklearn.impute import KNNImputer
        mu, sd = _std(Xtr)
        imp = KNNImputer(n_neighbors=5, weights="distance").fit((Xtr - mu) / sd)
        tr = pd.DataFrame(imp.transform((Xtr - mu) / sd), index=Xtr.index, columns=Xtr.columns) * sd + mu
        te = pd.DataFrame(imp.transform((Xte - mu) / sd), index=Xte.index, columns=Xte.columns) * sd + mu
        return tr, te
    if name == "rf":
        from sklearn.ensemble import RandomForestRegressor
        mu = Xtr.mean()
        btr, bte = Xtr.fillna(mu), Xte.fillna(mu)
        tr, te = Xtr.copy(), Xte.copy()
        for c in Xtr.columns:
            mtr, mte = Xtr[c].isna(), Xte[c].isna()
            if not (mtr.any() or mte.any()) or mtr.all():
                continue
            m = RandomForestRegressor(n_estimators=60, min_samples_leaf=2, max_features=0.5, n_jobs=-1, random_state=seed)
            m.fit(btr.drop(columns=c)[~mtr], Xtr.loc[~mtr, c])
            if mtr.any():
                tr.loc[mtr, c] = m.predict(btr.drop(columns=c)[mtr])
            if mte.any():
                te.loc[mte, c] = m.predict(bte.drop(columns=c)[mte])
        return tr.fillna(mu), te.fillna(mu)
    raise ValueError(name)


def downstream(f, feats):
    import lightgbm as lgb
    f = f.copy()
    nxt = f.groupby("ticker")["period"].shift(-1)
    qi = f.period.str[:4].astype(int) * 4 + f.period.str[-1].astype(int)
    consecutive = (qi.groupby(f.ticker).shift(-1) - qi) == 1
    for t in TARGETS:
        f[f"y_{t}"] = (f.groupby("ticker")[t].shift(-1) - f[t]).where(consecutive & nxt.notna())
    periods = sorted(f.period.unique())
    origins = [p for p in periods if TEST_ORIGINS[0] <= p <= TEST_ORIGINS[1]]
    tick_code = f.ticker.astype("category").cat.codes
    preds = []
    for o in origins:
        tr = f[f.period < o]
        te = f[f.period == o]
        Xtr_raw, Xte_raw = tr[feats], te[feats]
        for name in DOWN_METHODS:
            Xtr, Xte = _fit_transform(name, Xtr_raw, tr, Xte_raw, te, SEED)
            Xtr = Xtr.assign(bank=tick_code.loc[Xtr.index])
            Xte = Xte.assign(bank=tick_code.loc[Xte.index])
            for t in TARGETS:
                ytr = tr[f"y_{t}"]
                ok = ytr.notna()
                model = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=20,
                                          subsample=0.8, subsample_freq=1, colsample_bytree=0.7, reg_lambda=1.0,
                                          random_state=SEED, verbose=-1)
                model.fit(Xtr[ok], ytr[ok], categorical_feature=["bank"])
                yte = te[f"y_{t}"]
                k = yte.notna()
                if not k.any():
                    continue
                p = model.predict(Xte[k])
                preds.append(pd.DataFrame({"origin": o, "method": name, "target": t, "ticker": te.loc[k, "ticker"].values,
                                           "y_true": yte[k].values, "y_pred": p}))
        print(f"  anh huong: goc {o} xong", flush=True)
    P = pd.concat(preds)
    P["abs_err"] = (P.y_true - P.y_pred).abs()
    P["abs_naive"] = P.y_true.abs()  # naive: giu nguyen muc quy truoc -> thay doi du bao = 0
    s = P.groupby(["target", "method"]).agg(n=("abs_err", "size"), mae=("abs_err", "mean"), mae_naive=("abs_naive", "mean")).reset_index()
    s["skill_vs_naive_pct"] = (1 - s.mae / s.mae_naive) * 100
    ref = s[s.method == "native_nan"].set_index("target").mae
    s["change_vs_native_pct"] = (s.mae / s.target.map(ref) - 1) * 100
    return P, s


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    os.makedirs(OUT_DIR, exist_ok=True)
    quick, skip_dl, down_only = "--quick" in sys.argv, "--skip-dl" in sys.argv, "--downstream-only" in sys.argv
    f, feats, scored = load()
    miss_share = f[feats].isna().mean().mean() * 100
    print(f"du lieu: {len(f)} dong ({START} -> {f.period.max()}), {len(feats)} bien, cham {len(scored)} bien, "
          f"o thieu that {miss_share:.1f}%")
    if not down_only:
        methods = [m for m in METHODS if not (skip_dl and m in DL)]
        reps, fracs = (1, [0.10, 0.30]) if quick else (REPS, FRACTIONS)
        q, timing = quality(f, feats, scored, reps, fracs, methods)
        tag = "_quick" if quick else ""
        q.to_csv(f"{OUT_DIR}/imputation_quality{tag}.csv", index=False, encoding="utf-8-sig")
        summ = q.groupby(["pattern", "frac", "method"]).agg(nrmse_mean=("nrmse", "mean"), nrmse_median=("nrmse", "median"),
                                                              rank_mean=("rank", "mean")).reset_index()
        summ.to_csv(f"{OUT_DIR}/imputation_quality_summary{tag}.csv", index=False, encoding="utf-8-sig")
        overall = q.groupby("method").agg(nrmse_median=("nrmse", "median"), rank_mean=("rank", "mean")).sort_values("rank_mean")
        overall["sec_per_run"] = overall.index.map(timing)
        print("\nCHAT LUONG DIEN (NRMSE don vi do lech chuan, hang trung binh):")
        print(overall.round(3).to_string())
        print(summ.pivot_table(index=["pattern", "frac"], columns="method", values="rank_mean").round(2).to_string())
    if not quick:
        P, s = downstream(f, feats)
        P.to_csv(f"{OUT_DIR}/imputation_downstream_predictions.csv", index=False, encoding="utf-8-sig")
        s.to_csv(f"{OUT_DIR}/imputation_downstream.csv", index=False, encoding="utf-8-sig")
        print("\nANH HUONG LEN DU BAO THAY DOI QUY SAU (LightGBM, walk-forward):")
        print(s.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
