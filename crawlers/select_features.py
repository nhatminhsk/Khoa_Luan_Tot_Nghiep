from __future__ import annotations

import os
import sys
from datetime import date

import numpy as np
import pandas as pd

FEATURES = "data/model/features_quarterly.csv"
SPEC = "data/model/feature_spec.csv"
CATALOG = "data/model/feature_catalog.csv"
SELECTED = "data/model/features_selected.csv"  # bien co tac dung (tang 3) -- dau vao du an
CLEAN = "data/model/features_clean.csv"  # moi bien qua tang 1 (sach); EDA va thi nghiem doc file nay de do TRUOC khi chon
RANKING = "data/model/features_ranking_latest.csv"  # dau vao xep hang: BCTC quy gan nhat + lai suat / diem app moi nhat
KEYS = ["period", "period_end", "ticker"]

KEEP, KEEP_RANK, DROP = "Giữ", "Giữ cho xếp hạng", "Loại"
MIN_COVERAGE, MIN_BANKS, MODE_MAX, RHO_MAX, OUTLIER_FLAG = 70.0, 20, 95.0, 0.90, 2.0
RECENT_QUARTERS = 4
# Khong xet trung o R4: loi suat cho vay la tieu chi xep hang vay, loi suat TSSL chi hien tren ho so NH nen khong cong trung
# vao cung mot phep xep hang. Rho toan panel len tu 0,76 toi 0,91 ngay 02/11/2026 khi bo so 0 gia cua MAS.
R4_EXEMPT = {"loan_yield_ttm_pct", "earning_asset_yield_ttm_percent"}
# Tang 2 (chi MO TA, khong dung de chon): Spearman giua bien quy t (tru trung binh QUA KHU cua NH) va thay doi
# muc tieu t -> t+1. Truoc 13/10/2026 tru trung binh ca mau (lo tuong lai) va dung tang nay dat nhan "Loi du bao"
# cho 28 bien; thi nghiem walk-forward (tang 3) khong xac nhan nhan do.
REL_MIN, REL_HALF, SPLIT_AFTER = 0.15, 0.10, "2022-Q2"

# Tang 3 (13/10/2026): TAC DUNG. Tang 1 chi noi bien SACH; bien chi con duoc Giu khi co it nhat mot vai tro duoi day,
# do bang `experiments.feature_effect` (so lieu: data/model/experiments/feature_effect_*.csv).
#   Mục tiêu dự báo  6 chi tieu du bao.
#   Đầu vào dự báo   Mo hinh du bao = base co cau truc + Random Forest hoc phan du tren bo loi: lich su cua chinh chi
#                    tieu, so rieng tung quy (quy roi khoi TTM), lai tai cap von tre, quy trong nam. Them tung nhom
#                    CAMELS vao bo loi: tot len co y nghia 13 lan, te di 30 lan / 216 phep thu; chon nhom LONG tren
#                    2021-22 khong nhom nao thang bo loi tren 2023+ (0/18 o); dua ca 90 bien sach vao lam COF 4 quy
#                    te hon base 16,8%. Bien catalog duy nhat co tac dung la lai tai cap von: bo ra thi te di o 9/18 o
#                    (COF 2 quy 13,4%, 4 quy 16,5%). Tang truong tin dung he thong thi khong: bo ra te di 2 o (deu la
#                    o mo hinh thua base), tot len 3 o -> loai (algorithm_benchmark doc features_clean.csv nen
#                    van tai lap duoc ket qua 18/09).
#   Xếp hạng gửi     tieu chi an toan, moi tru CAMELS mot-hai bien chuan + loi ich (lai 12 thang) + trai nghiem (diem app).
#   Xếp hạng vay     gia vay (lai cho vay NH tu cong bo, loi suat cho vay tu BCTC) + muc tap trung cho vay ca nhan.
#   Hồ sơ NH         chi tieu hien tren ho so NH cua web (serving/export.py INDICATORS).
# Tieu chi xep hang con phai qua do o cat ngang 22 NH (feature_effect_ranking.csv): thu hang NH ben sau 4 quy
# (Spearman >= RANK_PERSIST; lai suat va diem app duoc web cap nhat lien tuc nen chi xet sau 1 quy) va khong trung
# voi tieu chi khac (|Spearman cat ngang| < RHO_MAX). Khong bien an toan nao bao truoc duoc thay doi NPL / ROA 4 quy
# toi (|t| < 2 o 76/78 bien) nen khong chon tieu chi theo kha nang bao truoc.
TARGET, FC_INPUT, RANK_DEP, RANK_LOAN, PROFILE = "Mục tiêu dự báo", "Đầu vào dự báo", "Xếp hạng gửi", "Xếp hạng vay", "Hồ sơ NH"
RANK_PERSIST = 0.5
ROLES = {
    "nim_ttm_percent": [TARGET, PROFILE], "cof_ttm_percent": [TARGET, PROFILE], "roe_ttm_percent": [TARGET, PROFILE],
    "npl_percent": [TARGET, RANK_DEP, PROFILE], "casa_percent": [TARGET, RANK_DEP, PROFILE],
    "ldr_computed_percent": [TARGET, RANK_DEP, RANK_LOAN, PROFILE],
    "refinancing_rate_pct": [FC_INPUT],
    # C
    "car_asof_percent": [RANK_DEP, PROFILE], "equity_to_assets_pct": [RANK_DEP],
    # A -- lai du thu: ung vien them 13/10, gan nhu khong trung NPL (rho cat ngang 0,10) hay no nhom 2 (-0,04)
    "loans_g2_percent": [RANK_DEP, PROFILE], "credit_cost_ttm_pct": [RANK_DEP], "accrued_interest_to_assets_pct": [RANK_DEP],
    # M, E, L, S
    "cir_ttm_pct": [RANK_DEP, PROFILE], "roa_ttm_percent": [RANK_DEP, PROFILE], "liquid_assets_pct": [RANK_DEP],
    "corp_bond_to_assets_pct": [RANK_DEP],
    # quy mo, so huu nha nuoc: kenh "qua lon de do" ma nguoi gui dua vao
    "log_total_assets": [RANK_DEP], "state_own_percent": [RANK_DEP],
    # loi ich, trai nghiem
    "dep12_online_pct": [RANK_DEP], "dep12_counter_pct": [RANK_DEP],
    # app_mean_score: bo khoi xep hang 14/10/2026 (ly do o NO_EFFECT_NOTE)
    # vay
    "lending_avg_pct": [RANK_LOAN], "loan_yield_ttm_pct": [RANK_LOAN, PROFILE], "retail_loan_share_pct": [RANK_LOAN, PROFILE],
    # chi hien tren ho so
    "earning_asset_yield_ttm_percent": [PROFILE], "loans_yoy_percent": [PROFILE],
}
REFRESHED = {"dep12_online_pct", "dep12_counter_pct", "lending_avg_pct"}
# features_ranking_latest lay so MOI NHAT cho REFRESHED (xem _fresh), khong lay trung binh quy
FRESH_DAYS, LENDING_MAX_MONTHS, APP_MIN_MONTHS, APP_MAX_MONTHS = 7, 12, 3, 12
EFFECT_FORECAST = "data/model/experiments/feature_effect_forecast.csv"
EFFECT_RANKING = "data/model/experiments/feature_effect_ranking.csv"
EFFECT_NESTED = "data/model/experiments/feature_effect_nested.csv"

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
            # tru trung binh QUA KHU cua NH (den quy t-1), khong dung trung binh ca mau vi lo tuong lai
            past = f.groupby("ticker")[feat].transform(lambda s: s.expanding().mean().shift(1))
            x = f[feat] - past if kind[feat] == "theo NH-quý" else f[feat]
            d = pd.DataFrame({"x": x, "y": y, "h": first_half}).dropna()
            if len(d) < 200 or d.x.nunique() < 3:
                continue
            with np.errstate(invalid="ignore", divide="ignore"):  # mot nua mau co the hang so
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


def _vn(x: float, d: int = 2) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def _effect_evidence():
    grp, rank = {}, pd.DataFrame()
    if os.path.exists(EFFECT_FORECAST):
        s = pd.read_csv(EFFECT_FORECAST, encoding="utf-8-sig")
        nst = pd.read_csv(EFFECT_NESTED, encoding="utf-8-sig") if os.path.exists(EFFECT_NESTED) else pd.DataFrame()
        for cfg, d in s[s.config.str.startswith("core+")].groupby("config"):
            g = cfg[len("core+"):]
            chosen = nst[nst.groups.fillna("").str.split("+").map(lambda x: g in x)] if len(nst) else nst
            won = int((chosen.chosen_vs_core_lo > 0).sum()) if len(chosen) else 0
            grp[g] = (int((d.lo_vs_ref > 0).sum()), int((d.hi_vs_ref < 0).sum()), len(d), len(chosen), won)
    if os.path.exists(EFFECT_RANKING):
        rank = pd.read_csv(EFFECT_RANKING, encoding="utf-8-sig").set_index("feature")
    if not grp or rank.empty:
        print(f"CANH BAO: thieu {EFFECT_FORECAST} hoac {EFFECT_RANKING} -> ly do tang 3 khong co so do; "
              "chay python -m experiments.feature_effect", file=sys.stderr)
    return grp, rank


# Ghi chu rieng cho vai bien bi loai o tang 3 ma so do chung chua noi het
NO_EFFECT_NOTE = {
    "app_mean_score": "bỏ khỏi xếp hạng 14/10/2026 (người dùng chốt): điểm app đo ứng dụng chứ không đo NH; NH nhỏ ít "
                      "review (PGB 31 review / 3 tháng, 4,71 sao, kéo PGB lên đầu gần mọi kỳ hạn); có đợt review bất "
                      "thường (BID 09/2026: 1.547 review, 4,54 sao). Monte Carlo gửi 12 tháng online: bỏ app thì 4 thuật "
                      "toán cùng top 1 từ 15% lên 41% số vòng",
    "system_credit_growth_asof_pct": "bỏ khỏi bộ lõi dự báo: tốt lên 3/18 ô, chỉ tệ đi ở 2 ô mà mô hình vốn thua base",
    "dep12_online_spread_pp": "cắt ngang trùng hẳn dep12_online_pct (cùng quý trừ cùng một trung bình)",
    "app_pct_1star": "cắt ngang trùng app_mean_score",
    "vamc_bonds_to_assets_pct": "ứng viên 13/10: VAMC gần hết, 2026-Q2 chỉ 5/22 NH còn số > 0",
    "retail_deposit_share_pct": "ứng viên 13/10: phủ 50% và trùng cắt ngang phí BHTG / tiền gửi (phí chỉ tính trên tiền gửi cá nhân)",
    "log_branches": "đếm từ OpenStreetMap, chỉ phủ ~39% điểm giao dịch NH tự công bố (TPB)",
    "n_provinces_present": "đếm từ OpenStreetMap, phủ thiếu",
    "atm_per_branch": "đếm từ OpenStreetMap, phủ thiếu",
}
# Ly do xep hang rieng theo nhom khi bien khong dao hang, khong trung ma van khong la tieu chi
GROUP_RANK_NOTE = {
    "T": "chỉ số cho nhà đầu tư cổ phiếu, không phải tiêu chí người gửi/vay",
    "P": "tham gia chương trình đã hiện riêng trên web (programs.csv); làm biến thì gần như tĩnh",
    "S": "trụ S đã có trái phiếu doanh nghiệp / tổng tài sản (rủi ro người gửi lo nhất sau 2022)",
}


def _no_effect_reason(r, grp, rank) -> str:
    parts = [NO_EFFECT_NOTE[r.feature]] if r.feature in NO_EFFECT_NOTE else []
    g = r.group[0]
    if g in grp and r.feature != "system_credit_growth_asof_pct":
        plus, minus, n, picked, won = grp[g]
        parts.append(f"dự báo: thêm nhóm {g} vào bộ lõi tốt lên {plus}/{n} ô, tệ đi {minus}/{n} ô (nhìn tập kiểm tra); "
                     f"chọn lồng chọn {g} ở {picked} ô, thắng bộ lõi {won} ô")
    elif g not in grp and r.kind != "chung mọi NH":
        parts.append("dự báo: không thử (phủ ít, chỉ từ 2023)")
    if r.kind == "chung mọi NH":
        parts.append("xếp hạng: biến vĩ mô chung, không phân biệt NH")
    elif r.feature in rank.index:
        x = rank.loc[r.feature]
        if r.kind == "tĩnh theo NH":
            parts.append("xếp hạng: ảnh chụp một ngày, không phải tiêu chí gửi/vay")
        elif pd.notna(x.persist_4q) and x.persist_4q < RANK_PERSIST:
            parts.append(f"xếp hạng: thứ hạng NH sau 4 quý chỉ còn ρ = {_vn(x.persist_4q)}")
        elif pd.notna(x.xs_partner_rho) and abs(x.xs_partner_rho) >= 0.75:
            parts.append(f"xếp hạng: cắt ngang gần trùng {x.xs_partner} (ρ = {_vn(x.xs_partner_rho)})")
        else:
            parts.append("xếp hạng: " + GROUP_RANK_NOTE.get(g, "không phải tiêu chí gửi/vay, trụ CAMELS đã có biến chuẩn hơn"))
    return "Không tác dụng — " + "; ".join(parts)


def _apply_effect(cat: pd.DataFrame) -> pd.DataFrame:
    grp, rank = _effect_evidence()
    roles = {k: list(v) for k, v in ROLES.items()}
    notes = {}
    for feat, rs in roles.items():
        if feat not in rank.index or not ({RANK_DEP, RANK_LOAN} & set(rs)):
            continue
        x = rank.loc[feat]
        p, k = (x.persist_1q, "1 quý") if feat in REFRESHED else (x.persist_4q, "4 quý")
        partner_is_crit = x.xs_partner in roles and bool({RANK_DEP, RANK_LOAN} & set(roles[x.xs_partner]))
        if x.kind != "tĩnh theo NH" and pd.notna(p) and p < RANK_PERSIST:
            notes[feat] = f"bỏ vai trò xếp hạng: thứ hạng NH sau {k} chỉ còn ρ = {_vn(p)}"
        elif partner_is_crit and abs(x.xs_partner_rho) >= RHO_MAX:
            notes[feat] = f"bỏ vai trò xếp hạng: cắt ngang trùng {x.xs_partner} (ρ = {_vn(x.xs_partner_rho)})"
        else:
            notes[feat] = (f"thứ hạng NH bền ρ = {_vn(p)} sau {k}" if x.kind != "tĩnh theo NH" else "ảnh chụp tĩnh") + \
                          (f"; gần nhất cắt ngang {x.xs_partner} ρ = {_vn(x.xs_partner_rho)}" if pd.notna(x.xs_partner_rho) else "")
            continue
        roles[feat] = [r for r in rs if r not in (RANK_DEP, RANK_LOAN)]
    cat["role"] = cat.feature.map(lambda x: "; ".join(roles.get(x, [])))
    alive = cat.decision.isin([KEEP, KEEP_RANK])
    for i in cat.index[alive]:
        r = cat.loc[i]
        if r.role:
            note = notes.get(r.feature, "")
            cat.loc[i, "reason"] = f"{r.reason} · Vai trò: {r.role}" + (f" ({note})" if note else "")
        else:
            cat.loc[i, ["decision", "reason"]] = [DROP, _no_effect_reason(r, grp, rank)]
    return cat


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
            if {feat, k} == R4_EXEMPT:
                continue
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
    cat["quality"] = cat.decision  # quyet dinh tang 1 (sach / khong sach); experiments.feature_effect do tren tap nay
    cat = _apply_effect(cat)
    cat["use"] = np.where(cat.decision == DROP, "", cat.role)
    order = {KEEP: 0, KEEP_RANK: 1, DROP: 2}
    cat = cat.sort_values(["decision", "use", "group", "feature"], key=lambda s: s.map(order) if s.name == "decision" else s)
    cols = ["feature", "group", "kind", "decision", "use", "reason", "quality", "flags", "relevant_for"] + [f"rho_next_{t}" for t in TARGETS] + [
            "redundant_with", "rho", "coverage_pct", "n_banks", "banks_last4q", "first_period", "last_period", "mode_share_pct",
            "icc", "outlier_share_pct", "median", "p01", "p99", "unit", "formula", "source", "processing"]
    cat = cat[cols]
    cat.to_csv(CATALOG, index=False, encoding="utf-8-sig")

    keep = cat.loc[cat.decision == KEEP, "feature"].tolist()
    f[KEYS + keep].to_csv(SELECTED, index=False, encoding="utf-8-sig")
    clean = cat.loc[cat.quality == KEEP, "feature"].tolist()
    f[KEYS + clean].to_csv(CLEAN, index=False, encoding="utf-8-sig")

    write_ranking(cat, f)
    return cat


def _fresh() -> pd.DataFrame:
    from crawlers import deposit_tiers
    from crawlers.build_features import APP, MIN_REVIEWS, app_spike_months
    from serving.export import export_lending_rates

    d = deposit_tiers.read()
    d = d[d.ticker.notna() & d.channel.isin(["online", "quay"])].copy()
    d["date"] = pd.to_datetime(d.date)
    d = d[d.date >= d.date.max() - pd.Timedelta(days=FRESH_DAYS)]
    last_day = d.groupby("ticker").date.max()
    d = d[d.date == d.ticker.map(last_day)]
    # Moi ky han, ca hai kenh: xep hang theo ky han + kenh nguoi gui chon (web: 1/3/6/9/12/13/18/24/36 thang).
    # Ten cot dep{T}_{online|counter}_pct; dep12_* trung ten bien trong catalog. Ky han nguon khong co (9, 13 thang
    # tu 2026) thi khong co cot.
    rates = d.pivot_table(index="ticker", columns=["term_months", "channel"], values="rate_percent", aggfunc="last")
    out = pd.DataFrame(index=rates.index)
    for term, ch in sorted(rates.columns):
        out[f"dep{term}_{'online' if ch == 'online' else 'counter'}_pct"] = rates[(term, ch)]
    out["dep_asof"] = last_day.dt.strftime("%Y-%m-%d")

    this_month = pd.Period(date.today(), "M")
    lend = export_lending_rates(narrow=False)  # xep hang: chua so nhom hep (SHB, SSB) voi so chung
    lend = lend[lend.month >= (this_month - LENDING_MAX_MONTHS).strftime("%Y-%m")].sort_values("month")
    last = lend.groupby("ticker").last()
    out["lending_avg_pct"], out["lending_asof"] = last.lending_avg_percent, last.month

    app = pd.read_csv(APP, encoding="utf-8-sig", usecols=["month", "ticker", "n_reviews", "mean_score"])
    app = app[app.month < this_month.strftime("%Y-%m")]  # thang chua het -> bo
    spike = app_spike_months(app)  # tren ca lich su de co nen
    recent_from = (this_month - APP_MAX_MONTHS).strftime("%Y-%m")
    out["app_mean_score"] = np.nan
    out["app_asof"] = out["app_excluded"] = pd.Series(pd.NA, index=out.index, dtype="string")
    for t, g in app[spike & (app.month >= recent_from)].groupby("ticker"):
        out.loc[t, "app_excluded"] = ",".join(sorted(g.month))
    app = app[~spike & (app.n_reviews > 0)]
    for t, g in app.sort_values("month", ascending=False).groupby("ticker"):
        g = g.head(APP_MAX_MONTHS)
        n = g.n_reviews.cumsum()
        enough = (n >= MIN_REVIEWS) & (np.arange(len(g)) >= APP_MIN_MONTHS - 1)
        if enough.any():
            g = g.iloc[: int(np.argmax(enough.to_numpy())) + 1]
            out.loc[t, "app_mean_score"] = (g.mean_score * g.n_reviews).sum() / g.n_reviews.sum()
            out.loc[t, "app_asof"] = f"{g.month.iloc[-1]}..{g.month.iloc[0]}"
    return out


def write_ranking(cat: pd.DataFrame | None = None, f: pd.DataFrame | None = None) -> dict:
    cat = pd.read_csv(CATALOG, encoding="utf-8-sig") if cat is None else cat
    f = pd.read_csv(FEATURES, encoding="utf-8-sig") if f is None else f
    rank_cols = cat.loc[cat.decision.isin([KEEP, KEEP_RANK]) & (cat.kind != "chung mọi NH"), "feature"].tolist()
    periods = sorted(f.period.unique())[-RECENT_QUARTERS:]
    recent = f[f.period.isin(periods)].sort_values("period")
    latest = recent.groupby("ticker")[rank_cols].agg("last")  # gia tri khac rong gan nhat
    asof = recent.groupby("ticker")["period"].max()
    fresh = _fresh().reindex(latest.index)
    for c in sorted(REFRESHED & set(rank_cols)):
        latest[c] = fresh[c]
    # lai cac ky han / kenh khac 12 thang: khong phai bien catalog, dung khi xep hang theo ky han nguoi gui chon
    terms = sorted((c for c in fresh.columns if c.startswith("dep") and c.endswith("_pct") and c not in latest.columns),
                   key=lambda c: (int(c[3:].split("_")[0]), c))
    latest = latest.join(fresh[terms])
    latest.insert(0, "window", f"{periods[0]}..{periods[-1]}")
    latest.insert(1, "latest_period", asof)
    asof_cols = ["dep_asof", "lending_asof"] + (["app_asof", "app_excluded"] if "app_mean_score" in rank_cols else [])
    for i, c in enumerate(asof_cols):
        latest.insert(2 + i, c, fresh[c])
    latest.reset_index().to_csv(RANKING, index=False, encoding="utf-8-sig")
    return {"path": RANKING, "banks": len(latest), "dep_asof": fresh.dep_asof.max(),
            "missing": {c: latest.index[latest[c].isna()].tolist() for c in rank_cols if latest[c].isna().any()}}


def summary(cat: pd.DataFrame) -> dict:
    by = cat.groupby("decision").feature.apply(list).to_dict()
    alive = cat[cat.decision != DROP]
    return {
        "features": len(cat),
        "counts": cat.decision.value_counts().to_dict(),
        "clean_tier1": int(cat.quality.isin([KEEP, KEEP_RANK]).sum()),
        "dropped_no_effect": int(cat.reason.str.startswith("Không tác dụng").sum()),
        "by_role": {r: alive.loc[alive.use.str.contains(r), "feature"].tolist() for r in (TARGET, FC_INPUT, RANK_DEP, RANK_LOAN, PROFILE)},
        "keep_for_ranking": by.get(KEEP_RANK, []),
        "dropped": cat.loc[cat.decision == DROP, ["feature", "reason"]].values.tolist(),
        "paths": [CATALOG, SELECTED, CLEAN, RANKING],
    }


if __name__ == "__main__":
    import json

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(summary(select()), indent=2, ensure_ascii=False, default=str))
