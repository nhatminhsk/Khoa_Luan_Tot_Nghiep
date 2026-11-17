from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from experiments import algorithm_benchmark as ab
from experiments import longer_history as lh

OUT = Path("data/model/experiments/forecasts_de_xuat.csv")
PUBLISH = Path("data/serving/forecasts.csv")
SELECTION = Path("data/model/experiments/forecast_selection.csv")
# sai so walk-forward co dau cua MOI phuong phap (base + RF), kem thang chuan hoa theo NH -- kho sai so cho vong Monte
# Carlo (experiments.montecarlo_ranking --ml) va kiem chung tach thoi gian (26/10/2026)
OOF = Path("data/model/experiments/forecast_oof_errors.csv")
OOF_ROWS: list[pd.DataFrame] = []
PANEL = Path("data/model/bank_panel_quarterly.csv")
# Chon ca hai tang (kieu base, roi base vs 3 RF) chi bang nhan co quy dich <= moc nay (26/10/2026, thao luan 3 ben ML x Monte
# Carlo): truoc day chon tren GOC 2021-22 nen h4 dung nhan toi 2023-Q4, chong len cac goc kiem tra tu 2023.
SELECT_LABEL_TO = "2022-Q4"
# goc dau cua tap chon base vs RF (buoc 3); kieu base (buoc 1) van chon tren goc tu ab.VALID_FROM.
# 10/11/2026 (nhan xet hoi dong): tra ve tap chon DAT TRUOC 2021-Q1. Ngay 26/10 tung doi sang 2019-Q1 SAU KHI da xem ket
# qua kiem tra; ban 2019 chi con la do nhay (experiments/danh_gia_co_dinh.py, cot lai_B).
SELECT_FROM = "2021-Q1"
# goc dau cua kho sai so walk-forward (kho thuc bat dau tu min(SELECT_FROM, OOF_FROM); noi doc kho tu loc theo goc);
# --oof-from 2015-Q1 keo kho lui (chi them dong sai so, lua chon van tren goc tu SELECT_FROM) va ghi ra
# forecast_oof_errors_tu2015.csv, khong ghi de du bao / lua chon (thu nghiem 26/10/2026)
OOF_FROM = ab.VALID_FROM
MIN_TRAIN = 50  # RF can toi thieu so dong huan luyen; goc som chua du dong (rf_2019 truoc 2019) thi bo phuong phap do
HORIZONS = (1, 2, 3, 4)
LEVEL = 0.90
IND = {"nim": "nim_ttm_percent", "cof": "cof_ttm_percent", "roe": "roe_ttm_percent",
       "npl": "npl_percent", "casa": "casa_percent", "ldr": "ldr_computed_percent"}
ASSET = {"npl_percent", "casa_percent", "ldr_computed_percent"}
NON_NEGATIVE = {"npl_percent", "casa_percent", "ldr_computed_percent", "cof_ttm_percent"}
# nhan cot method; moi dong ghi phuong phap cua chinh tam do
BASE_LABEL = {"naive": "giữ nguyên quý trước", "drift": "xu hướng trung vị", "seasonal": "mùa vụ",
              "rolloff": "trượt cửa sổ 4 quý"}
RF_LABEL = {"rf_2019": "RF phần dư từ 2019", "rf_2013": "RF phần dư từ 2013", "rf_2013w": "RF phần dư từ 2013 (nặng 0,5)"}
METHOD_MAX = 60


def _next(period: str, k: int) -> str:
    i = int(period[:4]) * 4 + int(period[-1]) - 1 + k
    return f"{i // 4}-Q{i % 4 + 1}"


def _target(f: pd.DataFrame, t: str) -> tuple[list[dict], list[dict]]:
    from joblib import Parallel, delayed

    per = sorted(f.period.unique())
    last = per[-1]
    fut = [_next(last, k) for k in range(1, max(HORIZONS) + 1)]
    pos = {p: i for i, p in enumerate(per)}
    pidx = f.period.map(pos).to_numpy()
    fb = f[f.period >= lh.BASE_FROM].reset_index(drop=True)
    per_b = sorted(fb.period.unique())
    rows, sel = [], []
    for h in HORIZONS:
        y = (f.groupby("ticker")[t].shift(-h) - f[t]).to_numpy()
        B = {}
        for io, p in enumerate(per):
            if p < "2013-Q1":
                continue
            if p >= lh.BASE_FROM:
                B[p] = ab.baselines(fb, t, h, per_b + fut, per_b.index(p))
            else:
                B[p] = ab.baselines(f, t, h, per + fut, io)
        # 1. base: MAE tren goc tu 2021-Q1 co quy dich <= SELECT_LABEL_TO (nhan da biet truoc moi goc kiem tra)
        val = []
        for p, b in B.items():
            if ab.VALID_FROM <= p and _next(p, h) <= SELECT_LABEL_TO:
                m = (f.period == p).to_numpy()
                for name in ab.BASELINES:
                    val.append((name, np.nanmean(np.abs(y[m] - b[name].reindex(f.ticker[m]).to_numpy()))))
        best = pd.DataFrame(val, columns=["m", "e"]).groupby("m").e.mean().dropna().idxmin()
        base = np.full(len(f), np.nan)
        for p, b in B.items():
            m = (f.period == p).to_numpy()
            base[m] = b[best].reindex(f.ticker[m]).to_numpy()
        X = f.assign(tq=((f.q + h - 1) % 4 + 1).astype(float))[lh.core(t)].to_numpy(np.float32)
        resid = y - base
        # 2. walk-forward tu min(SELECT_FROM, OOF_FROM): base + 3 bien the RF
        jobs, keys, errs = [], [], []
        for p in per:
            io = pos[p]
            if p < min(SELECT_FROM, OOF_FROM) or io + h >= len(per):
                continue
            te = (pidx == io) & ~np.isnan(y) & ~np.isnan(base)
            if not te.any():
                continue
            errs.append(pd.DataFrame({"origin": p, "ticker": f.ticker[te].to_numpy(), "method": "base",
                                      "err": y[te] - base[te]}))
            for name, (start, w_old) in lh.RUNS.items():
                tr = (f.period >= start).to_numpy() & (pidx <= io - h) & ~np.isnan(resid)
                if tr.sum() < MIN_TRAIN:
                    continue
                w = np.where((f.period < lh.BASE_FROM).to_numpy(), w_old, 1.0)
                jobs.append(delayed(lh._fit_predict)(X, resid, w, tr, te))
                keys.append((p, name, te))
        for (p, name, te), pr in zip(keys, Parallel(n_jobs=-1)(jobs)):
            errs.append(pd.DataFrame({"origin": p, "ticker": f.ticker[te].to_numpy(), "method": name,
                                      "err": y[te] - base[te] - pr}))
        E_all = pd.concat(errs, ignore_index=True).assign(abs_err=lambda d: d.err.abs())
        E = E_all[E_all.origin >= ab.VALID_FROM]  # q conformal, kiem tra: chi goc tu VALID_FROM nhu cu
        W = E.pivot_table(index=["origin", "ticker"], columns="method", values="abs_err").dropna()
        Ws = E_all[E_all.origin >= SELECT_FROM].pivot_table(index=["origin", "ticker"], columns="method",
                                                            values="abs_err").dropna()
        in_sel = np.array([_next(o, h) <= SELECT_LABEL_TO for o in Ws.index.get_level_values("origin")])
        val_mae = Ws[in_sel].mean()
        pick = val_mae.idxmin()
        # muc dao dong cua NH tai goc p: trung vi |thay doi h quy| cua cac thay doi da biet (ket thuc <= p)
        ay = pd.Series(np.abs(y), index=f.index)
        # 12 quy gan nhat: lich su 2012-14 (khung hoang no xau) lam muc dao dong cua VCB qua lon so voi hien tai
        own = ay.groupby(f.ticker).transform(lambda s: s.rolling(12, min_periods=4).median().shift(h))
        pooled = pd.Series({p: np.nanmedian(np.abs(y)[pidx <= pos[p] - h]) if (pidx <= pos[p] - h).any() else np.nan
                            for p in per})
        # co ve muc chung (trung binh nhan): NVB NPL 3,7% -> 35% -> 6,4% (2022-26) lam khoang rieng 0-50%
        pool = f.period.map(pooled)
        scale = np.sqrt(own.fillna(pool).clip(lower=0.1 * pool) * pool)
        sc = dict(zip(zip(f.ticker, f.period), scale))
        OOF_ROWS.append(E_all.drop(columns="abs_err").assign(
            indicator=t, h=h, target_period=[_next(p, h) for p in E_all.origin], base=best, chosen=pick,
            scale=[sc[(tk, p)] for tk, p in zip(E_all.ticker, E_all.origin)]))
        Ep = E[E.method == pick].copy()
        Ep["nerr"] = Ep.abs_err / [sc[(tk, p)] for tk, p in zip(Ep.ticker, Ep.origin)]
        q_val = float(Ep.loc[[_next(o, h) <= SELECT_LABEL_TO for o in Ep.origin], "nerr"].quantile(LEVEL))
        cov = float((Ep.loc[Ep.origin >= ab.TEST_FROM, "nerr"] <= q_val).mean())
        q = float(Ep.nerr.quantile(LEVEL))
        test = W[W.index.get_level_values("origin") >= ab.TEST_FROM]
        sel.append(dict(indicator=t, h=h, base=best, method=pick, valid_mae=val_mae[pick], valid_mae_base=val_mae["base"],
                        test_gain_vs_base=(1 - test[pick].mean() / test["base"].mean()) if len(test) else np.nan,
                        n_test=len(test), q90_norm=q, coverage_test=cov))
        # 3. du bao tu goc cuoi cung
        io = pos[last]
        now = (pidx == io) & ~np.isnan(f[t].to_numpy()) & ~np.isnan(base)
        delta = base[now].copy()
        if pick != "base":
            start, w_old = lh.RUNS[pick]
            tr = (f.period >= start).to_numpy() & (pidx <= io - h) & ~np.isnan(resid)
            w = np.where((f.period < lh.BASE_FROM).to_numpy(), w_old, 1.0)
            delta = delta + lh._fit_predict(X, resid, w, tr, now)
        for tk, d, b, s_ in zip(f.ticker[now], delta, base[now], scale[now]):
            rows.append(dict(ticker=tk, h=h, delta=d, naive_delta=b, method=pick, base=best, q=q * s_))
        print(f"  {t} h={h}: base {best}, chon {pick}, do phu kiem tra {cov:.0%}", flush=True)
    return rows, sel


def _label(method: str, base: str) -> str:
    lab = BASE_LABEL[base] if method == "base" else f"{RF_LABEL[method]} + {BASE_LABEL[base]}"
    if len(lab) > METHOD_MAX:
        raise ValueError(f"nhan phuong phap qua {METHOD_MAX} ky tu: {lab}")
    return lab


def build() -> tuple[pd.DataFrame, pd.DataFrame]:
    panel = pd.read_csv(PANEL, encoding="utf-8-sig")
    last = panel.period.max()
    anchor = panel[panel.period == last].set_index("ticker")
    frames = {False: lh.load(False), True: lh.load(True)}
    out, sels = [], []
    for code, t in IND.items():
        f = frames[t in ASSET]
        if f.period.max() != last:
            raise ValueError(f"{t}: chuoi hoc ket thuc {f.period.max()} khac panel {last}")
        rows, sel = _target(f, t)
        S = pd.DataFrame(sel).assign(indicator_code=code)
        sels.append(S)
        for r in rows:
            x0 = anchor[t].get(r["ticker"], np.nan)
            if x0 != x0:
                continue
            v, nv = x0 + r["delta"], x0 + r["naive_delta"]
            lo, hi = v - r["q"], v + r["q"]
            if t in NON_NEGATIVE:
                v, nv, lo = max(v, 0.0), max(nv, 0.0), max(lo, 0.0)
            out.append(dict(ticker=r["ticker"], indicator=code, origin_period=last, target_period=_next(last, r["h"]),
                            horizon=r["h"], value=round(v, 4), lower=round(lo, 4), upper=round(hi + 0, 4),
                            naive_value=round(nv, 4), method=_label(r["method"], r["base"])))
    return pd.DataFrame(out).sort_values(["ticker", "indicator", "horizon"]), pd.concat(sels, ignore_index=True)


def main():
    global OOF_FROM
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--oof-from" in sys.argv:  # chi keo kho sai so lui; kiem lua chon trung ban hien hanh roi ghi kho rieng
        OOF_FROM = sys.argv[sys.argv.index("--oof-from") + 1]
        F, S = build()
        old = pd.read_csv(SELECTION, encoding="utf-8-sig")
        same = (old[["indicator", "h", "base", "method"]].values == S[["indicator", "h", "base", "method"]].values).all()
        if not same:  # kho dai phai di voi DUNG lua chon dang dung (Nguoi 2, luot 3)
            raise SystemExit(f"lua chon phuong phap khong trung {SELECTION}: chay lai python -m serving.forecast truoc")
        dst = OOF.with_name(f"{OOF.stem}_tu{OOF_FROM[:4]}{OOF.suffix}")
        pd.concat(OOF_ROWS, ignore_index=True).to_csv(dst, index=False, encoding="utf-8-sig")
        print(f"-> {dst} (goc tu {OOF_FROM}); lua chon trung ban hien hanh: {same}")
        return
    F, S = build()
    out = PUBLISH if "--publish" in sys.argv else OUT
    F.to_csv(out, index=False, encoding="utf-8")  # hop dong serving: UTF-8 khong BOM
    S.to_csv(SELECTION, index=False, encoding="utf-8-sig")
    pd.concat(OOF_ROWS, ignore_index=True).to_csv(OOF, index=False, encoding="utf-8-sig")
    print(f"-> {out}: {len(F)} dong, {F.ticker.nunique()} NH x {F.indicator.nunique()} chi tieu x {F.horizon.nunique()} tam, "
          f"goc {F.origin_period.iloc[0]}")
    show = S.assign(test_gain_vs_base=(S.test_gain_vs_base * 100).round(1), coverage_test=(S.coverage_test * 100).round(0))
    print(show[["indicator_code", "h", "base", "method", "test_gain_vs_base", "coverage_test"]].to_string(index=False))


if __name__ == "__main__":
    main()
