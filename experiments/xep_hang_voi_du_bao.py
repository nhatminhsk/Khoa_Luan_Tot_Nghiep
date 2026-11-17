import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from experiments import montecarlo_ranking as m

ANH_CHUP = "data/model/experiments/inputs/features_ranking_2026-11-06.csv"
DU_BAO = "data/model/experiments/forecasts_de_xuat.csv"
COT = {"npl": "npl_percent", "casa": "casa_percent", "ldr": "ldr_computed_percent"}
RA = "data/model/experiments/xep_hang_voi_du_bao.csv"


def thay_du_bao(inp: dict) -> tuple[dict, int]:
    f = pd.read_csv(DU_BAO)
    f = f[(f.horizon == 1) & f.indicator.isin(COT)]
    vals = inp["vals"].copy()
    n = 0
    for r in f.itertuples():
        if r.ticker in vals.index:
            vals.at[r.ticker, COT[r.indicator]] = r.value
            n += 1
    return {**inp, "vals": vals}, n


def bang(inp: dict, truong_hop: str) -> pd.DataFrame:
    if truong_hop == "vay":
        spec, center = m.loan_spec()
        part = m.run_part("vay", spec, center, inp, m.SEED)
        banks = inp["banks"]
    else:
        ia, scale = inp, None
        if truong_hop == "gui_5ty":
            ia = m.with_amount(inp, 5e9)
            u = m.uninsured_share(5e9, float(np.nanmedian(ia["vals"][m.rate_col(12, "online")])), 12)
            scale = {"an toan": max(u, m.BHTG_FLOOR)}
        ib = m.subset_inputs(ia, [b for b in ia["banks"] if pd.notna(ia["vals"].at[b, m.rate_col(12, "online")])])
        part = m.run_part("gui", m.deposit_spec(12, "online"), m.DEPOSIT_TOP, ib, m.SEED, scale)
        banks = ib["banks"]
    t, _, _ = m.tables(part, banks)
    t = t[(t.scenario == "quanh_mac_dinh") & t.algorithm.isin(m.COMPENSATORY)]
    return t.groupby("ticker")[["p_top1", "p_top3", "mean_rank"]].mean()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    goc = m.build_inputs(False, ANH_CHUP)
    db, n = thay_du_bao(goc)
    print(f"Đã thay {n} ô NPL/CASA/LDR bằng dự báo 1 quý")
    rows = []
    for th in ("gui_mac_dinh", "gui_5ty", "vay"):
        a, b = bang(goc, th), bang(db, th)
        k = a.join(b, lsuffix="_cong_bo", rsuffix="_du_bao")
        top_a = set(a.mean_rank.nsmallest(3).index)
        top_b = set(b.mean_rank.nsmallest(3).index)
        rho = spearmanr(k.mean_rank_cong_bo, k.mean_rank_du_bao).statistic
        dp = (k.p_top1_du_bao - k.p_top1_cong_bo).abs()
        print(f"\n{th}: ρ hạng TB = {rho:.3f}; top 3 công bố {sorted(top_a)} / dự báo {sorted(top_b)}; "
              f"|ΔP(top1)| lớn nhất {dp.max():.3f} ({dp.idxmax()})")
        print(k.sort_values("mean_rank_cong_bo").head(6).round(3).to_string())
        for t, r in k.iterrows():
            rows.append(dict(truong_hop=th, ticker=t, **r.to_dict(), rho_hang=rho,
                             trung_top3=len(top_a & top_b)))
    pd.DataFrame(rows).round(4).to_csv(RA, index=False, encoding="utf-8-sig")
    print("ghi", RA)


if __name__ == "__main__":
    main()
