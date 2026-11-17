from __future__ import annotations

import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from experiments import algorithm_benchmark as ab  # noqa: E402
from experiments import longer_history as lh  # noqa: E402
from serving import forecast as fc  # noqa: E402

OUT_DIR = "data/model/experiments"
SELECTION = "data/model/experiments/forecast_selection.csv"
V2_FROM = "2019-Q1"
B = 2000
GRID = {"rf": [dict(min_samples_leaf=l, max_features=m) for l in (3, 5, 10, 20, 40) for m in (0.33, 0.6, 1.0)],
        "lgb": [dict(n_estimators=n, num_leaves=k, min_child_samples=c)
                for n in (100, 300) for k in (4, 8, 16) for c in (10, 20, 40)]}
FIXED = dict(min_samples_leaf=10, max_features=0.33)  # = lh.RF_PARAMS


def _name(kind: str, p: dict, run: str) -> str:
    if kind == "rf":
        return f"rf_l{p['min_samples_leaf']}_m{p['max_features']}|{run}"
    return f"lgb_n{p['n_estimators']}_k{p['num_leaves']}_c{p['min_child_samples']}|{run}"


def _fit_all(X, resid, w, tr, te) -> dict:
    import lightgbm as lgb
    from sklearn.ensemble import RandomForestRegressor
    out = {}
    for p in GRID["rf"]:
        m = RandomForestRegressor(n_estimators=300, random_state=lh.SEED, n_jobs=1, **p)
        out[("rf", tuple(p.items()))] = m.fit(X[tr], resid[tr], sample_weight=w[tr]).predict(X[te])
    for p in GRID["lgb"]:
        m = lgb.LGBMRegressor(learning_rate=0.03, subsample=0.8, subsample_freq=1, colsample_bytree=0.7, reg_lambda=1.0,
                              random_state=lh.SEED, verbose=-1, n_jobs=1, **p)
        out[("lgb", tuple(p.items()))] = m.fit(X[tr], resid[tr], sample_weight=w[tr]).predict(X[te])
    return out


def prep(f: pd.DataFrame, t: str, h: int) -> dict:
    per = sorted(f.period.unique())
    pos = {p: i for i, p in enumerate(per)}
    pidx = f.period.map(pos).to_numpy()
    fb = f[f.period >= lh.BASE_FROM].reset_index(drop=True)
    per_b = sorted(fb.period.unique())
    fut = [fc._next(per[-1], k) for k in range(1, max(fc.HORIZONS) + 1)]
    y = (f.groupby("ticker")[t].shift(-h) - f[t]).to_numpy()
    # base: y het buoc 1 cua serving.forecast._target
    Bs = {}
    for io, p in enumerate(per):
        if p < "2013-Q1":
            continue
        Bs[p] = ab.baselines(fb, t, h, per_b + fut, per_b.index(p)) if p >= lh.BASE_FROM else ab.baselines(f, t, h, per + fut, io)
    val = []
    for p, b in Bs.items():
        if ab.VALID_FROM <= p and fc._next(p, h) <= fc.SELECT_LABEL_TO:
            m = (f.period == p).to_numpy()
            for name in ab.BASELINES:
                val.append((name, np.nanmean(np.abs(y[m] - b[name].reindex(f.ticker[m]).to_numpy()))))
    best = pd.DataFrame(val, columns=["m", "e"]).groupby("m").e.mean().dropna().idxmin()
    base = np.full(len(f), np.nan)
    for p, b in Bs.items():
        m = (f.period == p).to_numpy()
        base[m] = b[best].reindex(f.ticker[m]).to_numpy()
    X = f.assign(tq=((f.q + h - 1) % 4 + 1).astype(float))[lh.core(t)].to_numpy(np.float32)
    return dict(per=per, pos=pos, pidx=pidx, y=y, base=base, best=best, X=X, resid=y - base,
                ticker=f.ticker.to_numpy(), period=f.period.to_numpy())


def train_mask(c: dict, io: int, h: int, run: str) -> tuple[np.ndarray, np.ndarray]:
    start, w_old = lh.RUNS[run]
    tr = (c["period"] >= start) & (c["pidx"] <= io - h) & ~np.isnan(c["resid"])
    return tr, np.where(c["period"] < lh.BASE_FROM, w_old, 1.0)


def _cell(f: pd.DataFrame, t: str, h: int) -> pd.DataFrame:
    from joblib import Parallel, delayed

    c = prep(f, t, h)
    per, pos, pidx, y, base, best, X, resid = (c[k] for k in ("per", "pos", "pidx", "y", "base", "best", "X", "resid"))
    jobs, keys, rows = [], [], []
    for p in per:
        io = pos[p]
        if p < V2_FROM or io + h >= len(per):
            continue
        te = (pidx == io) & ~np.isnan(y) & ~np.isnan(base)
        if not te.any():
            continue
        rows.append(pd.DataFrame({"origin": p, "ticker": f.ticker[te].to_numpy(), "method": "base",
                                  "abs_err": np.abs(y[te] - base[te])}))
        for run in lh.RUNS:
            tr, w = train_mask(c, io, h, run)
            if tr.sum() < fc.MIN_TRAIN:
                continue
            jobs.append(delayed(_fit_all)(X, resid, w, tr, te))
            keys.append((p, run, te))
    for (p, run, te), preds in zip(keys, Parallel(n_jobs=-1)(jobs)):
        for (kind, items), pr in preds.items():
            rows.append(pd.DataFrame({"origin": p, "ticker": f.ticker[te].to_numpy(), "method": _name(kind, dict(items), run),
                                      "abs_err": np.abs(y[te] - base[te] - pr)}))
    E = pd.concat(rows, ignore_index=True)
    E["target_period"] = [fc._next(o, h) for o in E.origin]
    E["base_is"] = best
    return E


def _boot(W: pd.DataFrame, a: str, b: str, rng) -> tuple[float, float, float]:
    if a == b:
        return 0.0, 0.0, 0.0
    by = W.groupby(level="ticker")[[a, b]].sum()
    g = 1 - W[a].mean() / W[b].mean()
    bs = [1 - by[a].iloc[i].sum() / by[b].iloc[i].sum() for i in (rng.integers(0, len(by), len(by)) for _ in range(B))]
    return g, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def analyse(E: pd.DataFrame, code: str, h: int, rng) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    W = E.pivot_table(index=["origin", "ticker"], columns="method", values="abs_err")
    o = W.index.get_level_values("origin")
    tp = np.array([fc._next(x, h) for x in o])
    fixed_cols = ["base"] + [f"rf_l10_m0.33|{r}" for r in lh.RUNS]
    v1 = W[(o >= ab.VALID_FROM) & (tp <= fc.SELECT_LABEL_TO)]
    v2 = W[(o >= V2_FROM) & (tp <= fc.SELECT_LABEL_TO)].dropna()
    T = W[o >= ab.TEST_FROM].dropna()
    fixed = v1[fixed_cols].dropna().mean().idxmin()
    rf_cols = ["base"] + [c for c in W.columns if c.startswith("rf_")]
    # co_dinh_v2: tham so goc nhung chon tren V2 -> tach tac dung cua TAP CHON rong hon khoi tac dung cua TINH CHINH
    picks = {"co_dinh": fixed,
             "chinh_rf_v1": v1[rf_cols].dropna().mean().idxmin(),
             "chinh_v1": v1.dropna().mean().idxmin(),
             "co_dinh_v2": v2[fixed_cols].mean().idxmin(),
             "chinh_v2": v2.mean().idxmin(),
             "tran_nhin_test": T.mean().idxmin()}
    row = dict(indicator=code, h=h, base_is=E.base_is.iloc[0], n_v1=len(v1.dropna()), n_v2=len(v2), n_test=len(T),
               mae_test_base=T["base"].mean())
    for k, m in picks.items():
        g, lo, hi = _boot(T, m, "base", rng)
        row |= {f"{k}": m, f"{k}_gain": g, f"{k}_lo": lo, f"{k}_hi": hi}
        if k != "co_dinh":
            g, lo, hi = _boot(T, m, fixed, rng)
            row |= {f"{k}_vs_codinh": g, f"{k}_vs_codinh_lo": lo, f"{k}_vs_codinh_hi": hi}
    g, lo, hi = _boot(T, picks["chinh_v2"], picks["co_dinh_v2"], rng)
    row |= {"chinh_v2_vs_codinhv2": g, "chinh_v2_vs_codinhv2_lo": lo, "chinh_v2_vs_codinhv2_hi": hi}
    cfg = pd.DataFrame({"mae_v1": v1.dropna().mean(), "mae_v2": v2.mean(), "mae_test": T.mean()}).rename_axis("method").reset_index()
    cfg.insert(0, "h", h)
    cfg.insert(0, "indicator", code)
    by = []
    for split, d in (("v1", v1.dropna()), ("v2", v2), ("test", T)):
        s = d.groupby(level="ticker").sum().stack().rename("sum_abs_err").reset_index()
        s["n"] = s.ticker.map(d.groupby(level="ticker").size())
        by.append(s.assign(split=split))
    by = pd.concat(by, ignore_index=True).assign(indicator=code, h=h)
    return row, cfg, by


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pd.set_option("display.width", 250)
    quick = "--quick" in sys.argv
    rng = np.random.default_rng(lh.SEED + 7)
    frames = {False: lh.load(False), True: lh.load(True)}
    cells = [("npl", 1)] if quick else [(c, h) for c in fc.IND for h in fc.HORIZONS]
    rows, cfgs, bys = [], [], []
    for code, h in cells:
        t = fc.IND[code]
        t0 = time.time()
        E = _cell(frames[t in fc.ASSET], t, h)
        row, cfg, by = analyse(E, code, h, rng)
        rows.append(row)
        cfgs.append(cfg)
        bys.append(by)
        print(f"  {code} h={h}: co dinh {row['co_dinh']} ({row['co_dinh_gain']:+.1%}), chinh V1 {row['chinh_v1']} "
              f"({row['chinh_v1_gain']:+.1%}), V2 {row['chinh_v2']} ({row['chinh_v2_gain']:+.1%}), "
              f"tran {row['tran_nhin_test_gain']:+.1%}  [{time.time() - t0:.0f}s]", flush=True)
    P = pd.DataFrame(rows)
    # doi chung phai trung serving.forecast (cung du lieu, cung quy tac chon); tu 26/10 forecast chon tren goc tu 2019 = V2
    S = pd.read_csv(SELECTION, encoding="utf-8-sig").set_index(["indicator_code", "h"])
    fixed_map = {"base": "base", **{f"rf_l10_m0.33|{r}": r for r in lh.RUNS}}
    ref = "co_dinh_v2" if fc.SELECT_FROM == V2_FROM else "co_dinh"
    for r in rows:
        s = S.loc[(r["indicator"], r["h"])]
        if fixed_map[r[ref]] != s.method or abs(r[f"{ref}_gain"] - s.test_gain_vs_base) > 1e-9:
            print(f"!! {r['indicator']} h={r['h']}: doi chung {r[ref]} {r[f'{ref}_gain']:.6f} khac "
                  f"forecast_selection {s.method} {s.test_gain_vs_base:.6f}")
    if quick:
        print(P.T.to_string())
        return
    P.to_csv(f"{OUT_DIR}/hyperparam_tuning_picks.csv", index=False, encoding="utf-8-sig")
    pd.concat(cfgs, ignore_index=True).to_csv(f"{OUT_DIR}/hyperparam_tuning_config.csv", index=False, encoding="utf-8-sig")
    pd.concat(bys, ignore_index=True).to_csv(f"{OUT_DIR}/hyperparam_tuning_by_bank.csv", index=False, encoding="utf-8-sig")
    pct = lambda c: (P[c] * 100).round(1)  # noqa: E731
    show = pd.DataFrame({"chi_tieu": P.indicator, "h": P.h, "co_dinh": pct("co_dinh_gain"), "chinh_v1": pct("chinh_v1_gain"),
                         "v1_vs_cd": pct("chinh_v1_vs_codinh"), "v1_vs_cd_lo": pct("chinh_v1_vs_codinh_lo"),
                         "v1_vs_cd_hi": pct("chinh_v1_vs_codinh_hi"), "co_dinh_v2": pct("co_dinh_v2_gain"),
                         "chinh_v2": pct("chinh_v2_gain"), "v2_vs_cdv2": pct("chinh_v2_vs_codinhv2"),
                         "tran": pct("tran_nhin_test_gain")})
    print(show.to_string(index=False))
    for k, ref in (("chinh_rf_v1", "codinh"), ("chinh_v1", "codinh"), ("co_dinh_v2", "codinh"), ("chinh_v2", "codinh"),
                   ("chinh_v2", "codinhv2")):
        c = f"{k}_vs_{ref}"
        print(f"{c}: loi TB {P[c].mean():+.1%}; hon co y nghia {(P[c + '_lo'] > 0).sum()}/{len(P)}, "
              f"kem co y nghia {(P[c + '_hi'] < 0).sum()}/{len(P)}")


if __name__ == "__main__":
    main()
