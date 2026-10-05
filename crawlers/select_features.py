from __future__ import annotations

import numpy as np
import pandas as pd

FEATURES = "data/model/features_quarterly.csv"
SPEC = "data/model/feature_spec.csv"
CATALOG = "data/model/feature_catalog.csv"
SELECTED = "data/model/features_selected.csv"
RANKING = "data/model/features_ranking_latest.csv"
KEYS = ["period", "period_end", "ticker"]

KEEP, KEEP_RANK, DROP = "Giữ", "Giữ cho xếp hạng", "Loại"
MIN_COVERAGE, MIN_BANKS, MODE_MAX, RHO_MAX, OUTLIER_FLAG = 70.0, 20, 95.0, 0.90, 2.0
RECENT_QUARTERS = 4
# Tang 2 (lien he du bao): |rho| toan mau >= REL_MIN va cung dau, |rho| >= REL_HALF o ca hai nua
REL_MIN, REL_HALF, SPLIT_AFTER = 0.15, 0.10, "2022-Q2"
CORE, DESCRIBE = "Lõi dự báo", "Mô tả / xếp hạng"

TARGETS = ["nim_ttm_percent", "cof_ttm_percent", "npl_percent", "casa_percent", "ldr_computed_percent", "roe_ttm_percent"]
LEAK = {
    "nim_ttm_percent": ["yield_cof_spread_pp", "nim_chg_qoq_pp"],
    "cof_ttm_percent": ["deposit_rate_paid_ttm_pct", "deposit_cost_implied_ttm_percent", "yield_cof_spread_pp", "cof_chg_qoq_pp"],
    "npl_percent": ["npl_coverage_percent", "npl_chg_qoq_pp"],
    "casa_percent": ["casa_chg_qoq_pp"],
    "ldr_computed_percent": ["ldr_chg_qoq_pp", "loans_over_assets_percent", "deposits_to_liabilities_pct"],
    "roe_ttm_percent": ["roa_ttm_percent", "roaa_ttm_pct", "roae_ttm_pct", "roe_chg_qoq_pp", "npat_yoy_sym_pct"],
}
ABSOLUTE = {
    "loans_vnd": "Mức tuyệt đối (đồng) — đã có log_total_assets và thị phần dư nợ",
    "deposits_vnd": "Mức tuyệt đối (đồng) — đã có thị phần tiền gửi",
    "total_assets_vnd": "Mức tuyệt đối (đồng) — đã có log_total_assets",
    "loan_provision_vnd": "Mức tuyệt đối (đồng) — đã có dự phòng / dư nợ",
    "eps_vnd": "Tính trên mỗi cổ phiếu, phụ thuộc số cổ phiếu — đã có P/E, ROE",
    "bvps_vnd": "Tính trên mỗi cổ phiếu, phụ thuộc số cổ phiếu — đã có P/B",
}
# bien bi loai -> (bien giu, ly do)
CONCEPT_DUP = {
    "car_percent": ("car_asof_percent", "Cùng CAR; bản as-of phủ cả quý giữa kỳ"),
    "cir_ttm_approx_percent": ("cir_ttm_pct", "Cùng CIR; bản tính trực tiếp từ KQKD có công thức rõ, bản MAS xấp xỉ và có ô 976%"),
    "roaa_ttm_pct": ("roa_ttm_percent", "Cùng ROA (r = 0,998); bản panel phủ 98,7%"),
    "roae_ttm_pct": ("roe_ttm_percent", "Cùng ROE (r = 0,998); bản panel phủ 98,7%"),
    "deposit_rate_paid_ttm_pct": ("deposit_cost_implied_ttm_percent", "Cùng chi phí trả lãi tiền gửi (r = 0,999)"),
    "ind_share_A_asof_pct": ("agri_share_asof_pct", "Cùng tỷ trọng nông nghiệp; agri_loans_annual phủ nhiều NH-năm hơn"),
}
# thu tu uu tien khi hai bien trung thong tin: tieu chi cot loi cua xep hang va muc tieu truoc
PRIORITY = [
    "npl_percent", "casa_percent", "nim_ttm_percent", "cof_ttm_percent", "ldr_computed_percent", "roe_ttm_percent",
    "roa_ttm_percent", "car_asof_percent", "equity_to_assets_pct", "cir_ttm_pct", "log_total_assets", "loans_yoy_percent",
    "earning_asset_yield_ttm_percent", "npl_coverage_percent", "loans_g2_percent", "credit_cost_ttm_pct", "pb", "pe",
    "deposit_cost_implied_ttm_percent", "liquid_assets_pct", "app_mean_score", "app_reviews_log", "dep12_online_pct",
    "refinancing_rate_pct", "cpi_yoy_q_pct", "vnindex_ret_q_pct", "stock_ret_q_pct", "n_programs_active",
    "agri_share_asof_pct", "state_own_percent", "loan_market_share_pct",
]


def _stats(f: pd.DataFrame, spec: pd.DataFrame) -> pd.DataFrame:
    periods = sorted(f.period.unique())
    recent = f[f.period.isin(periods[-RECENT_QUARTERS:])]
    rows = []
    for r in spec.itertuples():
        s = f[r.feature]
        nn = s.dropna()
        q1, q3 = nn.quantile([0.25, 0.75]) if len(nn) else (np.nan, np.nan)
        iqr = q3 - q1
        out_share = float(((nn < q1 - 3 * iqr) | (nn > q3 + 3 * iqr)).mean() * 100) if len(nn) and iqr > 0 else 0.0
        bank_means = f.groupby("ticker")[r.feature].mean()
        total_var = nn.var()
        icc = float(bank_means.var() / total_var) if total_var and total_var > 0 and r.kind == "theo NH-quý" else np.nan
        have = f.loc[s.notna(), "period"]
        rows.append(dict(
            feature=r.feature, coverage_pct=round(float(s.notna().mean() * 100), 1),
            n_banks=int(f.loc[s.notna(), "ticker"].nunique()),
            banks_last4q=int(recent.loc[recent[r.feature].notna(), "ticker"].nunique()),
            first_period=have.min() if len(have) else "", last_period=have.max() if len(have) else "",
            mode_share_pct=round(float(nn.value_counts(normalize=True).iloc[0] * 100), 1) if len(nn) else 100.0,
            icc=round(min(icc, 1.0), 3) if not np.isnan(icc) else np.nan,
            outlier_share_pct=round(out_share, 1),
            median=nn.median() if len(nn) else np.nan, p01=nn.quantile(0.01) if len(nn) else np.nan,
            p99=nn.quantile(0.99) if len(nn) else np.nan,
        ))
    return spec.merge(pd.DataFrame(rows), on="feature")


def _spearman(f: pd.DataFrame, a: str, b: str, kind_a: str, kind_b: str) -> float:
    if kind_a == "chung mọi NH" and kind_b == "chung mọi NH":
        d = f.groupby("period")[[a, b]].first().dropna()
    else:
        d = f[[a, b]].dropna()
    if len(d) < (20 if kind_a == kind_b == "chung mọi NH" else 200) or d[a].nunique() < 3 or d[b].nunique() < 3:
        return np.nan
    return float(d[a].rank().corr(d[b].rank()))


def _relevance(f: pd.DataFrame, cat: pd.DataFrame) -> pd.DataFrame:
    
    f = f.sort_values(["ticker", "period"]).copy()
    qi = f.period.str[:4].astype(int) * 4 + f.period.str[-1].astype(int)
    consecutive = f.groupby("ticker")["period"].shift(-1).notna() & (qi.groupby(f.ticker).shift(-1) - qi == 1)
    first_half = f.period <= SPLIT_AFTER
    kind = dict(zip(cat.feature, cat.kind))
    out = {}
    for t in TARGETS:
        y = (f.groupby("ticker")[t].shift(-1) - f[t]).where(consecutive)
        col = {}
        for feat in cat.loc[cat.decision == KEEP, "feature"]:
            if kind[feat] == "tĩnh theo NH":
                continue
            x = f[feat] - f.groupby("ticker")[feat].transform("mean") if kind[feat] == "theo NH-quý" else f[feat]
            d = pd.DataFrame({"x": x, "y": y, "h": first_half}).dropna()
            if len(d) < 200 or d.x.nunique() < 3:
                continue
            rho = d.x.rank().corr(d.y.rank())
            r1 = d[d.h].x.rank().corr(d[d.h].y.rank())
            r2 = d[~d.h].x.rank().corr(d[~d.h].y.rank())
            ok = abs(rho) >= REL_MIN and min(abs(r1), abs(r2)) >= REL_HALF and np.sign(r1) == np.sign(r2) == np.sign(rho)
            col[feat] = (round(rho, 3), ok)
        out[t] = col
    rel = pd.DataFrame({"feature": cat.feature})
    for t, col in out.items():
        rel[f"rho_next_{t}"] = rel.feature.map(lambda x: col.get(x, (np.nan, False))[0])
    rel["relevant_for"] = rel.feature.map(lambda x: ", ".join(t for t, col in out.items() if col.get(x, (0, False))[1]))
    return rel


def select() -> pd.DataFrame:
    f = pd.read_csv(FEATURES, encoding="utf-8-sig")
    spec = pd.read_csv(SPEC, encoding="utf-8-sig")
    cat = _stats(f, spec)
    cat["decision"], cat["reason"], cat["redundant_with"], cat["rho"] = "", "", "", np.nan

    def set_(mask, decision, reason):
        m = mask & (cat.decision == "")
        cat.loc[m, "decision"] = decision
        cat.loc[m, "reason"] = reason if isinstance(reason, str) else reason[m]

    set_(cat.feature.isin(ABSOLUTE), DROP, cat.feature.map(ABSOLUTE).fillna(""))
    dup = cat.feature.isin(CONCEPT_DUP)
    cat.loc[dup & (cat.decision == ""), "redundant_with"] = cat.feature.map(lambda x: CONCEPT_DUP.get(x, ("", ""))[0])
    set_(dup, DROP, cat.feature.map(lambda x: CONCEPT_DUP.get(x, ("", ""))[1]))
    set_(cat.mode_share_pct >= MODE_MAX, DROP, cat.mode_share_pct.map(lambda v: f"Gần như hằng số: một giá trị chiếm {v:.0f}% số ô"))
    low = (cat.coverage_pct < MIN_COVERAGE) | (cat.n_banks < MIN_BANKS)
    rank_ok = low & (cat.kind == "theo NH-quý") & (cat.banks_last4q >= MIN_BANKS)
    set_(rank_ok, KEEP_RANK, cat.apply(lambda r: f"Phủ {r.coverage_pct:.1f}% (từ {r.first_period}) — không đủ cho panel lịch sử, "
                                               f"nhưng {r.banks_last4q}/22 NH có số trong 4 quý gần nhất", axis=1))
    set_(low, DROP, cat.apply(lambda r: f"Phủ thấp: {r.coverage_pct:.1f}% ô (ngưỡng {MIN_COVERAGE:.0f}%), {r.n_banks}/22 NH, "
                                        f"4 quý gần nhất {r.banks_last4q}/22 NH", axis=1))

    # R4: trung thong tin, tham lam theo uu tien
    cand = cat[cat.decision == ""].copy()
    cand["prio"] = cand.feature.map({x: i for i, x in enumerate(PRIORITY)}).fillna(len(PRIORITY))
    cand = cand.sort_values(["prio", "coverage_pct", "outlier_share_pct"], ascending=[True, False, True])
    kind = dict(zip(cat.feature, cat.kind))
    kept: list[str] = []
    for feat in cand.feature:
        hit = None
        for k in kept:
            rho = _spearman(f, feat, k, kind[feat], kind[k])
            if not np.isnan(rho) and abs(rho) >= RHO_MAX:
                hit = (k, rho)
                break
        i = cat.index[cat.feature == feat][0]
        if hit:
            cat.loc[i, ["decision", "reason", "redundant_with", "rho"]] = [
                DROP, f"Trùng thông tin với {hit[0]} (Spearman {hit[1]:+.2f})", hit[0], round(hit[1], 3)]
        else:
            cat.loc[i, "decision"] = KEEP
            kept.append(feat)
    cat.loc[(cat.decision == KEEP) & (cat.reason == ""), "reason"] = "Qua cả 5 quy tắc"

    leak = {x: [t for t, fs in LEAK.items() if x in fs] for x in cat.feature}

    def flags(r):
        out = [f"leak:{t}" for t in leak[r.feature]]
        if r.outlier_share_pct > OUTLIER_FLAG:
            out.append("ngoại lai")
        if r.kind == "tĩnh theo NH":
            out.append("tĩnh")
        if r.kind == "chung mọi NH":
            out.append("chung")
        if "as-of" in str(r.processing):
            out.append("as-of")
        if r.feature in TARGETS:
            out.append("mục tiêu dự báo")
        return ", ".join(out)

    cat["flags"] = cat.apply(flags, axis=1)
    cat = cat.merge(_relevance(f, cat), on="feature", how="left")
    cat["use"] = np.where(cat.decision != KEEP, "", np.where(cat.relevant_for.fillna("") != "", CORE, DESCRIBE))
    order = {KEEP: 0, KEEP_RANK: 1, DROP: 2}
    cat = cat.sort_values(["decision", "use", "group", "feature"], key=lambda s: s.map(order) if s.name == "decision" else s)
    cols = ["feature", "group", "kind", "decision", "use", "reason", "flags", "relevant_for"] + [f"rho_next_{t}" for t in TARGETS] + [
            "redundant_with", "rho", "coverage_pct", "n_banks", "banks_last4q", "first_period", "last_period", "mode_share_pct",
            "icc", "outlier_share_pct", "median", "p01", "p99", "unit", "formula", "source", "processing"]
    cat = cat[cols]
    cat.to_csv(CATALOG, index=False, encoding="utf-8-sig")

    keep = cat.loc[cat.decision == KEEP, "feature"].tolist()
    f[KEYS + keep].to_csv(SELECTED, index=False, encoding="utf-8-sig")

    rank_cols = cat.loc[cat.decision.isin([KEEP, KEEP_RANK]) & (cat.kind != "chung mọi NH"), "feature"].tolist()
    periods = sorted(f.period.unique())[-RECENT_QUARTERS:]
    recent = f[f.period.isin(periods)].sort_values("period")
    latest = recent.groupby("ticker")[rank_cols].agg("last")  # gia tri khac rong gan nhat
    asof = recent.groupby("ticker")["period"].max()
    latest.insert(0, "window", f"{periods[0]}..{periods[-1]}")
    latest.insert(1, "latest_period", asof)
    latest.reset_index().to_csv(RANKING, index=False, encoding="utf-8-sig")
    return cat


def summary(cat: pd.DataFrame) -> dict:
    by = cat.groupby("decision").feature.apply(list).to_dict()
    core = cat[cat.use == CORE]
    return {
        "features": len(cat),
        "counts": cat.decision.value_counts().to_dict(),
        "use_counts": cat.loc[cat.decision == KEEP, "use"].value_counts().to_dict(),
        "core_by_target": {t: core.loc[core.relevant_for.str.contains(t), "feature"].tolist() for t in TARGETS},
        "kept_by_group": cat[cat.decision == KEEP].groupby("group").feature.apply(list).to_dict(),
        "keep_for_ranking": by.get(KEEP_RANK, []),
        "dropped": cat.loc[cat.decision == DROP, ["feature", "reason"]].values.tolist(),
        "paths": [CATALOG, SELECTED, RANKING],
    }


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(summary(select()), indent=2, ensure_ascii=False, default=str))
