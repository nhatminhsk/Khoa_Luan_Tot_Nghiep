from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from experiments import montecarlo_ranking as m

ANH_CHUP = "data/model/experiments/inputs/features_ranking_2026-11-06.csv"
OUT = Path("data/model/experiments/do_nhay_xep_hang")
QUET_LAI = [0.2, 0.3, 0.4, 0.5, 0.625, 0.7, 0.8, 0.9]
QUET_GIA = [0.2, 1 / 3, 0.5, 0.6, 0.7]
KAPPAS = [10.0, 30.0, 100.0]
NS = [1000, 2000, 5000, 10000, 20000]
HAT = [m.SEED, 1, 2, 3, 4]
CAT_NGOAI_LE = ["car_asof_percent", "equity_to_assets_pct", "npl_percent", "loans_g2_percent", "credit_cost_ttm_pct",
                "accrued_interest_to_assets_pct", "cir_ttm_pct", "roa_ttm_percent", "ldr_computed_percent",
                "liquid_assets_pct", "casa_percent", "corp_bond_to_assets_pct", "retail_loan_share_pct",
                "loan_yield_ttm_pct"]


def _gui(inp: dict, center: dict | None = None, spec: dict | None = None) -> tuple[dict, list[str]]:
    col = m.rate_col(12, "online")
    ib = m.subset_inputs(inp, [b for b in inp["banks"] if pd.notna(inp["vals"].at[b, col])])
    part = m.run_part("gui", spec or m.deposit_spec(12, "online"), center or m.DEPOSIT_TOP, ib, m.SEED)
    return part, ib["banks"]


def _vay(inp: dict, center: dict | None = None, spec: dict | None = None) -> tuple[dict, list[str]]:
    s0, c0 = m.loan_spec()
    part = m.run_part("vay", spec or s0, center or c0, inp, m.SEED)
    return part, inp["banks"]


def _ket_qua(part: dict, banks: list[str]) -> tuple[pd.DataFrame, float]:
    t, a, _ = m.tables(part, banks)
    t = t[(t.scenario == "quanh_mac_dinh") & t.algorithm.isin(m.COMPENSATORY)]
    g = t.groupby("ticker")[["p_top1", "p_top3", "mean_rank"]].mean()
    agree = float(a[(a.scenario == "quanh_mac_dinh") & (a.metric == "ca_4_cung_top1")].value.iloc[0])
    return g, agree


def _so(g: pd.DataFrame, g0: pd.DataFrame, agree: float, **kw) -> dict:
    k = g0.join(g, lsuffix="_0", rsuffix="_1", how="inner")
    top = g.p_top1.sort_values(ascending=False)
    top3 = list(g.mean_rank.nsmallest(3).index)
    top3_0 = list(g0.mean_rank.nsmallest(3).index)
    return dict(**kw, dung_dau=top.index[0], ty_le_dung_dau=top.iloc[0], thu_hai=top.index[1], ty_le_thu_hai=top.iloc[1],
                top3=", ".join(top3), trung_top3=len(set(top3) & set(top3_0)),
                rho=spearmanr(k.mean_rank_0, k.mean_rank_1).statistic, ca_4_cung_top1=agree)


def quet_trong_so(inp: dict, g0: pd.DataFrame, rows: list) -> None:
    for w in QUET_LAI:
        part, banks = _gui(inp, {"lai": w, "an toan": 1 - w})
        g, agree = _ket_qua(part, banks)
        rows.append(_so(g, g0, agree, phan="gui", phep_thu="trong_so_lai", gia_tri=w))
        print(f"  gửi, lãi {w:.3f}: {rows[-1]['dung_dau']} {rows[-1]['ty_le_dung_dau']:.3f}, ρ {rows[-1]['rho']:.3f}",
              flush=True)


def kappa_va_tru(inp: dict, g0: pd.DataFrame, rows: list) -> None:
    k0 = m.KAPPA
    for k in KAPPAS:
        m.KAPPA = k
        g, agree = _ket_qua(*_gui(inp))
        rows.append(_so(g, g0, agree, phan="gui", phep_thu="kappa", gia_tri=k))
    m.KAPPA = k0
    goc = m.draw_weights

    def tru_chia_deu(spec, center, mode, rng, n, scale=None):
        cols, tops, pillars = m._structure(spec)
        c0 = np.array([center[t] for t in tops])
        top = np.repeat(c0[None], n, axis=0) if rng is None else rng.dirichlet(
            np.ones(len(tops)) if mode == "flat" else m.KAPPA * c0, n)
        if scale:
            top = top * np.array([scale.get(t, 1.0) for t in tops])
            top = top / top.sum(1, keepdims=True)
        W = np.zeros((n, len(cols)))
        for ti, t in enumerate(tops):
            ps = pillars[t]
            for p in ps:
                idx = [j for j, c in enumerate(cols) if spec[c][1] == t and spec[c][2] == p]
                W[:, idx] = (top[:, ti] / len(ps) / len(idx))[:, None]
        return W, top

    m.draw_weights = tru_chia_deu
    try:
        g, agree = _ket_qua(*_gui(inp))
        rows.append(_so(g, g0, agree, phan="gui", phep_thu="tru_chia_deu", gia_tri=1))
    finally:
        m.draw_weights = goc


def on_dinh_mc(inp: dict) -> pd.DataFrame:
    n0, seed0 = m.N, m.SEED
    out = []
    for n in NS:
        for s in HAT:
            m.N, m.SEED = n, s
            g, agree = _ket_qua(*_gui(inp))
            top = g.p_top1.sort_values(ascending=False)
            out.append(dict(N=n, hat=s, VPB=g.p_top1.get("VPB", np.nan), VIB_top3=g.p_top3.get("VIB", np.nan),
                            dung_dau=top.index[0], ty_le=top.iloc[0], ca_4=agree))
        print(f"  N={n} xong", flush=True)
    m.N, m.SEED = n0, seed0
    return pd.DataFrame(out)


def du_lieu(inp: dict, g0: pd.DataFrame, rows: list, gv0: pd.DataFrame) -> None:
    thieu = {c: list(inp["vals"].index[inp["vals"][c].isna()]) for c in CAT_NGOAI_LE + ["lending_avg_pct"]}
    print("  ô thiếu:", {k: v for k, v in thieu.items() if v})
    m.MISSING = "bat_loi"
    try:
        g, agree = _ket_qua(*_gui(inp))
        rows.append(_so(g, g0, agree, phan="gui", phep_thu="thieu_xau_nhat", gia_tri=1))
        g, agree = _ket_qua(*_vay(inp))
        rows.append(_so(g, gv0, agree, phan="vay", phep_thu="thieu_xau_nhat", gia_tri=1))
    finally:
        m.MISSING = "trung_vi"
    vals = inp["vals"].copy()
    for c in CAT_NGOAI_LE:
        lo, hi = vals[c].quantile([0.05, 0.95])
        vals[c] = vals[c].clip(lo, hi)
    ic = {**inp, "vals": vals}
    g, agree = _ket_qua(*_gui(ic))
    rows.append(_so(g, g0, agree, phan="gui", phep_thu="cat_ngoai_le_5_95", gia_tri=1))
    g, agree = _ket_qua(*_vay(ic))
    rows.append(_so(g, gv0, agree, phan="vay", phep_thu="cat_ngoai_le_5_95", gia_tri=1))
    spec = {k: v for k, v in m.deposit_spec(12, "online").items() if k != "car_asof_percent"}
    g, agree = _ket_qua(*_gui(inp, spec=spec))
    rows.append(_so(g, g0, agree, phan="gui", phep_thu="bo_CAR", gia_tri=1))


def phia_vay(inp: dict, gv0: pd.DataFrame, rows: list) -> None:
    s0, c0 = m.loan_spec()
    for w in QUET_GIA:
        c = {"gia": w, "phu hop": (1 - w) / 2, "suc cho vay": (1 - w) / 2}
        g, agree = _ket_qua(*_vay(inp, c))
        rows.append(_so(g, gv0, agree, phan="vay", phep_thu="trong_so_gia", gia_tri=w))
    for bo, nhom in (("bo_LDR", "suc cho vay"), ("bo_ty_trong_ca_nhan", "phu hop")):
        spec = {k: v for k, v in s0.items() if v[1] != nhom}
        c = {k: v for k, v in c0.items() if k != nhom}
        c = {k: v / sum(c.values()) for k, v in c.items()}
        g, agree = _ket_qua(*_vay(inp, c, spec))
        rows.append(_so(g, gv0, agree, phan="vay", phep_thu=bo, gia_tri=1))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    inp = m.build_inputs(False, ANH_CHUP)
    g0, a0 = _ket_qua(*_gui(inp))
    gv0, av0 = _ket_qua(*_vay(inp))
    print(f"mặc định gửi: {g0.p_top1.idxmax()} {g0.p_top1.max():.3f}, cả 4 {a0:.3f}; vay: {gv0.p_top1.idxmax()} "
          f"{gv0.p_top1.max():.3f}, cả 4 {av0:.3f}")
    g0.to_csv(OUT / "mac_dinh_gui.csv", encoding="utf-8-sig")
    gv0.to_csv(OUT / "mac_dinh_vay.csv", encoding="utf-8-sig")
    rows: list[dict] = []
    quet_trong_so(inp, g0, rows)
    kappa_va_tru(inp, g0, rows)
    du_lieu(inp, g0, rows, gv0)
    phia_vay(inp, gv0, rows)
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "do_nhay.csv", index=False, encoding="utf-8-sig")
    print(R.round(3).to_string())
    M = on_dinh_mc(inp)
    M.to_csv(OUT / "on_dinh_monte_carlo.csv", index=False, encoding="utf-8-sig")
    print(M.groupby("N")[["VPB", "VIB_top3", "ca_4"]].agg(["mean", "std", "min", "max"]).round(4).to_string())
    print(f"xong sau {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
