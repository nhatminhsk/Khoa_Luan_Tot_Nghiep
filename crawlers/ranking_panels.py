from __future__ import annotations

import pandas as pd

from crawlers import deposit_tiers
from crawlers.build_features import _log
from crawlers.select_features import CATALOG, DROP, FEATURES, REFRESHED, SPEC

DAILY = "data/model/ranking_daily.csv"
MONTHLY = "data/model/ranking_monthly.csv"
QUARTERLY = "data/model/ranking_quarterly.csv"
RANK_SPEC = "data/model/ranking_spec.csv"

RANK_DEP, RANK_LOAN = "Xếp hạng gửi", "Xếp hạng vay"
CHANNELS = {"online": "online", "quay": "counter"}  # kenh nguon -> hau to cot (giong features_ranking_latest)
DEP_RATES = {"dep12_online_pct", "dep12_counter_pct"}  # catalog chi co 12 thang; file ngay co moi ky han
# Cua so lay "so moi nhat" cua features_ranking_latest (select_features.FRESH_DAYS / LENDING_MAX_MONTHS /
# RECENT_QUARTERS) -- chi de dem banks_window trong spec
WINDOW = {"ngày": "7 ngày", "tháng": "12 tháng", "quý": "4 quý"}

DEP_BASIS = "CAMELS: càng cao càng an toàn"
DEP_BASIS_NEG = "CAMELS: càng cao càng rủi ro"
LOAN_ASSUMED = "giả định (như montecarlo_ranking)"
# tieu chi -> (chieu +1 cang cao cang tot, co so). Thu tu = thu tu cot o file quy: gui theo tru C A M E L S G, roi vay.
DIRECTION = {
    "dep12_online_pct": (+1, "người gửi: lãi cao hơn tốt hơn"),
    "dep12_counter_pct": (+1, "người gửi: lãi cao hơn tốt hơn"),
    "car_asof_percent": (+1, DEP_BASIS), "equity_to_assets_pct": (+1, DEP_BASIS),
    "npl_percent": (-1, DEP_BASIS_NEG), "loans_g2_percent": (-1, DEP_BASIS_NEG),
    "credit_cost_ttm_pct": (-1, DEP_BASIS_NEG), "accrued_interest_to_assets_pct": (-1, DEP_BASIS_NEG),
    "cir_ttm_pct": (-1, "CAMELS: chi phí / thu nhập cao là quản trị kém"),
    "state_own_percent": (+1, "kênh nhà nước đứng sau mà người gửi dựa vào"),
    "roa_ttm_percent": (+1, DEP_BASIS),
    "ldr_computed_percent": (-1, "CAMELS: cho vay / huy động cao là thanh khoản căng; vay: " + LOAN_ASSUMED),
    "liquid_assets_pct": (+1, DEP_BASIS), "casa_percent": (+1, "CAMELS: vốn rẻ, ổn định hơn"),
    "corp_bond_to_assets_pct": (-1, DEP_BASIS_NEG),
    "log_total_assets": (+1, "kênh \"quá lớn để đổ\" mà người gửi dựa vào"),
    "lending_avg_pct": (-1, LOAN_ASSUMED), "loan_yield_ttm_pct": (-1, LOAN_ASSUMED),
    "retail_loan_share_pct": (+1, LOAN_ASSUMED),
}
# nhom trong so theo thanh uu tien cua web
LOAN_GROUP = {"lending_avg_pct": "giá", "loan_yield_ttm_pct": "giá", "retail_loan_share_pct": "phù hợp",
              "ldr_computed_percent": "sức cho vay"}


def criteria() -> pd.DataFrame:
    cat = pd.read_csv(CATALOG, encoding="utf-8-sig")
    use = cat.use.fillna("")
    c = cat.loc[(cat.decision != DROP) & use.str.contains("Xếp hạng"), ["feature", "group"]].copy()
    c["deposit"], c["loan"] = use[c.index].str.contains(RANK_DEP), use[c.index].str.contains(RANK_LOAN)
    if missing := set(c.feature) - set(DIRECTION):
        raise ValueError(f"tieu chi xep hang moi trong catalog chua co chieu trong DIRECTION: {sorted(missing)}")
    if extra := set(DIRECTION) - set(c.feature):
        print(f"CANH BAO: {sorted(extra)} khong con vai tro xep hang trong catalog -> khong vao file")
    if loan_missing := set(c.feature[c.loan]) - set(LOAN_GROUP):
        raise ValueError(f"tieu chi vay chua co nhom trong LOAN_GROUP: {sorted(loan_missing)}")
    return c.set_index("feature").loc[[f for f in DIRECTION if f in set(c.feature)]].reset_index()


def _term_key(col: str) -> tuple[int, bool]:
    return int(col[3:].split("_")[0]), not col.endswith("_online_pct")


def build_daily(tickers: list[str]) -> pd.DataFrame:
    d = deposit_tiers.read()
    d = d[d.ticker.isin(tickers) & d.channel.isin(list(CHANNELS))].copy()
    d["col"] = "dep" + d.term_months.astype(int).astype(str) + "_" + d.channel.map(CHANNELS) + "_pct"
    if d.duplicated(["date", "ticker", "col"]).any():
        raise ValueError(f"{deposit_tiers.MASTER}: mot o (ngay, NH, ky han, kenh) co nhieu so")
    w = d.pivot(index=["date", "ticker"], columns="col", values="rate_percent")
    cols = sorted(w.columns, key=_term_key)
    grid = pd.MultiIndex.from_product([sorted(d.date.unique()), tickers], names=["date", "ticker"])
    out = w.reindex(grid)[cols]
    # o da sua so nguon (bac so tien sai, lam tron vuot tran NHNN): ly do chi tiet o python -m crawlers.deposit_tiers
    adj = d[d.tier_override.notna()].groupby(["date", "ticker"]).col.agg(lambda s: ";".join(sorted(s, key=_term_key)))
    out["adjusted_cols"] = adj.reindex(grid)
    return out.reset_index()


def build_monthly(tickers: list[str]) -> pd.DataFrame:
    from serving.export import export_lending_rates  # chuoi lai cho vay cua web

    lend = export_lending_rates(narrow=False)  # xep hang: chua so nhom hep (SHB, SSB) voi so chung
    lend = lend[lend.ticker.isin(tickers)].rename(columns={
        "lending_avg_percent": "lending_avg_pct", "segment": "lending_segment", "basis": "lending_basis",
        "source": "lending_source"})
    months = pd.period_range(lend.month.min(), lend.month.max(), freq="M").strftime("%Y-%m")
    grid = pd.MultiIndex.from_product([months, tickers], names=["month", "ticker"]).to_frame(index=False)
    return grid.merge(lend[["month", "ticker", "lending_avg_pct", "lending_segment", "lending_basis", "lending_source"]],
                      on=["month", "ticker"], how="left")


def build_quarterly(crit: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    cols = [c for c in crit.feature if c not in REFRESHED]
    f = pd.read_csv(FEATURES, encoding="utf-8-sig")
    f = f[f.ticker.isin(tickers)]
    if f.duplicated(["period", "ticker"]).any():
        raise ValueError(f"{FEATURES}: trung khoa (period, ticker)")
    return f.sort_values(["period", "ticker"])[["period", "period_end", "ticker"] + cols].reset_index(drop=True)


def _coverage(frame: pd.DataFrame, time: str, col: str, window_from: str) -> dict:
    s = frame[col]
    have = frame.loc[s.notna(), time]
    last = frame[time].max()
    return dict(coverage_pct=round(float(s.notna().mean() * 100), 1), n_banks=int(frame.loc[s.notna(), "ticker"].nunique()),
                first=have.min() if len(have) else "", last=have.max() if len(have) else "",
                banks_latest=int(frame.loc[(frame[time] == last) & s.notna(), "ticker"].nunique()),
                banks_window=int(frame.loc[(frame[time] >= window_from) & s.notna(), "ticker"].nunique()))


def build_spec(crit: pd.DataFrame, daily: pd.DataFrame, monthly: pd.DataFrame, quarterly: pd.DataFrame) -> pd.DataFrame:
    spec = pd.read_csv(SPEC, encoding="utf-8-sig").set_index("feature")
    crit = crit.set_index("feature")
    last_day = pd.Timestamp(daily.date.max())
    windows = {
        "ngày": (last_day - pd.Timedelta(days=7)).strftime("%Y-%m-%d"),
        "tháng": (pd.Period(monthly.month.max(), "M") - 11).strftime("%Y-%m"),
        "quý": sorted(quarterly.period.unique())[-4],
    }
    rows = []

    def row(col, catalog_feature, freq, path, frame, time, **text):
        c = crit.loc[catalog_feature]
        direction, basis = DIRECTION[catalog_feature]
        rows.append(dict(
            feature=col, freq=freq, file=path, catalog_feature=catalog_feature,
            ranking="; ".join(k for k, on in (("gửi", c.deposit), ("vay", c.loan)) if on),
            deposit_group=("lãi" if catalog_feature in DEP_RATES else "an toàn") if c.deposit else "",
            loan_group=LOAN_GROUP.get(catalog_feature, "") if c.loan else "",
            pillar=c.group, direction=direction, direction_basis=basis,
            **text, window=WINDOW[freq], **_coverage(frame, time, col, windows[freq])))

    for col in [c for c in daily.columns if c.startswith("dep") and c.endswith("_pct")]:
        term, ch = col[3:].split("_")[:2]
        row(col, f"dep12_{ch}_pct", "ngày", DAILY, daily, "date", unit="%",
            formula=f"Lãi tiết kiệm {term} tháng {'online' if ch == 'online' else 'tại quầy'}, bậc số tiền thấp nhất",
            source="deposit_24hmoney_daily (qua deposit_tiers.read)",
            processing="ngày crawl, không forward-fill; ô sai bậc số tiền đã sửa, kỳ hạn 1–5 tháng vượt trần NHNN do làm "
                       "tròn đưa về trần (cột adjusted_cols)")
    row("lending_avg_pct", "lending_avg_pct", "tháng", MONTHLY, monthly, "month", unit="%",
        formula="Lãi cho vay bình quân: số NH tự công bố (khách cá nhân, rồi chung), thiếu thì VietnamNet",
        source="lending_rates_official → bank_lending_rates_monthly (serving.export.export_lending_rates)",
        processing="tháng, như trang Vay của web; nhóm khách hàng / cơ sở / nguồn ở cột lending_segment, lending_basis, "
                   "lending_source; tháng T có số khoảng ngày 20 tháng T+1")
    for col in quarterly.columns[3:]:
        s = spec.loc[col]
        row(col, col, "quý", QUARTERLY, quarterly, "period", unit=s.unit, formula=s.formula, source=s.source,
            processing=s.processing)
    return pd.DataFrame(rows)


def build(write: bool = True) -> dict:
    tickers = sorted(pd.read_csv(FEATURES, encoding="utf-8-sig", usecols=["ticker"]).ticker.unique())
    crit = criteria()
    daily, monthly, quarterly = build_daily(tickers), build_monthly(tickers), build_quarterly(crit, tickers)
    spec = build_spec(crit, daily, monthly, quarterly)
    outs = {}
    for path, frame, time in ((DAILY, daily, "date"), (MONTHLY, monthly, "month"), (QUARTERLY, quarterly, "period")):
        num = frame.select_dtypes("number").columns
        frame[num] = frame[num].round(6)
        if write:
            frame.to_csv(path, index=False, encoding="utf-8-sig")
        n_crit = int((spec.file == path).sum())
        outs[path] = f"{len(frame)} dong ({frame[time].nunique()} {time} x {frame.ticker.nunique()} NH) x {n_crit} tieu chi, " \
                     f"{frame[time].min()}..{frame[time].max()}"
    if write:
        spec.to_csv(RANK_SPEC, index=False, encoding="utf-8-sig")
        _log("ranking_panels: " + "; ".join(f"{k} {v}" for k, v in outs.items()))
    return {**outs, "spec": RANK_SPEC,
            "gui": spec.loc[spec.ranking.str.contains("gửi"), "feature"].tolist(),
            "vay": spec.loc[spec.ranking.str.contains("vay"), "feature"].tolist()}


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(build(), indent=2, ensure_ascii=False, default=str))
