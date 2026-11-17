from __future__ import annotations

import glob
import os
from datetime import date

import numpy as np
import pandas as pd

from crawlers import deposit_tiers
from crawlers.build_features import CPI, DEPOSIT, POLICY_RATE, PRICE_DIR, PRICE_IDX, VNINDEX, _log, _read, _to_period
from crawlers.select_features import CATALOG, DROP, KEEP, MIN_BANKS, MIN_COVERAGE, MODE_MAX, RHO_MAX, SELECTED

DAILY = "data/model/features_selected_daily.csv"
MONTHLY = "data/model/features_selected_monthly.csv"
SPEC = "data/model/feature_spec_hf.csv"
KEEP_SHORT = "Giữ (nguồn ngắn)"
START = "2018-01-01"  # cung moc voi panel quy (2018-Q1)
RECENT_DAYS = 365  # "gan nhat" = 12 thang, nhu 4 quy cua file quy
MIN_SESSIONS_M = 10  # thang < 10 phien -> NaN (file quy: quy < 20 phien)
VOL_WINDOW = 20  # phien

R, T, V = "R Lãi suất niêm yết", "T Thị trường", "V Vĩ mô"
BANK, COMMON = "theo NH", "chung mọi NH"
POLICY = {"tai_cap_von": ("refinancing_rate_pct", "tái cấp vốn"), "tai_chiet_khau": ("rediscount_rate_pct", "tái chiết khấu"),
          "cho_vay_qua_dem": ("overnight_sbv_rate_pct", "cho vay qua đêm")}
DEP_SRC, PX_SRC, LEND_SRC = "deposit_24hmoney_daily (qua deposit_tiers)", "data/price", "lending_rates_official → bank_lending_rates_monthly"
DEP_FORMULA = "Lãi tiết kiệm 12 tháng {}, bậc số tiền thấp nhất"

# (bien, nhom, loai, don vi, cong thuc, nguon, cach quy ve tan suat, bien tuong ung o file quy). Thu tu = uu tien khi trung.
SPEC_COLS = ["feature", "group", "kind", "unit", "formula", "source", "processing", "quarterly_feature"]
DAILY_CANDIDATES = [
    ("dep12_online_pct", R, BANK, "%", DEP_FORMULA.format("online"), DEP_SRC, "ngày quan sát; ngày không crawl để trống", "dep12_online_pct"),
    ("dep12_counter_pct", R, BANK, "%", DEP_FORMULA.format("tại quầy"), DEP_SRC, "ngày quan sát; ngày không crawl để trống", "dep12_counter_pct"),
    ("refinancing_rate_pct", V, COMMON, "%", "Lãi suất tái cấp vốn NHNN có hiệu lực trong ngày", "policy_rate", "sự kiện → giá trị đang hiệu lực", "refinancing_rate_pct"),
    ("vnindex_ret_d_pct", V, COMMON, "%", "Lợi suất VN-Index so phiên trước", "VNINDEX", "phiên", "vnindex_ret_q_pct"),
    ("stock_ret_d_pct", T, BANK, "%", "Lợi suất cổ phiếu so phiên giao dịch trước của mã", PX_SRC, "phiên", "stock_ret_q_pct"),
    ("excess_ret_d_pct", T, BANK, "điểm %", "Lợi suất cổ phiếu − lợi suất VN-Index cùng phiên", PX_SRC + " + VNINDEX", "phiên", "excess_ret_q_pct"),
    ("stock_vol_20d_pct", T, BANK, "%", "Độ lệch chuẩn lợi suất log 20 phiên gần nhất × √252", PX_SRC, "cửa sổ 20 phiên; chưa đủ 20 phiên → NaN", "stock_vol_q_pct"),
    ("log_value_vnd", T, BANK, "ln", "ln(giá trị giao dịch trong phiên, đồng)", PX_SRC, "phiên; khối lượng 0 → NaN", "log_adtv"),
    ("vnindex_vol_20d_pct", V, COMMON, "%", "Độ lệch chuẩn lợi suất log VN-Index 20 phiên × √252", "VNINDEX", "cửa sổ 20 phiên", "vnindex_vol_q_pct"),
    ("rediscount_rate_pct", V, COMMON, "%", "Lãi suất tái chiết khấu NHNN có hiệu lực trong ngày", "policy_rate", "sự kiện → giá trị đang hiệu lực", "rediscount_rate_pct"),
    ("overnight_sbv_rate_pct", V, COMMON, "%", "Lãi suất cho vay qua đêm NHNN có hiệu lực trong ngày", "policy_rate", "sự kiện → giá trị đang hiệu lực", "overnight_sbv_rate_pct"),
]
THIN_M = f"< {MIN_SESSIONS_M} phiên trong tháng → NaN"
# Loai truoc moi quy tac vi ly do cau truc (nhu ABSOLUTE cua select_features)
STRUCTURAL = {
    feat: "Giá VCI điều chỉnh theo cổ tức / thưởng cổ phiếu nhưng khối lượng thì không (HDB trước 02/10/2026: giá ÷ 1,30, "
          "khối lượng giữ nguyên) → giá trị giao dịch quá khứ bị hạ theo hệ số điều chỉnh, mỗi lần chia cổ phiếu tạo một bậc giả"
    for feat in ("log_value_vnd", "log_adtv")
}
MONTHLY_CANDIDATES = [
    ("dep12_online_pct", R, BANK, "%", DEP_FORMULA.format("online"), DEP_SRC, "ngày → trung bình các ngày quan sát trong tháng", "dep12_online_pct"),
    ("dep12_counter_pct", R, BANK, "%", DEP_FORMULA.format("tại quầy"), DEP_SRC, "ngày → trung bình các ngày quan sát trong tháng", "dep12_counter_pct"),
    ("lending_avg_pct", R, BANK, "%", "Lãi cho vay bình quân: số NH tự công bố (khách cá nhân, rồi chung), thiếu thì VietnamNet",
     LEND_SRC, "tháng (như trang Vay của web)", "lending_avg_pct"),
    ("refinancing_rate_pct", V, COMMON, "%", "Lãi suất tái cấp vốn NHNN có hiệu lực cuối tháng", "policy_rate", "sự kiện → giá trị cuối tháng", "refinancing_rate_pct"),
    ("cpi_yoy_pct", V, COMMON, "%", "CPI so cùng kỳ", "cpi (NSO)", "tháng", "cpi_yoy_q_pct"),
    ("vnindex_ret_m_pct", V, COMMON, "%", "Lợi suất VN-Index trong tháng", "VNINDEX", "phiên → tháng", "vnindex_ret_q_pct"),
    ("stock_ret_m_pct", T, BANK, "%", "Lợi suất cổ phiếu trong tháng", PX_SRC, f"phiên → tháng; {THIN_M}", "stock_ret_q_pct"),
    ("excess_ret_m_pct", T, BANK, "điểm %", "Lợi suất cổ phiếu − lợi suất VN-Index trong tháng", PX_SRC + " + VNINDEX", f"phiên → tháng; {THIN_M}", "excess_ret_q_pct"),
    ("stock_vol_m_pct", T, BANK, "%", "Độ lệch chuẩn lợi suất log ngày trong tháng × √252", PX_SRC, f"phiên → tháng; {THIN_M}", "stock_vol_q_pct"),
    ("log_adtv", T, BANK, "ln", "ln(giá trị giao dịch bình quân phiên trong tháng, đồng)", PX_SRC, f"phiên → tháng; {THIN_M}", "log_adtv"),
    ("vnindex_vol_m_pct", V, COMMON, "%", "Biến động VN-Index trong tháng (năm hóa)", "VNINDEX", "phiên → tháng", "vnindex_vol_q_pct"),
    ("usd_index_yoy_pct", V, COMMON, "%", "Chỉ số giá USD so cùng kỳ", "price_indices (NSO)", "tháng", "usd_index_yoy_q_pct"),
    ("gold_index_yoy_pct", V, COMMON, "%", "Chỉ số giá vàng so cùng kỳ", "price_indices (NSO)", "tháng", "gold_index_yoy_q_pct"),
    ("core_cpi_yoy_pct", V, COMMON, "%", "Lạm phát cơ bản so cùng kỳ", "price_indices (NSO)", "tháng", "core_cpi_yoy_q_pct"),
    ("rediscount_rate_pct", V, COMMON, "%", "Lãi suất tái chiết khấu NHNN có hiệu lực cuối tháng", "policy_rate", "sự kiện → giá trị cuối tháng", "rediscount_rate_pct"),
    ("overnight_sbv_rate_pct", V, COMMON, "%", "Lãi suất cho vay qua đêm NHNN có hiệu lực cuối tháng", "policy_rate", "sự kiện → giá trị cuối tháng", "overnight_sbv_rate_pct"),
]


# --------------------------------------------------------------------------- nguon
def _sessions() -> pd.DataFrame:
    files = [(os.path.basename(f)[:3], f) for f in sorted(glob.glob(os.path.join(PRICE_DIR, "*.csv")))] + [("_IDX", VNINDEX)]
    frames = []
    for t, f in files:
        d = _read(f)
        frames.append(pd.DataFrame({"date": pd.to_datetime(d.time).dt.normalize(), "ticker": t, "close": d.close, "volume": d.volume}))
    px = pd.concat(frames).drop_duplicates(["ticker", "date"], keep="last").sort_values(["ticker", "date"]).reset_index(drop=True)
    by = px.groupby("ticker")
    px["ret"] = (px.close / by.close.shift(1) - 1) * 100
    px["lr"] = np.log(px.close / by.close.shift(1))
    px["value"] = px.close * 1000 * px.volume  # gia luu theo nghin dong
    return px


def _deposit() -> pd.DataFrame:
    d = deposit_tiers.read(DEPOSIT)
    d = d[d.ticker.notna() & (d.term_months == 12)]
    d["date"] = pd.to_datetime(d.date)
    w = d.groupby(["date", "ticker", "channel"]).rate_percent.mean().unstack("channel").reindex(columns=["online", "quay"])
    return w.rename(columns={"online": "dep12_online_pct", "quay": "dep12_counter_pct"}).reset_index()


def _policy_asof(dates: pd.Series) -> pd.DataFrame:
    pr = _read(POLICY_RATE)
    pr["date"] = pd.to_datetime(pr.date_effective)
    out = pd.DataFrame({"date": np.sort(pd.to_datetime(dates).unique())})
    for rt, (nm, _) in POLICY.items():
        s = pr.loc[pr.rate_type == rt, ["date", "rate_percent"]].sort_values("date").rename(columns={"rate_percent": nm})
        out = pd.merge_asof(out, s, on="date")
    return out


# --------------------------------------------------------------------------- ngay
def build_daily(px: pd.DataFrame, dep: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    start = pd.Timestamp(START)
    sessions = set(px.loc[px.ticker == "_IDX", "date"])
    dates = sorted(d for d in sessions | set(dep.date) if d >= start)
    g = pd.MultiIndex.from_product([dates, tickers], names=["date", "ticker"]).to_frame(index=False)
    g["period"] = _to_period(g.date)
    g["trading_day"] = g.date.isin(sessions).astype(int)

    px = px.copy()
    px["vol20"] = px.groupby("ticker").lr.transform(lambda s: s.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std()) * np.sqrt(252) * 100
    idx = px[px.ticker == "_IDX"].rename(columns={"ret": "vnindex_ret_d_pct", "vol20": "vnindex_vol_20d_pct"})
    st = px[px.ticker != "_IDX"].rename(columns={"ret": "stock_ret_d_pct", "vol20": "stock_vol_20d_pct"})
    st["log_value_vnd"] = np.log(st.value.where(st.value > 0))
    g = g.merge(dep, on=["date", "ticker"], how="left")
    g = g.merge(st[["date", "ticker", "stock_ret_d_pct", "stock_vol_20d_pct", "log_value_vnd"]], on=["date", "ticker"], how="left")
    g = g.merge(idx[["date", "vnindex_ret_d_pct", "vnindex_vol_20d_pct"]], on="date", how="left")
    g["excess_ret_d_pct"] = g.stock_ret_d_pct - g.vnindex_ret_d_pct
    g = g.merge(_policy_asof(g.date), on="date", how="left")
    g["date"] = g.date.dt.strftime("%Y-%m-%d")
    return g


# --------------------------------------------------------------------------- thang
def _market_monthly(px: pd.DataFrame) -> pd.DataFrame:
    px = px.assign(mi=px.date.dt.year * 12 + px.date.dt.month - 1)
    m = px.groupby(["ticker", "mi"]).agg(close=("close", "last"), n=("close", "size"), vol=("lr", "std"),
                                          adtv=("value", "mean")).reset_index()
    by = m.groupby("ticker")
    m["ret"] = ((m.close / by.close.shift(1) - 1) * 100).where(by.mi.diff() == 1)
    m["vol"] = m.vol * np.sqrt(252) * 100
    thin = (m.n < MIN_SESSIONS_M) & (m.ticker != "_IDX")
    m.loc[thin, ["ret", "vol", "adtv"]] = np.nan
    m["log_adtv"] = np.log(m.adtv.where(m.adtv > 0))
    m["month"] = (m.mi // 12).astype(str) + "-" + (m.mi % 12 + 1).astype(str).str.zfill(2)
    return m


def build_monthly(px: pd.DataFrame, dep: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    from serving.export import export_lending_rates  # chuoi lai cho vay cua web

    last = (pd.Period(date.today(), "M") - 1).strftime("%Y-%m")  # thang hien tai chua het -> bo
    months = pd.period_range(START, last, freq="M").strftime("%Y-%m")
    g = pd.MultiIndex.from_product([months, tickers], names=["month", "ticker"]).to_frame(index=False)
    g["period"] = _to_period(g.month + "-01")

    dm = dep.assign(month=dep.date.dt.strftime("%Y-%m")).groupby(["month", "ticker"])[["dep12_online_pct", "dep12_counter_pct"]].mean()
    g = g.merge(dm.reset_index(), on=["month", "ticker"], how="left")
    lend = export_lending_rates(narrow=False)[["month", "ticker", "lending_avg_percent"]].rename(columns={"lending_avg_percent": "lending_avg_pct"})
    g = g.merge(lend, on=["month", "ticker"], how="left")

    m = _market_monthly(px)
    idx = m[m.ticker == "_IDX"].rename(columns={"ret": "vnindex_ret_m_pct", "vol": "vnindex_vol_m_pct"})
    st = m[m.ticker != "_IDX"].rename(columns={"ret": "stock_ret_m_pct", "vol": "stock_vol_m_pct"})
    g = g.merge(st[["month", "ticker", "stock_ret_m_pct", "stock_vol_m_pct", "log_adtv"]], on=["month", "ticker"], how="left")
    g = g.merge(idx[["month", "vnindex_ret_m_pct", "vnindex_vol_m_pct"]], on="month", how="left")
    g["excess_ret_m_pct"] = g.stock_ret_m_pct - g.vnindex_ret_m_pct

    ends = pd.Series(pd.PeriodIndex(months, freq="M").to_timestamp(how="end").normalize())
    pol = _policy_asof(ends)
    pol["month"] = pol.date.dt.strftime("%Y-%m")
    g = g.merge(pol.drop(columns="date"), on="month", how="left")
    cpi = _read(CPI)[["month", "cpi_yoy_percent"]].rename(columns={"cpi_yoy_percent": "cpi_yoy_pct"})
    pi = _read(PRICE_IDX)[["month", "usd_index_yoy_percent", "gold_index_yoy_percent", "core_inflation_yoy_percent"]].rename(columns={
        "usd_index_yoy_percent": "usd_index_yoy_pct", "gold_index_yoy_percent": "gold_index_yoy_pct",
        "core_inflation_yoy_percent": "core_cpi_yoy_pct"})
    return g.merge(cpi, on="month", how="left").merge(pi, on="month", how="left")


# --------------------------------------------------------------------------- chon loc
def _spearman(f: pd.DataFrame, time: str, a: str, b: str, both_common: bool) -> float:
    d = f.groupby(time)[[a, b]].first().dropna() if both_common else f[[a, b]].dropna()
    if len(d) < (20 if both_common else 200) or d[a].nunique() < 3 or d[b].nunique() < 3:
        return np.nan
    return float(d[a].rank().corr(d[b].rank()))


def _select(f: pd.DataFrame, cands: list[tuple], time: str, recent_from: str, freq: str) -> pd.DataFrame:
    spec = pd.DataFrame(cands, columns=SPEC_COLS)
    recent = f[f[time] >= recent_from]
    rows, kept = [], []
    for r in spec.itertuples():
        s = f[r.feature]
        nn = s.dropna()
        have = f.loc[s.notna(), time]
        st = dict(feature=r.feature, coverage_pct=round(float(s.notna().mean() * 100), 1),
                  n_banks=int(f.loc[s.notna(), "ticker"].nunique()),
                  banks_last12m=int(recent.loc[recent[r.feature].notna(), "ticker"].nunique()),
                  first=have.min() if len(have) else "", last=have.max() if len(have) else "",
                  mode_share_pct=round(float(nn.value_counts(normalize=True).iloc[0] * 100), 1) if len(nn) else 100.0,
                  redundant_with="", rho=np.nan)
        if r.feature in STRUCTURAL:
            st.update(decision=DROP, reason=STRUCTURAL[r.feature])
        elif st["mode_share_pct"] >= MODE_MAX:
            st.update(decision=DROP, reason=f"Gần như hằng số: một giá trị chiếm {st['mode_share_pct']:.0f}% số ô")
        elif st["coverage_pct"] < MIN_COVERAGE or st["n_banks"] < MIN_BANKS:
            if r.kind == BANK and st["banks_last12m"] >= MIN_BANKS:
                st.update(decision=KEEP_SHORT, reason=f"Phủ {st['coverage_pct']:.1f}% (từ {st['first']}) — nguồn ngắn, "
                                                      f"nhưng {st['banks_last12m']}/22 NH có số trong 12 tháng gần nhất")
            else:
                st.update(decision=DROP, reason=f"Phủ thấp: {st['coverage_pct']:.1f}% ô (ngưỡng {MIN_COVERAGE:.0f}%), "
                                                f"{st['n_banks']}/22 NH, 12 tháng gần nhất {st['banks_last12m']}/22 NH")
        if "decision" not in st:
            for k in kept:
                rho = _spearman(f, time, r.feature, k, r.kind == COMMON and spec.set_index("feature").kind[k] == COMMON)
                if not np.isnan(rho) and abs(rho) >= RHO_MAX:
                    st.update(decision=DROP, reason=f"Trùng thông tin với {k} (Spearman {rho:+.2f})", redundant_with=k, rho=round(rho, 3))
                    break
            else:
                st.update(decision=KEEP, reason="Qua 3 quy tắc tầng 1 (hằng số, độ phủ, trùng thông tin)")
                kept.append(r.feature)
        rows.append(st)
    out = spec.merge(pd.DataFrame(rows), on="feature")
    cat = pd.read_csv(CATALOG, encoding="utf-8-sig").set_index("feature")
    out["quarterly_decision"] = out.quarterly_feature.map(cat.decision).fillna("")
    out["quarterly_use"] = out.quarterly_feature.map(cat.use).fillna("")
    out.insert(0, "freq", freq)
    return out


def build(write: bool = True) -> dict:
    tickers = sorted(pd.read_csv(SELECTED, encoding="utf-8-sig", usecols=["ticker"]).ticker.unique())
    px, dep = _sessions(), _deposit()
    outs, specs = {}, []
    for freq, path, frame, cands, keys, time in (
            ("ngày", DAILY, build_daily(px, dep, tickers), DAILY_CANDIDATES, ["date", "period", "ticker", "trading_day"], "date"),
            ("tháng", MONTHLY, build_monthly(px, dep, tickers), MONTHLY_CANDIDATES, ["month", "period", "ticker"], "month")):
        last = pd.Timestamp(frame[time].max() if time == "date" else frame[time].max() + "-01")
        recent_from = (last - pd.Timedelta(days=RECENT_DAYS - 1)).strftime("%Y-%m-%d" if time == "date" else "%Y-%m")
        spec = _select(frame, cands, time, recent_from, freq)
        keep = spec.loc[spec.decision != DROP, "feature"].tolist()
        out = frame.sort_values([time, "ticker"])[keys + keep].reset_index(drop=True)
        if out.duplicated([time, "ticker"]).any():
            raise ValueError(f"{path}: trung khoa ({time}, ticker)")
        num = out[keep].select_dtypes("number").columns
        out[num] = out[num].replace([np.inf, -np.inf], np.nan).round(6)
        if write:
            out.to_csv(path, index=False, encoding="utf-8-sig")
        outs[freq] = dict(path=path, rows=len(out), span=f"{out[time].min()}..{out[time].max()}", features=keep,
                          dropped=spec.loc[spec.decision == DROP, ["feature", "reason"]].values.tolist())
        specs.append(spec)
    spec = pd.concat(specs, ignore_index=True)
    cols = ["freq", "feature", "group", "kind", "decision", "reason", "redundant_with", "rho", "quarterly_feature",
            "quarterly_decision", "quarterly_use", "coverage_pct", "n_banks", "banks_last12m", "first", "last",
            "mode_share_pct", "unit", "formula", "source", "processing"]
    if write:
        spec[cols].to_csv(SPEC, index=False, encoding="utf-8-sig")
        _log("select_features_hf: " + "; ".join(f"{k} {v['rows']} dong x {len(v['features'])} bien -> {v['path']}" for k, v in outs.items()))
    return {**outs, "spec": SPEC}


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(build(), indent=2, ensure_ascii=False, default=str))
