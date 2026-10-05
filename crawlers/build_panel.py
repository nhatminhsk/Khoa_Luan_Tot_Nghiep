"""Gop tat ca nguon thanh MOT panel bank-quarter san sang cho mo hinh.

Van de bao cao kiem ke chi ra: tren 748 o (22 NH x 34 quy 2018-Q1..2026-Q2),
chuoi quy LIEN TUC dai nhat moi ngan hang dat duoc chi la **20 quy**, tat ca deu
bat dau dung o 2021-Q3. Do khong phai gioi han cua du lieu ma la o 2021-Q2 bi
thieu trong file `ratio` cua VCI, cat doi chuoi 34 quy.

Module nay vaN lo hong do bang cach xep ba nguon theo thu tu uu tien, va ghi lai
tung o lay tu dau vao cot `*_src`:

  npl_percent      note (so cap)   -> credit VCI
  npl_coverage_percent  credit VCI -> |du phong cho vay| / no nhom 3-5 (note)
  casa_percent     note            (chua tung co trong du an)
  cof_ttm_percent  VCI ratio       -> MAS (cong 4 quy)
  nim_ttm_percent  VCI ratio       -> MAS (cong 4 quy)
  earning_asset_yield_ttm_percent  MAS (nguon cong bo) -> lending_yield (suy ra)
  roe/roa/cir/pe/pb/eps/bvps       MAS
  car_percent      bank_car_halfyear, gan cho quy cuoi cua nua nam tuong ung

Moi cot ty le deu kem mot cot `<ten>_src` nhan gia tri 'vci' | 'mas' | 'note' |
'derived' | 'halfyear' de truy nguoc duoc trong khoa luan.

Chay:
    python -m crawlers.build_panel
    python -m crawlers.build_panel --validate       # do phu va do dai chuoi
    python -m crawlers.build_panel --no-check       # bo qua cong chat luong

Sau khi ghi panel, module tu goi `crawlers.validate --scope panel` lam cong chat
luong. `validate()` o day do DO PHU va DO DAI CHUOI; `crawlers.validate` do TINH
DUNG DAN (mien gia tri, dang thuc noi bo, ty so tinh tren mau bang 0). Hai cai bo
sung cho nhau, khong thay the nhau. Co ERROR thi ma thoat la 1 de moi script noi
duoi (`build_panel && train`) dung lai thay vi hoc tren du lieu hong.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

OUT_PATH = "data/model/bank_panel_quarterly.csv"
LOG_PATH = "crawl_log.txt"

CREDIT = "data/credit/bank_credit_quarterly.csv"
NOTE = "data/credit/bank_asset_quality_quarterly.csv"
MAS = "data/vnstock_financial/ratio_mas_ttm.csv"
COF = "data/interest_rates/bank_cost_of_funds_quarterly.csv"
YIELD = "data/interest_rates/bank_earning_asset_yield_quarterly.csv"
CAR = "data/credit/bank_car_halfyear.csv"

QUARTERS = [f"{y}-Q{q}" for y in range(2018, 2027) for q in range(1, 5)][:34]
QUARTER_END = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}

# Cot dac trung dung de do "do day du" cho mo hinh chuoi.
CORE_FEATURES = [
    "loans_vnd", "deposits_vnd", "ldr_computed_percent",
    "npl_percent", "casa_percent",
    "nim_ttm_percent", "cof_ttm_percent", "earning_asset_yield_ttm_percent",
]


def _log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")


def _read(path, **kw):
    return pd.read_csv(path, encoding="utf-8-sig", **kw)


def _coalesce(frame, primary, fallback, primary_tag, fallback_tag):
    """Lay primary, thieu thi lay fallback; tra ve (gia tri, nguon)."""
    value = frame[primary].where(frame[primary].notna(), frame[fallback])
    source = np.where(
        frame[primary].notna(), primary_tag,
        np.where(frame[fallback].notna(), fallback_tag, None),
    )
    return value, source


def build(write=True):
    credit = _read(CREDIT)
    tickers = sorted(credit["ticker"].unique())
    grid = pd.MultiIndex.from_product(
        [tickers, QUARTERS], names=["ticker", "period"]
    ).to_frame(index=False)

    panel = grid.merge(
        credit[[
            "period", "ticker", "loans_vnd", "deposits_vnd", "total_assets_vnd",
            "loans_qoq_percent", "loans_yoy_percent", "loans_over_assets_percent",
            "ldr_computed_percent", "npl_coverage_percent",
            "provision_over_loans_percent", "loan_provision_vnd",
            "npl_percent", "nim_percent",
        ]].rename(columns={
            "npl_percent": "npl_vci", "nim_percent": "nim_vci",
        }),
        on=["ticker", "period"], how="left",
    )

    note = _read(NOTE)[[
        "period", "ticker", "npl_percent", "loans_g2_percent", "casa_percent",
        "loans_short_share_percent", "loans_medium_share_percent",
        "loans_long_share_percent", "vnd_deposit_share_percent",
        "deposit_cost_implied_ttm_percent", "npl_vnd",
    ]].rename(columns={"npl_percent": "npl_note"})
    panel = panel.merge(note, on=["ticker", "period"], how="left")
    # Bao phu tinh lai tu du phong (bang can doi) / no nhom 3-5 (thuyet minh). Do
    # 15/09/2026: khop VCI den 0,5 diem o 97% o co ca hai (lech trung vi 0,0).
    # Dung lap o VCI de trong - gom 2021-Q4/2022-Q1 da go loi quy chep lai.
    panel["cov_note"] = (100 * panel["loan_provision_vnd"].abs()
                         / panel["npl_vnd"].where(panel["npl_vnd"] > 0))

    mas = _read(MAS)[[
        "period", "ticker", "nim_ttm_percent", "cof_ttm_percent",
        "earning_asset_yield_ttm_percent", "roe_ttm_percent", "roa_ttm_percent",
        "cir_ttm_approx_percent", "pe", "pb", "eps_vnd", "bvps_vnd", "beta",
        "dividend_yield",
    ]].rename(columns={
        "nim_ttm_percent": "nim_mas", "cof_ttm_percent": "cof_mas",
        "earning_asset_yield_ttm_percent": "yield_mas",
    })
    panel = panel.merge(mas, on=["ticker", "period"], how="left")

    # Ty so tinh tren mau bang 0 khong phai la so sai mot chut - no vo nghia.
    # Nguon MAS de EPS = 0 o 3 quy cua NVB va van tra ve P/E, cho ra 94.451 /
    # 218.988 / 1.277.917. Giu lai thi mot o nuot tron bien do min-max cua ca
    # 22 ngan hang trong moi phep chuan hoa. Doi thanh NaN ngay tai tang doc.
    for ratio_col, base_col in (("pe", "eps_vnd"), ("pb", "bvps_vnd")):
        degenerate = panel[base_col] == 0
        if degenerate.any():
            panel.loc[degenerate, ratio_col] = np.nan
            _log(f"build_panel: {int(degenerate.sum())} o {ratio_col} tinh tren "
                 f"{base_col}=0 -> NaN")

    # Nguon MAS ghi 0 thay vi de trong khi ngan hang CHUA NIEM YET. Da doi chieu
    # voi phien giao dich dau tien trong data/price: toan bo 68 o pe=0 va 68 o
    # pb=0 deu nam trong giai doan truoc ngay len san, khong o nao sau do - trong
    # khi bvps va eps cua chinh nhung o do van binh thuong (11.000-32.000 dong).
    # P/B = 0 doi hoi thi gia = 0, dieu khong xay ra; day la o THIEU chu khong
    # phai dinh gia bang 0. De nguyen thi min-max se cham ngan hang chua niem yet
    # la re nhat, tuc la TOT nhat, o ca hai tieu chi dinh gia.
    # beta = 0 cung vay: 68 o truoc niem yet cong 26 o ngay sau khi len san, khi
    # chuoi gia con qua ngan de uoc luong - khong o nao la uoc luong that.
    # dividend_yield CO Y KHONG nam trong danh sach nay: 508 trong 576 o bang 0
    # nam sau ngay niem yet va la su that - ngan hang khong tra co tuc tien mat.
    for col in ("pe", "pb", "beta"):
        silent_zero = panel[col] == 0
        if silent_zero.any():
            panel.loc[silent_zero, col] = np.nan
            _log(f"build_panel: {int(silent_zero.sum())} o {col}=0 (chua niem yet "
                 f"hoac chua uoc luong duoc) -> NaN")

    cof = _read(COF)[["period", "ticker", "cof_ttm_percent"]].rename(
        columns={"cof_ttm_percent": "cof_vci"})
    panel = panel.merge(cof, on=["ticker", "period"], how="left")

    yld = _read(YIELD)[["period", "ticker", "earning_asset_yield_ttm_percent"]].rename(
        columns={"earning_asset_yield_ttm_percent": "yield_derived"})
    panel = panel.merge(yld, on=["ticker", "period"], how="left")

    # CAR nua nam -> gan cho quy cuoi cua nua nam do (H1 -> Q2, H2 -> Q4).
    car = _read(CAR)[["period", "ticker", "car_percent"]].dropna(subset=["car_percent"])
    car["period"] = car["period"].str[:4] + "-Q" + car["period"].str[-1].map(
        {"1": "2", "2": "4"})
    panel = panel.merge(car, on=["ticker", "period"], how="left")

    # --- xep thu tu uu tien ---
    panel["npl_percent"], panel["npl_src"] = _coalesce(
        panel, "npl_note", "npl_vci", "note", "vci")
    panel["npl_coverage_percent"], panel["npl_coverage_src"] = _coalesce(
        panel, "npl_coverage_percent", "cov_note", "vci", "note")
    panel["cof_ttm_percent"], panel["cof_src"] = _coalesce(
        panel, "cof_vci", "cof_mas", "vci", "mas")
    panel["nim_ttm_percent"], panel["nim_src"] = _coalesce(
        panel, "nim_vci", "nim_mas", "vci", "mas")
    panel["earning_asset_yield_ttm_percent"], panel["yield_src"] = _coalesce(
        panel, "yield_mas", "yield_derived", "mas", "derived")
    panel["casa_src"] = np.where(panel["casa_percent"].notna(), "note", None)
    panel["car_src"] = np.where(panel["car_percent"].notna(), "halfyear", None)

    panel["period_end"] = [f"{p[:4]}-{QUARTER_END[p[-1]]}" for p in panel["period"]]
    panel["built_at_utc"] = datetime.now(timezone.utc).isoformat()

    drop = ["npl_note", "npl_vci", "cof_vci", "cof_mas", "nim_vci", "nim_mas",
            "yield_mas", "yield_derived", "npl_vnd", "cov_note"]
    panel = panel.drop(columns=drop)

    lead = ["period", "period_end", "ticker"]
    panel = panel[lead + [c for c in panel.columns if c not in lead]]
    panel = panel.sort_values(["period", "ticker"]).reset_index(drop=True)

    num = panel.select_dtypes("number").columns
    panel[num] = panel[num].round(4)

    if write:
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        panel.to_csv(OUT_PATH, index=False, encoding="utf-8-sig",
                     lineterminator="\r\n")
        _log(
            f"build_panel: {len(panel)} dong, {panel['ticker'].nunique()} NH x "
            f"{panel['period'].nunique()} quy, du {len(CORE_FEATURES)} dac trung "
            f"o {int(panel[CORE_FEATURES].notna().all(axis=1).sum())} o -> {OUT_PATH}"
        )

    return {
        "rows": len(panel),
        "banks": int(panel["ticker"].nunique()),
        "quarters": int(panel["period"].nunique()),
        "coverage_percent": {
            col: round(100 * panel[col].notna().mean(), 1)
            for col in CORE_FEATURES + ["car_percent", "roe_ttm_percent",
                                        "loans_short_share_percent"]
        },
        "source_mix": {
            col: panel[col].value_counts(dropna=True).to_dict()
            for col in ("npl_src", "npl_coverage_src", "cof_src", "nim_src", "yield_src")
        },
        "complete_rows_all_core": int(
            panel[CORE_FEATURES].notna().all(axis=1).sum()),
        "path": OUT_PATH,
    }


def _runs(panel, features):
    """Do dai chuoi quy LIEN TUC day du `features`, theo tung ngan hang."""
    rows = []
    for ticker, group in panel.groupby("ticker"):
        group = group.set_index("period").reindex(QUARTERS)
        ok = group[features].notna().all(axis=1).tolist()
        best = current = 0
        best_end = current_start = best_start = 0
        for i, flag in enumerate(ok):
            if flag:
                if current == 0:
                    current_start = i
                current += 1
                if current > best:
                    best, best_start, best_end = current, current_start, i
            else:
                current = 0
        rows.append({
            "ticker": ticker,
            "n_ok": int(sum(ok)),
            "longest_run": best,
            "run_from": QUARTERS[best_start] if best else None,
            "run_to": QUARTERS[best_end] if best else None,
        })
    return pd.DataFrame(rows).sort_values("longest_run", ascending=False)


def validate():
    panel = _read(OUT_PATH)
    runs = _runs(panel, CORE_FEATURES)
    res = {
        "runs": {
            "median_longest_run": int(runs["longest_run"].median()),
            "max_longest_run": int(runs["longest_run"].max()),
            "min_longest_run": int(runs["longest_run"].min()),
            "banks_with_run_ge_20": int((runs["longest_run"] >= 20).sum()),
            "banks_with_run_ge_30": int((runs["longest_run"] >= 30).sum()),
            "total_bank_quarters_in_runs_ge_20": int(
                runs.loc[runs["longest_run"] >= 20, "longest_run"].sum()),
            "per_bank": runs.to_dict("records"),
        }
    }

    q212 = panel[panel["period"] == "2021-Q2"]
    res["2021Q2"] = {
        col: int(q212[col].notna().sum()) for col in CORE_FEATURES
    }

    # Hai nguon NPL phai noi cung mot chuyen o nhung o ca hai deu co.
    credit = _read(CREDIT)[["ticker", "period", "npl_percent"]].rename(
        columns={"npl_percent": "npl_vci"}).dropna()
    merged = panel[["ticker", "period", "npl_percent", "npl_src"]].merge(
        credit, on=["ticker", "period"])
    both = merged[merged["npl_src"] == "note"].dropna()
    gap = (both["npl_percent"] - both["npl_vci"]).abs()
    res["npl_note_vs_vci"] = {
        "n": len(both),
        "median_abs_gap_pp": round(float(gap.median()), 5),
        "share_within_0p05": round(float((gap < 0.05).mean()), 4),
    }
    return res


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--validate" in sys.argv:
        print(json.dumps(validate(), indent=2, ensure_ascii=False, default=str))
        sys.exit(0)

    print(json.dumps(build(), indent=2, ensure_ascii=False, default=str))

    if "--no-check" in sys.argv:
        sys.exit(0)

    # Cong chat luong. Import muon de build_panel van chay duoc neu module kiem
    # tra bi thieu - mat cong kiem thi te hon mat panel.
    try:
        from crawlers import validate as quality
    except ImportError as exc:
        print(f"\n[canh bao] khong nap duoc crawlers.validate ({exc}) - "
              f"panel da ghi nhung CHUA qua cong chat luong")
        sys.exit(0)

    findings = quality.run(scope="panel")
    errors = [f for f in findings if f.level == quality.ERROR]
    warns = [f for f in findings if f.level == quality.WARN]

    print(f"\ncong chat luong: {len(errors)} ERROR, {len(warns)} WARN "
          f"(chi tiet: python -m crawlers.validate)")
    for finding in errors:
        print(f"  ERROR [{finding.check}] {finding.message}")
    sys.exit(1 if errors else 0)
