from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from crawlers import policy_rate  # noqa: E402
from experiments import algorithm_benchmark as ab  # noqa: E402

MAS = "data/vnstock_financial/ratio_mas_ttm.csv"
LONG_PANEL = "data/model/bank_panel_long_quarterly.csv"
OUT_DIR = "data/model/experiments"
SEED = 20261013
TARGETS = {"nim_ttm_percent": "nim_quarter_percent", "cof_ttm_percent": "cof_quarter_percent",
           "roe_ttm_percent": "roe_quarter_percent"}
ASSET_TARGETS = {"npl_percent": None, "casa_percent": None, "ldr_computed_percent": None}  # khong co so rieng tung quy
LABEL = {"nim_ttm_percent": "NIM", "cof_ttm_percent": "COF", "roe_ttm_percent": "ROE", "npl_percent": "NPL",
         "casa_percent": "CASA", "ldr_computed_percent": "LDR"}
BASE_FROM = "2018-Q1"  # base giong ban goc: chi biet so tu 2018
RF_PARAMS = dict(n_estimators=300, min_samples_leaf=10, max_features=0.33, random_state=SEED, n_jobs=1)
RUNS = {"rf_2019": ("2019-Q1", 1.0), "rf_2013": ("2013-Q1", 1.0), "rf_2013w": ("2013-Q1", 0.5)}
SPARSE = ["BVB", "OCB", "TPB", "LPB", "MSB", "SSB", "BAB", "NAB"]  # < 50% so quy 2012-2017


def load(asset: bool = False, drop_congtyme: bool = False, drop_sparse: bool = False) -> pd.DataFrame:
    targets = ASSET_TARGETS if asset else TARGETS
    m = pd.read_csv(LONG_PANEL if asset else MAS, encoding="utf-8-sig")
    if asset:
        pre = m.period < BASE_FROM
        if drop_congtyme:
            m.loc[pre & m.scope_npl.eq("Congtyme"), "npl_percent"] = np.nan
            m.loc[pre & m.scope_casa.eq("Congtyme"), "casa_percent"] = np.nan
        if drop_sparse:
            m.loc[pre & m.ticker.isin(SPARSE), list(ASSET_TARGETS)] = np.nan
    cols = list(targets) + [c for c in targets.values() if c]
    m = m[["ticker", "period"] + cols]
    per = sorted(m.period.unique())
    grid = pd.MultiIndex.from_product([sorted(m.ticker.unique()), per], names=["ticker", "period"]).to_frame(index=False)
    f = grid.merge(m, on=["ticker", "period"], how="left").sort_values(["ticker", "period"]).reset_index(drop=True)
    daily = policy_rate.as_daily_series(start="2011-10-10")
    daily["period"] = daily.date.dt.year.astype(str) + "-Q" + daily.date.dt.quarter.astype(str)
    refi = daily.groupby("period").tai_cap_von.last().rename("refinancing_rate_pct")
    f = f.merge(refi, on="period", how="left")
    if f.refinancing_rate_pct.isna().any():
        raise ValueError("thieu lai tai cap von o mot so quy")
    f["q"] = f.period.str[-1].astype(int)
    g = f.groupby("ticker")
    for c in [c for c in targets.values() if c]:
        for k in (1, 2, 3):
            f[f"{c}_l{k}"] = g[c].shift(k)
    for t in targets:
        f[f"{t}_d1"] = g[t].diff()
        f[f"{t}_d1_l1"] = g[f"{t}_d1"].shift(1)
        f[f"{t}_dev"] = f[t] - g[t].transform(lambda s: s.expanding().mean())
    f["refi_d1"] = g.refinancing_rate_pct.diff()
    for k in (1, 2, 3):
        f[f"refi_d1_l{k}"] = g.refi_d1.shift(k)
    return f


def core(t: str) -> list[str]:
    c = {**TARGETS, **ASSET_TARGETS}[t]
    quarter = [c, f"{c}_l1", f"{c}_l3"] if c else []
    return [f"{t}_d1", f"{t}_d1_l1", f"{t}_dev", "refi_d1", "refi_d1_l1", "refi_d1_l2", "refi_d1_l3", *quarter, "tq"]


def _fit_predict(X, resid, w, tr, te):
    from sklearn.ensemble import RandomForestRegressor
    return RandomForestRegressor(**RF_PARAMS).fit(X[tr], resid[tr], sample_weight=w[tr]).predict(X[te])


def run(f: pd.DataFrame, targets: dict = TARGETS, first_origin: str = ab.TEST_FROM) -> pd.DataFrame:
    from joblib import Parallel, delayed

    per = sorted(f.period.unique())
    pos = {p: i for i, p in enumerate(per)}
    pidx = f.period.map(pos).to_numpy()
    fb = f[f.period >= BASE_FROM].reset_index(drop=True)  # khung cho base: giong ban goc
    per_b = sorted(fb.period.unique())
    out = []
    for t in targets:
        for h in ab.HORIZONS:
            y = (f.groupby("ticker")[t].shift(-h) - f[t]).to_numpy()
            # base cho moi goc tu 2013 (de lam nen phan du cho dong train truoc 2018): truoc 2018 dung drift/seasonal
            # tinh tren chinh lich su dai; tu 2018 dung dung ham cua ab tren khung tu 2018 nhu ban goc
            B = {}
            for io, p in enumerate(per):
                if io + h >= len(per) or p < "2013-Q1":
                    continue
                if p >= BASE_FROM:
                    B[p] = ab.baselines(fb, t, h, per_b, per_b.index(p))
                else:
                    B[p] = ab.baselines(f, t, h, per, io)
            val = []
            for p, b in B.items():
                if ab.VALID_FROM <= p < ab.TEST_FROM:
                    m = (f.period == p).to_numpy()
                    for name in ab.BASELINES:
                        val.append((name, np.nanmean(np.abs(y[m] - b[name].reindex(f.ticker[m]).to_numpy()))))
            best = pd.DataFrame(val, columns=["m", "e"]).groupby("m").e.mean().dropna().idxmin()
            base = np.full(len(f), np.nan)
            for p, b in B.items():
                m = (f.period == p).to_numpy()
                base[m] = b[best].reindex(f.ticker[m]).to_numpy()
            F = f.assign(tq=((f.q + h - 1) % 4 + 1).astype(float))
            X = F[core(t)].to_numpy(np.float32)
            resid = y - base
            jobs, keys = [], []
            for p in per:
                io = pos[p]
                if p < first_origin or io + h >= len(per):
                    continue
                te = (pidx == io) & ~np.isnan(y) & ~np.isnan(base)
                if not te.any():
                    continue
                out.append(pd.DataFrame({"target": LABEL[t], "h": h, "base_is": best, "origin": p, "ticker": f.ticker[te].to_numpy(),
                                         "method": "base", "y_true": y[te], "y_pred": base[te]}))
                for name, (start, w_old) in RUNS.items():
                    tr = (f.period >= start).to_numpy() & (pidx <= io - h) & ~np.isnan(resid)
                    w = np.where((f.period < BASE_FROM).to_numpy(), w_old, 1.0)
                    jobs.append(delayed(_fit_predict)(X, resid, w, tr, te))
                    keys.append((p, name, te, int(tr.sum())))
            preds = Parallel(n_jobs=-1)(jobs)
            for (p, name, te, ntr), pr in zip(keys, preds):
                out.append(pd.DataFrame({"target": LABEL[t], "h": h, "base_is": best, "origin": p, "ticker": f.ticker[te].to_numpy(),
                                         "method": name, "n_train": ntr, "y_true": y[te], "y_pred": base[te] + pr}))
            print(f"  {LABEL[t]} h={h}: base = {best}", flush=True)
    P = pd.concat(out, ignore_index=True)
    P["abs_err"] = (P.y_true - P.y_pred).abs()
    P["split"] = np.where(P.origin < ab.TEST_FROM, "valid", "test")
    return P


def summarize(P: pd.DataFrame, B: int = 2000) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows = []
    P = P[P.split == "test"] if "split" in P else P
    for (t, h), d in P.groupby(["target", "h"], sort=False):
        w = d.pivot_table(index=["origin", "ticker"], columns="method", values="abs_err").dropna()
        by = w.groupby(level="ticker").sum()
        idx = [rng.integers(0, len(by), len(by)) for _ in range(B)]
        ntr = d.groupby("method").n_train.agg(["min", "max"])
        for a, b in (("rf_2019", "base"), ("rf_2013", "base"), ("rf_2013w", "base"), ("rf_2013", "rf_2019"), ("rf_2013w", "rf_2019")):
            g = 1 - w[a].mean() / w[b].mean()
            bs = [1 - by[a].iloc[i].sum() / by[b].iloc[i].sum() for i in idx]
            rows.append(dict(target=t, h=h, base_is=d.base_is.iloc[0], compare=f"{a} vs {b}", n_test=len(w), gain=g,
                             lo=np.percentile(bs, 2.5), hi=np.percentile(bs, 97.5),
                             n_train=f"{int(ntr.loc[a, 'min'])}-{int(ntr.loc[a, 'max'])}"))
    return pd.DataFrame(rows)


def nested(P: pd.DataFrame, B: int = 2000) -> pd.DataFrame:
    rng = np.random.default_rng(SEED + 1)
    rows = []
    for (t, h), d in P.groupby(["target", "h"], sort=False):
        val = d[d.split == "valid"].pivot_table(index=["origin", "ticker"], columns="method", values="abs_err").dropna()
        pick = val.mean().idxmin()
        w = d[d.split == "test"].pivot_table(index=["origin", "ticker"], columns="method", values="abs_err").dropna()
        by = w.groupby(level="ticker").sum()
        bs = [1 - by[pick].iloc[i].sum() / by["base"].iloc[i].sum()
              for i in (rng.integers(0, len(by), len(by)) for _ in range(B))]
        rows.append(dict(target=t, h=h, base_is=d.base_is.iloc[0], chon_tren_2021_22=pick,
                         valid_gain=1 - val[pick].mean() / val["base"].mean(),
                         test_gain=1 - w[pick].mean() / w["base"].mean(), lo=np.percentile(bs, 2.5), hi=np.percentile(bs, 97.5)))
    return pd.DataFrame(rows)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pd.set_option("display.width", 250)
    os.makedirs(OUT_DIR, exist_ok=True)
    asset = "--asset" in sys.argv
    valid = "--valid" in sys.argv
    dc, dsp = "--drop-congtyme" in sys.argv, "--drop-sparse" in sys.argv
    targets = ASSET_TARGETS if asset else TARGETS
    f = load(asset, dc, dsp)
    pre = f[f.period < BASE_FROM]
    for t in targets:
        d1 = pre[f"{t}_d1"].notna()
        print(f"{LABEL[t]}: truoc {BASE_FROM} co {pre[t].notna().sum()} dong NH-quy ({pre.loc[pre[t].notna(), 'ticker'].nunique()} NH), "
              f"{d1.sum()} dong co thay doi quy lien ke")
    P = run(f, targets, ab.VALID_FROM if valid else ab.TEST_FROM)
    S = summarize(P)
    tag = ("longer_history_asset" if asset else "longer_history") + ("_valid" if valid else "") +         ("_bo_congtyme" if dc else "") + ("_bo_nh_it" if dsp else "")
    if valid:
        N = nested(P)
        N.to_csv(f"{OUT_DIR}/{tag}_nested.csv", index=False, encoding="utf-8-sig")
        print(N.assign(**{c: (N[c] * 100).round(1) for c in ("valid_gain", "test_gain", "lo", "hi")}).to_string(index=False))
    P.to_csv(f"{OUT_DIR}/{tag}_preds.csv", index=False, encoding="utf-8-sig")
    S.to_csv(f"{OUT_DIR}/{tag}_summary.csv", index=False, encoding="utf-8-sig")
    show = S.assign(**{c: (S[c] * 100).round(1) for c in ("gain", "lo", "hi")})
    print(show.pivot_table(index=["target", "h", "base_is"], columns="compare", values=["gain", "lo"], sort=False).to_string())
    print(show[["target", "h", "compare", "n_train"]].drop_duplicates(["target", "h", "compare"]).head(5).to_string(index=False))


if __name__ == "__main__":
    main()
