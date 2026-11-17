from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

FEATURES = "data/model/features_quarterly.csv"
DEPOSIT_DAILY = "data/interest_rates/deposit_daily.csv"
DEPOSIT_24H = "data/interest_rates/deposit_24hmoney_daily.csv"
PROGRAMS = "data/policy_credit/program_participation.csv"
MAS = "data/vnstock_financial/ratio_mas_ttm.csv"
APP_MONTHLY = "data/app_reviews/app_reviews_monthly.csv"
# So quy NIM/COF/loi suat rieng tung quy (MAS). Ban TTM cong 4 quy nen phan ung cham
# hon 2 quy - do tre 3-4 quy do tren TTM phan lon la do cach cong don.
QUARTERLY = ["cof_quarter_percent", "nim_quarter_percent", "earning_asset_yield_quarter_percent"]
# ROE, CIR rieng tung quy (MAS) chi dung cho cau 9
SEASON_MAS = ["roe_quarter_percent", "cir_quarter_percent"]
OUT_DIR = "data/model/eda"
START = "2019-Q1"
SEED = 20260915

CORE = {
    "npl_percent": ("NPL", "A"), "loans_g2_percent": ("Nợ nhóm 2", "A"), "credit_cost_ttm_pct": ("Chi phí tín dụng", "A"),
    "car_asof_percent": ("CAR", "C"), "equity_to_assets_pct": ("Vốn chủ / TTS", "C"),
    "roe_ttm_percent": ("ROE", "E"), "roa_ttm_percent": ("ROA", "E"), "nim_ttm_percent": ("NIM", "E"),
    "cof_ttm_percent": ("Chi phí vốn", "E"), "earning_asset_yield_ttm_percent": ("Lợi suất TSSL", "E"),
    "noii_share_ttm_pct": ("Thu ngoài lãi", "E"), "cir_ttm_pct": ("CIR", "M"),
    "casa_percent": ("CASA", "L"), "ldr_computed_percent": ("LDR", "L"), "liquid_assets_pct": ("TS thanh khoản", "L"),
    "invsec_to_assets_pct": ("CK đầu tư / TTS", "S"), "loans_yoy_percent": ("Tăng trưởng dư nợ", "G"),
    "log_total_assets": ("Quy mô (log TTS)", "G"), "pb": ("P/B", "T"), "app_mean_score": ("Điểm app", "K"),
}
TARGETS = ["nim_ttm_percent", "cof_ttm_percent", "npl_percent", "casa_percent", "ldr_computed_percent", "roe_ttm_percent"]


def spearman(a, b):
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    return (float(d.a.rank().corr(d.b.rank())), len(d)) if len(d) >= 5 else (np.nan, len(d))


def boot_ci(f, fn, rng, B=1000):
    banks = f.ticker.unique()
    vals = []
    for _ in range(B):
        pick = rng.choice(banks, len(banks), replace=True)
        g = pd.concat([f[f.ticker == b].assign(_c=i) for i, b in enumerate(pick)])
        vals.append(fn(g))
    v = np.array([x for x in vals if not np.isnan(x)])
    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) if len(v) > 50 else (np.nan, np.nan)


# --------------------------------------------------------------------------- 1
def variance(f):
    rows = []
    for c, (label, grp) in CORE.items():
        d = f[["ticker", "period", c]].dropna()
        x = d[c] - d[c].mean()
        tot = (x ** 2).sum()
        bank = x.groupby(d.ticker).transform("mean")
        within = x - bank
        quarter = within.groupby(d.period).transform("mean")
        resid = within - quarter
        rows.append(dict(feature=c, label=label, group=grp, n=len(d),
                         bank_share=float((bank ** 2).sum() / tot), quarter_share=float((quarter ** 2).sum() / tot),
                         resid_share=float((resid ** 2).sum() / tot)))
    v = pd.DataFrame(rows)
    s = v[["bank_share", "quarter_share", "resid_share"]].sum(axis=1)
    v[["bank_share", "quarter_share", "resid_share"]] = v[["bank_share", "quarter_share", "resid_share"]].div(s, axis=0)
    return v.sort_values("bank_share", ascending=False)


# --------------------------------------------------------------------------- 2
# casa_r4: CASA trung binh 4 quy cua tung NH. CASA cuoi nam cao hon quy 1 ke tiep (trung vi
# 0,6-2,4 diem o 6/7 nam) nen trung vi tho nhay theo mua vu va che xu huong that.
TREND_COLS = TARGETS + ["casa_r4", "cof_quarter_percent", "car_asof_percent", "loans_yoy_percent", "app_mean_score",
                        "dep12_online_pct"]


def add_derived(f):
    mas = pd.read_csv(MAS, encoding="utf-8-sig")[["ticker", "period"] + QUARTERLY + SEASON_MAS]
    # Giu nguyen thu tu dong: bootstrap theo NH phu thuoc thu tu ticker.unique().
    f = f.merge(mas, on=["ticker", "period"], how="left").reset_index(drop=True)
    if not f.groupby("ticker").period.apply(lambda p: p.is_monotonic_increasing).all():
        raise ValueError("features_quarterly.csv phai xep quy tang dan trong tung NH de tinh CASA 4 quy")
    f["casa_r4"] = f.groupby("ticker").casa_percent.transform(lambda s: s.rolling(4, min_periods=4).mean())
    return f


def casa_seasonality(f):
    w = f.pivot(index="ticker", columns="period", values="casa_percent")
    rows = []
    for y in sorted({int(p[:4]) for p in w.columns}):
        q4, q1 = f"{y}-Q4", f"{y + 1}-Q1"
        if q4 in w and q1 in w:
            d = (w[q4] - w[q1]).dropna()
            rows.append(dict(year=y, n=len(d), median_gap=float(d.median()), share_positive=float((d > 0).mean())))
    return pd.DataFrame(rows)


def trends(f, clusters: pd.Series):
    f = f.assign(cluster=f.ticker.map(clusters))
    out = []
    for c in TREND_COLS:
        q = f.groupby("period")[c].quantile([0.25, 0.5, 0.75]).unstack()
        for p in q.index:
            out.append(dict(feature=c, period=p, group="all", p25=q.loc[p, 0.25], median=q.loc[p, 0.5], p75=q.loc[p, 0.75],
                            n=int(f.loc[f.period == p, c].notna().sum())))
        g = f.groupby(["period", "cluster"])[c].agg(med="median", cnt="count").reset_index()
        for r in g.itertuples():
            out.append(dict(feature=c, period=r.period, group=str(r.cluster), p25=np.nan, median=r.med, p75=np.nan, n=int(r.cnt)))
    macro = f.groupby("period")[["refinancing_rate_pct", "system_credit_growth_asof_pct", "cpi_yoy_q_pct", "vnindex_ret_q_pct"]].first()
    return pd.DataFrame(out), macro.reset_index()


# --------------------------------------------------------------------------- 3
def leadlag(f):
    f = f.sort_values(["ticker", "period"]).copy()
    refi = f.groupby("period").refinancing_rate_pct.first().sort_index()
    d_refi = refi.diff()
    rows = []
    for c in ["cof_ttm_percent", "nim_ttm_percent", "earning_asset_yield_ttm_percent", "dep12_online_pct"] + QUARTERLY:
        dy = f.groupby("ticker")[c].diff()
        for k in range(0, 7):
            x = f.period.map(d_refi.shift(k))
            rho, n = spearman(x, dy)
            med = dy.groupby(f.period).median()
            r_med, n_med = spearman(d_refi.shift(k).reindex(med.index), med)
            rows.append(dict(feature=c, lag=k, rho_panel=rho, n_panel=n, rho_median=r_med, n_quarters=n_med))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- 4
def demean_two_way(f, cols):
    d = f[cols] - f.groupby("ticker")[cols].transform("mean")
    return d - d.groupby(f.period).transform("mean")


def correlation(f, rng):
    cols = list(CORE)
    means = f.groupby("ticker")[cols].mean()
    dem = demean_two_way(f, cols)
    between = means.rank().corr()
    within = dem.rank().corr()
    pairs = []
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            pairs.append(dict(a=a, b=b, between=float(between.loc[a, b]), within=float(within.loc[a, b])))
    P = pd.DataFrame(pairs)
    P["gap"] = P.between - P.within
    return between, within, P


# --------------------------------------------------------------------------- 5
SNAP_COLS = ["npl_percent", "loans_g2_percent", "credit_cost_ttm_pct", "car_asof_percent", "equity_to_assets_pct", "roa_ttm_percent",
             "nim_ttm_percent", "cof_ttm_percent", "cir_ttm_pct", "casa_percent", "ldr_computed_percent", "liquid_assets_pct",
             "log_total_assets", "loans_yoy_percent"]


def snapshot(f, upto=None):
    periods = sorted(p for p in f.period.unique() if upto is None or p <= upto)
    last4 = periods[-4:]
    recent = f[f.period.isin(last4)].sort_values("period")
    num = recent.select_dtypes("number").columns
    s = recent.groupby("ticker")[num].agg("last")
    return s, last4


def _standardize(snap):
    X = snap[SNAP_COLS].copy()
    X = X.fillna(X.median())
    return (X - X.mean()) / X.std()


def _kmeans(Z, seed=SEED, n_init=50):
    from sklearn.cluster import KMeans
    return KMeans(n_clusters=3, n_init=n_init, random_state=seed).fit(Z)


def _align(labels, reference):
    from itertools import permutations
    best, best_hit = labels, -1
    for perm in permutations(range(3)):
        mapped = labels.map(dict(enumerate(perm)))
        hit = int((mapped == reference).sum())
        if hit > best_hit:
            best, best_hit = mapped, hit
    return best


def group_stability(f, current, rng, B=300):
    from sklearn.metrics import silhouette_score
    periods = sorted(f.period.unique())[-4:]
    same = pd.Series(0, index=current.index)
    for q in periods:
        s, _ = snapshot(f, upto=q)
        lab = pd.Series(_kmeans(_standardize(s)).labels_, index=s.index).reindex(current.index)
        same += (_align(lab, current) == current).astype(int)
    Z = _standardize(snapshot(f)[0]).reindex(current.index)
    agree = pd.Series(0.0, index=current.index)
    for b in range(B):
        idx = rng.choice(len(Z), len(Z), replace=True)
        km = _kmeans(Z.iloc[idx], seed=int(rng.integers(1_000_000)), n_init=10)
        lab = pd.Series(km.predict(Z), index=Z.index)
        agree += (_align(lab, current) == current).astype(float)
    out = pd.DataFrame({"cluster": current, "quarters_same": same, "quarters": len(periods), "boot_agree": agree / B})
    out["stable"] = (out.quarters_same >= 3) & (out.boot_agree >= 0.5)
    return out, float(silhouette_score(Z, current))


def groups(snap):
    Z = _standardize(snap)
    U, S, Vt = np.linalg.svd(Z.to_numpy(), full_matrices=False)
    expl = S ** 2 / (S ** 2).sum()
    pcs = pd.DataFrame(U[:, :3] * S[:3], index=Z.index, columns=["pc1", "pc2", "pc3"])
    load = pd.DataFrame(Vt[:3].T, index=SNAP_COLS, columns=["pc1", "pc2", "pc3"])
    # huong PC1 sao cho quy mo duong
    for k in ["pc1", "pc2"]:
        if load.loc["log_total_assets", k] < 0 and k == "pc1":
            pcs[k] *= -1
            load[k] *= -1
    if load.loc["npl_percent", "pc2"] > 0:
        pcs["pc2"] *= -1
        load["pc2"] *= -1
    km = _kmeans(Z)
    pcs["cluster"] = km.labels_
    prof = snap.assign(cluster=km.labels_).groupby("cluster")[SNAP_COLS].median()
    return pcs, load, expl[:5], prof


# --------------------------------------------------------------------------- 6
def deposit_today(snap, rng):
    from crawlers import deposit_tiers
    d = deposit_tiers.read(DEPOSIT_24H)
    d = d[d.ticker.notna()]
    latest = d.date.max()
    t = d[(d.date == latest) & (d.term_months == 12)].groupby(["ticker", "channel"]).rate_percent.mean().unstack()
    t.columns = [f"rate12_{c}" for c in t.columns]
    dd = pd.read_csv(DEPOSIT_DAILY, encoding="utf-8-sig")
    dd = dd[dd.ticker.notna() & (dd.date == dd.date.max()) & (dd.term_months == 12) & (dd.channel == "online")]
    t = t.join(dd.groupby("ticker").rate_percent.mean().rename("rate12_online_check"), how="left")
    j = snap.join(t, how="left")
    j["rate_date"] = latest
    rate = "rate12_online"
    rows = []
    for c in ["log_total_assets", "casa_percent", "cof_ttm_percent", "npl_percent", "car_asof_percent", "equity_to_assets_pct",
              "roa_ttm_percent", "ldr_computed_percent", "state_own_percent", "app_mean_score"]:
        rho, n = spearman(j[rate], j[c])
        bs = []
        idx = j.index.to_numpy()
        for _ in range(2000):
            p = rng.choice(idx, len(idx), replace=True)
            r, _n = spearman(j.loc[p, rate].to_numpy(), j.loc[p, c].to_numpy())
            bs.append(r)
        bs = np.array([b for b in bs if not np.isnan(b)])
        rows.append(dict(feature=c, rho=rho, n=n, lo=float(np.percentile(bs, 2.5)), hi=float(np.percentile(bs, 97.5))))
    return j, pd.DataFrame(rows), latest, int(j[rate].notna().sum())


# --------------------------------------------------------------------------- 7
def app_links(f, rng):
    rows = []
    for c in ["roe_ttm_percent", "casa_percent", "cof_ttm_percent", "npl_percent", "log_total_assets", "cir_ttm_pct", "loans_yoy_percent"]:
        means = f.groupby("ticker")[["app_mean_score", c]].mean()
        rb, nb = spearman(means.app_mean_score, means[c])
        dem = demean_two_way(f, ["app_mean_score", c])
        rw, nw = spearman(dem.app_mean_score, dem[c])

        def within(g, c=c):
            d = g[["app_mean_score", c]] - g.groupby("_c")[["app_mean_score", c]].transform("mean")
            d = d - d.groupby(g.period).transform("mean")
            return spearman(d.app_mean_score, d[c])[0]
        lo, hi = boot_ci(f[["ticker", "period", "app_mean_score", c]], within, rng, B=400)
        blo, bhi = boot_ci(f[["ticker", "app_mean_score", c]], lambda g, c=c: spearman(
            g.groupby("_c").app_mean_score.mean(), g.groupby("_c")[c].mean())[0], rng, B=400)
        rows.append(dict(feature=c, rho_between=rb, n_banks=nb, between_lo=blo, between_hi=bhi,
                         rho_within=rw, n_within=nw, within_lo=lo, within_hi=hi))
    return pd.DataFrame(rows)


def app_monthly():
    a = pd.read_csv(APP_MONTHLY, encoding="utf-8-sig")
    a = a[a.month >= "2019-01"].assign(ws=lambda d: d.mean_score * d.n_reviews, w1=lambda d: d.pct_1star * d.n_reviews)
    g = a.groupby("month").agg(n_reviews=("n_reviews", "sum"), ws=("ws", "sum"), w1=("w1", "sum"), n_banks=("ticker", "nunique"))
    g["mean_score"] = g.ws / g.n_reviews
    g["pct_1star"] = 100 * g.w1 / g.n_reviews
    wide = a[a.n_reviews >= 30].pivot(index="ticker", columns="month", values="mean_score")
    events = []
    for m0, m1, label in (("2024-06", "2024-07", "QĐ 2345/QĐ-NHNN"), ("2024-12", "2025-01", "TT 17/2024/TT-NHNN")):
        d = (wide[m1] - wide[m0]).dropna()
        events.append(dict(month=m1, label=label, before=float(g.loc[m0, "mean_score"]), after=float(g.loc[m1, "mean_score"]),
                           pct1_before=float(g.loc[m0, "pct_1star"]), pct1_after=float(g.loc[m1, "pct_1star"]),
                           banks=len(d), share_down=float((d < 0).mean()), median_bank_change=float(d.median())))
    return g[["n_reviews", "n_banks", "mean_score", "pct_1star"]], pd.DataFrame(events)


# --------------------------------------------------------------------------- 8
def policy(f):
    pp = pd.read_csv(PROGRAMS, encoding="utf-8-sig")
    agri_prog = pp[pp.program_code.isin(["LTS_15K", "NLTS_100K", "NLTS_185K"])].groupby("ticker").participates.max()
    last = f[f.period.str.startswith("2025")].groupby("ticker").agri_share_asof_pct.mean()
    a = pd.DataFrame({"agri_share": last, "agri_program": agri_prog}).dropna()
    # Yagi: phoi nhiem chi nhanh (2024-Q4) vs thay doi NPL 2024-Q2 -> 2025-Q2
    npl = f.pivot(index="ticker", columns="period", values="npl_percent")
    expo = f[f.period == "2024-Q4"].set_index("ticker").disaster_branch_share_pct
    y = pd.DataFrame({"exposure": expo, "npl_change": npl["2025-Q2"] - npl["2024-Q2"],
                      "npl_before": npl["2024-Q2"]}).dropna()
    return a, y


# --------------------------------------------------------------------------- 9
# Bien "muc" (so du cuoi quy) xet thay doi so voi quy truoc; bien "dong" (so rieng tung quy) xet muc da tru
# trung binh NH. TTM khong dua vao: cong 4 quy nen mua vu tu triet tieu.
SEASON = {
    "npl_percent": ("NPL", "level"), "loans_g2_percent": ("Nợ nhóm 2", "level"),
    "casa_percent": ("CASA", "level"), "ldr_computed_percent": ("LDR", "level"),
    "loans_qoq_percent": ("Tăng trưởng dư nợ trong quý", "flow"), "cir_quarter_percent": ("CIR quý", "flow"),
    "roe_quarter_percent": ("ROE quý", "flow"), "cof_quarter_percent": ("Chi phí vốn quý", "flow"),
}
SEASON_TEST = ["npl_percent", "loans_g2_percent", "casa_percent", "ldr_computed_percent"]
SEASON_FROM = "2023-Q1"  # goc du bao dau tien, giong backtest naive vs AR(1) ngay 10/09


def _season_z(f, col, kind):
    g = f.groupby("ticker")[col]
    z = g.diff() if kind == "level" else f[col] - g.transform("mean")
    lo, hi = z.quantile([0.01, 0.99])
    return z.clip(lo, hi)


def seasonality(f):
    from scipy import stats
    rows, prof, years = [], [], []
    for col, (label, kind) in SEASON.items():
        d = pd.DataFrame({"ticker": f.ticker, "period": f.period, "z": _season_z(f, col, kind)}).dropna()
        d["q"] = d.period.str[-1].astype(int)
        d["year"] = d.period.str[:4].astype(int)
        m = d.z.mean()
        mq = d.groupby("q").z.transform("mean")
        mt = d.groupby("period").z.transform("mean")
        ss_q, ss_t, ss_w = ((mq - m) ** 2).sum(), ((mt - mq) ** 2).sum(), ((d.z - mt) ** 2).sum()
        tot = ss_q + ss_t + ss_w
        T = d.period.nunique()
        F = (ss_q / 3) / (ss_t / (T - 4))
        pm = d.groupby(["period", "year", "q"]).z.mean().reset_index()
        kw = stats.kruskal(*[pm.z[pm.q == k] for k in range(1, 5)]).pvalue
        eff = d.groupby("q").z.mean() - m
        peak = int(eff.abs().idxmax())
        pm["dev"] = pm.z - pm.groupby("year").z.transform("mean")
        full = pm.groupby("year").q.transform("count") >= 3
        pk = pm[full & (pm.q == peak)]
        rows.append(dict(feature=col, label=label, kind=kind, n=len(d), n_periods=T, share_season=ss_q / tot,
                         share_common=ss_t / tot, share_bank=ss_w / tot, F=F, p_F=float(stats.f.sf(F, 3, T - 4)), p_kw=float(kw),
                         peak_q=peak, peak_effect=float(eff[peak]), years_same=int((np.sign(pk.dev) == np.sign(eff[peak])).sum()),
                         years=len(pk)))
        for k in range(1, 5):
            z = d.z[d.q == k]
            prof.append(dict(feature=col, q=k, effect=float(eff[k]), median=float(z.median()), share_pos=float((z > 0).mean()),
                             share_neg=float((z < 0).mean()), n=len(z)))
        years += [dict(feature=col, year=int(r.year), q=int(r.q), dev=float(r.dev)) for r in pm[full].itertuples()]
    return pd.DataFrame(rows), pd.DataFrame(prof), pd.DataFrame(years)


def seasonal_naive(f, rng, B=2000):
    per = sorted(f.period.unique())
    qn = {p: int(p[-1]) for p in per}
    rows = []
    for col in SEASON_TEST:
        w = f.pivot(index="ticker", columns="period", values=col).reindex(columns=per)
        dz = w.diff(axis=1)
        for h in (1, 2, 3):
            err = []
            for i, p in enumerate(per):
                if p < SEASON_FROM or i + h >= len(per):
                    continue
                known = dz[per[1:i + 1]]
                med = {k: np.nanmedian(known[[c for c in known.columns if qn[c] == k]].to_numpy()) for k in range(1, 5)}
                adj = sum(med[qn[per[i + j]]] for j in range(1, h + 1))
                drift = h * np.nanmedian(known.to_numpy())
                y0, yh = w[p], w[per[i + h]]
                ok = y0.notna() & yh.notna()
                e = (yh - y0)[ok].to_numpy()
                err.append(pd.DataFrame({"ticker": w.index[ok], "naive": np.abs(e), "drift": np.abs(e - drift), "season": np.abs(e - adj)}))
            E = pd.concat(err)
            by = E.groupby("ticker")[["naive", "drift", "season"]].sum()
            boot = []
            for _ in range(B):
                s = by.iloc[rng.integers(0, len(by), len(by))].sum()
                boot.append((1 - s.season / s.naive, 1 - s.drift / s.naive, 1 - s.season / s.drift))
            lo, hi = np.percentile(boot, [2.5, 97.5], axis=0)
            mae = E[["naive", "drift", "season"]].mean()
            rows.append(dict(feature=col, label=SEASON[col][0], h=h, n=len(E), mae_naive=mae.naive, mae_drift=mae.drift,
                             mae_season=mae.season, gain=1 - mae.season / mae.naive, lo=lo[0], hi=hi[0],
                             gain_drift=1 - mae.drift / mae.naive, drift_lo=lo[1], drift_hi=hi[1],
                             gain_vs_drift=1 - mae.season / mae.drift, vs_drift_lo=lo[2], vs_drift_hi=hi[2]))
    return pd.DataFrame(rows)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pd.set_option("display.width", 220)
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(SEED)
    f = pd.read_csv(FEATURES, encoding="utf-8-sig")
    f = add_derived(f[f.period >= START])

    v = variance(f)
    snap, last4 = snapshot(f)
    pcs, load, expl, prof = groups(snap)
    # rng rieng: khong lam xe dich cac khoang tin cay bootstrap khac cua EDA
    stab, silhouette = group_stability(f, pcs.cluster, np.random.default_rng(SEED + 5))
    tr, macro = trends(f, pcs.cluster)
    ll = leadlag(f)
    between, within, P = correlation(f, rng)
    dep, dep_corr, dep_date, dep_banks = deposit_today(snap, rng)
    app = app_links(f, rng)
    app_m, app_events = app_monthly()
    season = casa_seasonality(f)
    agri, yagi = policy(f)
    s_anova, s_prof, s_years = seasonality(f)
    s_fc = seasonal_naive(f, np.random.default_rng(SEED + 9))

    for name, df in [("variance", v), ("trends", tr), ("macro", macro), ("leadlag", ll), ("corr_pairs", P), ("pca_banks", pcs),
                     ("pca_loadings", load), ("cluster_profile", prof), ("cluster_stability", stab),
                     ("pca_explained", pd.DataFrame({"component": [f"pc{i + 1}" for i in range(len(expl))], "share": expl,
                                                     "silhouette_k3": silhouette})), ("deposit_today", dep), ("deposit_corr", dep_corr),
                     ("app_links", app), ("app_monthly", app_m), ("app_events", app_events), ("casa_seasonality", season),
                     ("policy_agri", agri), ("policy_yagi", yagi), ("season_anova", s_anova), ("season_profile", s_prof),
                     ("season_years", s_years), ("season_forecast", s_fc)]:
        df.to_csv(f"{OUT_DIR}/{name}.csv", encoding="utf-8-sig")

    print("1. PHUONG SAI:\n", v.round(3).to_string(index=False))
    print("\n3. LEAD-LAG thay doi lai suat tai cap von -> thay doi chi so:\n",
          ll.pivot_table(index="lag", columns="feature", values=["rho_panel", "rho_median"]).round(2).to_string())
    print("\n4. CAP TUONG QUAN GIUA NH MANH NHAT:\n", P.reindex(P.between.abs().sort_values(ascending=False).index).head(14).round(2).to_string(index=False))
    print("   CHENH GIUA vs TRONG lon nhat:\n", P.reindex(P.gap.abs().sort_values(ascending=False).index).head(8).round(2).to_string(index=False))
    refi = macro.set_index("period").refinancing_rate_pct
    print("   so quy lai suat tai cap von thay doi:", int((refi.diff().fillna(0) != 0).sum()), refi[refi.diff().fillna(0) != 0].to_dict())
    print("\n5. PCA: ty le giai thich", np.round(expl, 3), "\n", load.round(2).to_string())
    print(pcs.round(2).sort_values("cluster").to_string())
    print(prof.round(2).T.to_string())
    print(f"   silhouette k=3: {silhouette:.3f}; nhom chua on dinh:",
          stab[~stab.stable].round(2).to_dict("index"))
    print(f"\n6. LAI SUAT 12T NGAY {dep_date} ({dep_banks} NH):\n", dep.filter(like="rate12").sort_values("rate12_online").T.round(2).to_string())
    print(dep_corr.round(2).to_string(index=False))
    print("   theo nhom:", dep.assign(cluster=pcs.cluster).groupby("cluster").rate12_online.describe().round(2).to_string())
    ck = dep[["rate12_online", "rate12_online_check"]].dropna()
    print("   doi chieu deposit_daily:", len(ck), "NH, lech TB", round(float((ck.rate12_online - ck.rate12_online_check).abs().mean()), 3))
    print("\n7. APP vs TAI CHINH:\n", app.round(2).to_string(index=False))
    print("   diem roi theo quy dinh:\n", app_events.round(2).to_string(index=False))
    print("   CASA quy 4 - quy 1 nam sau:\n", season.round(2).to_string(index=False))
    print("\n8. CHINH SACH:\n", agri.groupby("agri_program").agri_share.describe().round(2).to_string())
    print("   Yagi:", spearman(yagi.exposure, yagi.npl_change), yagi.round(2).sort_values("exposure").to_string())
    print("\n9. MUA VU (ANOVA long nhau, don vi = quy):\n", s_anova.drop(columns="feature").round(3).to_string(index=False))
    print("   ho so theo quy:\n", s_prof.pivot(index="feature", columns="q", values="effect").round(3).to_string())
    print("   naive co mua vu vs naive:\n", s_fc.drop(columns="feature").round(3).to_string(index=False))
    print("\nkhoang:", last4)
    print("trend median dau/cuoi:", tr.groupby("feature").apply(lambda g: (round(g.dropna(subset=['median'])['median'].iloc[0], 2), round(g.dropna(subset=['median'])['median'].iloc[-1], 2))).to_dict())


if __name__ == "__main__":
    main()
