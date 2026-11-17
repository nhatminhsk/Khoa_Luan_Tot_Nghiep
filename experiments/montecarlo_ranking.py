from __future__ import annotations

import os
import sys
from itertools import combinations

import numpy as np
import pandas as pd

from crawlers import deposit_tiers

FEATURES = "data/model/features_quarterly.csv"
RANKING = "data/model/features_ranking_latest.csv"
CATALOG = "data/model/feature_catalog.csv"
MONTHLY = "data/model/features_selected_monthly.csv"
OUT_DIR = "data/model/experiments"
N = 10_000
SEED, SEED_CHECK = 20261014, 7
KAPPA = 30.0  # quanh mac dinh: do lech chuan ~9 diem quanh 50
VIKOR_V = 0.5
WPM_EPS = 0.01  # san cua diem chuan hoa trong WPM 
# Han muc BHTG: Thong tu 05/2026/TT-NHNN, hieu luc 13/07/2026 (truoc do 125 trieu, QD 32/2021/QD-TTg)
BHTG_LIMIT = 350_000_000
BHTG_FLOOR = 1e-6  # phan trong so an toan giu lai khi toan bo tien duoc bao hiem: chi de phan dinh khi lai bang nhau
HIST_FROM = "2022-Q1"
LOOKBACK_Q = 4  # nhu features_ranking_latest
CHUNK = 500  # PROMETHEE khi so lieu doi moi vong: (CHUNK, NH, NH, tieu chi)

# tieu chi -> (chieu, nhom, tru). Tru an toan = chu cai dau nhom trong feature_catalog.
DEPOSIT = {
    "dep12_online_pct": (+1, "lai", "R"),
    "car_asof_percent": (+1, "an toan", "C"), "equity_to_assets_pct": (+1, "an toan", "C"),
    "npl_percent": (-1, "an toan", "A"), "loans_g2_percent": (-1, "an toan", "A"),
    "credit_cost_ttm_pct": (-1, "an toan", "A"), "accrued_interest_to_assets_pct": (-1, "an toan", "A"),
    "cir_ttm_pct": (-1, "an toan", "M"), "state_own_percent": (+1, "an toan", "M"),
    "roa_ttm_percent": (+1, "an toan", "E"),
    "ldr_computed_percent": (-1, "an toan", "L"), "liquid_assets_pct": (+1, "an toan", "L"),
    "casa_percent": (+1, "an toan", "L"),
    "corp_bond_to_assets_pct": (-1, "an toan", "S"),
    "log_total_assets": (+1, "an toan", "G"),
}
# Diem app bo khoi xep hang 14/10/2026 (select_features.NO_EFFECT_NOTE). Mac dinh web 50/30/20 bo app, giu ty le.
DEPOSIT_TOP = {"lai": 0.625, "an toan": 0.375}
DEFAULT_TERM, DEFAULT_CHANNEL = 12, "online"  # mac dinh cua trang Gui tiet kiem
CHANNELS = ("online", "counter")


def rate_col(term: int, channel: str) -> str:
    return f"dep{term}_{channel}_pct"


def deposit_spec(term: int, channel: str) -> dict:
    return {rate_col(term, channel): DEPOSIT["dep12_online_pct"],
            **{k: v for k, v in DEPOSIT.items() if k != "dep12_online_pct"}}


def with_app(spec: dict, center: dict, part: str) -> tuple[dict, dict]:
    return {**spec, **APP_CRIT}, APP_TOP[part]
LOAN = {
    "lending_avg_pct": (-1, "gia", "R"), "loan_yield_ttm_pct": (-1, "gia", "E"),
    "retail_loan_share_pct": (+1, "phu hop", "P"),
    "ldr_computed_percent": (-1, "suc cho vay", "L"),
}
LOAN_TOP = {"gia": 1 / 3, "phu hop": 1 / 3, "suc cho vay": 1 / 3}
# Nhom TUY CHON "suc khoe" ben cho vay = diem tai chinh tuong doi tham khao cac nhom chi tieu Moody's (serving.bank_health), theo
# quyet dinh 27/10/2026: mac dinh 0% (khong vao bang vay), nguoi dung chon trong so; 10% / 20% chi la minh hoa.
# --suc-khoe-vay W chia lai: 3 nhom cu x (1 - W), nhom suc khoe W; --von von_chu doi dai dien von (do nhay).
HEALTH_CRIT = {"loan_health_score": (+1, "suc khoe", "H")}
LOAN_HEALTH_W, HEALTH_CAPITAL = 0.0, "car"


def loan_spec(w: float | None = None) -> tuple[dict, dict]:
    w = LOAN_HEALTH_W if w is None else w
    if w <= 0:
        return LOAN, LOAN_TOP
    return {**LOAN, **HEALTH_CRIT}, {**{k: v * (1 - w) for k, v in LOAN_TOP.items()}, "suc khoe": w}
# --co-app: dua lai nhom app de doi chieu, trong so mac dinh nhu truoc (web 50/30/20, vay chia 4)
APP_CRIT = {"app_mean_score": (+1, "app", "K")}
APP_TOP = {"gui": {"lai": 0.5, "an toan": 0.3, "app": 0.2}, "vay": {"gia": 0.25, "phu hop": 0.25, "suc cho vay": 0.25, "app": 0.25}}

# O tranh chap: so 24hmoney cua CTG doi tu 05/10/2026, chua co nguon doc lap. 26/10: tai quay da co bieu chinh thuc
# (deposit_official_manual, hieu luc 21/10) nen chi con kenh online.
DISPUTED = {"tickers": ("CTG",), "since": "2026-10-05", "channels": ("online",)}
OFFICIAL = "data/interest_rates/deposit_official_manual.csv"
SCORE_TOL = 1e-9  # hai diem lech < SCORE_TOL coi la hoa (sai so dau phay dong khong duoc quyet dinh hang)
MISSING = "trung_vi"  # o thieu tieu chi: "trung_vi" cat ngang (mac dinh) | "bat_loi" (--thieu-bat-loi, do nhay)
# kich ban -> (kieu trong so, so lieu ngau nhien?)
SCENARIOS = {
    "ngau_nhien": ("flat", False),
    "quanh_mac_dinh": ("center", False),
    "ngau_nhien+so_lieu": ("flat", True),
}


def _qi(period: pd.Series) -> pd.Series:
    return period.str[:4].astype(int) * 4 + period.str[-1].astype(int) - 1


def _mi(month: pd.Series) -> pd.Series:
    return month.str[:4].astype(int) * 12 + month.str[5:7].astype(int) - 1


# --------------------------------------------------------------------------- so lieu
def _check_roles() -> None:
    cat = pd.read_csv(CATALOG, encoding="utf-8-sig").set_index("feature")
    use = cat.use.fillna("")
    dep = set(use.index[use.str.contains("Xếp hạng gửi")]) - {"dep12_counter_pct"}
    loan = set(use.index[use.str.contains("Xếp hạng vay")])
    if dep != set(DEPOSIT) or loan != set(LOAN):
        raise ValueError(f"lech vai tro catalog: gui {dep ^ set(DEPOSIT)}, vay {loan ^ set(LOAN)}")
    for c, (_, top, pillar) in DEPOSIT.items():
        if top == "an toan" and cat.group[c][0] != pillar:
            raise ValueError(f"{c}: tru {pillar} khac nhom catalog {cat.group[c]}")


def _quarterly_snapshot(f: pd.DataFrame, cols: list[str], now_qi: int):
    f = f.assign(qi=_qi(f.period)).sort_values(["ticker", "qi"])
    recent = f[f.qi > f.qi.max() - LOOKBACK_Q]
    vals, stale = {}, {}
    for c in cols:
        last = recent.dropna(subset=[c]).groupby("ticker").last()
        vals[c], stale[c] = last[c], now_qi - last.qi
    hist = f[f.period >= HIST_FROM]
    deltas = {}
    for c in cols:
        w = hist.pivot(index="qi", columns="ticker", values=c)
        deltas[c] = {h: (w.shift(-h) - w).stack().dropna().to_numpy() for h in range(1, LOOKBACK_Q + 3)}
    return pd.DataFrame(vals), pd.DataFrame(stale), deltas, {c: (f[c].min(), f[c].max()) for c in cols}


def _deposit_before(before: str) -> pd.DataFrame:
    d = deposit_tiers.read()
    d = d[d.ticker.notna() & d.channel.isin(["online", "quay"]) & (d.date < before)].sort_values("date")
    w = d.groupby(["ticker", "term_months", "channel"]).rate_percent.last().unstack(["term_months", "channel"])
    w.columns = [rate_col(t, "online" if c == "online" else "counter") for t, c in w.columns]
    return w


def _not_offered() -> list[tuple[str, str]]:
    m = pd.read_csv(OFFICIAL, encoding="utf-8-sig")
    m = m[m.evidence.fillna("").str.startswith("QUY UOC")]
    return [(t, rate_col(int(k), "online" if ch == "online" else "counter")) for t, k, ch in zip(m.ticker, m.term_months, m.channel)]


def subset_inputs(inp: dict, keep: list[str]) -> dict:
    idx = {t: i for i, t in enumerate(keep)}
    alt = {c: {idx[inp["banks"][b]]: v for b, v in d.items() if inp["banks"][b] in idx} for c, d in inp["alt"].items()}
    return {**inp, "vals": inp["vals"].loc[keep], "stale": inp["stale"].loc[keep], "banks": keep,
            "alt": {c: d for c, d in alt.items() if d}, "fill_from": inp.get("fill_from", inp["vals"])}


def _lending_history(until: str):
    m = pd.read_csv(MONTHLY, encoding="utf-8-sig", usecols=["month", "ticker", "lending_avg_pct"])
    m = m[m.month <= until]
    w = m.assign(mi=_mi(m.month)).pivot(index="mi", columns="ticker", values="lending_avg_pct")
    deltas = {k: (w.shift(-k) - w).stack().dropna().to_numpy() for k in range(1, 13)}
    return deltas, (m.lending_avg_pct.min(), m.lending_avg_pct.max())


def build_inputs(app: bool = False, ranking: str = RANKING) -> dict:
    rk = pd.read_csv(ranking, encoding="utf-8-sig").set_index("ticker")
    asof = pd.Timestamp(rk.dep_asof.max())
    f = pd.read_csv(FEATURES, encoding="utf-8-sig")
    f = f[f.period <= rk.latest_period.max()]
    _check_roles()
    now_qi = asof.year * 4 + asof.quarter - 2  # quy vua het
    now_mi = asof.year * 12 + asof.month - 2  # thang vua het
    banks = sorted(f.ticker.unique())
    rk = rk.reindex(banks)
    if app:  # khong con trong file xep hang
        from crawlers.select_features import _fresh
        rk["app_mean_score"] = _fresh().app_mean_score.reindex(banks)
    rates = [c for c in rk.columns if c.startswith("dep") and c.endswith("_pct")]  # moi ky han x kenh co trong file
    cols = sorted(set(rates) | (set(DEPOSIT) - {"dep12_online_pct"}) | set(LOAN) | (set(APP_CRIT) if app else set()))
    fresh = set(rates) | {"lending_avg_pct"} | (set(APP_CRIT) if app else set())  # so moi nhat, khong theo quy
    qcols = sorted(set(cols) - fresh)
    snap, stale, deltas, lo_hi = _quarterly_snapshot(f, qcols, now_qi)
    off = [c for c in qcols if not np.allclose(snap[c].reindex(banks), rk[c], equal_nan=True, rtol=0, atol=1e-6)]
    if off:
        raise ValueError(f"{RANKING} lech anh chup BCTC o {off}: chay lai python -m crawlers.select_features")
    vals = rk[cols].copy()
    stale = stale.reindex(banks)
    for c in rates + (list(APP_CRIT) if app else []):
        stale[c] = 0
        lo_hi[c] = (vals[c].min(), vals[c].max())
    stale["lending_avg_pct"] = now_mi - _mi(rk.lending_asof.fillna("1900-01"))
    deltas["lending_avg_pct"], lo_hi["lending_avg_pct"] = _lending_history(f"{now_mi // 12}-{now_mi % 12 + 1:02d}")
    for t, c in _not_offered():  # o "quy uoc" (san pham khong ton tai) -> khong xep NH o ky han x kenh do
        if t in vals.index and c in vals.columns:
            vals.at[t, c] = np.nan
    before = _deposit_before(DISPUTED["since"]).reindex(list(DISPUTED["tickers"]))
    alt = {}
    for c in rates:
        if c in before and any(c.endswith(f"_{ch}_pct") for ch in DISPUTED["channels"]):
            changed = before[c][(before[c] != vals.loc[before.index, c]) & before[c].notna()]  # chi o thuc su doi
            if len(changed):
                alt[c] = {banks.index(t): v for t, v in changed.items()}
    from serving.bank_health import inputs as health_inputs, score as health_score
    vals["loan_health_score"] = health_score(health_inputs(ranking), HEALTH_CAPITAL, MISSING).diem.reindex(banks)
    stale["loan_health_score"] = 0  # anh chup, khong co lich su de rut nhieu
    lo_hi["loan_health_score"] = (0.0, 1.0)
    terms = sorted({int(c[3:].split("_")[0]) for c in rates})
    return dict(vals=vals, stale=stale, deltas=deltas, lo_hi=lo_hi, banks=banks, alt=alt, terms=terms,
                rates=rates, rate_date=rk.dep_asof.max(),
                now_q=f"{now_qi // 4}-Q{now_qi % 4 + 1}", now_m=f"{now_mi // 12}-{now_mi % 12 + 1:02d}")


def _draw_data(inp: dict, cols: list[str], rng: np.random.Generator | None, n: int,
               dirs: np.ndarray | None = None) -> np.ndarray:
    base = inp["vals"][cols].to_numpy(float)
    full = inp.get("fill_from", inp["vals"])[cols].to_numpy(float)  # du 22 NH: gia tri dien khong doi theo tap xep
    X = np.repeat(base[None], n, axis=0)
    for j, c in enumerate(cols):
        known = ~np.isnan(base[:, j])
        pool_fill = full[~np.isnan(full[:, j]), j]
        if MISSING == "bat_loi" and dirs is not None and (~known).any():
            X[:, ~known, j] = pool_fill.min() if dirs[j] > 0 else pool_fill.max()  # cuc tri ANH CHUP (co dinh moi vong)
            if rng is None:
                continue
        elif rng is None:
            X[:, ~known, j] = np.median(pool_fill)
            continue
        for b, v in inp["alt"].get(c, {}).items():
            X[:, b, j] = np.where(rng.random(n) < 0.5, v, base[b, j])
        for b in np.where(known)[0]:
            h = int(inp["stale"][c].iloc[b])
            if h > 0:
                pool = inp["deltas"][c].get(h)
                if pool is None or not len(pool):
                    pool = inp["deltas"][c][max(inp["deltas"][c])]
                X[:, b, j] += rng.choice(pool, n)
        if MISSING != "bat_loi":
            for b in np.where(~known)[0]:
                X[:, b, j] = rng.choice(pool_fill, n)
        X[:, :, j] = np.clip(X[:, :, j], *inp["lo_hi"][c])
    return X


# --------------------------------------------------------------------------- trong so
def _structure(spec: dict):
    cols = list(spec)
    tops = list(dict.fromkeys(v[1] for v in spec.values()))
    pillars = {t: list(dict.fromkeys(v[2] for v in spec.values() if v[1] == t)) for t in tops}
    return cols, tops, pillars


def draw_weights(spec: dict, center: dict, mode: str, rng: np.random.Generator | None, n: int,
                 scale: dict | None = None):
    cols, tops, pillars = _structure(spec)
    c0 = np.array([center[t] for t in tops])
    if rng is None:
        top = np.repeat(c0[None], n, axis=0)
    else:
        top = rng.dirichlet(np.ones(len(tops)) if mode == "flat" else KAPPA * c0, n)
    if scale:
        top = top * np.array([scale.get(t, 1.0) for t in tops])
        top = top / top.sum(1, keepdims=True)
    W = np.zeros((n, len(cols)))
    for ti, t in enumerate(tops):
        ps = pillars[t]
        pw = np.full((n, len(ps)), 1 / len(ps)) if rng is None or len(ps) == 1 else rng.dirichlet(np.ones(len(ps)), n)
        for pi, p in enumerate(ps):
            idx = [j for j, c in enumerate(cols) if spec[c][1] == t and spec[c][2] == p]
            W[:, idx] = (top[:, ti] * pw[:, pi] / len(idx))[:, None]
    return W, top


# --------------------------------------------------------------------------- thuat toan
def normalise(X: np.ndarray, dirs: np.ndarray) -> np.ndarray:
    lo, hi = X.min(1, keepdims=True), X.max(1, keepdims=True)
    span = hi - lo
    Nm = (X - lo) / np.where(span > 0, span, 1)
    Nm = np.where(dirs > 0, Nm, 1 - Nm)
    return np.where(span > 0, Nm, 1.0)


def saw(Nm: np.ndarray, W: np.ndarray) -> np.ndarray:
    return (Nm * W[:, None, :]).sum(2)


def topsis(Nm: np.ndarray, W: np.ndarray) -> np.ndarray:
    V = Nm * W[:, None, :]
    dp = np.sqrt(((V - V.max(1, keepdims=True)) ** 2).sum(2))
    dm = np.sqrt(((V - V.min(1, keepdims=True)) ** 2).sum(2))
    return dm / np.where(dp + dm > 0, dp + dm, 1)


def vikor(Nm: np.ndarray, W: np.ndarray, v: float = VIKOR_V) -> np.ndarray:
    reg = W[:, None, :] * (1 - Nm)
    S, R = reg.sum(2), reg.max(2)

    def scale(a):
        lo, hi = a.min(1, keepdims=True), a.max(1, keepdims=True)
        return (a - lo) / np.where(hi > lo, hi - lo, 1)
    return -(v * scale(S) + (1 - v) * scale(R))


def _net_flow_per_criterion(Nm: np.ndarray) -> np.ndarray:
    B = Nm.shape[1]
    out = np.empty_like(Nm)
    for s in range(0, len(Nm), CHUNK):
        x = Nm[s:s + CHUNK]
        out[s:s + CHUNK] = np.sign(x[:, :, None, :] - x[:, None, :, :]).sum(2) / (B - 1)
    return out


def promethee(Nm: np.ndarray, W: np.ndarray) -> np.ndarray:
    return (_net_flow_per_criterion(Nm) * W[:, None, :]).sum(2)


def wpm(Nm: np.ndarray, W: np.ndarray) -> np.ndarray:
    return (np.log(WPM_EPS + (1 - WPM_EPS) * Nm) * W[:, None, :]).sum(2)


def wpm_group(Nm: np.ndarray, W: np.ndarray, gid: np.ndarray) -> np.ndarray:
    out = np.zeros((max(len(Nm), len(W)), Nm.shape[1]))  # so lieu co dinh: Nm (1, NH, tieu chi), W (N, tieu chi)
    for g in np.unique(gid):
        wg = W[:, gid == g]
        tot = wg.sum(1, keepdims=True)
        inner = (Nm[:, :, gid == g] * (wg / np.where(tot > 0, tot, 1))[:, None, :]).sum(2)
        out += tot * np.log(WPM_EPS + (1 - WPM_EPS) * inner)
    return out


COMPENSATORY = {"SAW": saw, "TOPSIS": topsis, "VIKOR": vikor, "PROMETHEE II": promethee}
ALGOS = {**COMPENSATORY, "WPM": wpm}
GROUP_ALGOS = {"WPM nhom": wpm_group}  # can biet tieu chi thuoc nhom nao
ALL_ALGOS = [*ALGOS, *GROUP_ALGOS]


def score_all(Nm: np.ndarray, W: np.ndarray, gid: np.ndarray) -> dict:
    return {**{a: f(Nm, W) for a, f in ALGOS.items()}, **{a: f(Nm, W, gid) for a, f in GROUP_ALGOS.items()}}


def ranks(score: np.ndarray) -> np.ndarray:
    return (score[:, None, :] > score[:, :, None] + SCORE_TOL).sum(2) + 1


# --------------------------------------------------------------------------- vong lap
def run_part(name: str, spec: dict, center: dict, inp: dict, seed: int, scale: dict | None = None) -> dict:
    cols, tops, _ = _structure(spec)
    dirs = np.array([spec[c][0] for c in cols], float)
    gid = np.array([tops.index(spec[c][1]) for c in cols])
    point_N = normalise(_draw_data(inp, cols, None, 1, dirs), dirs)
    point_W, _ = draw_weights(spec, center, "center", None, 1, scale)
    out = {"point": {a: s[0] for a, s in score_all(point_N, point_W, gid).items()}}
    for k, (mode, rand_data) in SCENARIOS.items():
        rng = np.random.default_rng([seed, list(SCENARIOS).index(k), len(cols)])
        W, top = draw_weights(spec, center, mode, rng, N, scale)
        Nm = normalise(_draw_data(inp, cols, rng, N, dirs) if rand_data else _draw_data(inp, cols, None, 1, dirs), dirs)
        out[k] = dict(W=W, top=top, R={a: ranks(s) for a, s in score_all(Nm, W, gid).items()})
    return dict(name=name, cols=cols, tops=tops, out=out)


def tables(part: dict, banks: list[str]):
    top_rows, agree_rows, weight_rows = [], [], []
    point_rank = {a: ranks(s[None])[0] for a, s in part["out"]["point"].items()}
    for k in SCENARIOS:
        o = part["out"][k]
        for a, R in o["R"].items():
            for b, t in enumerate(banks):
                r = R[:, b]
                share = (r == 1) / (R == 1).sum(1)  # hoa o hang 1: chia deu P(top1) cho cac NH hoa
                top_rows.append(dict(part=part["name"], scenario=k, algorithm=a, ticker=t,
                                     point_rank=int(point_rank[a][b]), p_top1=share.mean(), p_top3=(r <= 3).mean(),
                                     mean_rank=r.mean(), p05=int(np.percentile(r, 5, method="lower")),
                                     p95=int(np.percentile(r, 95, method="higher"))))
                if k == "ngau_nhien" and share.any():  # bo trong so nao dua NH len top 1 (hoa: trong so chia deu)
                    row = dict(part=part["name"], algorithm=a, ticker=t, p_top1=share.mean())
                    row.update({f"w_{g}": v for g, v in zip(part["tops"], (o["top"] * share[:, None]).sum(0) / share.sum())})
                    weight_rows.append(row)
        # (N, NH) True = NH o hang 1 cua thuat toan (co the nhieu NH khi hoa). "Cung top 1" = co CHUNG it nhat mot NH hang 1
        # (truoc 26/10 dung argmin -> hoa hang 1 luon chon NH dung truoc theo ma)
        top1 = {a: o["R"][a] == 1 for a in o["R"]}
        common = np.logical_and.reduce([top1[a] for a in COMPENSATORY])  # "ca 4" = 4 thuat toan bu tru, nhu truoc khi them WPM
        all_same = common.any(1)
        agree_rows.append(dict(part=part["name"], scenario=k, metric="ca_4_cung_top1", value=all_same.mean()))
        for a, b in combinations(o["R"], 2):
            agree_rows.append(dict(part=part["name"], scenario=k, metric=f"cung_top1_{a}_vs_{b}",
                                   value=(top1[a] & top1[b]).any(1).mean()))
        share = common / np.where(common.any(1), common.sum(1), 1)[:, None]  # chia deu khi nhieu NH cung hoa hang 1
        for b, t in enumerate(banks):
            p = share[:, b].mean()
            if p > 0:
                agree_rows.append(dict(part=part["name"], scenario=k, metric=f"ca_4_chon_{t}", value=p))
    return pd.DataFrame(top_rows), pd.DataFrame(agree_rows), pd.DataFrame(weight_rows)


def _print_detail(t: pd.DataFrame, a: pd.DataFrame, w: pd.DataFrame, label: str) -> None:
    for k in SCENARIOS:
        v = t[t.scenario == k].pivot(index="ticker", columns="algorithm", values="p_top1")[ALL_ALGOS]
        v["TB"] = v[list(COMPENSATORY)].mean(1)  # trung binh 4 thuat toan bu tru
        v.insert(0, "hang_diem_TOPSIS", t[(t.scenario == k) & (t.algorithm == "TOPSIS")].set_index("ticker").point_rank)
        v = v.sort_values("TB", ascending=False)
        agree = a[(a.scenario == k) & (a.metric == "ca_4_cung_top1")].value.iloc[0]
        print(f"\n=== {label} | {k} | ty le dung TOP 1 (ca 4 thuat toan cung top 1: {agree:.1%}) ===")
        print(v[v.TB > 0.005].round(3).to_string())
    print("Bo trong so (TB) khi NH dung top 1, kich ban ngau_nhien, TOPSIS:")
    print(w[w.algorithm == "TOPSIS"].sort_values("p_top1", ascending=False).head(8).round(3).to_string(index=False))


def _top3(df: pd.DataFrame, col: str = "p_top1") -> str:
    p = df.groupby("ticker")[col].mean().sort_values(ascending=False)
    return ", ".join(f"{x} {v:.0%}" for x, v in p.head(3).items())


def _summary_rows(t: pd.DataFrame, a: pd.DataFrame, keys: dict, **extra) -> list[dict]:
    rows = []
    for k in ("quanh_mac_dinh", "ngau_nhien"):
        tk = t[t.scenario == k]
        agree = a[(a.scenario == k) & (a.metric == "ca_4_cung_top1")].value.iloc[0]
        comp = tk[tk.algorithm.isin(list(COMPENSATORY))]
        rows.append(dict(**keys, kich_ban=k, ca_4_cung_top1=round(agree, 3),
                         p_top1_bu_tru=_top3(comp), p_top3_bu_tru=_top3(comp, "p_top3"),
                         wpm_nhom=_top3(tk[tk.algorithm == "WPM nhom"]), wpm=_top3(tk[tk.algorithm == "WPM"]), **extra))
    return rows


# --------------------------------------------------------------------------- so tien gui, BHTG
def uninsured_share(amount: float, rate_pct: float, term: int) -> float:
    due = amount * (1 + rate_pct / 100 * term / 12)
    return max(due - BHTG_LIMIT, 0.0) / due


def with_amount(inp: dict, amount: float) -> dict:
    d = deposit_tiers.read()
    tiers = deposit_tiers.amount_tiers(d[d.date <= inp["rate_date"]])
    tiers = tiers[tiers.min_amount_vnd <= amount].sort_values("min_amount_vnd")
    vals, lo_hi, changed = inp["vals"].copy(), dict(inp["lo_hi"]), []
    for (t, term, ch), g in tiers.groupby(["ticker", "term_months", "channel"]):
        c = rate_col(int(term), "online" if ch == "online" else "counter")
        if c in vals.columns and t in vals.index:
            changed.append(f"{t} {c} {vals.at[t, c]:g}->{g.rate_percent.iloc[-1]:g}")
            vals.at[t, c] = g.rate_percent.iloc[-1]
    for c in inp["rates"]:
        lo_hi[c] = (vals[c].min(), vals[c].max())
    return {**inp, "vals": vals, "lo_hi": lo_hi, "tier_changes": changed}


def run_amounts(inp: dict, amounts: list[float]) -> None:
    banks = inp["banks"]
    configs = [(term, ch) for term in inp["terms"] for ch in CHANNELS if rate_col(term, ch) in inp["rates"]]
    tops, agrees, weights, summary = [], [], [], []
    for amount in amounts:
        ia = with_amount(inp, amount)
        print(f"\n### So tien {amount:,.0f} dong: {len(ia['tier_changes'])} o lai doi bac", ia["tier_changes"][:8])
        for term, ch in configs:
            u = uninsured_share(amount, float(np.nanmedian(ia["vals"][rate_col(term, ch)])), term)
            f_safe = max(u, BHTG_FLOOR)
            ib = subset_inputs(ia, [b for b in banks if pd.notna(ia["vals"].at[b, rate_col(term, ch)])])
            part = run_part("gui", deposit_spec(term, ch), DEPOSIT_TOP, ib, SEED, {"an toan": f_safe})
            t, a, w = tables(part, ib["banks"])
            w_safe = DEPOSIT_TOP["an toan"] * f_safe / (DEPOSIT_TOP["lai"] + DEPOSIT_TOP["an toan"] * f_safe)
            for df in (t, a, w):
                df.insert(1, "so_tien_vnd", int(amount))
                df.insert(2, "term_months", term)
                df.insert(3, "channel", ch)
                df.insert(4, "phan_khong_bao_hiem", round(u, 4))
            tops.append(t), agrees.append(a), weights.append(w)
            summary += _summary_rows(t, a, dict(so_tien=f"{amount / 1e6:,.0f} tr", ky_han=term, kenh=ch),
                                     khong_bh=round(u, 2), w_an_toan_mac_dinh=round(w_safe, 3))
    s = pd.DataFrame(summary)
    print("\n=== Gui theo so tien: top 1 (top3 = TB 4 thuat toan bu tru; wpm_nhom, wpm = khong bu tru) ===")
    print(s[s.kich_ban == "quanh_mac_dinh"].drop(columns="kich_ban").to_string(index=False))
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, frames in (("top", tops), ("agreement", agrees), ("weights", weights)):
        pd.concat(frames).round(4).to_csv(f"{OUT_DIR}/montecarlo_{name}_so_tien.csv", index=False, encoding="utf-8-sig")


# --------------------------------------------------------------------------- ML trong vong Monte Carlo (--ml)
# Chot 26/10/2026. Vong NGOAI van la trong so (dinh nghia GVHD). Day la PHAN TICH DO NHAY,
# khong phai bang chinh: bang chinh xep bang so cong bo (scope).
# Cau hinh chot (ban toi thieu): tam = SO CONG BO (anh chup); chi NPL / CASA / LDR (vay: chi LDR)
# duoc cong scale x z, z = sai so walk-forward co dau / thang cua NH (serving.forecast), lay theo CA QUY goc u (chung 22 NH x 3
# chi tieu -> giu cu soc chung). Moi bo trong so ghep voi MOI quy u trong kho (liet ke du). Doi chung cung tam:
#   cong_bo_sai_so  z cua phuong phap da chon (base hoac RF)   | cong_bo_base  z cua base
# Dinh tam "tru_TB_NH": tru TB z rieng tung NH x chi tieu tren DUNG kho dang dung (truoc cat mien TB kich ban = so cong bo;
# SAU cat mien thi lech -- xuat theo NH, ham ml_clip_report). "giu_nguyen" (giu ca sai lech) la do nhay. Kho chinh: goc tu
# ML_ORIGIN_FROM (sau giai doan chon phuong phap, nhan <= 2022-Q4). Nhanh tam du bao (base_diem, chon_diem, base_sai_so,
# chon_sai_so) chi la tham do. Khong hoc lai RF trong vong; khong dung lower/upper lam phan phoi; khong cong nhieu _draw_data.
FORECASTS = "data/model/experiments/forecasts_de_xuat.csv"
FC_SELECTION = "data/model/experiments/forecast_selection.csv"
OOF = "data/model/experiments/forecast_oof_errors.csv"
ML_COLS = {"npl": "npl_percent", "casa": "casa_percent", "ldr": "ldr_computed_percent"}
ML_MAIN = ("hien_tai", "cong_bo_base", "cong_bo_sai_so")
ML_EXPLORE = ("base_diem", "chon_diem", "base_sai_so", "chon_sai_so")
ML_MODES = ("tru_TB_NH", "giu_nguyen")
ML_ORIGIN_FROM = "2023-Q1"
ML_DOMAIN = {"npl_percent": (0, 100), "casa_percent": (0, 100), "ldr_computed_percent": (0, np.inf)}


def ml_inputs(banks: list[str], origin_from: str = ML_ORIGIN_FROM, oof: str = OOF) -> dict:
    fc = pd.read_csv(FORECASTS)
    fc = fc[fc.indicator.isin(list(ML_COLS))]
    sel = pd.read_csv(FC_SELECTION, encoding="utf-8-sig").set_index(["indicator_code", "h"])
    oof = pd.read_csv(oof, encoding="utf-8-sig")
    oof = oof[oof.origin >= origin_from]
    for (c, h), g in oof[oof.indicator.isin(list(ML_COLS.values()))].groupby(["indicator", "h"]):  # dong bo phien ban
        code = {v: k for k, v in ML_COLS.items()}[c]
        if set(g.chosen) != {sel.at[(code, h), "method"]}:
            raise ValueError(f"kho sai so ({c} h{h}: {set(g.chosen)}) khong khop {FC_SELECTION} "
                             f"({sel.at[(code, h), 'method']}): chay lai serving.forecast")
    out = {}
    for h in sorted(fc.horizon.unique()):
        g = fc[fc.horizon == h]
        cen = {arm: pd.DataFrame({ML_COLS[i]: g[g.indicator == i].set_index("ticker")[col] for i in ML_COLS}).reindex(banks)
               for arm, col in (("chon", "value"), ("base", "naive_value"))}
        scale = pd.DataFrame({ML_COLS[i]: ((d.upper - d.value) / sel.at[(i, h), "q90_norm"]).values
                              for i, d in ((i, g[g.indicator == i].set_index("ticker").reindex(banks)) for i in ML_COLS)},
                             index=banks)
        Z, origins = {}, None
        for arm in ("chon", "base"):
            parts = []
            for i, c in ML_COLS.items():
                o = oof[(oof.indicator == c) & (oof.h == h)]
                o = o[o.method == (o.chosen if arm == "chon" else "base")]
                parts.append(o.assign(z=o.err / o.scale).pivot(index="origin", columns="ticker", values="z")
                             .reindex(columns=banks).rename_axis(None))
            ok = sorted(set.intersection(*[set(p.index[p.notna().all(1)]) for p in parts]))
            origins = ok if origins is None else sorted(set(origins) & set(ok))
            Z[arm] = parts
        Z = {arm: np.stack([p.loc[origins].to_numpy() for p in ps], axis=2) for arm, ps in Z.items()}  # (U, NH, 3)
        out[h] = dict(center=cen, scale=scale, Z=Z, origins=origins,
                      method={i: sel.at[(i, h), "method"] for i in ML_COLS}, target=g.target_period.iloc[0])
    return out


def _ml_src(arm: str) -> str:
    return "base" if arm in ("cong_bo_base", "base_diem", "base_sai_so") else "chon"


def _ml_z(m: dict, arm: str, mode: str, drop: int | None = None) -> np.ndarray:
    Z = m["Z"][_ml_src(arm)]
    if drop is not None:
        Z = np.delete(Z, drop, axis=0)
    return Z - Z.mean(0, keepdims=True) if mode == "tru_TB_NH" else Z


def _ml_matrix(base_X: np.ndarray, cols: list[str], m: dict, arm: str, mode: str, drop: int | None = None) -> list[np.ndarray]:
    if arm == "hien_tai":
        return [base_X]
    jj = [(j, c) for j, c in enumerate(cols) if c in ML_COLS.values()]
    order = list(ML_COLS.values())
    X0 = base_X.copy()
    if not arm.startswith("cong_bo"):
        for j, c in jj:
            X0[0, :, j] = m["center"][_ml_src(arm)][c].to_numpy()
    if arm.endswith("_diem"):
        return [X0]
    Z = _ml_z(m, arm, mode, drop)
    mats = []
    for u in range(Z.shape[0]):
        X = X0.copy()
        for j, c in jj:
            X[0, :, j] = np.clip(X0[0, :, j] + m["scale"][c].to_numpy() * Z[u, :, order.index(c)], *ML_DOMAIN[c])
        mats.append(X)
    return mats


def _ml_parts(inp: dict) -> list:
    banks = inp["banks"]
    out = []
    for name, spec, center, term, ch in [("gui", deposit_spec(DEFAULT_TERM, DEFAULT_CHANNEL), DEPOSIT_TOP, DEFAULT_TERM,
                                          DEFAULT_CHANNEL), ("vay", *loan_spec(), None, None)]:
        ip = inp if name == "vay" else subset_inputs(inp, [b for b in banks if pd.notna(inp["vals"].at[b, rate_col(term, ch)])])
        cols, tops, _ = _structure(spec)
        dirs = np.array([spec[c][0] for c in cols], float)
        out.append(dict(name=name, spec=spec, center=center, ip=ip, cols=cols, dirs=dirs,
                        gid=np.array([tops.index(spec[c][1]) for c in cols]), base_X=_draw_data(ip, cols, None, 1, dirs),
                        keep=[banks.index(b) for b in ip["banks"]]))
    return out


def _ml_sub(m: dict, P: dict) -> dict:
    return {**m, "center": {a: d.loc[P["ip"]["banks"]] for a, d in m["center"].items()},
            "scale": m["scale"].loc[P["ip"]["banks"]], "Z": {a: z[:, P["keep"], :] for a, z in m["Z"].items()}}


def _ml_eval(mats: list, P: dict, W: np.ndarray, algos=None) -> dict:
    nb = len(P["ip"]["banks"])
    acc = {}
    for X in mats:
        for a, s in score_all(normalise(X, P["dirs"]), W, P["gid"]).items():
            if algos and a not in algos:
                continue
            R = ranks(s)
            d = acc.setdefault(a, dict(top1_w=np.zeros((len(W), nb)), top3=np.zeros(nb), mean=np.zeros(nb),
                                       hist=np.zeros((nb, nb))))
            d["top1_w"] += (R == 1) / (R == 1).sum(1, keepdims=True) / len(mats)
            d["top3"] += (R <= 3).mean(0) / len(mats)
            d["mean"] += R.mean(0) / len(mats)
            for b in range(nb):
                d["hist"][b] += np.bincount(R[:, b] - 1, minlength=nb)[:nb]
    return acc


def _q_rank(hist: np.ndarray, q: float) -> int:
    c = np.cumsum(hist) / hist.sum()
    return int(np.searchsorted(c, q - 1e-12) + 1)


def run_ml(inp: dict, origin_from: str = ML_ORIGIN_FROM, seed: int = SEED, arms=ML_MAIN + ML_EXPLORE, modes=ML_MODES,
           suffix: str = "", oof: str = OOF) -> pd.DataFrame:
    banks = inp["banks"]
    ml = ml_inputs(banks, origin_from, oof)
    rows, cmp_rows = [], []
    for P in _ml_parts(inp):
        for h, m0 in ml.items():
            m = _ml_sub(m0, P)
            for scen in ("quanh_mac_dinh", "ngau_nhien"):
                rng = np.random.default_rng([seed, list(SCENARIOS).index(scen), len(P["cols"])])  # cung trong so voi run_part
                W, _ = draw_weights(P["spec"], P["center"], SCENARIOS[scen][0], rng, N)
                done = {}
                for mode in modes:
                    for arm in arms:
                        key = arm if (arm == "hien_tai" or arm.endswith("_diem")) else (arm, mode)
                        if key not in done:
                            done[key] = _ml_eval(_ml_matrix(P["base_X"], P["cols"], m, arm, mode), P, W)
                        for a, d in done[key].items():
                            p1 = d["top1_w"].mean(0)
                            for b, t in enumerate(P["ip"]["banks"]):
                                rows.append(dict(part=P["name"], h=h, quy_dich=m["target"], kho_tu=origin_from,
                                                 kho_thuc_tu=m["origins"][0], seed=seed,
                                                 scenario=scen, sai_so=mode, arm=arm, algorithm=a, ticker=t, p_top1=p1[b],
                                                 mcse_p_top1=d["top1_w"][:, b].std(ddof=1) / np.sqrt(len(W)),
                                                 p_top3=d["top3"][b], mean_rank=d["mean"][b],
                                                 p05=_q_rank(d["hist"][b], 0.05), p95=_q_rank(d["hist"][b], 0.95),
                                                 n_quy_sai_so=1 if key == arm else len(m["origins"])))
                    for a in COMPENSATORY:  # so cap: cung trong so, cung quy sai so
                        for x, y in (("cong_bo_sai_so", "hien_tai"), ("cong_bo_base", "hien_tai"),
                                     ("cong_bo_sai_so", "cong_bo_base"), ("chon_sai_so", "cong_bo_sai_so")):
                            kx = x if x == "hien_tai" else (x, mode)
                            ky = y if y == "hien_tai" else (y, mode)
                            if kx not in done or ky not in done:
                                continue
                            dw = done[kx][a]["top1_w"] - done[ky][a]["top1_w"]  # ghep cap theo bo trong so
                            d = dw.mean(0)
                            px, py = done[kx][a]["top1_w"].mean(0), done[ky][a]["top1_w"].mean(0)
                            j = int(np.argmax(np.abs(d)))
                            cmp_rows.append(dict(part=P["name"], h=h, kho_tu=origin_from, kho_thuc_tu=m["origins"][0], seed=seed,
                                                 scenario=scen,
                                                 sai_so=mode, algorithm=a, so_sanh=f"{x}-{y}",
                                                 max_abs_dP_top1=float(np.abs(d).max()), NH_max=P["ip"]["banks"][j],
                                                 mcse_dP=float(dw[:, j].std(ddof=1) / np.sqrt(len(W))),
                                                 mcse_dP_max=float((dw.std(0, ddof=1) / np.sqrt(len(W))).max()),
                                                 NH_dan_dau=P["ip"]["banks"][int(np.argmax(px))],
                                                 dan_dau_doi=int(np.argmax(px)) != int(np.argmax(py))))
            print(f"  ML x MC {P['name']} h{h} ({m['target']}, kho yeu cau tu {origin_from}, thuc dung {m['origins'][0]}: "
                  f"{len(m['origins'])} quy, phuong phap "
                  f"{m['method']}, seed {seed}): xong", flush=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    T, C = pd.DataFrame(rows), pd.DataFrame(cmp_rows)
    T.to_csv(f"{OUT_DIR}/montecarlo_ml_top{suffix}.csv", index=False, encoding="utf-8-sig", float_format="%.6g")
    C.to_csv(f"{OUT_DIR}/montecarlo_ml_compare{suffix}.csv", index=False, encoding="utf-8-sig", float_format="%.6g")
    comp = T[T.algorithm.isin(list(COMPENSATORY)) & (T.scenario == "quanh_mac_dinh") & T.arm.isin(ML_MAIN)]
    s = comp.groupby(["part", "h", "sai_so", "arm", "ticker"]).p_top1.mean().reset_index()
    top = s.sort_values("p_top1", ascending=False).groupby(["part", "h", "sai_so", "arm"]).head(2)
    for (pt, h, md, arm), g in top.groupby(["part", "h", "sai_so", "arm"]):
        print(f"    {pt} h{h} {md:10s} {arm:15s} " + ", ".join(f"{t} {p:.1%}" for t, p in zip(g.ticker, g.p_top1)))
    return T


def ml_clip_report(inp: dict, origin_from: str = ML_ORIGIN_FROM) -> pd.DataFrame:
    ml = ml_inputs(inp["banks"], origin_from)
    order = list(ML_COLS.values())
    rows = []
    for P in _ml_parts(inp):
        for h, m0 in ml.items():
            m = _ml_sub(m0, P)
            for arm in ("cong_bo_base", "cong_bo_sai_so"):
                for mode in ML_MODES:
                    Z = _ml_z(m, arm, mode)
                    for j, c in enumerate(P["cols"]):
                        if c not in order:
                            continue
                        x0 = P["base_X"][0, :, j]
                        v = x0[None, :] + m["scale"][c].to_numpy()[None, :] * Z[:, :, order.index(c)]
                        vc = np.clip(v, *ML_DOMAIN[c])
                        for b, t in enumerate(P["ip"]["banks"]):
                            rows.append(dict(part=P["name"], h=h, kho_tu=origin_from, arm=arm, sai_so=mode, chi_tieu=c,
                                             ticker=t, so_cong_bo=x0[b], so_kich_ban=len(v),
                                             so_bi_cat=int((v[:, b] != vc[:, b]).sum()),
                                             lech_TB_truoc_cat=v[:, b].mean() - x0[b], lech_TB_sau_cat=vc[:, b].mean() - x0[b]))
    R = pd.DataFrame(rows)
    R.to_csv(f"{OUT_DIR}/montecarlo_ml_cat_mien.csv", index=False, encoding="utf-8-sig", float_format="%.6g")
    return R


def main(app: bool = False, amounts: list[float] | None = None, ranking: str = RANKING) -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    inp = build_inputs(app, ranking)
    print(f"Dau vao: {ranking}")
    if "--ml-kho2015" in sys.argv:  # do nhay: kho sai so lui ve 2015 (python -m serving.forecast --oof-from 2015-Q1)
        run_ml(inp, origin_from="2015-Q1", arms=ML_MAIN, suffix="_kho2015", oof=OOF.replace(".csv", "_tu2015.csv"))
        return
    if "--ml" in sys.argv:  # chinh: kho tu 2023-Q1, seed SEED; do nhay: seed SEED_CHECK, kho 2021+ (chi cau hinh chinh)
        run_ml(inp)
        run_ml(inp, seed=SEED_CHECK, arms=ML_MAIN, modes=("tru_TB_NH",), suffix="_seed7")
        run_ml(inp, origin_from="2021-Q1", arms=ML_MAIN, suffix="_kho2021")
        R = ml_clip_report(inp)
        bad = R[R.so_bi_cat > 0]
        print(f"Cat mien (kho tu {ML_ORIGIN_FROM}): {len(bad)} dong NH x chi tieu x h x phuong an co kich ban bi cat")
        if len(bad):
            print(bad.reindex(bad.lech_TB_sau_cat.abs().sort_values(ascending=False).index).head(8).round(3).to_string(index=False))
        return
    if amounts:
        run_amounts(inp, amounts)
        return
    keep = (lambda s, c, part: with_app(s, c, part)) if app else (lambda s, c, part: (s, c))
    suffix = ("_co_app" if app else "") + ("_thieu_bat_loi" if MISSING == "bat_loi" else "") + (
        f"_suc_khoe_{round(LOAN_HEALTH_W * 100)}" + ("_von_chu" if HEALTH_CAPITAL == "von_chu" else "") if LOAN_HEALTH_W > 0 else "")
    if app:
        print("CO DIEM APP (doi chieu): gui = lai + an toan + app (50/30/20), vay them app (chia 4)")
    banks = inp["banks"]
    print(f"Anh chup: lai ngay {inp['rate_date']} ({len(inp['terms'])} ky han x 2 kenh), BCTC <= {LOOKBACK_Q} quy "
          f"(quy vua het {inp['now_q']}), lai vay den {inp['now_m']}; N = {N} vong / kich ban; o tranh chap: "
          f"{ {c: {banks[b]: v for b, v in d.items()} for c, d in inp['alt'].items()} }")
    # gui: moi ky han x kenh co trong file xep hang; vay: mot lan
    configs = [(term, ch) for term in inp["terms"] for ch in CHANNELS if rate_col(term, ch) in inp["rates"]]
    runs = [("gui", *keep(deposit_spec(term, ch), DEPOSIT_TOP, "gui"), term, ch) for term, ch in configs]
    runs.append(("vay", *keep(*loan_spec(), "vay"), None, None))
    tops, agrees, weights, summary = [], [], [], []
    for name, spec, center, term, ch in runs:
        missing = set()
        ip = inp
        if name == "gui":  # NH khong co lai cho ky han x kenh nay (khong co san pham / khong co so) -> khong xep
            missing = set(inp["vals"].index[inp["vals"][rate_col(term, ch)].isna()])
            ip = subset_inputs(inp, [b for b in banks if b not in missing])
        part = run_part(name, spec, center, ip, SEED)
        t, a, w = tables(part, ip["banks"])
        is_default = name == "vay" or (term, ch) == (DEFAULT_TERM, DEFAULT_CHANNEL)
        if is_default:  # hoi tu: hat giong khac, cung N
            t2, _, _ = tables(run_part(name, spec, center, ip, SEED_CHECK), ip["banks"])
            gap = (t.p_top1 - t2.p_top1).abs().max()
            a = pd.concat([a, pd.DataFrame([dict(part=name, scenario="tat_ca", metric="hoi_tu_max_abs_dP_top1", value=gap)])])
        for df in (t, a, w):
            df.insert(1, "term_months", term)
            df.insert(2, "channel", ch)
        tops.append(t), agrees.append(a), weights.append(w)
        if is_default:
            _print_detail(t, a, w, name if name == "vay" else f"gui {term}T {ch}")
            print(f"hoi tu (hai hat giong): lech P(top1) toi da {gap:.4f}")
        if name == "gui":
            summary += _summary_rows(t, a, dict(ky_han=term, kenh=ch, so_nh=len(ip["banks"])),
                                     khong_xep=",".join(sorted(missing)))
    print("\n=== Gui theo ky han x kenh: 3 NH co P(top1) / P(top3) TB 4 thuat toan bu tru cao nhat; wpm_nhom, wpm = tich "
          "(it bu tru hon); khong_xep = NH khong co lai o ky han x kenh do ===")
    print(pd.DataFrame(summary).to_string(index=False))

    os.makedirs(OUT_DIR, exist_ok=True)
    pd.concat(tops).round(4).to_csv(f"{OUT_DIR}/montecarlo_top{suffix}.csv", index=False, encoding="utf-8-sig")
    pd.concat(agrees).round(4).to_csv(f"{OUT_DIR}/montecarlo_agreement{suffix}.csv", index=False, encoding="utf-8-sig")
    pd.concat(weights).round(4).to_csv(f"{OUT_DIR}/montecarlo_weights{suffix}.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    def _arg(flag):
        return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else None
    amounts = _arg("--so-tien")  # vi du --so-tien 100e6,500e6,1e9
    if "--thieu-bat-loi" in sys.argv:
        MISSING = "bat_loi"
    if _arg("--suc-khoe-vay"):  # trong so nhom suc khoe ben cho vay, vd 0.1
        LOAN_HEALTH_W = float(_arg("--suc-khoe-vay"))
    if _arg("--von"):  # car (mac dinh) | von_chu
        HEALTH_CAPITAL = _arg("--von")
    main(app="--co-app" in sys.argv, amounts=[float(x) for x in amounts.split(",")] if amounts else None,
         ranking=_arg("--ranking") or RANKING)
