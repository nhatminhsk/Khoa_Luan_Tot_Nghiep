"""Gom ket qua data/model/eda/*.csv thanh JSON va nhung vao trang bao cao EDA."""
import json
import os
import sys

import numpy as np
import pandas as pd

os.chdir(r"D:\KLTN")
sys.path.insert(0, r"D:\KLTN")
from experiments.eda import CORE  # noqa: E402

OUT = sys.argv[1]
E = "data/model/eda"
rd = lambda n, **k: pd.read_csv(f"{E}/{n}.csv", encoding="utf-8-sig", **k)  # noqa: E731


def num(x, d=3):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), d)


def vi(x, d=1, sign=False):
    """So kieu Viet: dau phay thap phan, dau tru that."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    s = f"{abs(x):,.{d}f}".replace(",", " ").replace(".", ",")
    return ("−" if x < 0 else ("+" if sign and x > 0 else "")) + s


pcs = rd("pca_banks", index_col=0)
# dat ten nhom theo thanh vien, khong theo so hieu k-means
cid = {int(pcs.loc["VCB", "cluster"]): 0, int(pcs.loc["VPB", "cluster"]): 2}
cid[next(c for c in range(3) if c not in cid)] = 1
# Ten theo ho so nhom tren anh chup HIEN TAI (so gan nhat, 16/09/2026). Ten la nhan dinh, nen
# kiem lai ho so moi lan dung lai trang: neu ho so khong con khop ten thi in canh bao.
GROUP_NAMES = ["Lớn, vốn rẻ, nợ xấu thấp", "Vốn đắt, sinh lời thấp", "Tăng trưởng nhanh, biên cao"]
pcs["g"] = pcs.cluster.map(cid)
stab = rd("cluster_stability", index_col=0)
pcs = pcs.join(stab[["quarters_same", "quarters", "boot_agree", "stable"]])
pex = rd("pca_explained", index_col=0).set_index("component")

v = rd("variance", index_col=0)
variance = [dict(label=r.label, group=r.group, bank=num(r.bank_share), quarter=num(r.quarter_share), resid=num(r.resid_share))
            for r in v.itertuples()]

t = rd("trends", index_col=0)
periods = sorted(t.period.unique())
PANELS = [("nim_ttm_percent", "NIM", "%"), ("cof_ttm_percent", "Chi phí vốn", "%"), ("npl_percent", "Nợ xấu (NPL)", "%"),
          ("casa_r4", "CASA (trung bình 4 quý)", "%"), ("ldr_computed_percent", "Dư nợ / tiền gửi (LDR)", "%"),
          ("roe_ttm_percent", "ROE", "%")]
trends = []
for f, label, unit in PANELS:
    a = t[(t.feature == f) & (t.group == "all")].set_index("period").reindex(periods)
    groups = {}
    for raw, gi in cid.items():
        s = t[(t.feature == f) & (t.group == str(raw))].set_index("period").reindex(periods)["median"]
        groups[gi] = [num(x) for x in s]
    trends.append(dict(key=f, label=label, unit=unit, median=[num(x) for x in a["median"]], p25=[num(x) for x in a.p25],
                       p75=[num(x) for x in a.p75], groups=[groups[0], groups[1], groups[2]]))
macro = rd("macro", index_col=0).set_index("period").reindex(periods)
dep = t[(t.feature == "dep12_online_pct") & (t.group == "all")].set_index("period").reindex(periods)
context = [dict(key="refi", label="Lãi suất tái cấp vốn NHNN", unit="%", median=[num(x) for x in macro.refinancing_rate_pct]),
           dict(key="dep12", label="Lãi suất tiết kiệm 12 tháng niêm yết (trung vị)", unit="%", median=[num(x) for x in dep["median"]],
                p25=[num(x) for x in dep.p25], p75=[num(x) for x in dep.p75])]

ll = rd("leadlag", index_col=0)
LL = {"quarter": [("cof_quarter_percent", "Chi phí vốn"), ("nim_quarter_percent", "NIM"),
                  ("earning_asset_yield_quarter_percent", "Lợi suất tài sản sinh lãi")],
      "ttm": [("cof_ttm_percent", "Chi phí vốn"), ("nim_ttm_percent", "NIM"), ("earning_asset_yield_ttm_percent", "Lợi suất tài sản sinh lãi")]}
leadlag = dict(lags=sorted(ll.lag.unique().tolist()),
               **{mode: [dict(label=lab, values=[num(x, 2) for x in ll[ll.feature == k].sort_values("lag").rho_panel],
                              n=[int(x) for x in ll[ll.feature == k].sort_values("lag").n_panel]) for k, lab in items]
                  for mode, items in LL.items()})

P = rd("corr_pairs", index_col=0)
lab = {k: v[0] for k, v in CORE.items()}
KEY = {("cof_ttm_percent", "casa_percent"), ("nim_ttm_percent", "loans_yoy_percent"), ("roa_ttm_percent", "nim_ttm_percent"),
       ("roe_ttm_percent", "roa_ttm_percent"), ("roa_ttm_percent", "cir_ttm_pct"), ("casa_percent", "log_total_assets"),
       ("cir_ttm_pct", "log_total_assets")}
pairs = [dict(a=lab[r.a], b=lab[r.b], between=num(r.between, 2), within=num(r.within, 2), key=(r.a, r.b) in KEY)
         for r in P.itertuples()]
cols = list(CORE)
Mb = np.eye(len(cols))
Mw = np.eye(len(cols))
idx = {c: i for i, c in enumerate(cols)}
for r in P.itertuples():
    i, j = idx[r.a], idx[r.b]
    Mb[i, j] = Mb[j, i] = r.between
    Mw[i, j] = Mw[j, i] = r.within
corr = dict(labels=[lab[c] for c in cols], groups=[CORE[c][1] for c in cols],
            between=[[num(x, 2) for x in row] for row in Mb], within=[[num(x, 2) for x in row] for row in Mw])

load = rd("pca_loadings", index_col=0)
prof = rd("cluster_profile", index_col=0)
PROF = [("npl_percent", "NPL", 2), ("loans_g2_percent", "Nợ nhóm 2", 2), ("credit_cost_ttm_pct", "Chi phí tín dụng", 2),
        ("car_asof_percent", "CAR", 1), ("roa_ttm_percent", "ROA", 2), ("nim_ttm_percent", "NIM", 2), ("cof_ttm_percent", "Chi phí vốn", 2),
        ("cir_ttm_pct", "CIR", 1), ("casa_percent", "CASA", 1), ("ldr_computed_percent", "LDR", 1), ("loans_yoy_percent", "Tăng trưởng dư nợ", 1)]
profile = []
for key, label, d in PROF:
    profile.append(dict(label=label, values=[num(prof.loc[raw, key], d) for raw in sorted(cid, key=lambda r: cid[r])]))
explained = rd("pca_loadings", index_col=0)  # placeholder de doc kich thuoc
gp = prof.rename(index=cid).sort_index()
checks = {
    "nhom 0 NPL thap nhat": gp.npl_percent.idxmin() == 0,
    "nhom 0 CASA cao nhat": gp.casa_percent.idxmax() == 0,
    "nhom 1 ROA thap nhat": gp.roa_ttm_percent.idxmin() == 1,
    "nhom 1 chi phi von cao hon nhom 0": gp.loc[1, "cof_ttm_percent"] > gp.loc[0, "cof_ttm_percent"],
    "nhom 2 tang truong du no cao nhat": gp.loans_yoy_percent.idxmax() == 2,
}
for name, ok in checks.items():
    if not ok:
        print(f"CANH BAO: ten nhom khong con khop ho so ({name}) - xem lai GROUP_NAMES")

groups = dict(
    names=GROUP_NAMES,
    counts=[int((pcs.g == i).sum()) for i in range(3)],
    explained=[num(pex.loc["pc1", "share"] * 100, 1), num(pex.loc["pc2", "share"] * 100, 1)],
    banks=[dict(t=tk, x=num(r.pc1, 2), y=num(r.pc2, 2), g=int(r.g), stable=bool(r.stable),
                qs=int(r.quarters_same), q=int(r.quarters), boot=num(r.boot_agree, 2)) for tk, r in pcs.iterrows()],
    profile=profile,
    pc1_top=[dict(label=lab.get(k, k), w=num(load.loc[k, "pc1"], 2)) for k in load.pc1.abs().sort_values(ascending=False).index[:5]],
    pc2_top=[dict(label=lab.get(k, k), w=num(load.loc[k, "pc2"], 2)) for k in load.pc2.abs().sort_values(ascending=False).index[:5]],
)

dt = rd("deposit_today", index_col=0)
dc = rd("deposit_corr", index_col=0)
DLAB = dict(lab, state_own_percent="Sở hữu nhà nước", app_mean_score="Điểm app")
deposit = dict(
    banks=sorted([dict(t=tk, online=num(r.rate12_online, 2), counter=num(r.rate12_quay, 2), g=int(pcs.loc[tk, "g"]))
                  for tk, r in dt.iterrows()], key=lambda b: (b["online"] is None, b["online"])),
    corr=[dict(label=DLAB.get(r.feature, r.feature), rho=num(r.rho, 2), lo=num(r.lo, 2), hi=num(r.hi, 2), n=int(r.n)) for r in dc.itertuples()],
)

ap = rd("app_links", index_col=0)
app = [dict(label=lab.get(r.feature, r.feature), between=num(r.rho_between, 2), blo=num(r.between_lo, 2), bhi=num(r.between_hi, 2),
            within=num(r.rho_within, 2), wlo=num(r.within_lo, 2), whi=num(r.within_hi, 2)) for r in ap.itertuples()]

am = rd("app_monthly", index_col=0)
ev = rd("app_events", index_col=0)
app_monthly = dict(
    months=am.index.tolist(), score=[num(x, 2) for x in am.mean_score], pct1=[num(x, 1) for x in am.pct_1star],
    reviews=[int(x) for x in am.n_reviews], banks=[int(x) for x in am.n_banks],
    events=[dict(month=r.month, label=r.label, before=num(r.before, 2), after=num(r.after, 2), pct1_before=num(r.pct1_before, 1),
                 pct1_after=num(r.pct1_after, 1), share_down=num(r.share_down, 2), banks=int(r.banks)) for r in ev.itertuples()],
)

ag = rd("policy_agri", index_col=0)
yg = rd("policy_yagi", index_col=0)
policy = dict(
    agri=[dict(t=tk, share=num(r.agri_share, 2), program=int(r.agri_program)) for tk, r in ag.iterrows()],
    yagi=[dict(t=tk, x=num(r.exposure, 1), y=num(r.npl_change, 2), before=num(r.npl_before, 2)) for tk, r in yg.iterrows()],
)
yx = yg.drop(index="NVB")
policy["yagi_rho_ex_nvb"] = num(yx.exposure.rank().corr(yx.npl_change.rank()), 2)

# ---------- 9. mua vu
sa = rd("season_anova", index_col=0).set_index("feature")
sp = rd("season_profile", index_col=0)
sy = rd("season_years", index_col=0)
sf = rd("season_forecast", index_col=0)
season = dict(
    vars=[dict(key=k, label=r.label, kind=r.kind, season=num(r.share_season), common=num(r.share_common), bank=num(r.share_bank),
               F=num(r.F, 2), p=num(r.p_F, 4), p_kw=num(r.p_kw, 4), T=int(r.n_periods), peak=int(r.peak_q), years_same=int(r.years_same),
               years=int(r.years),
               effect=[num(x, 3) for x in sp[sp.feature == k].sort_values("q").effect],
               share_neg=[num(x, 3) for x in sp[sp.feature == k].sort_values("q").share_neg],
               share_pos=[num(x, 3) for x in sp[sp.feature == k].sort_values("q").share_pos],
               dots=[[dict(y=int(d.year), v=num(d.dev, 3)) for d in sy[(sy.feature == k) & (sy.q == q)].itertuples()] for q in range(1, 5)])
          for k, r in sa.iterrows()],
    forecast=[dict(label=r.label, h=int(r.h), n=int(r.n), mae_naive=num(r.mae_naive), mae_drift=num(r.mae_drift), mae_season=num(r.mae_season),
                   gain=num(r.gain), lo=num(r.lo), hi=num(r.hi), vs_drift=num(r.gain_vs_drift), vd_lo=num(r.vs_drift_lo),
                   vd_hi=num(r.vs_drift_hi)) for r in sf.itertuples()],
)
# Loi van cau 9 viet cho mau hinh hien tai; chay lai voi du lieu moi ma mau hinh doi thi canh bao.
fc1 = sf[sf.h == 1].set_index("feature")
s_checks = {
    "NPL dinh o quy 4 va co y nghia": sa.loc["npl_percent", "peak_q"] == 4 and sa.loc["npl_percent", "p_F"] < 0.05,
    "CASA dinh o quy 1 va co y nghia": sa.loc["casa_percent", "peak_q"] == 1 and sa.loc["casa_percent", "p_F"] < 0.05,
    "tang truong du no dinh o quy 4": sa.loc["loans_qoq_percent", "peak_q"] == 4 and sa.loc["loans_qoq_percent", "p_F"] < 0.05,
    "LDR, CIR, ROE, chi phi von khong co mua vu": bool((sa.loc[["ldr_computed_percent", "cir_quarter_percent", "roe_quarter_percent",
                                                                  "cof_quarter_percent"], "p_F"] >= 0.05).all()),
    "NPL, CASA thang drift (KTC > 0)": bool((fc1.loc[["npl_percent", "casa_percent"], "vs_drift_lo"] > 0).all()),
    "LDR khong thang drift": fc1.loc["ldr_computed_percent", "vs_drift_lo"] <= 0 <= fc1.loc["ldr_computed_percent", "vs_drift_hi"],
}
for name, ok in s_checks.items():
    if not ok:
        print(f"CANH BAO: loi van cau 9 khong con khop du lieu ({name}) - xem lai eda_template.html")


def pv(x):
    return "< 0,001" if x < 0.001 else "= " + vi(x, 3)


def gain_ci(r, v="gain", lo="lo", hi="hi"):
    return f"{vi(r[v] * 100, 1, True)}% [{vi(r[lo] * 100, 1)}; {vi(r[hi] * 100, 1)}]"


spq = sp.set_index(["feature", "q"])
null_vars = ["ldr_computed_percent", "cir_quarter_percent", "roe_quarter_percent", "cof_quarter_percent"]

# ---------- so trong loi van: tinh tu du lieu de trang dung voi anh chup hien tai sau moi lan chay lai
feat = pd.read_csv("data/model/features_quarterly.csv", encoding="utf-8-sig")
last_q = sorted(feat.period.unique())[-1]
first_q = sorted(feat.period.unique())[-4]
members = lambda g, stable=None: sorted(tk for tk, r in pcs.iterrows() if r.g == g and (stable is None or r.stable == stable))  # noqa: E731


def group_trend(feature, g, period=None):
    raw = next(k for k, v in cid.items() if v == g)
    s = t[(t.feature == feature) & (t.group == str(raw))].set_index("period")["median"].dropna()
    return s.loc[period] if period else (s.iloc[0], s.iloc[-1], s.index[0])


border = pcs[~pcs.stable].sort_index()
stb_g = int(pcs.loc["STB", "g"])
stb_npl = feat[feat.ticker == "STB"].set_index("period").npl_percent
dc_sorted = dc.reindex(dc.rho.abs().sort_values(ascending=False).index)
c1, c2 = dc_sorted.iloc[0], dc_sorted.iloc[1]
rates = dt.rate12_online.dropna()
rate_by_g = dt.assign(g=pcs.g).groupby("g").rate12_online.median()
all_ci_zero = bool(((dc.lo <= 0) & (dc.hi >= 0)).all())
g0_casa = group_trend("casa_r4", 0)
g1_casa = group_trend("casa_r4", 1)
dd = str(dt.rate_date.dropna().iloc[0])
facts = {
    "dep_date": f"{dd[8:10]}/{dd[5:7]}/{dd[:4]}",
    "window": f"{first_q} → {last_q}", "snap_period": last_q,
    "pc1": vi(pex.loc["pc1", "share"] * 100), "pc2": vi(pex.loc["pc2", "share"] * 100),
    "pc12": vi((pex.loc["pc1", "share"] + pex.loc["pc2", "share"]) * 100, 0),
    "silhouette": vi(float(pex.silhouette_k3.iloc[0]), 2),
    "n0": str(len(members(0))), "n1": str(len(members(1))), "n2": str(len(members(2))),
    "g0_list": ", ".join(members(0)), "g2_list": " và ".join(members(2)),
    "g1_core": ", ".join(members(1, True)), "n1_core": str(len(members(1, True))),
    "n_stable": str(int(pcs.stable.sum())), "n_border": str(len(border)),
    "border_detail": ", ".join(f"{tk} ({int(r.quarters_same)}/{int(r.quarters)} quý)" for tk, r in border.iterrows()),
    "g0_npl": vi(gp.loc[0, "npl_percent"], 2), "g0_casa": vi(gp.loc[0, "casa_percent"]), "g0_cof": vi(gp.loc[0, "cof_ttm_percent"], 2),
    "g0_roa": vi(gp.loc[0, "roa_ttm_percent"], 2),
    "g1_npl": vi(gp.loc[1, "npl_percent"], 2), "g1_casa": vi(gp.loc[1, "casa_percent"]), "g1_cof": vi(gp.loc[1, "cof_ttm_percent"], 2),
    "g1_roa": vi(gp.loc[1, "roa_ttm_percent"], 2), "g1_cir": vi(gp.loc[1, "cir_ttm_pct"], 0),
    "g2_nim": vi(gp.loc[2, "nim_ttm_percent"], 2), "g2_loans": vi(gp.loc[2, "loans_yoy_percent"], 0),
    "g2_g2": vi(gp.loc[2, "loans_g2_percent"], 2), "g2_cc": vi(gp.loc[2, "credit_cost_ttm_pct"], 2),
    "g0_npl_2022": vi(group_trend("npl_percent", 0, "2022-Q4"), 2), "g0_npl_last": vi(group_trend("npl_percent", 0)[1], 2),
    "g1_npl_2022": vi(group_trend("npl_percent", 1, "2022-Q4"), 2), "g1_npl_last": vi(group_trend("npl_percent", 1)[1], 2),
    "g0_casa_first": vi(g0_casa[0]), "g0_casa_last": vi(g0_casa[1]), "g1_casa_first": vi(g1_casa[0]), "g1_casa_last": vi(g1_casa[1]),
    "casa_from": g0_casa[2],
    "stb_group": GROUP_NAMES[stb_g].lower(), "stb_npl_2024": vi(stb_npl.get("2024-Q4"), 2), "stb_npl_now": vi(stb_npl.get(last_q), 2),
    "stb_size_rank": str(int(dt.log_total_assets.rank(ascending=False)["STB"])),
    "rate_min": vi(rates.min()), "rate_min_t": rates.idxmin(), "rate_max": vi(rates.max()), "rate_max_t": rates.idxmax(),
    "rate_g0": vi(rate_by_g[0], 2), "rate_g1": vi(rate_by_g[1], 2), "rate_g2": vi(rate_by_g[2], 2),
    "corr1": f"{DLAB.get(c1.feature, c1.feature)} ({vi(c1.rho, 2, True)})",
    "corr2": (lambda lab: f"{lab[0].lower()}{lab[1:]} ({vi(c2.rho, 2, True)})")(DLAB.get(c2.feature, c2.feature)),
    "corr_ci": "mọi khoảng tin cậy 95% vẫn chứa 0" if all_ci_zero else "vài khoảng tin cậy 95% không chứa 0",
    "s_npl_share": vi(sa.loc["npl_percent", "share_season"] * 100), "s_npl_p": pv(sa.loc["npl_percent", "p_F"]),
    "s_npl_q4neg": vi(spq.loc[("npl_percent", 4), "share_neg"] * 100, 0),
    "s_npl_q4": vi(spq.loc[("npl_percent", 4), "median"], 2), "s_npl_q1": vi(spq.loc[("npl_percent", 1), "median"], 2, True),
    "s_npl_q1pos": vi(spq.loc[("npl_percent", 1), "share_pos"] * 100, 0),
    "s_npl_years": f"{int(sa.loc['npl_percent', 'years_same'])}/{int(sa.loc['npl_percent', 'years'])}",
    "s_casa_share": vi(sa.loc["casa_percent", "share_season"] * 100), "s_casa_p": pv(sa.loc["casa_percent", "p_F"]),
    "s_casa_q1neg": vi(spq.loc[("casa_percent", 1), "share_neg"] * 100, 0),
    "s_casa_q1": vi(spq.loc[("casa_percent", 1), "median"], 2), "s_casa_q4": vi(spq.loc[("casa_percent", 4), "median"], 2, True),
    "s_casa_years": f"{int(sa.loc['casa_percent', 'years_same'])}/{int(sa.loc['casa_percent', 'years'])}",
    "s_loans_q4": vi(spq.loc[("loans_qoq_percent", 4), "effect"], 1, True), "s_loans_q3": vi(spq.loc[("loans_qoq_percent", 3), "effect"], 1, True),
    "s_loans_share": vi(sa.loc["loans_qoq_percent", "share_season"] * 100), "s_loans_p": pv(sa.loc["loans_qoq_percent", "p_F"]),
    "s_loans_years": f"{int(sa.loc['loans_qoq_percent', 'years_same'])}/{int(sa.loc['loans_qoq_percent', 'years'])}",
    "s_g2_p": pv(sa.loc["loans_g2_percent", "p_F"]), "s_g2_pkw": pv(sa.loc["loans_g2_percent", "p_kw"]),
    "s_null_pmin": vi(np.floor(sa.loc[null_vars, "p_F"].min() * 100) / 100, 2),
    "s_cof_common": vi(sa.loc["cof_quarter_percent", "share_common"] * 100, 0),
    "s_T": f"{int(sa.n_periods.min())}–{int(sa.n_periods.max())}",
    "s_npl_gain": gain_ci(fc1.loc["npl_percent"]), "s_casa_gain": gain_ci(fc1.loc["casa_percent"]),
    "s_npl_vd": gain_ci(fc1.loc["npl_percent"], "gain_vs_drift", "vs_drift_lo", "vs_drift_hi"),
    "s_casa_vd": gain_ci(fc1.loc["casa_percent"], "gain_vs_drift", "vs_drift_lo", "vs_drift_hi"),
    "s_ldr_gain": gain_ci(fc1.loc["ldr_computed_percent"]),
    "s_ldr_vd": gain_ci(fc1.loc["ldr_computed_percent"], "gain_vs_drift", "vs_drift_lo", "vs_drift_hi"),
    "s_npl_gain_short": vi(fc1.loc["npl_percent", "gain"] * 100, 1), "s_casa_gain_short": vi(fc1.loc["casa_percent", "gain"] * 100, 1),
    "s_n": str(int(fc1.n.iloc[0])),
}

data = dict(periods=periods, variance=variance, trends=trends, context=context, leadlag=leadlag, pairs=pairs, corr=corr,
            groups=groups, deposit=deposit, app=app, app_monthly=app_monthly, policy=policy, season=season, facts=facts)
tpl = open(os.path.join(os.path.dirname(__file__), "eda_template.html"), encoding="utf-8").read()
out = tpl.replace("/*__DATA__*/", "const DATA = " + json.dumps(data, ensure_ascii=False) + ";")
missing = sorted({k for k in __import__("re").findall(r'data-fact="([a-z0-9_]+)"', tpl)} - set(facts))
assert not missing, f"template can so chua tinh: {missing}"
open(OUT, "w", encoding="utf-8").write(out)
print(OUT, len(out), "yagi rho (bo NVB):", policy["yagi_rho_ex_nvb"], "nhom:", groups["counts"])
