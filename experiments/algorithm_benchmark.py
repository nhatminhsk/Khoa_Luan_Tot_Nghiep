from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

FEATURES = "data/model/features_clean.csv"  # tap sach tang 1 (= features_selected truoc 13/10/2026)
MAS = "data/vnstock_financial/ratio_mas_ttm.csv"
OUT_DIR = "data/model/experiments"
START = "2019-Q1"
VALID_FROM, TEST_FROM = "2021-Q1", "2023-Q1"
HORIZONS = (1, 2, 4)
SEED = 20260918
TARGETS = ["nim_ttm_percent", "cof_ttm_percent", "roe_ttm_percent", "npl_percent", "casa_percent", "ldr_computed_percent"]
LABEL = {"nim_ttm_percent": "NIM", "cof_ttm_percent": "COF", "roe_ttm_percent": "ROE", "npl_percent": "NPL",
         "casa_percent": "CASA", "ldr_computed_percent": "LDR"}
QUARTERLY = {"nim_ttm_percent": "nim_quarter_percent", "cof_ttm_percent": "cof_quarter_percent", "roe_ttm_percent": "roe_quarter_percent"}
MAS_COLS = ["nim_quarter_percent", "cof_quarter_percent", "roe_quarter_percent", "cir_quarter_percent", "earning_asset_yield_quarter_percent"]
BASELINES = ["naive", "drift", "seasonal", "rolloff"]
LGB_PARAMS = dict(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=20, subsample=0.8, subsample_freq=1,
                  colsample_bytree=0.7, reg_lambda=1.0, random_state=SEED, verbose=-1)


def load():
    f = pd.read_csv(FEATURES, encoding="utf-8-sig")
    mas = pd.read_csv(MAS, encoding="utf-8-sig")[["ticker", "period"] + MAS_COLS]
    f = f.merge(mas, on=["ticker", "period"], how="left").sort_values(["ticker", "period"]).reset_index(drop=True)
    if f.groupby("ticker").size().nunique() != 1:
        raise ValueError("panel phai can (moi NH du so quy) de dich dong theo quy")
    f["q"] = f.period.str[-1].astype(int)
    g = f.groupby("ticker")
    for c in MAS_COLS:
        for k in (1, 2, 3):
            f[f"{c}_l{k}"] = g[c].shift(k)
    for t in TARGETS:
        f[f"{t}_d1"] = g[t].diff()
        f[f"{t}_d1_l1"] = g[f"{t}_d1"].shift(1)
        # lech so voi trung binh cua chinh NH tinh den quy t (khong dung tuong lai)
        f[f"{t}_dev"] = f[t] - g[t].transform(lambda s: s.expanding().mean())
    f["refi_d1"] = g.refinancing_rate_pct.diff()
    for k in (1, 2, 3):
        f[f"refi_d1_l{k}"] = g.refi_d1.shift(k)
    return f


def baselines(f, t, h, per, io):
    known = f[f.period <= per[io]]
    d1 = known[f"{t}_d1"]
    med_q = d1.groupby(known.q).median()
    tq = [int(per[io + j][-1]) for j in range(1, h + 1)]
    out = {"naive": 0.0, "drift": h * d1.median(), "seasonal": float(sum(med_q.get(q, 0.0) for q in tq))}
    row = f[f.period == per[io]].set_index("ticker")
    if t in QUARTERLY:
        c = QUARTERLY[t]
        x_t = row[c]
        # quy roi ra: t-3, ..., t-4+h ; quy moi vao gia su = x_t
        out_q = sum(row[c] if k == 0 else row[f"{c}_l{k}"] for k in range(3, 3 - h, -1))
        out["rolloff"] = h * x_t - out_q
    else:
        out["rolloff"] = pd.Series(np.nan, index=row.index)
    return {k: (v if isinstance(v, pd.Series) else pd.Series(v, index=row.index)) for k, v in out.items()}


def small_features(t):
    cols = [f"{t}_d1", f"{t}_d1_l1", f"{t}_dev", "refi_d1", "refi_d1_l1", "refi_d1_l2", "refi_d1_l3", "system_credit_growth_asof_pct"]
    if t in QUARTERLY:
        c = QUARTERLY[t]
        cols += [c, f"{c}_l1", f"{c}_l3"]
    return cols


def run():
    import lightgbm as lgb
    from sklearn.linear_model import Ridge

    f = load()
    per = sorted(f.period.unique())
    pos = {p: i for i, p in enumerate(per)}
    base_feats = [c for c in pd.read_csv(FEATURES, encoding="utf-8-sig", nrows=1).columns if c not in ("period", "period_end", "ticker")]
    lag_feats = [c for c in f.columns if c.endswith(("_l1", "_l2", "_l3", "_d1", "_dev"))]
    all_feats = list(dict.fromkeys(base_feats + MAS_COLS + lag_feats + ["q"]))
    bank = f.ticker.astype("category").cat.codes
    rows = []
    for t in TARGETS:
        g = f.groupby("ticker")[t]
        for h in HORIZONS:
            y = g.shift(-h) - f[t]
            # baseline cho moi goc tu START: lam nen cho mo hinh phan du (du lich su de hoc) va de chon base
            B = {}
            for io, p in enumerate(per):
                if p < START or io + h >= len(per):
                    continue
                B[p] = baselines(f, t, h, per, io)
            # chon base tren tap kiem dinh
            val = []
            for p, b in B.items():
                if not VALID_FROM <= p < TEST_FROM:
                    continue
                m = f.period == p
                yt = y[m].to_numpy()
                for name in BASELINES:
                    e = np.abs(yt - b[name].reindex(f.ticker[m]).to_numpy())
                    val.append((name, np.nanmean(e)))
            vm = pd.DataFrame(val, columns=["m", "e"]).groupby("m").e.mean().dropna()
            best = vm.idxmin()
            # nen (base) cho moi dong co the lam dong train: base tinh tai chinh goc cua dong do
            base_all = pd.Series(np.nan, index=f.index)
            for p, b in B.items():
                m = f.period == p
                base_all[m] = b[best].reindex(f.ticker[m]).to_numpy()
            for p in per:
                if p < TEST_FROM or pos[p] + h >= len(per):
                    continue
                io = pos[p]
                trm = (f.period >= START) & (f.period.map(pos) <= io - h) & y.notna()
                tem = (f.period == p) & y.notna()
                if not tem.any():
                    continue
                pred = {name: B[p][name].reindex(f.ticker[tem]).to_numpy() for name in BASELINES}
                pred["base"] = pred[best]
                # Ridge tren phan du so voi base
                sf = small_features(t) + ["q1", "q2", "q3", "q4"]
                X = f[small_features(t)].assign(**{f"q{k}": ((f.q + h - 1) % 4 + 1 == k).astype(float) for k in range(1, 5)})
                rtr = trm & base_all.notna()
                Xtr, Xte = X[rtr][sf], X[tem][sf]
                mu, sd = Xtr.mean(), Xtr.std().replace(0, 1)
                Xtr_s, Xte_s = ((Xtr - mu) / sd).fillna(0), ((Xte - mu) / sd).fillna(0)
                if rtr.sum() >= 40:
                    r = Ridge(alpha=10.0).fit(Xtr_s, (y - base_all)[rtr])
                    pred["ridge"] = pred["base"] + r.predict(Xte_s)
                # LightGBM thang va tren phan du
                XL = f[all_feats].assign(bank=bank, tq=(f.q + h - 1) % 4 + 1)
                m1 = lgb.LGBMRegressor(**LGB_PARAMS).fit(XL[trm], y[trm], categorical_feature=["bank"])
                pred["lgbm"] = m1.predict(XL[tem])
                if rtr.sum() >= 40:
                    XLr = XL.assign(base=base_all)
                    m2 = lgb.LGBMRegressor(**LGB_PARAMS).fit(XLr[rtr], (y - base_all)[rtr], categorical_feature=["bank"])
                    pred["lgbm_res"] = pred["base"] + m2.predict(XLr[tem].assign(base=pred["base"]))
                yt = y[tem].to_numpy()
                for name, v in pred.items():
                    rows.append(pd.DataFrame({"target": t, "h": h, "origin": p, "ticker": f.ticker[tem].to_numpy(), "method": name,
                                              "base_is": best, "y_true": yt, "y_pred": v}))
            print(f"  {LABEL[t]} h={h}: base = {best} (kiem dinh {vm.round(3).to_dict()})", flush=True)
    P = pd.concat(rows, ignore_index=True)
    P["abs_err"] = (P.y_true - P.y_pred).abs()
    return P


def summarize(P, B=2000, seed=SEED):
    rng = np.random.default_rng(seed)
    out = []
    for (t, h), d in P.groupby(["target", "h"]):
        w = d.pivot_table(index=["origin", "ticker"], columns="method", values="abs_err").dropna(axis=1, how="all")
        w = w.dropna()
        by = w.groupby(level="ticker").sum()
        idx = [rng.integers(0, len(by), len(by)) for _ in range(B)]
        for m in w.columns:
            r = dict(target=LABEL[t], h=h, method=m, base_is=d.base_is.iloc[0], n=len(w), mae=w[m].mean())
            for ref in ("naive", "base"):
                g = 1 - w[m].mean() / w[ref].mean()
                bs = [1 - by[m].iloc[i].sum() / by[ref].iloc[i].sum() for i in idx]
                r[f"gain_vs_{ref}"], r[f"lo_vs_{ref}"], r[f"hi_vs_{ref}"] = g, np.percentile(bs, 2.5), np.percentile(bs, 97.5)
            out.append(r)
    return pd.DataFrame(out)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pd.set_option("display.width", 250)
    os.makedirs(OUT_DIR, exist_ok=True)
    P = run()
    S = summarize(P)
    P.to_csv(f"{OUT_DIR}/algorithm_benchmark_preds.csv", index=False, encoding="utf-8-sig")
    S.to_csv(f"{OUT_DIR}/algorithm_benchmark_summary.csv", index=False, encoding="utf-8-sig")
    show = S.assign(**{c: (S[c] * 100).round(1) for c in S.columns if c.startswith(("gain", "lo_", "hi_"))}, mae=S.mae.round(3))
    for (t, h), d in show.groupby(["target", "h"], sort=False):
        print(f"\n{t} h={h} (base = {d.base_is.iloc[0]}, n = {d.n.iloc[0]})")
        print(d.sort_values("mae")[["method", "mae", "gain_vs_naive", "lo_vs_naive", "hi_vs_naive", "gain_vs_base", "lo_vs_base",
                                    "hi_vs_base"]].to_string(index=False))


if __name__ == "__main__":
    main()
