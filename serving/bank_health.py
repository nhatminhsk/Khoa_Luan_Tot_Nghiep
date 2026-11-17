from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RANKING = "data/model/features_ranking_latest.csv"
PANEL = "data/model/bank_panel_quarterly.csv"
CAR_FILE = "data/credit/bank_car_halfyear.csv"
OUT = Path("data/serving/bank_health.csv")
NAME = "Điểm tài chính tương đối tham khảo các nhóm chỉ tiêu Moody's"
# nhom -> (cot, chieu, trong so); cot von doi theo CAPITAL
GROUPS = {"tai_san": ("problem_loans_pct", -1, 0.25), "von": (None, +1, 0.25), "sinh_loi": ("roa_ttm_percent", +1, 0.15),
          "huy_dong": ("deposits_to_assets_pct", +1, 0.20), "thanh_khoan": ("liquid_assets_pct", +1, 0.15)}
CAPITAL = {"car": "car_asof_percent", "von_chu": "equity_to_assets_pct"}


def inputs(ranking: str = RANKING) -> pd.DataFrame:
    rk = pd.read_csv(ranking, encoding="utf-8-sig").set_index("ticker")
    p = pd.read_csv(PANEL, encoding="utf-8-sig").set_index(["ticker", "period"])
    out = pd.DataFrame(index=rk.index)
    out["ky_BCTC"] = rk.latest_period
    out["problem_loans_pct"] = rk.npl_percent + rk.loans_g2_percent
    out["car_asof_percent"] = rk.car_asof_percent
    out["equity_to_assets_pct"] = rk.equity_to_assets_pct
    out["roa_ttm_percent"] = rk.roa_ttm_percent
    dep = [p.deposits_vnd.get((t, q), np.nan) / p.total_assets_vnd.get((t, q), np.nan) * 100 for t, q in zip(rk.index, rk.latest_period)]
    out["deposits_to_assets_pct"] = dep
    out["liquid_assets_pct"] = rk.liquid_assets_pct
    car = pd.read_csv(CAR_FILE, encoding="utf-8-sig").dropna(subset=["car_percent"]).sort_values("period")
    last = car.groupby("ticker").last()
    out["ky_CAR"] = last.period.reindex(out.index)
    out["CAR_thong_tu"] = last.thong_tu.reindex(out.index)
    return out


def score(raw: pd.DataFrame, capital: str = "car", missing: str = "trung_vi", drop: tuple = ()) -> pd.DataFrame:
    P, w = pd.DataFrame(index=raw.index), {}
    for g, (col, d, wt) in GROUPS.items():
        if g in drop:
            continue
        c = col or CAPITAL[capital]
        x = raw[c].astype(float)
        fill = x.median() if missing == "trung_vi" else (x.min() if d > 0 else x.max())
        P[f"pv_{g}"] = (x.fillna(fill) * d).rank(pct=True)
        w[g] = wt
    tot = sum(w.values())
    P["diem"] = sum(P[f"pv_{g}"] * wt / tot for g, wt in w.items())
    P["hang"] = P.diem.rank(ascending=False, method="min").astype(int)
    return P


def build(ranking: str = RANKING) -> pd.DataFrame:
    raw = inputs(ranking)
    a, b = score(raw, "car"), score(raw, "von_chu")
    out = raw.join(a.drop(columns=["diem", "hang"]))
    out["diem_car"], out["hang_car"] = a.diem, a.hang
    out["diem_von_chu"], out["hang_von_chu"] = b.diem, b.hang
    out["dich_hang_doi_von"] = b.hang - a.hang
    miss = raw[[c for c in ("problem_loans_pct", "car_asof_percent", "equity_to_assets_pct", "roa_ttm_percent",
                            "deposits_to_assets_pct", "liquid_assets_pct")]].isna()
    out["o_thieu_dien_trung_vi"] = miss.apply(lambda r: ",".join(r.index[r]), axis=1)
    out["ten_bang"] = NAME
    return out.reset_index()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ranking = sys.argv[sys.argv.index("--ranking") + 1] if "--ranking" in sys.argv else RANKING
    T = build(ranking)
    T.round(6).to_csv(OUT, index=False, encoding="utf-8", lineterminator="\n")
    print(f"-> {OUT}: {len(T)} NH, anh chup {ranking}")
    print(T.sort_values("hang_car")[["ticker", "ky_BCTC", "problem_loans_pct", "car_asof_percent", "roa_ttm_percent",
                                     "deposits_to_assets_pct", "liquid_assets_pct", "hang_car", "hang_von_chu",
                                     "o_thieu_dien_trung_vi"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
