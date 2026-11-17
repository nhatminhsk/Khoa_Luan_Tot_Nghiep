from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from experiments import algorithm_benchmark as ab
from experiments import longer_history as lh

warnings.filterwarnings("ignore")

OUT = Path("data/model/experiments/danh_gia_co_dinh")
CAU_HINH = dict(
    muc_tieu=["npl_percent", "casa_percent", "ldr_computed_percent"],
    tam=[1, 2, 3, 4],
    du_lieu=lh.LONG_PANEL,
    TRAIN_FROM="2019-Q1",            # cửa sổ học chính của Ridge, LightGBM, RF
    VALID_FROM="2021-Q1",            # tập chọn đặt trước (trước khi có kết quả kiểm tra)
    VALID_FROM_DOI="2019-Q1",        # tập chọn đã đổi ngày 26/10/2026, chỉ chạy làm độ nhạy
    VALID_LABEL_TO="2022-Q4",
    TEST_FROM="2023-Q1",
    co_so=["naive", "drift", "seasonal"],
    rf=dict(lh.RF_PARAMS, random_state=lh.SEED),
    rf_cua_so=lh.RUNS,
    ridge_alpha=10.0,
    lgbm=ab.LGB_PARAMS,
    bootstrap=dict(B=2000, seed=ab.SEED, don_vi="ngan_hang"),
    muc_khoang=0.90,
    hat_giong_rf=[lh.SEED, 1, 2, 3, 4],
    nguong_canh_bao_npl=0.20,
)
LABEL = {"npl_percent": "NPL", "casa_percent": "CASA", "ldr_computed_percent": "LDR"}
MIN_TRAIN = 50
LUOI_THAM_SO = ([dict(n_estimators=n) for n in (50, 100, 200, 300, 500, 1000)]
                + [dict(min_samples_leaf=k) for k in (1, 3, 5, 10, 20, 40)]
                + [dict(max_features=v) for v in (0.2, 0.33, 0.5, 0.75, 1.0)])


def _next(period: str, k: int) -> str:
    i = int(period[:4]) * 4 + int(period[-1]) - 1 + k
    return f"{i // 4}-Q{i % 4 + 1}"


def _sha(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _rf(X, y, w, tr, te, **kw):
    from sklearn.ensemble import RandomForestRegressor
    p = {**CAU_HINH["rf"], **kw}
    return RandomForestRegressor(**p).fit(X[tr], y[tr], sample_weight=w[tr]).predict(X[te])


def _ridge(Xr, y, tr, te):
    from sklearn.linear_model import Ridge
    Xtr, Xte = Xr[tr], Xr[te]
    mu, sd = np.nanmean(Xtr, 0), np.nanstd(Xtr, 0)
    sd[sd == 0] = 1
    Xtr_s, Xte_s = np.nan_to_num((Xtr - mu) / sd), np.nan_to_num((Xte - mu) / sd)
    return Ridge(alpha=CAU_HINH["ridge_alpha"]).fit(Xtr_s, y[tr]).predict(Xte_s)


def _lgbm(X, y, tr, te):
    import lightgbm as lgb
    return lgb.LGBMRegressor(**CAU_HINH["lgbm"]).fit(X[tr], y[tr]).predict(X[te])


class Khung:
    def __init__(self, f: pd.DataFrame, t: str, h: int):
        self.f, self.t, self.h = f, t, h
        self.per = sorted(f.period.unique())
        self.pos = {p: i for i, p in enumerate(self.per)}
        self.pidx = f.period.map(self.pos).to_numpy()
        self.y = (f.groupby("ticker")[t].shift(-h) - f[t]).to_numpy()
        self.x0 = f[t].to_numpy()
        fut = [_next(self.per[-1], k) for k in range(1, h + 1)]
        fb = f[f.period >= lh.BASE_FROM].reset_index(drop=True)
        per_b = sorted(fb.period.unique())
        B = {}
        for io, p in enumerate(self.per):
            if p < "2013-Q1":
                continue
            B[p] = (ab.baselines(fb, t, h, per_b + fut, per_b.index(p)) if p >= lh.BASE_FROM
                    else ab.baselines(f, t, h, self.per + fut, io))
        self.B = B
        self.base_all = {}
        for name in CAU_HINH["co_so"]:
            v = np.full(len(f), np.nan)
            for p, b in B.items():
                m = (f.period == p).to_numpy()
                v[m] = b[name].reindex(f.ticker[m]).to_numpy()
            self.base_all[name] = v
        # chọn mô hình cơ sở trên tập chọn đặt trước (gốc từ VALID_FROM, quý đích <= VALID_LABEL_TO)
        val = {}
        for name, v in self.base_all.items():
            m = np.array([CAU_HINH["VALID_FROM"] <= p and _next(p, h) <= CAU_HINH["VALID_LABEL_TO"] for p in f.period])
            val[name] = np.nanmean(np.abs(self.y[m] - v[m]))
        self.val_base = val
        self.best = min(val, key=val.get)
        self.base = self.base_all[self.best]
        self.resid = self.y - self.base
        self.X = f.assign(tq=((f.q + h - 1) % 4 + 1).astype(float))[lh.core(t)].to_numpy(np.float32)
        tq = (f.q + h - 1) % 4 + 1
        self.Xr = np.column_stack([f[[c for c in lh.core(t) if c != "tq"]].to_numpy(float)]
                                  + [(tq == k).to_numpy(float) for k in (1, 2, 3)])
        self.w_old = {name: np.where((f.period < lh.BASE_FROM).to_numpy(), w, 1.0) for name, (_, w) in lh.RUNS.items()}

    def train_mask(self, io: int, start: str, target: np.ndarray) -> np.ndarray:
        return (self.f.period >= start).to_numpy() & (self.pidx <= io - self.h) & ~np.isnan(target)

    def test_mask(self, io: int) -> np.ndarray:
        return (self.pidx == io) & ~np.isnan(self.y) & ~np.isnan(self.base)


def chay_mot_o(f: pd.DataFrame, t: str, h: int, hat: list[int]) -> tuple[pd.DataFrame, Khung]:
    from joblib import Parallel, delayed
    K = Khung(f, t, h)
    jobs, keys = [], []
    origins = [p for p in K.per if p >= CAU_HINH["VALID_FROM_DOI"] and K.pos[p] + h < len(K.per)]
    for p in origins:
        io = K.pos[p]
        te = K.test_mask(io)
        if not te.any():
            continue
        for name, (start, _) in lh.RUNS.items():
            tr = K.train_mask(io, start, K.resid)
            if tr.sum() >= MIN_TRAIN:
                jobs.append(delayed(_rf)(K.X, K.resid, K.w_old[name], tr, te))
                keys.append((p, name, te))
        tr = K.train_mask(io, CAU_HINH["TRAIN_FROM"], K.resid)
        if tr.sum() >= MIN_TRAIN:
            for s in hat[1:]:
                jobs.append(delayed(_rf)(K.X, K.resid, np.ones(len(f)), tr, te, random_state=s))
                keys.append((p, f"rf_2019_s{s}", te))
            jobs.append(delayed(_ridge)(K.Xr, K.resid, tr, te))
            keys.append((p, "ridge", te))
            jobs.append(delayed(_lgbm)(K.X, K.resid, tr, te))
            keys.append((p, "lgbm_res", te))
        tr13 = K.train_mask(io, "2013-Q1", K.resid)
        if tr13.sum() >= MIN_TRAIN:  # cùng điều kiện với rf_2013: học thêm 2013–2017
            jobs.append(delayed(_ridge)(K.Xr, K.resid, tr13, te))
            keys.append((p, "ridge_2013", te))
            jobs.append(delayed(_lgbm)(K.X, K.resid, tr13, te))
            keys.append((p, "lgbm_2013", te))
        trd = K.train_mask(io, CAU_HINH["TRAIN_FROM"], K.y)
        if trd.sum() >= MIN_TRAIN:
            jobs.append(delayed(_lgbm)(K.X, K.y, trd, te))
            keys.append((p, "lgbm_thang", te))
    preds = Parallel(n_jobs=-1)(jobs)
    rows = []
    for p in origins:
        te = K.test_mask(K.pos[p])
        if not te.any():
            continue
        d = dict(origin=p, ticker=K.f.ticker[te].to_numpy(), y=K.y[te], x0=K.x0[te])
        for name in CAU_HINH["co_so"]:
            rows.append(pd.DataFrame({**d, "method": name, "pred": K.base_all[name][te]}))
        rows.append(pd.DataFrame({**d, "method": "base", "pred": K.base[te]}))
    for (p, name, te), pr in zip(keys, preds):
        d = dict(origin=p, ticker=K.f.ticker[te].to_numpy(), y=K.y[te], x0=K.x0[te])
        pred = pr if name == "lgbm_thang" else K.base[te] + pr
        rows.append(pd.DataFrame({**d, "method": name, "pred": pred}))
    P = pd.concat(rows, ignore_index=True).assign(indicator=t, h=h, base_is=K.best)
    P["target_period"] = [_next(o, h) for o in P.origin]
    P["err"] = P.y - P.pred
    return P, K


def chon(P: pd.DataFrame, valid_from: str) -> tuple[str, pd.Series]:
    cand = ["base", *lh.RUNS]
    W = P[P.method.isin(cand)].pivot_table(index=["origin", "ticker"], columns="method", values="err",
                                         aggfunc="first").abs()
    W = W.dropna()
    o = W.index.get_level_values("origin")
    h = int(P.h.iloc[0])
    m = (o >= valid_from) & np.array([_next(x, h) <= CAU_HINH["VALID_LABEL_TO"] for x in o])
    mae = W[m].mean()
    return mae.idxmin(), mae


def tom_tat(P: pd.DataFrame, chon_a: str, chon_b: str, rng_seed: int) -> list[dict]:
    T = P[P.origin >= CAU_HINH["TEST_FROM"]].copy()
    W = T.pivot_table(index=["origin", "ticker"], columns="method", values="err", aggfunc="first")
    W["lai_A"], W["lai_B"] = W[chon_a], W[chon_b]
    main = ["naive", "drift", "seasonal", "base", "ridge", "lgbm_res", "lgbm_thang", "rf_2019", "rf_2013", "rf_2013w",
            "ridge_2013", "lgbm_2013", "lai_A", "lai_B"]
    W = W.dropna(subset=main)
    lvl = T.drop_duplicates(["origin", "ticker"]).set_index(["origin", "ticker"]).reindex(W.index)
    actual = (lvl.x0 + lvl.y).to_numpy()
    by = W.abs().groupby(level="ticker").sum()
    rng = np.random.default_rng(rng_seed)
    idx = [rng.integers(0, len(by), len(by)) for _ in range(CAU_HINH["bootstrap"]["B"])]
    out = []
    for m in [c for c in W.columns if c in main or c.startswith("rf_2019_s")]:
        e = W[m].to_numpy()
        r = dict(method=m, n=len(W), mae=np.mean(np.abs(e)), rmse=np.sqrt(np.mean(e ** 2)),
                 mape=np.mean(np.abs(e) / np.abs(actual)) * 100)
        g = 1 - by[m].sum() / by["base"].sum()
        bs = [1 - by[m].iloc[i].sum() / by["base"].iloc[i].sum() for i in idx]
        r.update(gain_vs_base=g, lo=np.percentile(bs, 2.5), hi=np.percentile(bs, 97.5),
                 gain_vs_naive=1 - by[m].sum() / by["naive"].sum())
        for nhan, (a, b) in {"2023_2024": ("2023-Q1", "2024-Q4"), "2025_2026": ("2025-Q1", "2099-Q4")}.items():
            o = W.index.get_level_values("origin")
            s = (o >= a) & (o <= b)
            r[f"mae_{nhan}"] = np.mean(np.abs(e[s]))
            r[f"gain_{nhan}"] = 1 - np.mean(np.abs(e[s])) / np.mean(np.abs(W["base"].to_numpy()[s]))
        t_ = W.index.get_level_values("ticker")
        s = ~np.isin(t_, ["NVB", "STB"])
        r["mae_bo_nvb_stb"] = np.mean(np.abs(e[s]))
        r["gain_bo_nvb_stb"] = 1 - np.mean(np.abs(e[s])) / np.mean(np.abs(W["base"].to_numpy()[s]))
        out.append(r)
    return out


def khoang(P: pd.DataFrame, K: Khung, method: str) -> tuple[dict, pd.Series, float]:
    f, h = K.f, K.h
    ay = pd.Series(np.abs(K.y), index=f.index)
    own = ay.groupby(f.ticker).transform(lambda s: s.rolling(12, min_periods=4).median().shift(h))
    pooled = pd.Series({p: np.nanmedian(np.abs(K.y)[K.pidx <= K.pos[p] - h]) if (K.pidx <= K.pos[p] - h).any()
                        else np.nan for p in K.per})
    pool = f.period.map(pooled)
    scale = np.sqrt(own.fillna(pool).clip(lower=0.1 * pool) * pool)
    sc = dict(zip(zip(f.ticker, f.period), scale))
    E = P[P.method == method].dropna(subset=["err"]).copy()
    E["scale"] = [sc[(a, b)] for a, b in zip(E.ticker, E.origin)]
    E["nerr"] = E.err.abs() / E.scale
    v = (E.origin >= CAU_HINH["VALID_FROM"]) & np.array([_next(o, h) <= CAU_HINH["VALID_LABEL_TO"] for o in E.origin])
    q = float(E.loc[v, "nerr"].quantile(CAU_HINH["muc_khoang"]))
    T = E[E.origin >= CAU_HINH["TEST_FROM"]]
    inside = T.nerr <= q
    big = T.y.abs() > (1.0 if K.t == "npl_percent" else T.y.abs().quantile(0.9))
    r = dict(q90=q, phu=inside.mean(), n=len(T), phu_thay_doi_lon=inside[big].mean(), n_lon=int(big.sum()),
             phu_thay_doi_thuong=inside[~big].mean(), do_rong_tb=float((2 * q * T.scale).mean()),
             phu_bo_nvb_stb=inside[~T.ticker.isin(["NVB", "STB"])].mean())
    # khoảng thích nghi: q cập nhật ở mỗi gốc bằng các sai số đã biết (quý đích <= gốc), chỉ để đối chiếu
    T2 = E[E.origin >= CAU_HINH["TEST_FROM"]]
    cov = []
    for o, g in T2.groupby("origin"):
        known = E[np.array([_next(x, h) <= o for x in E.origin])]
        cov.extend(g.nerr <= known.nerr.quantile(CAU_HINH["muc_khoang"]))
    r["phu_thich_nghi"] = float(np.mean(cov))
    return r, scale, q


def canh_bao(P: pd.DataFrame, method: str, h: int, nguong: float) -> tuple[dict, pd.DataFrame]:
    T = P[(P.origin >= CAU_HINH["TEST_FROM"]) & P.method.isin([method, "naive"])]
    W = T.pivot_table(index=["origin", "ticker"], columns="method", values="pred", aggfunc="first").dropna()
    y = T[T.method == "naive"].set_index(["origin", "ticker"]).y.reindex(W.index)
    alert = W[method] > nguong
    up = y > nguong
    r = dict(h=h, n=len(W), ty_le_tang_that=up.mean(), so_canh_bao=int(alert.sum()),
             chinh_xac=up[alert].mean() if alert.any() else np.nan, bat_duoc=alert[up].mean() if up.any() else np.nan)
    return r, W.assign(y=y, alert=alert, up=up)


def tham_so_rf(frames: dict) -> pd.DataFrame:
    from joblib import Parallel, delayed
    rows = []
    for t in CAU_HINH["muc_tieu"]:
        for h in CAU_HINH["tam"]:
            K = Khung(frames[t], t, h)
            origins = [p for p in K.per if p >= CAU_HINH["VALID_FROM"] and _next(p, h) <= CAU_HINH["VALID_LABEL_TO"]]
            for kw in LUOI_THAM_SO:
                jobs, tes = [], []
                for p in origins:
                    io = K.pos[p]
                    te, tr = K.test_mask(io), K.train_mask(io, CAU_HINH["TRAIN_FROM"], K.resid)
                    if te.any() and tr.sum() >= MIN_TRAIN:
                        jobs.append(delayed(_rf)(K.X, K.resid, np.ones(len(K.f)), tr, te, **kw))
                        tes.append(te)
                pr = Parallel(n_jobs=-1)(jobs)
                e_rf = np.concatenate([K.resid[te] - p_ for te, p_ in zip(tes, pr)])
                e_b = np.concatenate([K.resid[te] for te in tes])
                k, v = next(iter(kw.items()))
                rows.append(dict(indicator=LABEL[t], h=h, tham_so=k, gia_tri=v, n=len(e_b),
                                 ty_so=np.mean(np.abs(e_rf)) / np.mean(np.abs(e_b))))
            print(f"  tham số {LABEL[t]} h={h} xong", flush=True)
    return pd.DataFrame(rows)


def du_bao_ky_toi(K: Khung, method: str, q: float, scale: pd.Series) -> list[dict]:
    io = len(K.per) - 1
    now = (K.pidx == io) & ~np.isnan(K.x0) & ~np.isnan(K.base)
    delta = K.base[now].copy()
    if method != "base":
        start, _ = lh.RUNS[method]
        tr = K.train_mask(io, start, K.resid)
        delta = delta + _rf(K.X, K.resid, K.w_old[method], tr, now)
    out = []
    for tk, x0, d, s in zip(K.f.ticker[now], K.x0[now], delta, scale.to_numpy()[now]):
        v = max(x0 + d, 0.0)
        out.append(dict(ticker=tk, indicator={"npl_percent": "npl", "casa_percent": "casa",
                                              "ldr_computed_percent": "ldr"}[K.t],
                        origin_period=K.per[-1], target_period=_next(K.per[-1], K.h), horizon=K.h,
                        value=round(v, 4), lower=round(max(x0 + d - q * s, 0.0), 4), upper=round(x0 + d + q * s, 4),
                        method=method, base=K.best))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    meta = dict(CAU_HINH, chay_luc=time.strftime("%Y-%m-%d %H:%M:%S"),
                commit=subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
                sha256_du_lieu=_sha(lh.LONG_PANEL), python=sys.version.split()[0])
    import lightgbm
    import sklearn
    meta.update(sklearn=sklearn.__version__, lightgbm=lightgbm.__version__)
    (OUT / "config.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    f = lh.load(True)
    frames = {t: f for t in CAU_HINH["muc_tieu"]}
    allP, summ, chosen, cov, warn, fc = [], [], [], [], [], []
    warn_rows = []
    for t in CAU_HINH["muc_tieu"]:
        for h in CAU_HINH["tam"]:
            P, K = chay_mot_o(f, t, h, CAU_HINH["hat_giong_rf"])
            a, mae_a = chon(P, CAU_HINH["VALID_FROM"])
            b, mae_b = chon(P, CAU_HINH["VALID_FROM_DOI"])
            chosen.append(dict(indicator=LABEL[t], h=h, base=K.best, chon_2021=a, chon_2019=b,
                               **{f"val_base_{k}": v for k, v in K.val_base.items()},
                               **{f"val2021_{k}": v for k, v in mae_a.items()},
                               **{f"val2019_{k}": v for k, v in mae_b.items()}))
            for r in tom_tat(P, a, b, CAU_HINH["bootstrap"]["seed"]):
                summ.append(dict(indicator=LABEL[t], h=h, base_is=K.best, chon_2021=a, chon_2019=b, **r))
            for meth in sorted({a, "rf_2019", "base"}):
                r, scale, q = khoang(P, K, meth)
                cov.append(dict(indicator=LABEL[t], h=h, method=meth, la_quy_tac=meth == a, **r))
                if meth == a:
                    fc.extend(du_bao_ky_toi(K, a, q, scale))
            if t == "npl_percent":
                for meth in ("rf_2019", "base", a):
                    r, W = canh_bao(P, meth, h, CAU_HINH["nguong_canh_bao_npl"])
                    warn.append(dict(method=meth, **r))
                    if meth == "rf_2019":
                        warn_rows.append(W.reset_index().assign(h=h))
                # quy tắc ngây thơ: quý vừa rồi tăng > ngưỡng thì báo tăng
                T = P[(P.origin >= CAU_HINH["TEST_FROM"]) & (P.method == "naive")].copy()
                d1 = f.set_index(["ticker", "period"])[f"{t}_d1"]
                T["d1"] = [d1.get((tk, o), np.nan) for tk, o in zip(T.ticker, T.origin)]
                al, up = T.d1 > CAU_HINH["nguong_canh_bao_npl"], T.y > CAU_HINH["nguong_canh_bao_npl"]
                warn.append(dict(method="quy_vua_roi_tang", h=h, n=len(T), ty_le_tang_that=up.mean(),
                                 so_canh_bao=int(al.sum()), chinh_xac=up[al].mean(), bat_duoc=al[up].mean()))
            allP.append(P)
            print(f"{LABEL[t]} h={h}: cơ sở {K.best}, chọn (2021) {a}, chọn (2019) {b}  [{time.time() - t0:.0f}s]",
                  flush=True)
    P = pd.concat(allP, ignore_index=True)
    P.to_csv(OUT / "sai_so_tung_dong.csv", index=False, encoding="utf-8-sig")
    S = pd.DataFrame(summ)
    S.to_csv(OUT / "tom_tat.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(chosen).to_csv(OUT / "lua_chon.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(cov).to_csv(OUT / "khoang_du_bao.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(warn).to_csv(OUT / "canh_bao_npl.csv", index=False, encoding="utf-8-sig")
    pd.concat(warn_rows).to_csv(OUT / "canh_bao_npl_tung_dong.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(fc).to_csv(OUT / "du_bao_ky_toi.csv", index=False, encoding="utf-8")
    show = S[S.method.isin(["base", "ridge", "lgbm_res", "lgbm_thang", "rf_2019", "lai_A", "lai_B"])]
    print(show.pivot_table(index=["indicator", "h"], columns="method", values="mae").round(3).to_string())
    if "--khong-tham-so" not in sys.argv:
        R = tham_so_rf(frames)
        R.to_csv(OUT / "tham_so_rf_tap_chon.csv", index=False, encoding="utf-8-sig")
        print(R.groupby(["tham_so", "gia_tri"]).ty_so.mean().round(4).to_string())
    print(f"xong sau {time.time() - t0:.0f}s -> {OUT}")


if __name__ == "__main__":
    main()
