from __future__ import annotations

import json
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from experiments import algorithm_benchmark as ab  # noqa: E402
from experiments import hyperparam_tuning as ht  # noqa: E402
from experiments import longer_history as lh  # noqa: E402
from serving import forecast as fc  # noqa: E402

OUT_DIR = "data/model/experiments"
N_RANDOM, N_HYPERBAND, N_BAYES = 40, 40, 60
B = 2000
SEED = 20261026
# = lh.RF_PARAMS. Khong dat max_samples=1.0: sklearn 1.9 co sample_weight thi max_samples tinh theo TONG trong so (cua so
# 2013 nang 0,5 -> it mau bootstrap hon) nen khac None; rut mau con la lua chon bat / tat rieng.
FIXED_RF = dict(n_estimators=300, max_depth=None, min_samples_leaf=10, max_features=0.33, subsample_rows=False)
STEPS = list(fc.IND)  # buoc Hyperband: moi chi tieu (4 tam) mot buoc


def space(trial, kind: str) -> dict:
    if kind == "rf":
        p = dict(n_estimators=trial.suggest_int("n_estimators", 100, 600, step=50),
                 max_depth=trial.suggest_categorical("max_depth", [None, 3, 5, 8, 12]),
                 min_samples_leaf=trial.suggest_int("min_samples_leaf", 1, 80, log=True),
                 max_features=trial.suggest_float("max_features", 0.1, 1.0))
        if trial.suggest_categorical("subsample_rows", [False, True]):
            p["max_samples"] = trial.suggest_float("max_samples", 0.3, 0.95)
        return p
    return dict(n_estimators=trial.suggest_int("n_estimators", 50, 1000, log=True),
                learning_rate=trial.suggest_float("learning_rate", 0.005, 0.2, log=True),
                num_leaves=trial.suggest_int("num_leaves", 2, 64, log=True),
                min_child_samples=trial.suggest_int("min_child_samples", 5, 100, log=True),
                subsample=trial.suggest_float("subsample", 0.5, 1.0),
                colsample_bytree=trial.suggest_float("colsample_bytree", 0.3, 1.0),
                reg_lambda=trial.suggest_float("reg_lambda", 1e-3, 30, log=True),
                reg_alpha=trial.suggest_float("reg_alpha", 1e-3, 10, log=True))


def _fit(kind: str, params: dict, Xtr, ytr, wtr, Xte) -> np.ndarray:
    if kind == "rf":
        from sklearn.ensemble import RandomForestRegressor
        m = RandomForestRegressor(random_state=lh.SEED, n_jobs=1, **params)
    else:
        import lightgbm as lgb
        m = lgb.LGBMRegressor(subsample_freq=1, random_state=lh.SEED, verbose=-1, n_jobs=1, **params)
    return m.fit(Xtr, ytr, sample_weight=wtr).predict(Xte)


def cells() -> dict:
    frames = {False: lh.load(False), True: lh.load(True)}
    out = {}
    for code, t in fc.IND.items():
        for h in fc.HORIZONS:
            c = ht.prep(frames[t in fc.ASSET], t, h)
            sel, test = [], []
            for p in c["per"]:
                io = c["pos"][p]
                if p < fc.SELECT_FROM or io + h >= len(c["per"]):
                    continue
                te = (c["pidx"] == io) & ~np.isnan(c["y"]) & ~np.isnan(c["base"])
                if not te.any():
                    continue
                masks = {run: ht.train_mask(c, io, h, run) for run in lh.RUNS}
                if min(tr.sum() for tr, _ in masks.values()) < fc.MIN_TRAIN:
                    continue
                o = dict(origin=p, te=te, masks=masks)
                if fc._next(p, h) <= fc.SELECT_LABEL_TO:
                    sel.append(o)
                elif p >= ab.TEST_FROM:
                    test.append(o)
            c["sel"], c["test"] = sel, test
            c["base_sel"] = np.mean(np.concatenate([np.abs(c["y"] - c["base"])[o["te"]] for o in sel]))
            out[(code, h)] = c
    return out


def errors(C: dict, keys: list, kind: str, params: dict, split: str, par) -> dict:
    from joblib import delayed
    jobs, meta = [], []
    for k in keys:
        c = C[k]
        for o in c[split]:
            for run, (tr, w) in o["masks"].items():
                jobs.append(delayed(_fit)(kind, params, c["X"][tr], c["resid"][tr], w[tr], c["X"][o["te"]]))
                meta.append((k, run, o))
    out = {}
    for (k, run, o), pr in zip(meta, par(jobs)):
        c = C[k]
        e = np.abs(c["resid"][o["te"]] - pr)
        out.setdefault(k, {}).setdefault(run, []).append(pd.DataFrame({"origin": o["origin"], "ticker": c["ticker"][o["te"]],
                                                                         "abs_err": e}))
    return {k: {run: pd.concat(v, ignore_index=True) for run, v in d.items()} for k, d in out.items()}


def ratio(C: dict, k, E: dict) -> float:
    return min(1.0, min(E[k][run].abs_err.mean() for run in lh.RUNS) / C[k]["base_sel"])


def run_study(C: dict, kind: str, method: str, n: int, par, quick: bool) -> tuple[pd.DataFrame, dict]:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    # max_samples la tham so co dieu kien: TPE da bien rut no doc lap (canh bao tat di, ket qua khong doi)
    sampler = (optuna.samplers.TPESampler(seed=SEED, n_startup_trials=10, multivariate=True, warn_independent_sampling=False)
               if method == "bayes"
               else optuna.samplers.RandomSampler(seed=SEED + (method == "hyperband")))
    pruner = (optuna.pruners.NopPruner() if method == "random"
              else optuna.pruners.HyperbandPruner(min_resource=1, max_resource=len(STEPS), reduction_factor=3))
    study = optuna.create_study(direction="minimize", sampler=sampler, pruner=pruner)
    if method == "bayes" and kind == "rf":
        study.enqueue_trial(FIXED_RF)
    keys_by_step = [[k for k in C if k[0] == s] for s in STEPS]

    def objective(trial):
        params = space(trial, kind)
        r = []
        for step, keys in enumerate(keys_by_step):
            E = errors(C, keys, kind, params, "sel", par)
            r += [ratio(C, k, E) for k in keys]
            trial.report(float(np.mean(r)), step + 1)  # tai nguyen Hyperband = so chi tieu da danh gia (1..6)
            if trial.should_prune():
                raise optuna.TrialPruned()
        return float(np.mean(r))

    t0 = time.time()
    study.optimize(objective, n_trials=3 if quick else n)
    T = study.trials_dataframe(attrs=("number", "value", "state", "duration", "params"))
    T.insert(0, "method", method)
    T.insert(0, "family", kind)
    done = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    print(f"  {kind} {method}: {len(done)} xong / {len(study.trials)} lan thu, tot nhat {study.best_value:.4f} "
          f"[{time.time() - t0:.0f}s]", flush=True)
    return T, dict(params=space(optuna.trial.FixedTrial(study.best_params), kind), value=study.best_value,
                   n_complete=len(done), n_trials=len(study.trials), seconds=time.time() - t0)


def grid_best(kind: str) -> tuple[dict, float, dict]:
    G = pd.read_csv(f"{OUT_DIR}/hyperparam_tuning_config.csv", encoding="utf-8-sig")
    G = G[G.indicator.isin(list(fc.IND))]
    base = G[G.method == "base"].set_index(["indicator", "h"]).mae_v2
    G = G[G.method.str.startswith(kind + "_")].assign(combo=lambda d: d.method.str.split("|").str[0])
    per_cell = G.groupby(["combo", "indicator", "h"]).mae_v2.min()
    r = (per_cell / base.reindex(per_cell.droplevel(0).index).to_numpy()).clip(upper=1.0)
    obj = r.groupby(level="combo").mean()
    best = obj.idxmin()
    if kind == "rf":
        l, m = best[len("rf_l"):].split("_m")
        params = dict(n_estimators=300, max_depth=None, min_samples_leaf=int(l), max_features=float(m))
    else:
        n_, k_, c_ = (int(x[1:]) for x in best[len("lgb_"):].split("_"))
        params = dict(n_estimators=n_, num_leaves=k_, min_child_samples=c_, learning_rate=0.03, subsample=0.8,
                      colsample_bytree=0.7, reg_lambda=1.0)
    return params, float(obj[best]), {"rf_l10_m0.33": float(obj.get("rf_l10_m0.33", np.nan))}


def production() -> dict:
    oof = pd.read_csv(fc.OOF, encoding="utf-8-sig")
    oof = oof[(oof.origin >= ab.TEST_FROM) & (oof.method == oof.chosen)]
    code = {v: k for k, v in fc.IND.items()}
    return {(code[i], h): g.assign(abs_err=g.err.abs())[["origin", "ticker", "abs_err"]].reset_index(drop=True)
            for (i, h), g in oof.groupby(["indicator", "h"])}


def evaluate(C: dict, kind: str, params: dict, par, prod: dict) -> pd.DataFrame:
    Es, Et = errors(C, list(C), kind, params, "sel", par), errors(C, list(C), kind, params, "test", par)
    rows = []
    for k, c in C.items():
        mae = {run: Es[k][run].abs_err.mean() for run in lh.RUNS}
        run = min(mae, key=mae.get)
        pick = run if mae[run] < c["base_sel"] else "base"
        bt = pd.concat([pd.DataFrame({"origin": o["origin"], "ticker": c["ticker"][o["te"]],
                                      "abs_err": np.abs(c["resid"][o["te"]])}) for o in c["test"]], ignore_index=True)
        mt = bt if pick == "base" else Et[k][pick]
        key = ["origin", "ticker"]
        j = bt.merge(mt, on=key, suffixes=("_base", "_pick")).merge(prod[k].rename(columns={"abs_err": "abs_err_prod"}), on=key)
        if len(j) != len(bt):
            raise ValueError(f"{k}: dong kiem tra lech ban dang dung ({len(j)} / {len(bt)})")
        s = j.groupby("ticker")[["abs_err_base", "abs_err_pick", "abs_err_prod"]].sum()
        rows.append(s.reset_index().assign(indicator=k[0], h=k[1], pick=pick, n=j.groupby("ticker").size().to_numpy()))
    return pd.concat(rows, ignore_index=True)


def summarize(S: pd.DataFrame, rng) -> tuple[dict, pd.DataFrame]:
    banks = sorted(S.ticker.unique())
    cube = {k: g.set_index("ticker").reindex(banks) for k, g in S.groupby(["indicator", "h"], sort=False)}
    idx = [rng.integers(0, len(banks), len(banks)) for _ in range(B)]

    def gains(g, i=None):
        g = g.fillna(0.0) if i is None else g.fillna(0.0).iloc[i]
        return 1 - g.abs_err_pick.sum() / g.abs_err_base.sum(), 1 - g.abs_err_pick.sum() / g.abs_err_prod.sum()

    cells, boot = [], {k: np.array([gains(g, i) for i in idx]) for k, g in cube.items()}
    for k, g in cube.items():
        gb, gp = gains(g)
        lo_b, hi_b = np.percentile(boot[k][:, 0], [2.5, 97.5])
        lo_p, hi_p = np.percentile(boot[k][:, 1], [2.5, 97.5])
        cells.append(dict(indicator=k[0], h=k[1], pick=g.pick.dropna().iloc[0], gain_base=gb, gain_base_lo=lo_b,
                          gain_base_hi=hi_b, gain_prod=gp, gain_prod_lo=lo_p, gain_prod_hi=hi_p))
    cells = pd.DataFrame(cells)
    avg = np.mean([v for v in boot.values()], axis=0)  # (B, 2)
    tot = dict(gain_base=cells.gain_base.mean(), gain_base_lo=np.percentile(avg[:, 0], 2.5),
               gain_base_hi=np.percentile(avg[:, 0], 97.5), gain_prod=cells.gain_prod.mean(),
               gain_prod_lo=np.percentile(avg[:, 1], 2.5), gain_prod_hi=np.percentile(avg[:, 1], 97.5),
               # dung sai 1e-9: cung du bao nhung cong theo thu tu khac lech ~1e-16
               hon_ban_dang_dung=int((cells.gain_prod_lo > 1e-9).sum()),
               kem_ban_dang_dung=int((cells.gain_prod_hi < -1e-9).sum()),
               so_o_khac_ban_dang_dung=None)
    return tot, cells


def main():
    from joblib import Parallel
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pd.set_option("display.width", 250)
    quick = "--quick" in sys.argv
    t0 = time.time()
    C = cells()
    print(f"24 o: goc chon {min(len(c['sel']) for c in C.values())}-{max(len(c['sel']) for c in C.values())}, "
          f"goc kiem tra {min(len(c['test']) for c in C.values())}-{max(len(c['test']) for c in C.values())} "
          f"[{time.time() - t0:.0f}s]", flush=True)
    prod = production()
    sel = pd.read_csv(fc.SELECTION, encoding="utf-8-sig").set_index(["indicator_code", "h"]).method
    rng = np.random.default_rng(SEED)
    trials, best_rows, cell_rows = [], [], []
    with Parallel(n_jobs=-1) as par:
        # doi chung truoc: tham so dang dung qua evaluate phai tai lap DUNG serving.forecast (0 o lech, loi 0)
        fixed = {k: v for k, v in FIXED_RF.items() if k != "subsample_rows"}
        _, cl = summarize(evaluate(C, "rf", fixed, par, prod), np.random.default_rng(0))
        bad = [k for k in zip(cl.indicator, cl.h) if cl.set_index(["indicator", "h"]).pick[k] != sel[k]]
        if bad or cl.gain_prod.abs().max() > 1e-12:
            raise SystemExit(f"tham so dang dung khong tai lap serving.forecast: o lech {bad}, |loi| {cl.gain_prod.abs().max()}")
        print("  doi chung: tham so dang dung tai lap dung serving.forecast (24/24 o)", flush=True)
        for kind in ("rf", "lgb"):
            gp, gv, ref = grid_best(kind)
            found = {"grid": dict(params=gp, value=gv, n_complete=15 if kind == "rf" else 18,
                                  n_trials=15 if kind == "rf" else 18, seconds=np.nan)}
            if kind == "rf":
                print(f"  muc tieu cua tham so dang dung (luoi lan 1): {ref['rf_l10_m0.33']:.4f}", flush=True)
            for method, n in (("random", N_RANDOM), ("hyperband", N_HYPERBAND), ("bayes", N_BAYES)):
                T, info = run_study(C, kind, method, n, par, quick)
                trials.append(T)
                found[method] = info
            if kind == "rf":
                found["dang_dung"] = dict(params=fixed, value=ref["rf_l10_m0.33"], n_complete=0, n_trials=0, seconds=0)
            for method, info in found.items():
                S = evaluate(C, kind, info["params"], par, prod)
                tot, cl = summarize(S, rng)
                picks = cl.set_index(["indicator", "h"]).pick
                tot["so_o_khac_ban_dang_dung"] = int(sum(picks[k] != sel[k] for k in picks.index))
                best_rows.append(dict(family=kind, method=method, objective_sel=info["value"], n_complete=info["n_complete"],
                                      n_trials=info["n_trials"], seconds=info["seconds"],
                                      params=json.dumps(info["params"]), **tot))
                cell_rows.append(cl.assign(family=kind, method=method))
                print(f"    {kind} {method:9s} muc tieu {info['value']:.4f}; kiem tra: so base {tot['gain_base']:+.1%} "
                      f"[{tot['gain_base_lo']:+.1%}; {tot['gain_base_hi']:+.1%}], so ban dang dung {tot['gain_prod']:+.1%} "
                      f"[{tot['gain_prod_lo']:+.1%}; {tot['gain_prod_hi']:+.1%}], hon {tot['hon_ban_dang_dung']}/24 "
                      f"kem {tot['kem_ban_dang_dung']}/24; {info['params']}", flush=True)
    if quick:
        return
    pd.concat(trials, ignore_index=True).to_csv(f"{OUT_DIR}/hyperparam_search_trials.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(best_rows).to_csv(f"{OUT_DIR}/hyperparam_search_best.csv", index=False, encoding="utf-8-sig")
    pd.concat(cell_rows, ignore_index=True).to_csv(f"{OUT_DIR}/hyperparam_search_cells.csv", index=False, encoding="utf-8-sig")
    print(f"xong [{time.time() - t0:.0f}s]")


if __name__ == "__main__":
    main()
