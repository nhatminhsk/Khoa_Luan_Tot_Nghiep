from __future__ import annotations

import json
import os
import re
import sys

import numpy as np
import pandas as pd
from scipy import stats

FEATURES = "data/model/features_selected.csv"
CATALOG = "data/model/feature_catalog.csv"
RANKING = "data/model/features_ranking_latest.csv"
MAS = "data/vnstock_financial/ratio_mas_ttm.csv"
REVIEWS_DIR = "data/app_reviews"
APP_MONTHLY = "data/app_reviews/app_reviews_monthly.csv"
DEPOSIT_CORR = "data/model/eda/deposit_corr.csv"
OUT_DIR = "data/model/eda_ml"
START = "2019-Q1"
SPLIT = "2022-Q2"          # hai nua de kiem on dinh, giong select_features
SEED = 20260923

# So rieng tung quy (MAS) 
MAS_COLS = ["nim_quarter_percent", "cof_quarter_percent", "roe_quarter_percent", "cir_quarter_percent",
            "earning_asset_yield_quarter_percent"]
TARGETS = {"nim_ttm_percent": "NIM", "cof_ttm_percent": "COF", "npl_percent": "NPL", "casa_percent": "CASA",
           "ldr_computed_percent": "LDR", "roe_ttm_percent": "ROE"}
# chuoi quy tuong ung cua muc tieu TTM (de do rolloff)
QUARTER_OF = {"nim_ttm_percent": "nim_quarter_percent", "cof_ttm_percent": "cof_quarter_percent",
              "roe_ttm_percent": "roe_quarter_percent"}
HORIZONS = (1, 2, 4)

# Che do cho giu nguyen nhom no: TT 01/2020 (COVID, hieu luc 13/03/2020, TT 14/2021 keo toi 30/06/2022);
# TT 02/2023 (24/04/2023, TT 06/2024 keo toi 31/12/2024).
REGIMES = {"TT 01/2020": ("2020-Q1", "2022-Q2"), "TT 02/2023": ("2023-Q2", "2024-Q4")}

SNAP_COLS = ["npl_percent", "loans_g2_percent", "credit_cost_ttm_pct", "car_asof_percent", "equity_to_assets_pct",
             "roa_ttm_percent", "nim_ttm_percent", "cof_ttm_percent", "cir_ttm_pct", "casa_percent",
             "ldr_computed_percent", "liquid_assets_pct", "log_total_assets", "loans_yoy_percent"]

# Tieu chi ung vien cho xep hang. Chieu: +1 cang cao cang tot cho nguoi dung, -1 nguoc lai.
RANK_CRITERIA = {
    "dep12_online_pct": ("Lãi 12 tháng online", "gửi", +1), "car_asof_percent": ("CAR", "gửi", +1),
    "equity_to_assets_pct": ("Vốn chủ / TTS", "gửi", +1), "npl_percent": ("NPL", "gửi", -1),
    "loans_g2_percent": ("Nợ nhóm 2", "gửi", -1), "credit_cost_ttm_pct": ("Chi phí tín dụng", "gửi", -1),
    "roa_ttm_percent": ("ROA", "gửi", +1), "liquid_assets_pct": ("TS thanh khoản", "gửi", +1),
    "ldr_computed_percent": ("LDR", "gửi/vay", -1), "log_total_assets": ("Quy mô", "gửi", +1),
    "state_own_percent": ("Sở hữu nhà nước", "gửi", +1), "casa_percent": ("CASA", "gửi", +1),
    "cof_ttm_percent": ("Chi phí vốn", "gửi", -1), "app_mean_score": ("Điểm app", "gửi/vay", +1),
    "loan_yield_ttm_pct": ("Lợi suất cho vay", "vay", -1), "lending_avg_pct": ("Lãi vay niêm yết", "vay", -1),
    "loans_yoy_percent": ("Tăng trưởng dư nợ", "vay", +1), "nim_ttm_percent": ("NIM", "vay", -1),
}

# Tu mo cho khia canh review (chu thuong, co dau va khong dau). Chi de do do phu, khong phai nhan.
ASPECTS = {
    "giao_dich": ("Giao dịch, chuyển tiền", r"chuyển (?:tiền|khoản)|chuyen (?:tien|khoan)|giao dịch|giao dich|nạp tiền|rút tiền|thanh toán|thanh toan|\bqr\b"),
    "dang_nhap": ("Đăng nhập, OTP, sinh trắc", r"đăng nhập|dang nhap|\botp\b|mật khẩu|mat khau|sinh trắc|sinh trac|xác thực|xac thuc|khuôn mặt|khuon mat|cccd|căn cước|\bnfc\b|vân tay|faceid|face id"),
    "giao_dien": ("Giao diện, cập nhật, tiện dụng", r"giao diện|giao dien|cập nhật|cap nhat|phiên bản|phien ban|\bupdate\b|dễ sử dụng|de su dung|dễ dùng|de dung|tiện lợi|tien loi|tiện ích|tien ich"),
    "toc_do": ("Tốc độ, ổn định", r"chậm|\bcham\b|\blag\b|\bđơ\b|\btreo\b|văng|thoát ra|\bload\b|\blâu\b|không vào được|ko vào được|k vào được|khong vao duoc|lỗi kết nối|mất kết nối|bảo trì|bao tri"),
    "cskh": ("Chăm sóc khách hàng", r"tổng đài|tong dai|nhân viên|nhan vien|hỗ trợ|ho tro|chăm sóc|cham soc|\bcskh\b|hotline|chi nhánh|chi nhanh|phòng giao dịch|quầy"),
    "the": ("Thẻ, ATM", r"\bthẻ\b|\bthe atm\b|\batm\b|\bvisa\b|mastercard|mở thẻ|khóa thẻ|khoá thẻ"),
    "phi": ("Phí", r"\bphí\b|mất phí|mat phi|miễn phí|mien phi|thu phí|thu phi|trừ tiền|tru tien"),
    # rong nhat co the; van dinh "tiet kiem thoi gian"
    "tiet_kiem": ("Tiết kiệm, lãi suất", r"tiết kiệm|tiet kiem|tiền gửi|tien gui|gửi tiền|gui tien|lãi suất|lai suat|\blãi\b|kỳ hạn|ky han|tất toán|tat toan"),
    "vay": ("Vay, tín dụng", r"\bvay\b|khoản vay|khoan vay|tín dụng|tin dung|giải ngân|giai ngan|trả góp|tra gop|hạn mức|han muc|thấu chi|thau chi"),
}
VN_DIACRITIC = re.compile(r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿\U0001F000-\U0001F2FF]")
EN_WORDS = {"the", "is", "are", "very", "good", "great", "nice", "bad", "not", "this", "it", "to", "and", "please", "can",
            "cannot", "why", "excellent", "love", "thanks", "thank", "easy", "useful", "convenient", "fast", "best", "worst",
            "you", "my", "i", "so", "too", "app", "of", "for", "with", "work", "working", "doesn't", "don't", "can't"}
VN_PLAIN = {"khong", "duoc", "chuyen", "tien", "qua", "rat", "toi", "cua", "lam", "tai", "khoan", "nhu", "cai", "gi",
            "sao", "bi", "loi", "dang", "nhap", "cap", "nhat", "ngan", "hang", "dung", "tot", "on", "hay", "ko", "k",
            "ma", "vao", "thi", "roi", "nua", "mat", "mot", "nay", "cho", "nhung", "phai", "moi", "de", "su"}


def spearman(a, b):
    d = pd.DataFrame({"a": a, "b": b}).dropna()
    return (float(d.a.rank().corr(d.b.rank())), len(d)) if len(d) >= 10 else (np.nan, len(d))


def load():
    f = pd.read_csv(FEATURES, encoding="utf-8-sig")
    mas = pd.read_csv(MAS, encoding="utf-8-sig")[["ticker", "period"] + MAS_COLS]
    f = f.merge(mas, on=["ticker", "period"], how="left").sort_values(["ticker", "period"]).reset_index(drop=True)
    cat = pd.read_csv(CATALOG, encoding="utf-8-sig").set_index("feature")
    return f, cat


def feature_meta(cat, feats):
    """Nhom, loai (theo NH-quy / chung / tinh), vai tro cho moi dac trung; MAS la dac trung de xuat moi."""
    rows = {}
    for c in feats:
        if c in cat.index:
            r = cat.loc[c]
            rows[c] = dict(group=r["group"], kind=r["kind"], use=r["use"] if isinstance(r["use"], str) else "Xếp hạng",
                           unit=r["unit"], new=False)
        else:
            rows[c] = dict(group="E Thu nhập & chi phí vốn", kind="theo NH-quý", use="Đề xuất thêm (MAS)", unit="%", new=True)
    return pd.DataFrame(rows).T


# --------------------------------------------------------------------------- 1
def univariate(f, feats, meta):
    rows = []
    for c in feats:
        v = f[c].dropna().astype(float)
        n_all = len(f)
        q1, med, q3 = v.quantile([0.25, 0.5, 0.75])
        iqr = q3 - q1
        nun = v.nunique()
        is_out = ((v < q1 - 3 * iqr) | (v > q3 + 3 * iqr)) if iqr > 0 else pd.Series(False, index=v.index)
        out_banks = f.loc[is_out[is_out].index, "ticker"].value_counts()
        sk = float(stats.skew(v)) if nun > 2 else np.nan
        ku = float(stats.kurtosis(v)) if nun > 2 else np.nan
        sk_yj = np.nan
        if nun > 2 and v.std() > 0:
            try:
                sk_yj = float(stats.skew(stats.yeojohnson(v.to_numpy())[0]))
            except Exception:  
                pass
        rows.append(dict(feature=c, n=len(v), missing_pct=100 * (1 - len(v) / n_all), mean=v.mean(), std=v.std(), min=v.min(),
                         q1=q1, median=med, q3=q3, max=v.max(), skew=sk, kurtosis=ku, skew_yeojohnson=sk_yj,
                         outlier_pct=100 * float(is_out.mean()), zero_pct=100 * float((v == 0).mean()), n_unique=nun,
                         top_outlier_bank=out_banks.index[0] if len(out_banks) else "",
                         top_outlier_bank_share=float(out_banks.iloc[0] / out_banks.sum()) if len(out_banks) else np.nan))
    u = pd.DataFrame(rows).set_index("feature").join(meta)

    def shape(r):
        if r.n_unique <= 2:
            return "nhị phân"
        if abs(r["skew"]) > 2:
            return "lệch mạnh"
        if abs(r["skew"]) > 1:
            return "lệch vừa"
        return "gần đối xứng"

    def action(r):
        if r.n_unique <= 2:
            return "giữ 0/1"
        acts = []
        if abs(r["skew"]) > 1:
            acts.append("Yeo-Johnson")
        if r.outlier_pct > 2:
            acts.append("winsorize p1/p99")
        return " + ".join(acts) if acts else "chỉ chuẩn hóa z"
    u["shape"] = u.apply(shape, axis=1)
    u["linear_action"] = u.apply(action, axis=1)
    return u.reset_index()


# --------------------------------------------------------------------------- 2
def _within(s, ticker):
    return s - s.groupby(ticker).transform("mean")


def _acf(x, ticker, k):
    lag = x.groupby(ticker).shift(k)
    d = pd.DataFrame({"a": x, "b": lag}).dropna()
    return float(d.a.corr(d.b)) if len(d) > 20 else np.nan


def _adf_t(y):
    """ADF 1 tre, co hang so: t cua he so y(t-1)."""
    y = np.asarray(y, float)
    y = y[~np.isnan(y)]
    if len(y) < 15:
        return np.nan
    dy = np.diff(y)
    Y = dy[1:]
    X = np.column_stack([np.ones(len(Y)), y[1:-1], dy[:-1]])
    beta = np.linalg.lstsq(X, Y, rcond=None)[0]
    e = Y - X @ beta
    s2 = e @ e / (len(Y) - X.shape[1])
    cov = s2 * np.linalg.pinv(X.T @ X)
    return float(beta[1] / np.sqrt(cov[1, 1])) if cov[1, 1] > 0 else np.nan


def ips_null(N, T, rng, B=2000):
    """Phan phoi t-bar (trung binh t ADF cua N chuoi) duoi gia thuyet ca N chuoi deu la buoc ngau nhien."""
    return np.array([np.nanmean([_adf_t(np.cumsum(rng.standard_normal(T))) for _ in range(N)]) for _ in range(B)])


def target_profile(f, rng):
    base = f[f.period >= START].copy()
    T = base.period.nunique()
    null = ips_null(22, T, rng)
    prof, acf_rows = [], []
    series = dict(TARGETS)
    series.update({"nim_quarter_percent": "NIM quý", "cof_quarter_percent": "COF quý"})
    for c, label in series.items():
        x = base[c]
        w = _within(x, base.ticker)
        d1 = x.groupby(base.ticker).diff()
        for k in range(1, 5):
            acf_rows.append(dict(target=c, label=label, lag=k, acf_level=_acf(w, base.ticker, k), acf_change=_acf(d1, base.ticker, k)))
        r1 = _acf(w, base.ticker, 1)
        half = float(np.log(0.5) / np.log(r1)) if 0 < r1 < 1 else np.nan
        t_lvl = np.nanmean([_adf_t(g.to_numpy()) for _, g in base.groupby("ticker")[c]])
        t_chg = np.nanmean([_adf_t(g.diff().to_numpy()) for _, g in base.groupby("ticker")[c]])
        # phan ra thay doi 1 quy: chung theo quy / xu huong rieng NH / rieng NH-quy
        dd = pd.DataFrame({"t": base.ticker, "p": base.period, "d": d1}).dropna()
        z = dd.d - dd.d.mean()
        tot = (z ** 2).sum()
        q = z.groupby(dd.p).transform("mean")
        b = (z - q).groupby(dd.t).transform("mean")
        r = z - q - b
        mad = (dd.d - dd.d.median()).abs().median()
        prof.append(dict(target=c, label=label, n_change=len(dd), acf1_level=r1, half_life_q=half,
                         ips_tbar_level=t_lvl, ips_p_level=float((null <= t_lvl).mean()),
                         ips_tbar_change=t_chg, ips_p_change=float((null <= t_chg).mean()),
                         change_common=float((q ** 2).sum() / tot), change_bank=float((b ** 2).sum() / tot),
                         change_idio=float((r ** 2).sum() / tot), change_kurtosis=float(stats.kurtosis(dd.d)),
                         change_tail_pct=100 * float(((dd.d - dd.d.median()).abs() > 5 * 1.4826 * mad).mean()) if mad > 0 else np.nan,
                         between_sd=float(base.groupby("ticker")[c].mean().std()), change_sd=float(dd.d.std())))
    return pd.DataFrame(prof), pd.DataFrame(acf_rows), dict(T=T, null_p5=float(np.percentile(null, 5)))


# --------------------------------------------------------------------------- 3
def _gauss(x):
    """Diem chuan tac (normal scores) - bien doi mot-mot giu thu tu."""
    r = stats.rankdata(x) / (len(x) + 1)
    return stats.norm.ppf(r)


def _past_within(s, ticker, min_periods=4):
    """Tru trung binh QUA KHU cua chinh NH (toi quy t). Tru trung binh ca mau se lo tuong lai: muc da tru
    trung binh ca mau 'biet truoc' NH se quay ve dau, lam tuong quan voi thay doi sau nay cao gia."""
    return s - s.groupby(ticker).transform(lambda x: x.expanding(min_periods=min_periods).mean())


def _folds(periods, n_splits=5, gap=None):
    """Chia theo quy. gap=None: GroupKFold (moi quy o mot phan, cac quy ke ben van nam trong tap huan luyen).
    gap=g: khoi quy lien nhau, bo khoi tap huan luyen cac quy cach khoi kiem tra < = g quy (purge) - vi thay
    doi t -> t+h cua hai quy gan nhau chong len nhau, va TTM cong 4 quy."""
    up = np.array(sorted(set(periods)))
    pos = pd.Series(np.arange(len(up)), index=up).loc[periods].to_numpy()
    if gap is None:
        from sklearn.model_selection import GroupKFold
        yield from GroupKFold(n_splits=n_splits).split(pos, pos, pos)
        return
    for b in np.array_split(np.arange(len(up)), n_splits):
        te = (pos >= b[0]) & (pos <= b[-1])
        tr = (pos < b[0] - gap) | (pos > b[-1] + gap)
        if tr.sum() >= 60:
            yield np.where(tr)[0], np.where(te)[0]


def _cv_pred(Xa, y, periods, make, gap=None, n_splits=5):
    """Du bao ngoai mau cho cac quy duoc kiem tra (NaN o quy khong kiem tra duoc)."""
    pred = np.full(len(y), np.nan)
    for tr, te in _folds(periods, n_splits, gap):
        pred[te] = make().fit(Xa[tr], y[tr]).predict(Xa[te])
    return pred


def _skill(y, pred, ref):
    """Muc giam tong binh phuong sai so so voi du bao tham chieu, tren cac o co ca hai."""
    ok = ~np.isnan(pred) & ~np.isnan(ref)
    return float(1 - ((y[ok] - pred[ok]) ** 2).sum() / ((y[ok] - ref[ok]) ** 2).sum()) if ok.sum() >= 30 else np.nan


def feature_target(f, feats, meta):
    
    import lightgbm as lgb
    from sklearn.dummy import DummyRegressor
    from sklearn.linear_model import LinearRegression, Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import SplineTransformer
    common = set(meta.index[meta.kind == "chung mọi NH"])
    Xall = pd.DataFrame({c: (f[c] if c in common else _past_within(f[c], f.ticker)) for c in feats})
    base = f[f.period >= START]
    X = Xall.loc[base.index]
    q = base.period.str[-1].astype(int)
    Q = pd.DataFrame({f"q{k}": (q == k).astype(float) for k in (2, 3, 4)}, index=base.index)
    half1 = (base.period <= SPLIT).to_numpy()
    per = base.period.to_numpy()
    spline = lambda: make_pipeline(SplineTransformer(n_knots=5, degree=3), Ridge(alpha=1.0))  # noqa: E731
    gbm = lambda: lgb.LGBMRegressor(n_estimators=200, learning_rate=0.05, num_leaves=7, min_child_samples=20,  # noqa: E731
                                    subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=0, verbose=-1)
    ridge = lambda: Ridge(alpha=10.0)  # noqa: E731
    const = lambda: DummyRegressor()  # noqa: E731
    std = lambda M: M.apply(lambda s: (s - s.mean()) / s.std()).fillna(0)  # noqa: E731
    rows, ceil = [], []
    for y, label in TARGETS.items():
        for h in HORIZONS:
            dy = base.groupby("ticker")[y].shift(-h) - base[y]
            lo, hi = dy.quantile([0.01, 0.99])
            dy = dy.clip(lo, hi)
            gap = h + 3 if y in QUARTER_OF else h
            for c in feats:
                ok = (X[c].notna() & dy.notna()).to_numpy()
                if ok.sum() < 100 or X.loc[ok, c].nunique() < 3:
                    continue
                xa, ya, ga = X.loc[ok, c].to_numpy(), dy[ok].to_numpy(), per[ok]
                rho = float(stats.spearmanr(xa, ya)[0])
                r1 = float(stats.spearmanr(xa[half1[ok]], ya[half1[ok]])[0]) if half1[ok].sum() > 30 else np.nan
                r2 = float(stats.spearmanr(xa[~half1[ok]], ya[~half1[ok]])[0]) if (~half1[ok]).sum() > 30 else np.nan
                row = dict(target=y, label=label, h=h, feature=c, n=int(ok.sum()), n_unique=int(X.loc[ok, c].nunique()),
                           rho=rho, rho_h1=r1, rho_h2=r2, skill_linear=np.nan, skill_spline=np.nan)
                if row["n_unique"] >= 20:
                    gx = _gauss(xa).reshape(-1, 1)
                    ref = _cv_pred(gx, ya, ga, const, gap)
                    row["skill_linear"] = _skill(ya, _cv_pred(gx, ya, ga, LinearRegression, gap), ref)
                    row["skill_spline"] = _skill(ya, _cv_pred(gx, ya, ga, spline, gap), ref)
                rows.append(row)
            sub = [r for r in rows if r["target"] == y and r["h"] == h]
            for r in sub:
                r["stable"] = bool(abs(r["rho"]) >= 0.15 and np.sign(r["rho_h1"]) == np.sign(r["rho"]) == np.sign(r["rho_h2"])
                                   and min(abs(r["rho_h1"]), abs(r["rho_h2"])) >= 0.10)
                r["nonlinear"] = bool(r["skill_spline"] >= 0.02 and r["skill_spline"] - max(r["skill_linear"], 0.0) >= 0.02)
            ok = dy.notna().to_numpy()
            yv, gv = dy[ok].to_numpy(), per[ok]
            d = pd.DataFrame({"dy": yv, "p": gv})
            r2_common = 1 - ((d.dy - d.groupby("p").dy.transform("mean")) ** 2).sum() / ((d.dy - d.dy.mean()) ** 2).sum()
            stab = [r["feature"] for r in sub if r["stable"]]
            usable = [r["feature"] for r in sub]
            Zq = Q[ok].to_numpy()
            Zs = pd.concat([std(X.loc[ok, stab]), Q[ok]], axis=1).to_numpy() if stab else Zq
            Za = pd.concat([std(X.loc[ok, usable]), Q[ok]], axis=1).to_numpy()
            Zl = pd.concat([X.loc[ok, usable], Q[ok]], axis=1).to_numpy()
            zero = np.zeros(len(yv))
            sk = lambda p: _skill(yv, p, zero)  # noqa: E731
            ceil.append(dict(target=y, label=label, h=h, n=int(ok.sum()), n_features=len(sub), n_stable=len(stab),
                             n_nonlinear=sum(r["nonlinear"] for r in sub), share_common=float(r2_common), purge_gap=gap,
                             skill_drift=sk(_cv_pred(Zq, yv, gv, const, gap)),
                             skill_seasonal=sk(_cv_pred(Zq, yv, gv, LinearRegression, gap)),
                             skill_ridge_stable=sk(_cv_pred(Zs, yv, gv, ridge, gap)),
                             skill_ridge_all=sk(_cv_pred(Za, yv, gv, ridge, gap)),
                             skill_lgbm_all=sk(_cv_pred(Zl, yv, gv, gbm, gap)),
                             skill_lgbm_leaky=sk(_cv_pred(Zl, yv, gv, gbm, None)),
                             top_features=", ".join(sorted(stab, key=lambda c: -abs(next(r["rho"] for r in sub if r["feature"] == c)))[:5])))
    return pd.DataFrame(rows), pd.DataFrame(ceil)


# --------------------------------------------------------------------------- 4
def _clusters(C, names, thr=0.7):
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform
    D = 1 - C.abs().to_numpy()
    np.fill_diagonal(D, 0)
    Z = linkage(squareform(np.clip(D, 0, None), checks=False), method="complete")
    lab = fcluster(Z, t=1 - thr, criterion="distance")
    return pd.Series(lab, index=names)


def _n_components(M, share):
    M = M.apply(lambda s: (s - s.mean()) / s.std()).fillna(0).to_numpy()
    s = np.linalg.svd(M, compute_uv=False) ** 2
    return int(np.searchsorted(np.cumsum(s / s.sum()), share) + 1)


def feature_feature(f, meta):
    base = f[f.period >= START].copy()
    varying = [c for c in meta.index if meta.loc[c, "kind"] == "theo NH-quý" and c in base and base[c].nunique() > 2]
    core = [c for c in varying if meta.loc[c, "use"] in ("Lõi dự báo", "Đề xuất thêm (MAS)")]
    # trong NH: tru TB NH va TB quy
    d = base[varying] - base.groupby("ticker")[varying].transform("mean")
    d = d - d.groupby(base.period).transform("mean")
    Cw = d.rank().corr()
    Cb = base.groupby("ticker")[varying].mean().rank().corr()
    pairs = []
    for i, a in enumerate(varying):
        for b in varying[i + 1:]:
            pairs.append(dict(a=a, b=b, between=Cb.loc[a, b], within=Cw.loc[a, b]))
    P = pd.DataFrame(pairs).dropna()
    P["gap"] = P.between - P.within
    # VIF trong NH cho cac bien loi
    Z = d[core].apply(lambda s: (s - s.mean()) / s.std()).fillna(0)
    vif = []
    for c in core:
        others = [o for o in core if o != c]
        A = np.column_stack([np.ones(len(Z)), Z[others].to_numpy()])
        e = Z[c].to_numpy() - A @ np.linalg.lstsq(A, Z[c].to_numpy(), rcond=None)[0]
        r2 = 1 - (e @ e) / ((Z[c] - Z[c].mean()) ** 2).sum()
        vif.append(dict(feature=c, vif=1 / max(1e-9, 1 - r2)))
    cl_w = _clusters(Cw.loc[core, core].fillna(0), core)
    cl_b = _clusters(Cb.fillna(0), varying)
    dims = dict(n_varying=len(varying), n_core=len(core),
                within_core_80=_n_components(d[core], 0.8), within_core_90=_n_components(d[core], 0.9),
                between_all_80=_n_components(base.groupby("ticker")[varying].mean(), 0.8),
                between_all_90=_n_components(base.groupby("ticker")[varying].mean(), 0.9),
                clusters_within_core=int(cl_w.nunique()), clusters_between_all=int(cl_b.nunique()),
                pairs=len(P), pairs_between_07=int((P.between.abs() >= 0.7).sum()), pairs_within_07=int((P.within.abs() >= 0.7).sum()),
                pairs_sign_flip=int(((np.sign(P.between) != np.sign(P.within)) & (P.between.abs() >= 0.3) & (P.within.abs() >= 0.1)).sum()),
                pairs_gap_05=int((P.gap.abs() >= 0.5).sum()), median_abs_within=float(P.within.abs().median()),
                median_abs_between=float(P.between.abs().median()))
    clw = pd.DataFrame({"feature": core, "cluster": cl_w.values}).merge(pd.DataFrame(vif), on="feature")
    clb = pd.DataFrame({"feature": varying, "cluster": cl_b.values})
    return P, clw, clb, dims, Cw.loc[core, core]


# --------------------------------------------------------------------------- 5
def structure(f, meta):
    base = f[f.period >= START].copy()
    out = {}
    # 5a. rolloff: thay doi TTM quy toi = (quy moi vao - quy roi ra)/4; phan "quy roi ra" da biet tai t
    roll = []
    for ttm, qc in QUARTER_OF.items():
        g = base.groupby("ticker")
        dnext = g[ttm].shift(-1) - base[ttm]
        known = (base[qc] - g[qc].shift(3)) / 4          # gia su quy moi vao = quy t (naive tren so quy)
        d = pd.DataFrame({"y": dnext, "x": known}).dropna()
        r = float(d.y.corr(d.x))
        prev = g[ttm].diff()
        dp = pd.DataFrame({"y": dnext, "x": prev}).dropna()
        roll.append(dict(target=ttm, label=TARGETS[ttm], n=len(d), corr_rolloff=r, r2_rolloff=r ** 2,
                         corr_prev_change=float(dp.y.corr(dp.x)),
                         acf1_ttm_change=_acf(base[ttm].groupby(base.ticker).diff(), base.ticker, 1),
                         acf1_quarter_change=_acf(base[qc].groupby(base.ticker).diff(), base.ticker, 1)))
    # 5b. che do gian no: thay doi NPL/no nhom 2 theo quy (trung vi 22 NH), hoi quy tren dummy quy + che do
    per = sorted(base.period.unique())
    reg = []
    for c in ["npl_percent", "loans_g2_percent"]:
        med = base.assign(d=base.groupby("ticker")[c].diff()).groupby("period").d.median().reindex(per).dropna()
        on = pd.Series(0, index=med.index)
        for a, b in REGIMES.values():
            on[(on.index >= a) & (on.index <= b)] = 1
        q = med.index.str[-1].astype(int)
        A = np.column_stack([np.ones(len(med)), on.to_numpy()] + [(q == k).astype(float) for k in (2, 3, 4)])
        beta, *_ = np.linalg.lstsq(A, med.to_numpy(), rcond=None)
        e = med.to_numpy() - A @ beta
        s2 = e @ e / (len(med) - A.shape[1])
        se = np.sqrt(np.diag(s2 * np.linalg.inv(A.T @ A)))
        after = {k: float(med.get(p, np.nan)) for k, p in (("2022-Q3", "2022-Q3"), ("2025-Q1", "2025-Q1"))}
        lvl = base.groupby("period")[c].median()
        reg.append(dict(feature=c, n_quarters=len(med), regime_quarters=int(on.sum()), effect_regime=float(beta[1]),
                        se=float(se[1]), t=float(beta[1] / se[1]), p=float(2 * stats.t.sf(abs(beta[1] / se[1]), len(med) - A.shape[1])),
                        median_change_regime=float(med[on == 1].median()), median_change_other=float(med[on == 0].median()),
                        change_2022Q3=after["2022-Q3"], change_2025Q1=after["2025-Q1"],
                        level_2019Q4=float(lvl.get("2019-Q4", np.nan)), level_2022Q2=float(lvl.get("2022-Q2", np.nan)),
                        level_2024Q4=float(lvl.get("2024-Q4", np.nan)), level_last=float(lvl.iloc[-1])))
    # 5c. ngan sach mau cho walk-forward
    budget = []
    for h in HORIZONS:
        dy = base.groupby("ticker")["npl_percent"].shift(-h) - base.npl_percent
        ok = dy.notna()
        budget.append(dict(h=h, samples=int(ok.sum()), origins=int(base.loc[ok, "period"].nunique()),
                           train_at_2023Q1=int((ok & (base.period < "2023-Q1")).sum()),
                           test_from_2023Q1=int((ok & (base.period >= "2023-Q1")).sum())))
    params = dict(lstm_h32_f8=4 * (32 * (8 + 32) + 32) + 33, gru_h16_f8=3 * (16 * (8 + 16) + 16) + 17,
                  lgbm_100x15=100 * 15, ridge_28=29)
    out.update(params=params)
    return pd.DataFrame(roll), pd.DataFrame(reg), pd.DataFrame(budget), out


# --------------------------------------------------------------------------- 6
def missingness(f, feats, meta):
    f = f.copy()
    f["year"] = f.period.str[:4]
    varying = [c for c in feats if c in meta.index and meta.loc[c, "kind"] != "chung mọi NH"]
    by_year = f.groupby("year")[varying].apply(lambda g: g.isna().to_numpy().mean() * 100).rename("missing_pct").reset_index()
    cells = f[varying].isna()
    tot = cells.to_numpy().sum()
    share_2018 = float(cells[f.year == "2018"].to_numpy().sum() / tot)
    after = f[f.period >= START]
    by_bank = after.groupby("ticker")[varying].apply(lambda g: g.isna().to_numpy().mean() * 100).rename("missing_pct").reset_index()
    # thieu co phu thuoc thoi gian? ty le o thieu theo quy tu 2019
    by_q = after.groupby("period")[varying].apply(lambda g: g.isna().to_numpy().mean() * 100)
    return by_year, by_bank, dict(share_missing_in_2018=share_2018, missing_pct_all=float(cells.to_numpy().mean() * 100),
                                  missing_pct_from_2019=float(after[varying].isna().to_numpy().mean() * 100),
                                  missing_pct_2019_first_q=float(by_q.iloc[0]), missing_pct_last_q=float(by_q.iloc[-1]))


# --------------------------------------------------------------------------- 7
def _hopkins(X, rng, m=5, reps=300):
    from sklearn.neighbors import NearestNeighbors
    nn = NearestNeighbors(n_neighbors=2).fit(X)
    lo, hi = X.min(0), X.max(0)
    H = []
    for _ in range(reps):
        U = rng.uniform(lo, hi, size=(m, X.shape[1]))
        u = nn.kneighbors(U, n_neighbors=1)[0][:, 0]
        idx = rng.choice(len(X), m, replace=False)
        w = nn.kneighbors(X[idx], n_neighbors=2)[0][:, 1]
        H.append(u.sum() / (u.sum() + w.sum()))
    return float(np.mean(H))


def clustering_tendency(f, rng):
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    per = sorted(f.period.unique())[-4:]
    snap = f[f.period.isin(per)].sort_values("period").groupby("ticker")[SNAP_COLS].agg("last")
    Z = snap.fillna(snap.median())
    Z = ((Z - Z.mean()) / Z.std()).to_numpy()
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    P3 = U[:, :3] * S[:3]
    cov = np.cov(Z.T)
    res = []
    for k in range(2, 7):
        sil = float(silhouette_score(Z, KMeans(n_clusters=k, n_init=30, random_state=0).fit(Z).labels_))
        null = []
        for _ in range(100):
            G = rng.multivariate_normal(np.zeros(Z.shape[1]), cov, size=len(Z), check_valid="ignore")
            null.append(silhouette_score(G, KMeans(n_clusters=k, n_init=5, random_state=0).fit(G).labels_))
        res.append(dict(k=k, silhouette=sil, null_mean=float(np.mean(null)), null_p95=float(np.percentile(null, 95)),
                        p=float((np.array(null) >= sil).mean())))
    h_data = _hopkins(P3, rng)
    h_null = [_hopkins(rng.multivariate_normal(np.zeros(3), np.cov(P3.T), size=len(P3)), rng, reps=100) for _ in range(100)]
    return pd.DataFrame(res), dict(hopkins_pca3=h_data, hopkins_null_mean=float(np.mean(h_null)),
                                   hopkins_null_p95=float(np.percentile(h_null, 95)), n_banks=len(Z), n_features=Z.shape[1])


# --------------------------------------------------------------------------- 8
def ranking_data():
    r = pd.read_csv(RANKING, encoding="utf-8-sig").set_index("ticker")
    crit = [c for c in RANK_CRITERIA if c in r]
    X = r[crit].astype(float)
    C = X.rank().corr()
    rows = []
    for c in crit:
        v = X[c].dropna()
        med = v.median()
        mad = 1.4826 * (v - med).abs().median()
        rz = (v - med) / mad if mad > 0 else v * 0
        dom = rz.abs().idxmax() if len(v) else ""
        # ty le thang min-max bi mot NH chiem: khoang cach tu NH cuc tri toi NH ke tiep / toan khoang
        s = v.sort_values()
        span = s.iloc[-1] - s.iloc[0]
        gap = max(s.iloc[1] - s.iloc[0], s.iloc[-1] - s.iloc[-2]) / span if span > 0 else np.nan
        label, side, sign = RANK_CRITERIA[c]
        rows.append(dict(feature=c, label=label, side=side, direction=sign, n=len(v), missing=int(X[c].isna().sum()),
                         skew=float(stats.skew(v)), max_robust_z=float(rz.abs().max()), extreme_bank=dom,
                         extreme_gap_share=float(gap)))
    cl = _clusters(C.fillna(0), crit)
    out = pd.DataFrame(rows)
    out["cluster"] = out.feature.map(cl)
    pairs = [dict(a=a, b=b, rho=float(C.loc[a, b])) for i, a in enumerate(crit) for b in crit[i + 1:] if abs(C.loc[a, b]) >= 0.6]
    return out, pd.DataFrame(pairs).sort_values("rho", key=abs, ascending=False), C


# --------------------------------------------------------------------------- 9
def _norm_text(s):
    s = s.str.lower().str.replace(r"[^\w\s]", " ", regex=True).str.replace(r"\s+", " ", regex=True).str.strip()
    return s


def text_eda():
    frames = []
    for fn in sorted(os.listdir(REVIEWS_DIR)):
        if re.fullmatch(r"[A-Z]{3}\.csv", fn):
            frames.append(pd.read_csv(f"{REVIEWS_DIR}/{fn}", usecols=["ticker", "at_utc", "score", "content"], encoding="utf-8-sig"))
    r = pd.concat(frames, ignore_index=True)
    r = r[r.content.notna() & (r.content.str.strip() != "")].copy()
    r["year"] = r.at_utc.str[:4].astype(int)
    low = r.content.str.lower()
    r["words"] = low.str.split().str.len()
    norm = _norm_text(r.content)
    r["dup"] = norm.duplicated(keep=False)
    r["dup_extra"] = norm.duplicated(keep="first")
    r["diacritic"] = low.str.contains(VN_DIACRITIC)
    r["emoji"] = r.content.str.contains(EMOJI)
    toks = norm.str.split()
    en = toks.apply(lambda t: sum(w in EN_WORDS for w in t))
    vn = toks.apply(lambda t: sum(w in VN_PLAIN for w in t))
    r["lang"] = np.where(r.diacritic, "có dấu",
                         np.where((en > vn) & (en > 0), "tiếng Anh", np.where(vn > 0, "tiếng Việt không dấu", "khác (ngắn, ký hiệu)")))
    for k, (_, pat) in ASPECTS.items():
        r[f"a_{k}"] = low.str.contains(pat, regex=True)
    acols = [f"a_{k}" for k in ASPECTS]
    r["n_aspects"] = r[acols].sum(axis=1)

    overview = dict(n_reviews=len(r), n_banks=int(r.ticker.nunique()), first_year=int(r.year.min()), last_year=int(r.year.max()),
                    share_before_2019=float((r.year < 2019).mean()),
                    words_p25=float(r.words.quantile(0.25)), words_p50=float(r.words.median()), words_p75=float(r.words.quantile(0.75)),
                    words_p90=float(r.words.quantile(0.9)), words_p95=float(r.words.quantile(0.95)),
                    words_p99=float(r.words.quantile(0.99)), words_max=int(r.words.max()),
                    share_le3=float((r.words <= 3).mean()), share_le5=float((r.words <= 5).mean()), share_le10=float((r.words <= 10).mean()),
                    share_gt64=float((r.words > 64).mean()), share_gt128=float((r.words > 128).mean()),
                    dup_share=float(r.dup.mean()), dup_extra_share=float(r.dup_extra.mean()),
                    dup_extra_share_gt3=float(r.loc[r.words > 3, "dup_extra"].mean()),
                    emoji_share=float(r.emoji.mean()),
                    reviews_min_bank=int(r.ticker.value_counts().min()), reviews_min_bank_ticker=r.ticker.value_counts().idxmin(),
                    reviews_max_bank=int(r.ticker.value_counts().max()), reviews_max_bank_ticker=r.ticker.value_counts().idxmax(),
                    share_top3_banks=float(r.ticker.value_counts().head(3).sum() / len(r)),
                    share_no_aspect=float((r.n_aspects == 0).mean()), share_multi_aspect=float((r.n_aspects >= 2).mean()),
                    share_no_aspect_gt5=float((r.loc[r.words > 5, "n_aspects"] == 0).mean()))
    stars = r.score.value_counts(normalize=True).sort_index().rename("share").reset_index()
    bins = [0, 1, 3, 5, 10, 20, 40, 64, 128, 10_000]
    labels = ["1", "2–3", "4–5", "6–10", "11–20", "21–40", "41–64", "65–128", ">128"]
    r["len_bin"] = pd.cut(r.words, bins=bins, labels=labels)
    by_len = r.groupby("len_bin", observed=False).agg(n=("score", "size"), mean_star=("score", "mean"),
                                                      pct_1star=("score", lambda s: 100 * (s == 1).mean()),
                                                      pct_5star=("score", lambda s: 100 * (s == 5).mean()),
                                                      pct_mid=("score", lambda s: 100 * s.between(2, 4).mean()),
                                                      pct_no_aspect=("n_aspects", lambda s: 100 * (s == 0).mean())).reset_index()
    by_len["share"] = by_len.n / len(r)
    # do thua khi gop len NH-quy (don vi cua xep hang) tu 2019
    r["quarter"] = r.at_utc.str[:4] + "-Q" + ((r.at_utc.str[5:7].astype(int) - 1) // 3 + 1).astype(str)
    recent = r[r.year >= 2019]
    n_bq = recent.groupby(["ticker", "quarter"]).size()
    asp = []
    for k, (label, _) in ASPECTS.items():
        m = r[f"a_{k}"]
        bq = recent[recent[f"a_{k}"]].groupby(["ticker", "quarter"]).size().reindex(n_bq.index, fill_value=0)
        asp.append(dict(aspect=k, label=label, n=int(m.sum()), share=float(m.mean()), mean_star=float(r.loc[m, "score"].mean()),
                        pct_1star=100 * float((r.loc[m, "score"] == 1).mean()), median_words=float(r.loc[m, "words"].median()),
                        bq_median=float(bq.median()), bq_share_ge30=float((bq >= 30).mean())))
    overview.update(bank_quarters=int(len(n_bq)), bq_reviews_median=float(n_bq.median()), bq_share_ge30=float((n_bq >= 30).mean()))
    lang = r.lang.value_counts(normalize=True).rename("share").reset_index()
    lang_star = r.groupby("lang").score.mean().rename("mean_star").reset_index()
    lang = lang.merge(lang_star, on="lang")
    by_bank = r.groupby("ticker").agg(n=("score", "size"), mean_star=("score", "mean"),
                                      pct_1star=("score", lambda s: 100 * (s == 1).mean())).reset_index().sort_values("n")
    by_year = r.groupby("year").agg(n=("score", "size"), mean_star=("score", "mean")).reset_index()
    am = pd.read_csv(APP_MONTHLY, encoding="utf-8-sig")
    overview.update(bank_months=int(len(am)), bank_months_bombing=int((am.bombing_days > 0).sum()),
                    bank_months_usable=int(am.usable.sum()) if "usable" in am else None)
    return overview, stars, by_len, pd.DataFrame(asp), lang, by_bank, by_year


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pd.set_option("display.width", 240)
    pd.set_option("display.max_columns", 40)
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(SEED)
    f, cat = load()
    feats = [c for c in cat.index[cat.decision == "Giữ"] if c in f] + MAS_COLS
    meta = feature_meta(cat, feats)
    facts = {}

    uni = univariate(f[f.period >= START], feats, meta)
    tprof, tacf, ips = target_profile(f, rng)
    ft, ceil = feature_target(f, feats, meta)
    P, clw, clb, dims, Cw = feature_feature(f, meta)
    roll, reg, budget, sinfo = structure(f, meta)
    miss_year, miss_bank, minfo = missingness(f, feats, meta)
    clus, cinfo = clustering_tendency(f[f.period >= START], rng)
    rk, rk_pairs, _ = ranking_data()
    tov, stars, by_len, asp, lang, by_bank, by_year = text_eda()

    facts.update(n_rows=int((f.period >= START).sum()), n_banks=int(f.ticker.nunique()), n_features=len(feats),
                 n_periods=int(f[f.period >= START].period.nunique()), ips=ips, dims=dims, structure=sinfo, missing=minfo,
                 clustering=cinfo, text=tov)
    dep = pd.read_csv(DEPOSIT_CORR, encoding="utf-8-sig", index_col=0)
    facts["deposit_corr"] = dep.to_dict("records")

    for name, df in [("univariate", uni), ("target_profile", tprof), ("target_acf", tacf), ("feature_target", ft),
                     ("signal_ceiling", ceil), ("corr_pairs_all", P), ("clusters_within_core", clw), ("clusters_between", clb),
                     ("corr_within_core", Cw), ("rolloff", roll), ("regime", reg), ("sample_budget", budget),
                     ("missing_by_year", miss_year), ("missing_by_bank", miss_bank), ("cluster_tendency", clus),
                     ("ranking_criteria", rk), ("ranking_pairs", rk_pairs), ("text_stars", stars), ("text_length", by_len),
                     ("text_aspects", asp), ("text_lang", lang), ("text_by_bank", by_bank), ("text_by_year", by_year)]:
        df.to_csv(f"{OUT_DIR}/{name}.csv", encoding="utf-8-sig", index=(name == "corr_within_core"))
    with open(f"{OUT_DIR}/facts.json", "w", encoding="utf-8") as fh:
        json.dump(facts, fh, ensure_ascii=False, indent=1, default=float)

    print("1. DON BIEN:", uni["shape"].value_counts().to_dict(), "| hanh dong:", uni.linear_action.value_counts().to_dict())
    print("   NH chiem ngoai lai nhieu nhat:", uni[uni.outlier_pct > 2][["feature", "outlier_pct", "top_outlier_bank", "top_outlier_bank_share"]].round(2).to_string(index=False))
    print("\n2. MUC TIEU:\n", tprof.round(3).to_string(index=False))
    print(tacf.pivot(index="label", columns="lag", values=["acf_level", "acf_change"]).round(2).to_string())
    print("   IPS:", ips)
    print("\n3. DAC TRUNG-MUC TIEU (tran R2):\n", ceil.round(3).to_string(index=False))
    print("   bien phi tuyen:", ft[ft.nonlinear][["label", "h", "feature", "rho", "skill_linear", "skill_spline"]].round(3).to_string(index=False))
    print("\n4. DAC TRUNG-DAC TRUNG:", dims)
    print(clw.sort_values(["cluster", "vif"]).round(2).to_string(index=False))
    print("\n5. ROLLOFF:\n", roll.round(3).to_string(index=False))
    print("   CHE DO GIAN NO:\n", reg.round(3).to_string(index=False))
    print("   NGAN SACH MAU:\n", budget.to_string(index=False), sinfo)
    print("\n6. THIEU:", minfo)
    print("\n7. PHAN CUM:\n", clus.round(3).to_string(index=False), cinfo)
    print("\n8. XEP HANG:\n", rk.round(2).to_string(index=False))
    print(rk_pairs.round(2).to_string(index=False))
    print("\n9. VAN BAN:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in tov.items()})
    print(stars.round(3).to_string(index=False))
    print(by_len.round(2).to_string(index=False))
    print(asp.round(3).to_string(index=False))
    print(lang.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
