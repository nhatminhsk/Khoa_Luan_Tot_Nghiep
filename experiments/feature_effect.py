from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from experiments import algorithm_benchmark as ab  # noqa: E402

FEATURES = "data/model/features_quarterly.csv"
CATALOG = "data/model/feature_catalog.csv"
OUT_DIR = "data/model/experiments"
SEED = 20261013
RF_PARAMS = dict(n_estimators=300, min_samples_leaf=10, max_features=0.33, random_state=SEED, n_jobs=1)
GROUP_NAME = {"A": "Chất lượng tài sản", "C": "Vốn", "D": "Động lượng", "E": "Thu nhập & chi phí vốn",
              "G": "Quy mô & tăng trưởng", "K": "Khách hàng số", "L": "Thanh khoản", "M": "Quản trị",
              "P": "Chính sách & cơ cấu tín dụng", "S": "Nhạy cảm thị trường", "T": "Thị trường (cổ phiếu NH)",
              "V": "Vĩ mô", "R": "Lãi suất niêm yết"}
RANK_FROM, MIN_XS = "2019-Q1", 15


# --------------------------------------------------------------------------- du bao
def _core(t: str) -> list[str]:
    return ab.small_features(t) + ["tq"]


def _prepare(f, t, h, per, pos):
    y = f.groupby("ticker")[t].shift(-h) - f[t]
    B = {p: ab.baselines(f, t, h, per, io) for io, p in enumerate(per) if p >= ab.START and io + h < len(per)}
    val = []
    for p, b in B.items():
        if ab.VALID_FROM <= p < ab.TEST_FROM:
            m = f.period == p
            for name in ab.BASELINES:
                val.append((name, np.nanmean(np.abs(y[m].to_numpy() - b[name].reindex(f.ticker[m]).to_numpy()))))
    best = pd.DataFrame(val, columns=["m", "e"]).groupby("m").e.mean().dropna().idxmin()
    base = pd.Series(np.nan, index=f.index)
    for p, b in B.items():
        m = f.period == p
        base[m] = b[best].reindex(f.ticker[m]).to_numpy()
    origins = [p for p in per if p >= ab.TEST_FROM and pos[p] + h < len(per)]
    return y.to_numpy(), base.to_numpy(), best, origins


def _run_config(X, y, base, pidx, origins_idx, h, name, meta):
    from sklearn.ensemble import RandomForestRegressor

    out = []
    resid = y - base
    for io in origins_idx:
        tr = (pidx <= io - h) & ~np.isnan(resid)
        te = (pidx == io) & ~np.isnan(y) & ~np.isnan(base)
        if tr.sum() < 40 or not te.any():
            continue
        if X.shape[1] == 0:
            pred = base[te]
        else:
            rf = RandomForestRegressor(**RF_PARAMS).fit(X[tr], resid[tr])
            pred = base[te] + rf.predict(X[te])
        out.append(pd.DataFrame({**meta, "config": name, "origin_idx": io, "row": np.flatnonzero(te),
                                 "y_true": y[te], "y_pred": pred}))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def forecast(f, groups):
    from joblib import Parallel, delayed

    per = sorted(f.period.unique())
    pos = {p: i for i, p in enumerate(per)}
    pidx = f.period.map(pos).to_numpy()
    jobs, bases = [], {}
    for t in ab.TARGETS:
        core = _core(t)
        gfeat = {g: [c for c in cols if c not in core] for g, cols in groups.items()}
        every = [c for cols in gfeat.values() for c in cols]
        for h in ab.HORIZONS:
            y, base, best, origins = _prepare(f, t, h, per, pos)
            bases[(t, h)] = best
            oi = [pos[p] for p in origins]
            tq = ((f.q + h - 1) % 4 + 1).to_numpy(dtype=float)
            F = f.assign(tq=tq)
            configs = {"base": [], "core": core, "all": core + every}
            for g, cols in gfeat.items():
                if cols:
                    configs[f"core+{g}"] = core + cols
                    configs[f"all-{g}"] = core + [c for c in every if c not in cols]
            meta = {"target": t, "h": h, "base_is": best}
            for name, cols in configs.items():
                X = F[cols].to_numpy(dtype=np.float32) if cols else np.empty((len(F), 0), np.float32)
                jobs.append(delayed(_run_config)(X, y, base, pidx, oi, h, name, meta))
    print(f"  {len(jobs)} cau hinh x goc walk-forward ...", flush=True)
    res = Parallel(n_jobs=-1, verbose=0)(jobs)
    P = pd.concat([r for r in res if len(r)], ignore_index=True)
    P["ticker"] = f.ticker.to_numpy()[P.row]
    P["origin"] = np.array(per)[P.origin_idx]
    P["abs_err"] = (P.y_true - P.y_pred).abs()
    return P.drop(columns=["row", "origin_idx"])


def _gain(w, a, b, idx):
    by = w.groupby(level="ticker")[[a, b]].sum()
    g = 1 - w[a].mean() / w[b].mean()
    bs = [1 - by[a].iloc[i].sum() / by[b].iloc[i].sum() for i in idx]
    return g, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


def summarize_forecast(P, B=2000):
    rng = np.random.default_rng(SEED)
    rows = []
    for (t, h), d in P.groupby(["target", "h"]):
        w = d.pivot_table(index=["origin", "ticker"], columns="config", values="abs_err").dropna()
        idx = [rng.integers(0, w.index.get_level_values("ticker").nunique(), w.index.get_level_values("ticker").nunique())
               for _ in range(B)]
        for c in w.columns:
            ref = "core" if c.startswith("core+") else "all" if c.startswith("all-") else "base"
            r = dict(target=ab.LABEL[t], h=h, config=c, base_is=d.base_is.iloc[0], n=len(w), mae=w[c].mean())
            r["gain_vs_base"], r["lo_vs_base"], r["hi_vs_base"] = _gain(w, c, "base", idx)
            if c.startswith("all-"):  # bo nhom: duong = bo thi tot hon -> nhom vo dung/nhieu
                r["gain_vs_ref"], r["lo_vs_ref"], r["hi_vs_ref"] = _gain(w, c, "all", idx)
            elif c.startswith("core+"):
                r["gain_vs_ref"], r["lo_vs_ref"], r["hi_vs_ref"] = _gain(w, c, "core", idx)
            r["ref"] = ref
            rows.append(r)
    return pd.DataFrame(rows)


def nested(f, groups, min_gain=0.01, max_steps=3):
    from joblib import Parallel, delayed

    per = sorted(f.period.unique())
    pos = {p: i for i, p in enumerate(per)}
    pidx = f.period.map(pos).to_numpy()
    cells = {}
    for t in ab.TARGETS:
        core = _core(t)
        gfeat = {g: [c for c in cols if c not in core] for g, cols in groups.items()}
        for h in ab.HORIZONS:
            y, base, best, origins = _prepare(f, t, h, per, pos)
            val = [pos[p] for p in per if ab.VALID_FROM <= p < ab.TEST_FROM and pos[p] + h < len(per)]
            F = f.assign(tq=((f.q + h - 1) % 4 + 1).astype(float))
            cells[(t, h)] = dict(y=y, base=base, best=best, val=val, test=[pos[p] for p in origins], F=F, core=core,
                                 gfeat=gfeat, chosen=[], mae=None, done=False)

    def job(key, cols, origins, name):
        c = cells[key]
        X = c["F"][cols].to_numpy(dtype=np.float32)
        return delayed(_run_config)(X, c["y"], c["base"], pidx, origins, key[1], name, {"target": key[0], "h": key[1]})

    def mae(df):
        return (df.y_true - df.y_pred).abs().mean() if len(df) else np.inf

    keys = list(cells)
    first = Parallel(n_jobs=-1)(job(k, cells[k]["core"], cells[k]["val"], "core") for k in keys)
    for k, d in zip(keys, first):
        cells[k]["mae"] = mae(d)
    log = []
    for step in range(1, max_steps + 1):
        todo = [(k, g) for k, c in cells.items() if not c["done"] for g, cols in c["gfeat"].items()
                if cols and g not in c["chosen"]]
        if not todo:
            break
        res = Parallel(n_jobs=-1)(job(
            k, cells[k]["core"] + [x for gg in cells[k]["chosen"] + [g] for x in cells[k]["gfeat"][gg]], cells[k]["val"], g)
            for k, g in todo)
        by = {}
        for (k, g), d in zip(todo, res):
            by.setdefault(k, {})[g] = mae(d)
        for k, m in by.items():
            c = cells[k]
            g = min(m, key=m.get)
            gain = 1 - m[g] / c["mae"]
            log.append(dict(target=ab.LABEL[k[0]], h=k[1], step=step, best_group=g, val_gain=gain))
            if gain >= min_gain:
                c["chosen"].append(g)
                c["mae"] = m[g]
            else:
                c["done"] = True
    picked = [k for k, c in cells.items() if c["chosen"]]
    final = Parallel(n_jobs=-1)(job(k, cells[k]["core"] + [x for g in cells[k]["chosen"] for x in cells[k]["gfeat"][g]],
                                    cells[k]["test"], "nested") for k in picked)
    P = pd.concat(final, ignore_index=True) if final else pd.DataFrame()
    if len(P):
        P["ticker"] = f.ticker.to_numpy()[P.row]
        P["origin"] = np.array(per)[P.origin_idx]
        P = P.drop(columns=["row", "origin_idx"])
    chosen = pd.DataFrame([dict(target=ab.LABEL[k[0]], h=k[1], groups="+".join(c["chosen"])) for k, c in cells.items()])
    return P, chosen, pd.DataFrame(log)


def core_ablation(f):
    from joblib import Parallel, delayed

    per = sorted(f.period.unique())
    pos = {p: i for i, p in enumerate(per)}
    pidx = f.period.map(pos).to_numpy()
    drop = {"core_no_refi": lambda c: c.startswith("refi_"),
            "core_no_credit": lambda c: c == "system_credit_growth_asof_pct"}
    jobs = []
    for t in ab.TARGETS:
        for h in ab.HORIZONS:
            y, base, best, origins = _prepare(f, t, h, per, pos)
            F = f.assign(tq=((f.q + h - 1) % 4 + 1).astype(float))
            for name, out in drop.items():
                cols = [c for c in _core(t) if not out(c)]
                jobs.append(delayed(_run_config)(F[cols].to_numpy(np.float32), y, base, pidx, [pos[p] for p in origins], h,
                                                 name, {"target": t, "h": h, "base_is": best}))
    N = pd.concat(Parallel(n_jobs=-1)(jobs), ignore_index=True)
    N["ticker"] = f.ticker.to_numpy()[N.row]
    N["origin"] = np.array(per)[N.origin_idx]
    N["abs_err"] = (N.y_true - N.y_pred).abs()
    return N.drop(columns=["row", "origin_idx"]), list(drop)


# --------------------------------------------------------------------------- xep hang
def _xs_spearman(a: pd.DataFrame, b: pd.DataFrame) -> pd.Series:
    out = {}
    for p in a.index.intersection(b.index):
        d = pd.DataFrame({"a": a.loc[p], "b": b.loc[p]}).dropna()
        if len(d) >= MIN_XS and d.a.nunique() > 2 and d.b.nunique() > 2:
            out[p] = d.a.rank().corr(d.b.rank())
    return pd.Series(out, dtype=float)


def ranking(f, cat):
    per = sorted(f.period.unique())
    use = cat[(cat.kind != "chung mọi NH") & cat.quality.isin(["Giữ", "Giữ cho xếp hạng"])].feature.tolist()
    wide = {c: f.pivot(index="period", columns="ticker", values=c) for c in use + ["npl_percent", "roa_ttm_percent"]}
    fut = {k: wide[c].shift(-4) - wide[c] for k, c in (("npl", "npl_percent"), ("roa", "roa_ttm_percent"))}
    # trung thong tin cat ngang: ma tran Spearman giua cac bien trong tung quy gan nhat, roi trung binh
    mats = []
    for p in per[-8:]:
        snap = f.loc[f.period == p, use]
        snap = snap.loc[:, snap.nunique() > 2]
        mats.append(snap.rank().corr(min_periods=MIN_XS))
    xs = pd.concat(mats).groupby(level=0).mean().reindex(index=use, columns=use)
    rows = []
    for c in use:
        x = wide[c][wide[c].index >= RANK_FROM]
        r = dict(feature=c)
        for k in (1, 4):
            s = _xs_spearman(x, wide[c].shift(-k))
            r[f"persist_{k}q"], r[f"persist_{k}q_n"] = (s.mean(), len(s)) if len(s) else (np.nan, 0)
        for k, dy in fut.items():
            s = _xs_spearman(x, dy)
            n = len(s)
            r[f"fm_d_{k}"], r[f"fm_d_{k}_n"] = (s.mean(), n) if n else (np.nan, 0)
            r[f"fm_d_{k}_t"] = s.mean() / (s.std(ddof=1) / np.sqrt(max(n / 4, 1))) if n >= 8 and s.std() > 0 else np.nan
            r[f"fm_d_{k}_same_sign"] = float((np.sign(s) == np.sign(s.mean())).mean()) if n else np.nan
        other = xs[c].drop(c).dropna()
        best = other.abs().idxmax() if len(other) else ""
        r["xs_partner"], r["xs_partner_rho"] = best, (other[best] if best else np.nan)
        last = wide[c].loc[per[-4:]].ffill().iloc[-1]
        r["banks_latest"] = int(last.notna().sum())
        r["xs_cv_latest"] = float(last.std() / abs(last.mean())) if last.notna().sum() > 2 and last.mean() != 0 else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pd.set_option("display.width", 250)
    os.makedirs(OUT_DIR, exist_ok=True)
    ab.FEATURES = FEATURES
    f = ab.load()
    cat = pd.read_csv(CATALOG, encoding="utf-8-sig")
    if "quality" not in cat:  # catalog truoc 13/10/2026 chua tach tang 1 / tang 3
        cat["quality"] = cat.decision
    keep = cat[cat.quality == "Giữ"]  # do tren tap SACH cua tang 1, khong phai tap da loc theo chinh ket qua nay
    groups = {g: keep.loc[keep.group.str[0] == g, "feature"].tolist() for g in sorted(keep.group.str[0].unique())}
    print("Nhom:", {g: len(v) for g, v in groups.items()})
    steps = set(sys.argv[1:]) or {"forecast", "nested", "core", "ranking"}
    preds = f"{OUT_DIR}/feature_effect_preds.csv"

    if "forecast" in steps:
        print("1. Du bao: them/bo tung nhom ...", flush=True)
        P = forecast(f, groups)
        S = summarize_forecast(P)
        P.to_csv(preds, index=False, encoding="utf-8-sig")
        S.to_csv(f"{OUT_DIR}/feature_effect_forecast.csv", index=False, encoding="utf-8-sig")
        _print_forecast(S)

    if "nested" in steps:
        print("2. Du bao: chon nhom long (kiem dinh 2021-22 -> kiem tra 2023+) ...", flush=True)
        N, chosen, log = nested(f, groups)
        P = pd.read_csv(preds, encoding="utf-8-sig")
        P = P[P.config.isin(["base", "core", "all"])]
        if len(N):
            N = N.merge(P[P.config == "base"][["target", "h", "base_is"]].drop_duplicates(), on=["target", "h"])
            N["abs_err"] = (N.y_true - N.y_pred).abs()
            P = pd.concat([P, N], ignore_index=True)
        rng = np.random.default_rng(SEED)
        rows = []
        for (t, h), d in P.groupby(["target", "h"]):
            w = d.pivot_table(index=["origin", "ticker"], columns="config", values="abs_err").dropna()
            nb = w.index.get_level_values("ticker").nunique()
            idx = [rng.integers(0, nb, nb) for _ in range(2000)]
            r = dict(target=ab.LABEL[t], h=h, base_is=d.base_is.iloc[0])
            r["groups"] = chosen.loc[(chosen.target == ab.LABEL[t]) & (chosen.h == h), "groups"].iloc[0]
            m = "nested" if "nested" in w else "core"  # khong chon them nhom nao -> bo chot chinh la core
            for name, a, b in (("chosen_vs_base", m, "base"), ("chosen_vs_core", m, "core"),
                               ("core_vs_base", "core", "base"), ("all_vs_base", "all", "base")):
                r[name], r[f"{name}_lo"], r[f"{name}_hi"] = _gain(w, a, b, idx)
            rows.append(r)
        out = pd.DataFrame(rows)
        out.to_csv(f"{OUT_DIR}/feature_effect_nested.csv", index=False, encoding="utf-8-sig")
        log.to_csv(f"{OUT_DIR}/feature_effect_nested_steps.csv", index=False, encoding="utf-8-sig")
        show = out.assign(**{c: (out[c] * 100).round(1) for c in out.columns if "_vs_" in c})
        print(show.to_string(index=False))

    if "core" in steps:
        print("3. Du bao: bo tung bien catalog khoi bo loi ...", flush=True)
        N, names = core_ablation(f)
        P = pd.read_csv(preds, encoding="utf-8-sig")
        P = pd.concat([P[P.config.isin(["base", "core"])], N], ignore_index=True)
        rng = np.random.default_rng(SEED)
        rows = []
        for (t, h), d in P.groupby(["target", "h"]):
            w = d.pivot_table(index=["origin", "ticker"], columns="config", values="abs_err").dropna()
            nb = w.index.get_level_values("ticker").nunique()
            idx = [rng.integers(0, nb, nb) for _ in range(2000)]
            r = dict(target=ab.LABEL[t], h=h, base_is=d.base_is.iloc[0])
            r["core_vs_base"], r["core_vs_base_lo"], r["core_vs_base_hi"] = _gain(w, "core", "base", idx)
            for c in names:  # duong = bo loi tot hon khi co bien -> bien co ich
                r[f"core_vs_{c}"], r[f"core_vs_{c}_lo"], r[f"core_vs_{c}_hi"] = _gain(w, "core", c, idx)
            rows.append(r)
        out = pd.DataFrame(rows)
        out.to_csv(f"{OUT_DIR}/feature_effect_core.csv", index=False, encoding="utf-8-sig")
        print(out.assign(**{c: (out[c] * 100).round(1) for c in out.columns if "_vs_" in c}).to_string(index=False))

    if "ranking" in steps:
        print("4. Xep hang ...", flush=True)
        R = ranking(f, cat)
        R = cat[["feature", "group", "kind", "quality", "coverage_pct", "banks_last4q", "icc"]].merge(R, on="feature", how="right")
        R.to_csv(f"{OUT_DIR}/feature_effect_ranking.csv", index=False, encoding="utf-8-sig")


def _print_forecast(S):
    pct = S.assign(**{c: (S[c] * 100).round(1) for c in S.columns if c.startswith(("gain", "lo_", "hi_"))})
    for kind in ("core+", "all-"):
        d = pct[pct.config.str.startswith(kind)].copy()
        d["cell"] = d.target + " h" + d.h.astype(str)
        d["sig"] = np.where(d.lo_vs_ref > 0, "+", np.where(d.hi_vs_ref < 0, "-", "."))
        print(f"\n{kind}<nhom> so voi {'core' if kind == 'core+' else 'all'} (+ tot hon co y nghia, - te hon):")
        print(d.pivot_table(index="config", columns="cell", values="sig", aggfunc="first").to_string())
    print("\nSo voi base:")
    d = pct[pct.config.isin(["core", "all"])]
    print(d.pivot_table(index=["target", "h"], columns="config", values=["gain_vs_base", "lo_vs_base"]).to_string())


if __name__ == "__main__":
    main()
