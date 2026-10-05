"""Dung trang "EDA dinh huong mo hinh" tu data/model/eda_ml/*.csv (chay sau `python -m experiments.eda_ml`).

    python reports/eda_ml/make_report.py <file_ra.html>

Moi so tren trang doc tu CSV/facts.json. Loi van o phan "Quyet dinh" la nhan dinh: neu so doi chieu
khong con khop (vi du LightGBM bat dau thang naive), script in CANH BAO de sua loi van.
"""
import html
import json
import os
import sys

import numpy as np
import pandas as pd

os.chdir(r"D:\KLTN")
OUT = sys.argv[1] if len(sys.argv) > 1 else "reports/eda_ml/eda_ml.html"
E = "data/model/eda_ml"
rd = lambda n, **k: pd.read_csv(f"{E}/{n}.csv", encoding="utf-8-sig", **k)  # noqa: E731
F = json.load(open(f"{E}/facts.json", encoding="utf-8"))
WARN = []


def vi(x, d=1, sign=False):
    """So kieu Viet: dau cham hang nghin, dau phay thap phan, dau tru that."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    s = f"{abs(x):,.{d}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return ("−" if x < 0 and float(s.replace(".", "").replace(",", ".")) != 0 else ("+" if sign and x > 0 else "")) + s


def pc(x, d=0, sign=False):
    return vi(100 * x, d, sign) + "%"


esc = html.escape
LABEL = {}
cat = pd.read_csv("data/model/feature_catalog.csv", encoding="utf-8-sig")
MAS_LABEL = {"nim_quarter_percent": "NIM riêng quý", "cof_quarter_percent": "COF riêng quý", "roe_quarter_percent": "ROE riêng quý",
             "cir_quarter_percent": "CIR riêng quý", "earning_asset_yield_quarter_percent": "Lợi suất TSSL riêng quý"}


def code(name):
    return f"<code>{esc(name)}</code>"


# ---------------------------------------------------------------- du lieu
uni = rd("univariate")
tprof = rd("target_profile").set_index("label")
tacf = rd("target_acf")
ceil = rd("signal_ceiling")
ft = rd("feature_target")
pairs = rd("corr_pairs_all")
clw = rd("clusters_within_core")
roll = rd("rolloff").set_index("label")
reg = rd("regime").set_index("feature")
budget = rd("sample_budget").set_index("h")
miss_year = rd("missing_by_year")
clus = rd("cluster_tendency")
rk = rd("ranking_criteria")
rk_pairs = rd("ranking_pairs")
stars = rd("text_stars").set_index("score")
tlen = rd("text_length")
asp = rd("text_aspects")
lang = rd("text_lang").set_index("lang")
dep = pd.DataFrame(F["deposit_corr"])
T = F["text"]
D = F["dims"]
P = F["structure"]["params"]
C = F["clustering"]
M = F["missing"]

cont = uni[uni.n_unique > 2]
skewed = cont[cont["skew"].abs() > 1]
fixed = skewed[skewed.skew_yeojohnson.abs() < 0.5]
with_out = uni[uni.outlier_pct > 0]
nvb_top = int((with_out.top_outlier_bank == "NVB").sum())
npl_u = uni.set_index("feature").loc["npl_percent"]
lvl_nonstat = [lab for lab in ["NIM", "COF", "NPL", "CASA", "LDR", "ROE"] if tprof.loc[lab, "ips_p_level"] > 0.05]
ceil["key"] = ceil.label + ceil.h.astype(str)
cs = ceil.set_index("key")
nl = ft[ft.skill_spline.notna()]
n_nl, n_cont_pairs = int(nl.nonlinear.sum()), len(nl)
sil3 = clus.set_index("k").loc[3]
train1 = int(budget.loc[1, "train_at_2023Q1"])
leaky_h24 = ceil[ceil.h > 1].skill_lgbm_leaky
purged_h24 = ceil[ceil.h > 1].skill_lgbm_all
reg_npl = reg.loc["npl_percent"]
sav = asp.set_index("aspect").loc["tiet_kiem"]
loan = asp.set_index("aspect").loc["vay"]
rp = rk_pairs.iloc[0]

# kiem loi van con khop so khong
ml_wins = ceil[(ceil.skill_lgbm_all > 0.05) & (~ceil.label.isin(["COF"]))]
if len(ml_wins):
    WARN.append(f"LightGBM (purge) thang naive > 5% o chi tieu khac COF: {ml_wins[['label', 'h', 'skill_lgbm_all']].to_dict('records')}")
if sil3.p < 0.1:
    WARN.append(f"silhouette k=3 nay khac khoi Gauss (p = {sil3.p:.2f}) - sua muc 'khong co cum'")
if reg_npl.p < 0.1:
    WARN.append("che do gian no co y nghia voi NPL - sua muc cau truc thoi gian")
if n_nl / n_cont_pairs > 0.1:
    WARN.append("phi tuyen khong con hiem (>10% cap)")

# ---------------------------------------------------------------- SVG helpers
TICKF = 'class="tick"'


def lin(d0, d1, r0, r1):
    return lambda v: r0 + (v - d0) / (d1 - d0) * (r1 - r0)


def svg_open(w, h, label):
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}" preserveAspectRatio="xMinYMin meet" '
            f'style="max-width:{w}px">')


def txt(x, y, s, cls="tick", anchor="start", extra=""):
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}" {extra}>{esc(str(s))}</text>'


def hline(x0, x1, y, cls="grid"):
    return f'<line x1="{x0:.1f}" x2="{x1:.1f}" y1="{y:.1f}" y2="{y:.1f}" class="{cls}"/>'


def vline(x, y0, y1, cls="grid"):
    return f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{y0:.1f}" y2="{y1:.1f}" class="{cls}"/>'


def legend(items):
    return '<div class="legend">' + "".join(f'<span><i class="{c}"></i>{esc(t)}</span>' for c, t in items) + "</div>"


# ---- 1. don bien: lech vs ngoai lai
def chart_univariate():
    W, H, l, r, t, b = 720, 330, 52, 16, 14, 44
    sym = lambda v: np.sign(v) * np.log1p(abs(v))  # noqa: E731
    xs = lin(sym(-3), sym(25), l, W - r)
    ys = lin(0, 20, H - b, t)
    out = [svg_open(W, H, "Độ lệch và tỷ lệ ngoại lai của 87 đặc trưng liên tục")]
    for v in (0, 5, 10, 15, 20):
        out += [hline(l, W - r, ys(v)), txt(l - 8, ys(v) + 4, f"{v}%", anchor="end")]
    for v in (-2, -1, 0, 1, 2, 5, 10, 20):
        out += [vline(xs(sym(v)), t, H - b, "grid"), txt(xs(sym(v)), H - b + 16, vi(v, 0), anchor="middle")]
    out += [vline(xs(sym(1)), t, H - b, "ref"), vline(xs(sym(-1)), t, H - b, "ref"), hline(l, W - r, ys(2), "ref")]
    out += [txt((l + W - r) / 2, H - 6, "Độ lệch (skewness), thang log đối xứng", "axis", "middle"),
            txt(xs(sym(1)) + 4, t + 10, "|lệch| > 1", "note"), txt(W - r - 4, ys(2) - 5, "ngoại lai > 2%", "note", "end")]
    cls = {"chỉ chuẩn hóa z": "s1", "Yeo-Johnson": "s2"}
    for rrow in cont.itertuples():
        c = cls.get(rrow.linear_action, "s3")
        x, y = xs(sym(np.clip(rrow.skew, -3, 25))), ys(min(rrow.outlier_pct, 20))
        tip = f"{rrow.feature}\nđộ lệch {vi(rrow.skew, 2)} → {vi(rrow.skew_yeojohnson, 2)} sau Yeo-Johnson\nngoại lai {vi(rrow.outlier_pct, 1)}%\n→ {rrow.linear_action}"
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" class="dot {c}"><title>{esc(tip)}</title></circle>')
    out.append(txt(14, (t + H - b) / 2, "Ngoại lai (ngoài 3×IQR)", "axis", "middle", f'transform="rotate(-90 14 {(t + H - b) / 2:.0f})"'))
    return legend([("s1", "chỉ chuẩn hóa z"), ("s2", "Yeo-Johnson"), ("s3", "winsorize p1/p99 (± Yeo-Johnson)")]) + \
        '<div class="fig">' + "".join(out) + "</svg></div>"


# ---- 2. ACF muc vs thay doi, small multiples
def chart_acf():
    panels = []
    order = ["NIM", "NIM quý", "COF", "COF quý", "NPL", "CASA", "LDR", "ROE"]
    for lab in order:
        g = tacf[tacf.label == lab].sort_values("lag")
        W, H, l, r, t, b = 220, 150, 34, 10, 22, 26
        xs = lin(1, 4, l + 8, W - r - 8)
        ys = lin(-0.6, 1.0, H - b, t)
        o = [svg_open(W, H, f"Tự tương quan {lab}"), txt(l, 14, lab, "ptitle")]
        for v in (-0.5, 0, 0.5, 1.0):
            o += [hline(l, W - r, ys(v), "base" if v == 0 else "grid"), txt(l - 5, ys(v) + 4, vi(v, 1), anchor="end")]
        for k in range(1, 5):
            o.append(txt(xs(k), H - b + 15, k, anchor="middle"))
        for col, c in (("acf_level", "s1"), ("acf_change", "s2")):
            pts = " ".join(f"{xs(k):.1f},{ys(v):.1f}" for k, v in zip(g.lag, g[col]))
            o.append(f'<polyline points="{pts}" class="ln {c}"/>')
            for k, v in zip(g.lag, g[col]):
                o.append(f'<circle cx="{xs(k):.1f}" cy="{ys(v):.1f}" r="4" class="dot {c}"><title>{esc(lab)} · trễ {k} quý · '
                         f'{"mức" if col == "acf_level" else "thay đổi"}: {vi(v, 2)}</title></circle>')
        panels.append('<div class="panel">' + "".join(o) + "</svg></div>")
    return legend([("s1", "mức (đã trừ trung bình từng NH)"), ("s2", "thay đổi so với quý trước")]) + \
        '<div class="multiples">' + "".join(panels) + "</div><p class='cap'>Trục ngang: độ trễ (quý). Trục dọc: hệ số tự tương quan gộp 22 NH, 2019-Q1 → 2026-Q2.</p>"


# ---- 3. bang nhiet muc giam sai so so voi naive
def heat_cls(v):
    if v is None or np.isnan(v):
        return "h0"
    for lim, c in ((-0.5, "n4"), (-0.2, "n3"), (-0.05, "n2")):
        if v < lim:
            return c
    if v <= 0.05:
        return "h0"
    for lim, c in ((0.15, "p1"), (0.3, "p2")):
        if v <= lim:
            return c
    return "p3"


def table_skill():
    cols = [("skill_drift", "Drift"), ("skill_seasonal", "Mùa vụ"), ("skill_ridge_stable", "Ridge, biến ổn định"),
            ("skill_ridge_all", "Ridge, mọi biến"), ("skill_lgbm_all", "LightGBM, mọi biến")]
    head = "".join(f"<th>{esc(n)}</th>" for _, n in cols)
    rows = []
    for r_ in ceil.itertuples():
        cells = "".join(f'<td class="hc {heat_cls(getattr(r_, c))}">{vi(100 * getattr(r_, c), 0, True)}</td>' for c, _ in cols)
        rows.append(f"<tr><th class='rl'>{r_.label} · {r_.h} quý</th><td class='num'>{r_.n_stable}</td><td class='num'>{pc(r_.share_common)}</td>"
                    f"{cells}<td class='gapc'></td><td class='hc {heat_cls(r_.skill_lgbm_leaky)}'>{vi(100 * r_.skill_lgbm_leaky, 0, True)}</td></tr>")
    scale = "".join(f'<span class="hc {c}">{t}</span>' for c, t in
                    (("n4", "< −50"), ("n3", "−50…−20"), ("n2", "−20…−5"), ("h0", "±5"), ("p1", "+5…+15"), ("p2", "+15…+30"), ("p3", "> +30")))
    return (f'<div class="scale"><span class="lbl">Giảm sai số bình phương so với naive (%)</span>{scale}</div>'
            '<div class="tw"><table class="heat"><thead><tr><th rowspan="2">Chỉ tiêu · tầm</th><th rowspan="2">Biến ổn định</th>'
            '<th rowspan="2">Phần chung ngành</th><th colspan="5">Kiểm chéo khối quý có purge (đúng)</th><th class="gapc" rowspan="2"></th>'
            '<th rowspan="2">LightGBM, chia theo quý không purge (rò rỉ)</th></tr>'
            f"<tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>")


# ---- 4. giua NH vs trong NH
def chart_pairs():
    W, H, l, r, t, b = 560, 380, 50, 16, 14, 44
    xs, ys = lin(-1, 1, l, W - r), lin(-1, 1, H - b, t)
    o = [svg_open(W, H, "Tương quan giữa ngân hàng so với trong ngân hàng, 2.701 cặp đặc trưng")]
    for v in (-1, -0.5, 0, 0.5, 1):
        o += [hline(l, W - r, ys(v), "base" if v == 0 else "grid"), txt(l - 8, ys(v) + 4, vi(v, 1), anchor="end"),
              vline(xs(v), t, H - b, "base" if v == 0 else "grid"), txt(xs(v), H - b + 16, vi(v, 1), anchor="middle")]
    o.append(f'<line x1="{xs(-1):.1f}" y1="{ys(-1):.1f}" x2="{xs(1):.1f}" y2="{ys(1):.1f}" class="ref"/>')
    for p_ in pairs.itertuples():
        # chi gan tooltip cho cap dang chu y (lech nhieu hoac manh trong NH) de trang ve nhanh
        note = abs(p_.gap) >= 0.5 or abs(p_.within) >= 0.5
        tip = f"<title>{esc(p_.a)} × {esc(p_.b)}: giữa NH {vi(p_.between, 2)} · trong NH {vi(p_.within, 2)}</title>" if note else ""
        o.append(f'<circle cx="{xs(p_.between):.1f}" cy="{ys(p_.within):.1f}" r="2.6" class="dot s1 faint">{tip}</circle>')
    for a, b_, lab in (("cof_ttm_percent", "casa_percent", "CASA–COF"), ("nim_ttm_percent", "loans_yoy_percent", "NIM–tăng trưởng dư nợ"),
                       ("roe_ttm_percent", "roa_ttm_percent", "ROE–ROA")):
        m = pairs[((pairs.a == a) & (pairs.b == b_)) | ((pairs.a == b_) & (pairs.b == a))]
        if len(m):
            x, y = xs(m.between.iloc[0]), ys(m.within.iloc[0])
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" class="dot s2"/>')
            o.append(txt(x + (8 if x < W / 2 else -8), y - 8, lab, "note", "start" if x < W / 2 else "end"))
    o += [txt((l + W - r) / 2, H - 6, "Tương quan giữa NH (trung bình từng NH, 22 điểm)", "axis", "middle"),
          txt(14, (t + H - b) / 2, "Tương quan trong NH (đã trừ TB NH và TB quý)", "axis", "middle", f'transform="rotate(-90 14 {(t + H - b) / 2:.0f})"')]
    return '<div class="fig narrow">' + "".join(o) + "</svg></div>"


# ---- bar ngang don gian (mot chuoi)
def hbars(items, fmt, vmax, label, unit_note="", w=560):
    rowh, l, r = 30, 150, 70
    H = rowh * len(items) + 10
    xs = lin(0, vmax, l, w - r)
    o = [svg_open(w, H, label)]
    for i, (name, v, tip) in enumerate(items):
        y = 6 + i * rowh
        wbar = max(0.0, xs(max(v, 0)) - l)
        o.append(txt(l - 10, y + 16, name, "tick lab", "end"))
        o.append(f'<path d="M{l},{y + 5} h{max(wbar - 4, 0):.1f} q4,0 4,4 v8 q0,4 -4,4 h-{max(wbar - 4, 0):.1f} z" class="bar s1"><title>{esc(tip)}</title></path>')
        o.append(txt(l + wbar + 6, y + 16, fmt(v), "val"))
    o.append(vline(l, 2, H - 4, "base"))
    return '<div class="fig narrow">' + "".join(o) + "</svg></div>" + (f"<p class='cap'>{unit_note}</p>" if unit_note else "")


# ---- 7. silhouette vs khoi Gauss
def chart_silhouette():
    W, H, l, r, t, b = 520, 250, 50, 16, 14, 44
    xs, ys = lin(1.5, 6.5, l, W - r), lin(0, 0.35, H - b, t)
    o = [svg_open(W, H, "Silhouette của k-means so với khối Gauss ngẫu nhiên")]
    for v in (0, 0.1, 0.2, 0.3):
        o += [hline(l, W - r, ys(v), "base" if v == 0 else "grid"), txt(l - 8, ys(v) + 4, vi(v, 1), anchor="end")]
    for c in clus.itertuples():
        x = xs(c.k)
        o.append(f'<rect x="{x - 14:.1f}" y="{ys(c.null_p95):.1f}" width="28" height="{ys(c.null_mean) - ys(c.null_p95):.1f}" class="band"><title>Khối Gauss: trung bình {vi(c.null_mean, 3)}, ngưỡng 95% {vi(c.null_p95, 3)}</title></rect>')
        o.append(hline(x - 14, x + 14, ys(c.null_mean), "nullmean"))
        o.append(f'<circle cx="{x:.1f}" cy="{ys(c.silhouette):.1f}" r="5" class="dot s1"><title>k = {c.k}: silhouette {vi(c.silhouette, 3)}, p = {vi(c.p, 2)}</title></circle>')
        o.append(txt(x, H - b + 16, f"k = {c.k}", anchor="middle"))
    o.append(txt(14, (t + H - b) / 2, "Silhouette", "axis", "middle", f'transform="rotate(-90 14 {(t + H - b) / 2:.0f})"'))
    return legend([("s1", "22 NH (ảnh chụp 2026-Q2, 14 chỉ số)"), ("nul", "khối Gauss cùng hiệp phương sai: trung bình → ngưỡng 95%")]) + \
        '<div class="fig narrow">' + "".join(o) + "</svg></div>"


# ---- 8. heatmap tuong quan tieu chi xep hang
def chart_rank_corr():
    crit = rk.feature.tolist()
    lab = dict(zip(rk.feature, rk.label))
    Cm = pd.read_csv("data/model/features_ranking_latest.csv", encoding="utf-8-sig").set_index("ticker")[crit].astype(float).rank().corr()
    n, cell, l, t = len(crit), 24, 150, 150
    W, H = l + n * cell + 110, t + n * cell + 10
    o = [svg_open(W, H, "Tương quan hạng giữa các tiêu chí xếp hạng, 22 NH")]
    for i, a in enumerate(crit):
        o.append(txt(l - 6, t + i * cell + 16, lab[a], "tick lab", "end"))
        x = l + i * cell + 14
        o.append(txt(x, t - 6, lab[a], "tick lab", "start", f'transform="rotate(-55 {x} {t - 6})"'))
        for j, b_ in enumerate(crit):
            v = Cm.loc[a, b_]
            c = "diag" if i == j else heat_rho(v)
            o.append(f'<rect x="{l + j * cell + 1}" y="{t + i * cell + 1}" width="{cell - 2}" height="{cell - 2}" rx="2" class="hc {c}">'
                     f"<title>{esc(lab[a])} × {esc(lab[b_])}: ρ = {vi(v, 2)}</title></rect>")
    return '<div class="scale"><span class="lbl">Tương quan hạng (Spearman)</span>' + "".join(
        f'<span class="hc {c}">{t_}</span>' for c, t_ in (("n4", "≤ −0,5"), ("n3", "−0,5…−0,2"), ("h0", "|ρ| < 0,2"), ("p2", "0,2…0,5"), ("p3", "≥ 0,5"))) + \
        '</div><div class="fig tw">' + "".join(o) + "</svg></div>"


def heat_rho(v):
    return "n4" if v <= -0.5 else "n3" if v <= -0.2 else "p3" if v >= 0.5 else "p2" if v >= 0.2 else "h0"


# ---- 9. do dai review x sao
def chart_len_stars():
    W, l, r, rowh = 640, 150, 150, 28
    rows = tlen[tlen.n > 100]
    H = rowh * len(rows) + 30
    xs = lin(0, 100, l, W - r)
    o = [svg_open(W, H, "Phân bố số sao theo độ dài review")]
    for v in (0, 25, 50, 75, 100):
        o.append(txt(xs(v), 12, f"{v}%", anchor="middle"))
    for i, rr in enumerate(rows.itertuples()):
        y = 20 + i * rowh
        o.append(txt(l - 10, y + 14, f"{rr.len_bin} từ · {pc(rr.share, 0)}", "tick lab", "end"))
        x0 = l
        for share, c, name in ((rr.pct_1star, "neg", "1 sao"), (rr.pct_mid, "mid", "2–4 sao"), (rr.pct_5star, "pos", "5 sao")):
            w_ = xs(share) - l
            o.append(f'<rect x="{x0:.1f}" y="{y + 3}" width="{max(w_ - 2, 0):.1f}" height="16" class="{c}"><title>{esc(rr.len_bin)} từ: {name} {vi(share, 1)}%</title></rect>')
            x0 += w_
        o.append(txt(W - r + 10, y + 15, f"{vi(rr.pct_no_aspect, 0)}% không khía cạnh", "tick"))
    return legend([("neg", "1 sao"), ("mid", "2–4 sao"), ("pos", "5 sao")]) + '<div class="fig tw">' + "".join(o) + "</svg></div>"


def chart_forest():
    W, l, r, rowh = 560, 170, 20, 26
    d = dep.sort_values("rho")
    H = rowh * len(d) + 40
    xs = lin(-1, 1, l, W - r)
    NAMES = {"log_total_assets": "Quy mô (log TTS)", "casa_percent": "CASA", "cof_ttm_percent": "Chi phí vốn", "npl_percent": "NPL",
             "car_asof_percent": "CAR", "equity_to_assets_pct": "Vốn chủ / TTS", "roa_ttm_percent": "ROA", "ldr_computed_percent": "LDR",
             "state_own_percent": "Sở hữu nhà nước", "app_mean_score": "Điểm app"}
    o = [svg_open(W, H, "Tương quan lãi 12 tháng online với các chỉ số an toàn")]
    for v in (-1, -0.5, 0, 0.5, 1):
        o += [vline(xs(v), 8, H - 26, "base" if v == 0 else "grid"), txt(xs(v), H - 10, vi(v, 1), anchor="middle")]
    for i, rr in enumerate(d.itertuples()):
        y = 18 + i * rowh
        o.append(txt(l - 10, y + 4, NAMES.get(rr.feature, rr.feature), "tick lab", "end"))
        o.append(f'<line x1="{xs(rr.lo):.1f}" x2="{xs(rr.hi):.1f}" y1="{y}" y2="{y}" class="ci"/>')
        o.append(f'<circle cx="{xs(rr.rho):.1f}" cy="{y}" r="4.5" class="dot s1"><title>ρ = {vi(rr.rho, 2)} [{vi(rr.lo, 2)}; {vi(rr.hi, 2)}], n = {rr.n}</title></circle>')
    return '<div class="fig narrow">' + "".join(o) + "</svg></div>"


# ---------------------------------------------------------------- bang nho
def tbl(head, rows, cls=""):
    h = "".join(f"<th>{x}</th>" for x in head)
    b = "".join("<tr>" + "".join(f"<td>{x}</td>" for x in r_) + "</tr>" for r_ in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def decision(items):
    return '<div class="decide"><div class="dh">Quyết định cho mô hình</div><ul>' + "".join(f"<li>{x}</li>" for x in items) + "</ul></div>"


t_rows = []
for lab in ["NIM", "COF", "NPL", "CASA", "LDR", "ROE"]:
    r_ = tprof.loc[lab]
    t_rows.append([lab, vi(r_.acf1_level, 2), vi(r_.half_life_q, 1), vi(r_.ips_p_level, 2), vi(r_.ips_p_change, 2),
                   pc(r_.change_common), pc(r_.change_idio), vi(r_.change_kurtosis, 0)])

out_tbl = uni[uni.outlier_pct > 2].sort_values("outlier_pct", ascending=False)
out_rows = [[code(r_.feature), vi(r_.outlier_pct, 1) + "%", vi(r_["skew"], 1), f"{r_.top_outlier_bank} ({pc(r_.top_outlier_bank_share)})"]
            for _, r_ in out_tbl.head(10).iterrows()]

vif_hi = clw[clw.vif >= 5].sort_values("vif", ascending=False)
rk_ext = rk.sort_values("extreme_gap_share", ascending=False).head(6)
rk_ext_rows = [[esc(r_.label), r_.extreme_bank, pc(r_.extreme_gap_share), vi(r_.max_robust_z, 1) if r_.max_robust_z < 100 else "— (đa số = 0)"]
               for r_ in rk_ext.itertuples()]
rk_pair_rows = [[f"{esc(dict(zip(rk.feature, rk.label))[r_.a])} – {esc(dict(zip(rk.feature, rk.label))[r_.b])}", vi(r_.rho, 2)]
                for r_ in rk_pairs.head(8).itertuples()]
asp_rows = []
for r_ in asp.sort_values("share", ascending=False).itertuples():
    bq = f"{vi(r_.bq_median, 0)} · {pc(r_.bq_share_ge30, 0)}" if "bq_median" in asp else "—"
    asp_rows.append([esc(r_.label), vi(r_.n, 0), pc(r_.share, 1), vi(r_.mean_star, 2), vi(r_.pct_1star, 0) + "%", bq])
lang_rows = [[esc(k), pc(v.share, 1), vi(v.mean_star, 2)] for k, v in lang.iterrows()]
param_rows = [["Ridge, 28 biến lõi", vi(P["ridge_28"], 0), vi(P["ridge_28"] / train1, 2)],
              ["LightGBM 100 cây × 15 lá", vi(P["lgbm_100x15"], 0), vi(P["lgbm_100x15"] / train1, 1)],
              ["GRU ẩn 16, 8 biến", vi(P["gru_h16_f8"], 0), vi(P["gru_h16_f8"] / train1, 1)],
              ["LSTM ẩn 32, 8 biến", vi(P["lstm_h32_f8"], 0), vi(P["lstm_h32_f8"] / train1, 1)]]
miss_items = [(r_.year, r_.missing_pct, f"{r_.year}: {vi(r_.missing_pct, 1)}% ô thiếu") for r_ in miss_year.itertuples()]
roll_items = [(lab, roll.loc[lab, "r2_rolloff"], f"{lab}: tương quan {vi(roll.loc[lab, 'corr_rolloff'], 2)}, n = {roll.loc[lab, 'n']}")
              for lab in ["COF", "NIM", "ROE"]]

# ---------------------------------------------------------------- ket luan
S = lambda lab, h, col: cs.loc[f"{lab}{h}", col]  # noqa: E731
concl = [
    ("Hướng đi", f"Mức các chỉ tiêu rất bền: tự tương quan bậc 1 {vi(tprof.loc[['NIM','COF','NPL','CASA','LDR','ROE'], 'acf1_level'].min(), 2)}–{vi(tprof.loc[['NIM','COF','NPL','CASA','LDR','ROE'], 'acf1_level'].max(), 2)}; kiểm định IPS không bác bỏ nghiệm đơn vị ở {', '.join(lvl_nonstat)}. Thay đổi thì dừng ở cả 6.",
     "Dự báo <b>thay đổi</b> so với quý gốc, không dự báo mức. Mốc so sánh là naive."),
    ("Hướng đi", f"Phần thay đổi chung cả ngành: COF {pc(tprof.loc['COF','change_common'])}, CASA {pc(tprof.loc['CASA','change_common'])}, các chỉ tiêu khác {pc(tprof.loc[['NIM','NPL','LDR','ROE'],'change_common'].min())}–{pc(tprof.loc[['NIM','NPL','LDR','ROE'],'change_common'].max())}.",
     "COF: mô hình mức chung ngành + độ lệch từng NH. Các chỉ tiêu còn lại chủ yếu là biến động riêng từng NH, khó dự báo."),
    ("Hướng đi", f"ROE: {pc(tprof.loc['ROE','change_idio'])} thay đổi là riêng NH–quý, độ nhọn {vi(tprof.loc['ROE','change_kurtosis'], 0)}. Không cách nào thắng naive.",
     "Không dự báo ROE; chỉ hiển thị số công bố."),
    ("Hướng đi", f"22 NH không tạo cụm: silhouette k = 3 là {vi(sil3.silhouette, 2)}, bằng khối Gauss ngẫu nhiên ({vi(sil3.null_mean, 2)}; p = {vi(sil3.p, 2)}).",
     "Bỏ phân nhóm cứng. Dùng kNN tìm NH tương tự; xếp hạng không dựa vào nhóm."),
    ("Thuật toán", f"Tín hiệu ngoài mẫu yếu. Chỉ drift (COF {vi(100*S('COF',2,'skill_drift'),0,True)}% / {vi(100*S('COF',4,'skill_drift'),0,True)}%), mùa vụ (CASA 1 quý {vi(100*S('CASA',1,'skill_seasonal'),0,True)}%) và Ridge trên biến ổn định (CASA 1 quý {vi(100*S('CASA',1,'skill_ridge_stable'),0,True)}%, LDR 4 quý {vi(100*S('LDR',4,'skill_ridge_stable'),0,True)}%) thắng naive. Ridge trên mọi biến thua ở cả 18 ô.",
     "Baseline có cấu trúc làm mô hình chính. Học máy chỉ ít tham số, chọn biến chặt, dùng ở ô thắng trong walk-forward."),
    ("Thuật toán", f"Quan hệ phi tuyến hiếm: {n_nl}/{vi(n_cont_pairs,0)} cặp đặc trưng–mục tiêu ({pc(n_nl/n_cont_pairs,1)}) có spline hơn đường thẳng ≥ 2 điểm.",
     "Không cần mô hình phi tuyến để bắt quan hệ. LightGBM chỉ đáng thử ở COF (biến vĩ mô)."),
    ("Thuật toán", f"Mẫu nhỏ: {train1} mẫu huấn luyện ở gốc 2023-Q1. LSTM 32 ẩn cần {vi(P['lstm_h32_f8'],0)} tham số ({vi(P['lstm_h32_f8']/train1,0)} tham số / mẫu).",
     "Không dùng DL cho số liệu tài chính. DL chỉ dùng cho review."),
    ("Thuật toán", f"Thay đổi có đuôi rất dày: độ nhọn NIM {vi(tprof.loc['NIM','change_kurtosis'],0)}, NPL {vi(tprof.loc['NPL','change_kurtosis'],0)}, ROE {vi(tprof.loc['ROE','change_kurtosis'],0)}.",
     "Hàm mất mát MAE hoặc Huber; đánh giá bằng MAE; baseline dùng trung vị."),
    ("Thuật toán", f"Review rất ngắn (trung vị {vi(T['words_p50'],0)} từ, p99 {vi(T['words_p99'],0)}), sao phân hai cực ({pc(stars.loc[1,'share'])} 1 sao, {pc(stars.loc[5,'share'])} 5 sao), và độ dài quyết định số sao.",
     "max_len 64–96; báo macro-F1; lấy mẫu gán nhãn phân tầng theo độ dài và số sao."),
    ("Đặc trưng", f"{len(skewed)}/{len(cont)} biến liên tục lệch |skew| > 1; Yeo-Johnson đưa {len(fixed)} biến về gần đối xứng. Ngoại lai dồn vào NVB ({nvb_top}/{len(with_out)} biến).",
     "Mô hình tuyến tính, kNN, PCA, TOPSIS: Yeo-Johnson + winsorize p1/p99 fit trên tập train. Mô hình cây: giữ nguyên."),
    ("Đặc trưng", f"Phần đã biết trước của TTM, (x<sub>t</sub> − x<sub>t−3</sub>)/4, giải thích {pc(roll.loc['COF','r2_rolloff'])} thay đổi COF quý sau, NIM {pc(roll.loc['NIM','r2_rolloff'])}, ROE {pc(roll.loc['ROE','r2_rolloff'])}.",
     "Thêm đặc trưng rolloff và số riêng từng quý (MAS) vào <code>build_features</code>."),
    ("Đặc trưng", "Mùa vụ: NPL giảm quý 4, CASA giảm quý 1 (EDA nghiệp vụ, câu 9). Mô hình mùa vụ giảm sai số CASA 1 quý "
     f"{vi(100*S('CASA',1,'skill_seasonal'),0,True)}%, NPL {vi(100*S('NPL',1,'skill_seasonal'),0,True)}%.",
     "Thêm biến quý trong năm."),
    ("Đặc trưng", f"Giai đoạn giãn nợ (TT 01/2020, TT 02/2023) không làm đổi nhịp thay đổi NPL (hệ số {vi(reg_npl.effect_regime,3,True)} điểm/quý, p = {vi(reg_npl.p,2)}).",
     "Không thêm cờ chế độ giãn nợ; ghi chú khi viết."),
    ("Đặc trưng", f"Giữa NH: {D['pairs_between_07']} cặp |ρ| ≥ 0,7; {D['n_varying']} biến chỉ mang {D['between_all_80']} chiều (80% phương sai). Trong NH: {D['pairs_within_07']} cặp; VIF cao chỉ ở ROE/ROA.",
     "Dự báo: bỏ một trong ROE/ROA. Xếp hạng: mỗi cụm trùng lặp chỉ giữ một tiêu chí."),
    ("Đặc trưng", f"Review về tiết kiệm chỉ {pc(sav.share,1)}, về vay {pc(loan.share,1)}; phần lớn NH–quý chỉ có vài review mỗi khía cạnh.",
     "Không làm chỉ số khía cạnh tiết kiệm theo NH–quý. Gộp nhiều quý + co rút Bayes, hoặc dùng khía cạnh dịch vụ chung."),
    ("Đánh giá", f"Chia sai làm phồng kết quả: LightGBM chia theo quý không purge đạt {pc(leaky_h24.min())} đến {pc(leaky_h24.max())} ở tầm 2–4 quý; có purge chỉ còn {pc(purged_h24.min())} đến {pc(purged_h24.max())}.",
     "Walk-forward, hoặc kiểm chéo khối có purge h (+3 quý với TTM). Không bao giờ chia ngẫu nhiên."),
    ("Đánh giá", f"Thiếu có cấu trúc: {pc(M['share_missing_in_2018'])} ô thiếu nằm ở 2018; từ 2019 còn {vi(M['missing_pct_from_2019'],1)}%.",
     "Bắt đầu từ 2019-Q1; LightGBM để NaN; mô hình cần đủ ô dùng số quý trước + cờ thiếu."),
]
concl_rows = "".join(f'<tr><td><span class="tag t{["Hướng đi","Thuật toán","Đặc trưng","Đánh giá"].index(k)}">{k}</span></td><td>{f_}</td><td>{d_}</td></tr>'
                     for k, f_, d_ in concl)

# ---------------------------------------------------------------- trang
CSS = open("reports/eda_ml/style.css", encoding="utf-8").read()
page = f"""<title>EDA định hướng mô hình</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style>
<main class="wrap">
<header class="top">
  <p class="eyebrow">Khóa luận · hệ thống chọn ngân hàng · 22 NHTM niêm yết</p>
  <h1>EDA định hướng mô hình</h1>
  <p class="lede">Trong bài toán AI/ML, EDA dùng để tìm liên hệ giữa các trường dữ liệu, từ đó chọn <b>hướng đi</b>, <b>thuật toán</b> và <b>cách tạo đặc trưng</b>. Mỗi mục dưới đây trả lời một câu hỏi mà bước mô hình cần hỏi, và kết thúc bằng quyết định rút ra từ số liệu.</p>
  <dl class="meta">
    <div><dt>Panel</dt><dd>{vi(F['n_rows'],0)} NH–quý · {F['n_periods']} quý (2019-Q1 → 2026-Q2) · {F['n_features']} đặc trưng</dd></div>
    <div><dt>Ảnh chụp xếp hạng</dt><dd>22 NH · {len(rk)} tiêu chí ứng viên</dd></div>
    <div><dt>Review</dt><dd>{vi(T['n_reviews'],0)} review có nội dung · {T['first_year']}–{T['last_year']}</dd></div>
  </dl>
  <p class="note-old">Trang “Khám phá dữ liệu 22 ngân hàng” (18/09) là phân tích nghiệp vụ, ví dụ ngân hàng nào trả lãi cao, nhóm nào nợ xấu tăng. Trang này không lặp lại phần đó mà chỉ giữ những gì quyết định cách làm mô hình.</p>
</header>

<section id="ketluan">
  <h2>Phát hiện → quyết định</h2>
  <p class="sub">Tóm tắt toàn trang. Chi tiết và biểu đồ ở các mục bên dưới.</p>
  <div class="tw"><table class="concl"><thead><tr><th>Loại</th><th>Phát hiện từ EDA</th><th>Quyết định</th></tr></thead><tbody>{concl_rows}</tbody></table></div>
</section>

<section id="cachdoc">
  <h2>Bốn kiểu EDA và ba bài toán</h2>
  <div class="two">
    <div>{tbl(["Kiểu EDA (IBM)", "Ở trang này"], [
        ["Đơn biến, không đồ thị", "Bảng thống kê mô tả 93 biến: lệch, nhọn, ngoại lai, thiếu (mục 1)"],
        ["Đơn biến, có đồ thị", "Phân bố độ lệch – ngoại lai; độ dài review (mục 1, 9)"],
        ["Đa biến, không đồ thị", "Tương quan, VIF, kiểm định IPS, ANOVA, kiểm chéo (mục 2–5, 8)"],
        ["Đa biến, có đồ thị", "Tự tương quan, bản đồ nhiệt, tương quan giữa/trong NH, phân cụm (mục 2–8)"]], "plain")}</div>
    <div>{tbl(["Bài toán", "Dữ liệu", "Mục liên quan"], [
        ["Dự báo 6 chỉ tiêu, 1–4 quý", "Panel NH–quý", "1–6"],
        ["Xếp hạng, gợi ý NH", "Ảnh chụp 22 NH", "1, 4, 7, 8"],
        ["Phân tích review (DL)", "531.988 review", "9"]], "plain")}</div>
  </div>
</section>

<section id="donbien">
  <h2>1. Phân phối từng đặc trưng</h2>
  <p class="q">Có cần biến đổi hay chuẩn hóa đặc trưng trước khi đưa vào mô hình không?</p>
  {chart_univariate()}
  <ul class="find">
    <li>{len(cont)} biến liên tục: {int((cont['skew'].abs() <= 1).sum())} gần đối xứng, {len(skewed)} lệch |skew| &gt; 1. Biến đổi Yeo-Johnson đưa {len(fixed)}/{len(skewed)} biến lệch về |skew| &lt; 0,5. Còn 6 biến nhị phân (các gói tín dụng chính sách).</li>
    <li>{int((uni.outlier_pct > 2).sum())} biến có hơn 2% ô ngoại lai. NVB đứng đầu số ô ngoại lai ở {nvb_top}/{len(with_out)} biến. Riêng NPL, {pc(npl_u.top_outlier_bank_share)} số ô ngoại lai là của NVB (độ lệch {vi(npl_u['skew'],1)}, độ nhọn {vi(npl_u['kurtosis'],0)}).</li>
  </ul>
  {tbl(["Biến", "Ngoại lai", "Độ lệch", "NH chiếm nhiều ô ngoại lai nhất"], out_rows)}
  {decision(["Mô hình cây (LightGBM): không cần biến đổi; ngoại lai chỉ ảnh hưởng qua hàm mất mát.",
             "Mô hình tuyến tính, kNN, PCA và chuẩn hóa TOPSIS: Yeo-Johnson cho biến lệch, winsorize p1/p99 cho biến nhiều ngoại lai, rồi chuẩn hóa z. Tham số của cả ba bước fit trên tập train.",
             "NVB là quan sát có ảnh hưởng lớn: tương quan dùng Spearman, sai số dùng MAE, và khi viết phải báo kết quả có/không có NVB."])}
  <p class="file">Bảng đầy đủ 93 biến (trung bình, độ lệch chuẩn, min, tứ phân vị, max, độ lệch, độ nhọn, thiếu, ngoại lai): {code("data/model/eda_ml/univariate.csv")}</p>
</section>

<section id="muctieu">
  <h2>2. Biến mục tiêu dự báo</h2>
  <p class="q">Nên dự báo mức hay thay đổi? Mốc so sánh nào? Hàm mất mát nào?</p>
  {chart_acf()}
  {tbl(["Chỉ tiêu", "Tự tương quan bậc 1 của mức", "Nửa vòng đời (quý)", "p IPS: mức", "p IPS: thay đổi", "Phần chung của thay đổi", "Phần riêng NH–quý", "Độ nhọn của thay đổi"], t_rows, "numt")}
  <ul class="find">
    <li>Mức rất bền: một cú lệch khỏi trung bình của NH cần {vi(tprof.loc['NIM','half_life_q'],0)} quý (NIM) đến {vi(tprof.loc['NPL','half_life_q'],0)} quý (NPL) mới giảm một nửa. Kiểm định IPS (t-bar của ADF, ngưỡng mô phỏng Monte Carlo cho 22 chuỗi × {F['ips']['T']} quý) không bác bỏ nghiệm đơn vị ở {', '.join(lvl_nonstat)}. Chuỗi thay đổi thì dừng ở cả 6 (p &lt; 0,001).</li>
    <li>Thay đổi của COF TTM có quán tính (tự tương quan bậc 1 là {vi(tacf[(tacf.label=='COF')&(tacf.lag==1)].acf_change.iloc[0],2)}), nhưng COF riêng từng quý thì không ({vi(tacf[(tacf.label=='COF quý')&(tacf.lag==1)].acf_change.iloc[0],2)}). Nghĩa là quán tính này sinh ra từ cách cộng 4 quý, không phải từ hành vi ngân hàng. NIM và ROE riêng từng quý có thay đổi đảo chiều mạnh ({vi(tacf[(tacf.label=='NIM quý')&(tacf.lag==1)].acf_change.iloc[0],2)}): đó là nhiễu của từng quý.</li>
    <li>Phần chung cả ngành trong thay đổi 1 quý: COF {pc(tprof.loc['COF','change_common'])}, CASA {pc(tprof.loc['CASA','change_common'])}; các chỉ tiêu còn lại chỉ {pc(tprof.loc[['NIM','NPL','LDR','ROE'],'change_common'].min())}–{pc(tprof.loc[['NIM','NPL','LDR','ROE'],'change_common'].max())}. Xu hướng riêng của từng NH (drift) gần như bằng 0 (≤ {pc(tprof.loc[['NIM','COF','NPL','CASA','LDR','ROE'],'change_bank'].max(),1)}).</li>
  </ul>
  {decision(["Mục tiêu mô hình là <b>thay đổi</b> t → t+h. Dự báo mức rồi báo R² cao là tự lừa: mức gần như không đổi nên naive đã đạt R² đó.",
             "Mốc so sánh bắt buộc: naive, naive có mùa vụ (NPL, CASA), drift (LDR, COF).",
             "COF: tách mức chung ngành (chịu tác động lãi điều hành) khỏi độ lệch riêng từng NH. NIM, NPL, LDR, ROE: phần dự báo được chỉ là phần nhỏ.",
             "Đuôi rất dày (độ nhọn 49–242) → hàm mất mát MAE hoặc Huber, không dùng MSE thuần."])}
</section>

<section id="dactrung-muctieu">
  <h2>3. Đặc trưng ↔ mục tiêu</h2>
  <p class="q">Có bao nhiêu tín hiệu? Quan hệ tuyến tính hay phi tuyến? Mô hình nên phức tạp đến đâu?</p>
  <p class="how">Mỗi đặc trưng quý t (theo NH thì trừ trung bình <i>quá khứ</i> của NH, để không nhìn tương lai) so với thay đổi mục tiêu t → t+h. “Biến ổn định”: |ρ| ≥ 0,15 và cùng dấu ở hai nửa giai đoạn (trước/sau 2022-Q2). Các ô trong bảng là mức giảm sai số so với naive khi kiểm chéo theo khối quý, bỏ khỏi tập huấn luyện các quý có thay đổi chồng lên khối kiểm tra (purge h quý, TTM thêm 3). Tập huấn luyện có cả quý sau nên đây là đo <i>tín hiệu</i>, không phải dự báo.</p>
  {table_skill()}
  <ul class="find">
    <li>Mô hình dùng tất cả biến thua naive ở gần hết các ô: Ridge thua ở cả 18 ô, LightGBM thua ở {int((ceil.skill_lgbm_all < -0.05).sum())}/18. Chỉ COF là có tín hiệu, và phần đó drift đã bắt được gần hết.</li>
    <li>Mùa vụ và Ridge trên vài biến ổn định là cách duy nhất thắng naive ở NPL và CASA tầm 1 quý.</li>
    <li>Phi tuyến hiếm: {n_nl}/{vi(n_cont_pairs,0)} cặp ({pc(n_nl/n_cont_pairs,1)}) có spline bậc 3 hơn đường thẳng từ 2 điểm trở lên.</li>
    <li>Cột cuối là cùng LightGBM nhưng chia theo quý mà không purge. Nó "thắng" naive tới {pc(leaky_h24.max())}, vì thay đổi 4 quý của hai quý liền nhau chồng 3 quý lên nhau và mô hình chỉ cần nhận ra NH.</li>
  </ul>
  {decision(["Baseline có cấu trúc (naive, mùa vụ, drift, rolloff) là mô hình chính. Học máy là mô hình thách thức, và chỉ được dùng ở ô nào thắng trong walk-forward.",
             "Mô hình thách thức phải ít tham số, chọn biến chặt theo từng chỉ tiêu × tầm: Ridge trên biến ổn định, hoặc LightGBM nông cho COF.",
             "Không cần mạng nơ-ron hay mô hình phi tuyến phức tạp để bắt quan hệ.",
             "Đánh giá bằng walk-forward hoặc kiểm chéo khối có purge. Chia ngẫu nhiên hay chia theo quý mà không purge sẽ cho kết quả đẹp giả."])}
  <p class="file">Từng cặp đặc trưng × mục tiêu × tầm (ρ hai nửa, kỹ năng tuyến tính/spline): {code("data/model/eda_ml/feature_target.csv")}</p>
</section>

<section id="dactrung-dactrung">
  <h2>4. Đặc trưng ↔ đặc trưng</h2>
  <p class="q">Các đặc trưng có trùng thông tin nhau không, và mức trùng có giống nhau khi so giữa NH với khi theo dõi trong một NH?</p>
  {chart_pairs()}
  <ul class="find">
    <li>Giữa NH, trung vị |ρ| là {vi(D['median_abs_between'],2)} và {D['pairs_between_07']} cặp có |ρ| ≥ 0,7. {D['n_varying']} biến theo NH–quý chỉ mang {D['between_all_80']} chiều (80% phương sai), {D['between_all_90']} chiều (90%).</li>
    <li>Trong NH, trung vị |ρ| là {vi(D['median_abs_within'],2)} và chỉ {D['pairs_within_07']} cặp có |ρ| ≥ 0,7. {D['n_core']} biến lõi mang {D['within_core_80']} chiều (80%). {D['pairs_sign_flip']} cặp đổi dấu giữa hai góc nhìn, {D['pairs_gap_05']} cặp lệch nhau từ 0,5 trở lên.</li>
    <li>VIF (trong NH) chỉ cao ở {', '.join(f"{code(r_.feature)} {vi(r_.vif,1)}" for r_ in vif_hi.itertuples())}.</li>
  </ul>
  {decision(["Dự báo (trong NH): đa cộng tuyến thấp, giữ phần lớn biến; bỏ một trong ROE/ROA và một trong NIM TTM/NIM quý. Ridge đủ xử lý phần còn lại.",
             "Xếp hạng và kNN (giữa NH): trùng lặp nặng. Mỗi cụm |ρ| ≥ 0,7 chỉ giữ một tiêu chí, nếu không một chiều thông tin sẽ bị tính nhiều lần.",
             "Không dùng tương quan giữa NH để chọn biến cho mô hình dự báo, và ngược lại."])}
</section>

<section id="thoigian">
  <h2>5. Cấu trúc thời gian và cỡ mẫu</h2>
  <p class="q">Cấu trúc thời gian nào cần biến thành đặc trưng? Dữ liệu đủ cho mô hình cỡ nào?</p>
  <div class="two">
    <div><h3>Phần đã biết trước của TTM</h3>
    {hbars(roll_items, lambda v: pc(v), 1.0, "R2 của phần rolloff", "R² giữa thay đổi TTM quý sau và (x<sub>t</sub> − x<sub>t−3</sub>)/4 tính từ số riêng từng quý. Phần này biết tại quý t.")}</div>
    <div><h3>Tham số so với mẫu huấn luyện</h3>
    {tbl(["Mô hình", "Tham số", "Tham số / mẫu"], param_rows, "numt")}
    <p class="cap">{train1} mẫu huấn luyện (NH–quý có nhãn tầm 1 quý trước 2023-Q1), {budget.loc[1,'test_from_2023Q1']} mẫu kiểm tra.</p></div>
  </div>
  <ul class="find">
    <li>TTM là tổng 4 quý, nên thay đổi TTM quý sau = (quý mới vào − quý rơi ra)/4. Quý rơi ra đã biết tại t. Riêng phần này giải thích {pc(roll.loc['COF','r2_rolloff'])} thay đổi COF quý sau.</li>
    <li>Giãn nợ (TT 01/2020: 2020-Q1 → 2022-Q2; TT 02/2023: 2023-Q2 → 2024-Q4, {int(reg_npl.regime_quarters)}/{int(reg_npl.n_quarters)} quý): hồi quy thay đổi NPL trung vị theo quý trên biến chế độ và biến quý cho hệ số {vi(reg_npl.effect_regime,3,True)} (p = {vi(reg_npl.p,2)}). Nợ nhóm 2 cũng không có ý nghĩa (p = {vi(reg.loc['loans_g2_percent','p'],2)}).</li>
    <li>Lãi tái cấp vốn tác động lên COF theo quý sau 1–2 quý (EDA nghiệp vụ, câu 3), nhưng cả giai đoạn chỉ đổi 7 lần.</li>
  </ul>
  {decision(["Đưa vào <code>build_features</code>: số riêng từng quý (NIM, COF, ROE, CIR, lợi suất), số hạng rolloff, biến quý trong năm, lãi điều hành trễ 1–2 quý. Hiện các biến này chỉ có trong code thí nghiệm.",
             "Không thêm cờ chế độ giãn nợ.",
             "Mô hình cho số liệu tài chính giữ dưới khoảng 0,1 tham số/mẫu hiệu dụng (Ridge, LightGBM nông, regularize mạnh). LSTM/GRU cần gấp hàng chục lần số mẫu đang có."])}
</section>

<section id="thieu">
  <h2>6. Dữ liệu thiếu</h2>
  <p class="q">Ô thiếu ngẫu nhiên hay có cấu trúc? Điền hay để trống?</p>
  {hbars(miss_items, lambda v: vi(v, 1) + "%", max(v for _, v, _ in miss_items) * 1.1, "Tỷ lệ ô thiếu theo năm", "Tỷ lệ ô thiếu của các đặc trưng theo NH–quý, theo năm.")}
  <ul class="find">
    <li>{pc(M['share_missing_in_2018'])} số ô thiếu nằm ở 2018: đó là ô chưa thể có số (thuyết minh, chỉ số trễ), không phải ô bị mất. Từ 2019 còn {vi(M['missing_pct_from_2019'],1)}%, giảm từ {vi(M['missing_pct_2019_first_q'],1)}% (2019-Q1) xuống {vi(M['missing_pct_last_q'],1)}% (2026-Q2).</li>
    <li>Thử nghiệm điền khuyết (15/09): đổi cách điền chỉ đổi MAE dự báo từ −3,5% đến +4,4%. Với xếp hạng, lấy số gần nhất của chính NH làm hạng lệch ít nhất (0,39 bậc).</li>
  </ul>
  {decision(["Mô hình bắt đầu từ 2019-Q1. LightGBM để NaN. Mô hình cần đủ ô dùng số quý trước + cờ thiếu.",
             "Xếp hạng dùng số gần nhất ≤ 4 quý. Cũ hơn thì báo khoảng hạng, không điền trung bình."])}
</section>

<section id="phancum">
  <h2>7. Dữ liệu có cụm không?</h2>
  <p class="q">Có nên chia 22 NH thành nhóm bằng k-means không?</p>
  {chart_silhouette()}
  <ul class="find">
    <li>Với mọi k từ 2 đến 6, silhouette của 22 NH nằm trong khoảng của một khối Gauss ngẫu nhiên có cùng hiệp phương sai. Với k = 3: {vi(sil3.silhouette,3)} so với {vi(sil3.null_mean,3)} (p = {vi(sil3.p,2)}).</li>
    <li>Hopkins trên 3 thành phần chính: {vi(C['hopkins_pca3'],2)}, ngưỡng 95% của khối Gauss là {vi(C['hopkins_null_p95'],2)}. Dữ liệu chỉ hơi co cụm hơn ngẫu nhiên, chưa đủ để có ý nghĩa thống kê.</li>
    <li>Điều này giải thích vì sao 6/22 NH đổi nhóm giữa các quý: ranh giới k-means chỉ là đường cắt ngang một đám liên tục.</li>
  </ul>
  {decision(["Không dùng nhóm k-means làm đặc trưng hay làm tầng lọc cho xếp hạng.",
             "Chức năng “ngân hàng tương tự” dùng kNN (k = 3) trên các biến đã chuẩn hóa và bỏ trùng.",
             "Nếu cần mô tả nhóm khi viết: ghi rõ silhouette {0} và p = {1}.".format(vi(sil3.silhouette, 2), vi(sil3.p, 2))])}
</section>

<section id="xephang">
  <h2>8. Dữ liệu cho xếp hạng</h2>
  <p class="q">Tiêu chí nào trùng nhau? Có cần xếp hạng đa tiêu chí không? Chuẩn hóa thế nào?</p>
  {chart_rank_corr()}
  <div class="two">
    <div><h3>Cặp tiêu chí trùng (|ρ| ≥ 0,6)</h3>{tbl(["Cặp", "ρ"], rk_pair_rows, "numt")}</div>
    <div><h3>Một NH chiếm thang min-max</h3>{tbl(["Tiêu chí", "NH", "Phần thang bị chiếm", "z bền"], rk_ext_rows, "numt")}
    <p class="cap">“Phần thang bị chiếm” = khoảng cách từ NH cực trị tới NH kế tiếp / toàn khoảng min-max.</p></div>
  </div>
  <h3>Lãi 12 tháng online so với các chỉ số an toàn</h3>
  {chart_forest()}
  <ul class="find">
    <li>Cặp trùng mạnh nhất: {esc(dict(zip(rk.feature, rk.label))[rp.a])} – {esc(dict(zip(rk.feature, rk.label))[rp.b])} ({vi(rp.rho,2)}). Chi phí vốn còn trùng với lợi suất cho vay, nợ nhóm 2 trùng với chi phí tín dụng, ROA trùng với NIM.</li>
    <li>Lãi suất tiết kiệm không đi cùng bất kỳ chỉ số an toàn nào: mọi khoảng tin cậy đều chứa 0 (n = 22). Tức là lãi suất và mức an toàn là hai chiều riêng, người gửi thật sự phải đánh đổi giữa chúng.</li>
    <li>Ở vài tiêu chí, một NH chiếm tới 1/3 thang min-max (VPB ở NIM và LDR, HDB ở nợ nhóm 2), nên các NH còn lại bị nén vào 2/3 thang. Sở hữu nhà nước gần như là biến nhị phân (đa số NH bằng 0).</li>
  </ul>
  {decision(["Cần xếp hạng đa tiêu chí (TOPSIS/AHP): nếu lãi suất đi cùng an toàn thì chỉ cần một tiêu chí.",
             "Mỗi cụm trùng chỉ giữ một tiêu chí: CASA hoặc chi phí vốn; nợ nhóm 2 hoặc chi phí tín dụng; ROA hoặc NIM.",
             "Chuẩn hóa: winsorize hoặc chuẩn hóa theo hạng/vector thay vì min-max thô. Sở hữu nhà nước dùng dạng có/không.",
             "Báo khoảng hạng (SMAA) vì hạng nhạy với trọng số và chuẩn hóa."])}
</section>

<section id="vanban">
  <h2>9. Dữ liệu văn bản (review app)</h2>
  <p class="q">Cần tiền xử lý gì? Độ dài đầu vào bao nhiêu? Nhãn có cân bằng không? Khía cạnh nào đủ dữ liệu?</p>
  {chart_len_stars()}
  <ul class="find">
    <li>Rất ngắn: trung vị {vi(T['words_p50'],0)} từ, p90 {vi(T['words_p90'],0)}, p99 {vi(T['words_p99'],0)}. {pc(T['share_le3'])} review ≤ 3 từ; chỉ {pc(T['share_gt64'],1)} dài hơn 64 từ.</li>
    <li>Số sao phân hai cực: 1 sao {pc(stars.loc[1,'share'])}, 2–4 sao {pc(stars.loc[[2,3,4],'share'].sum())}, 5 sao {pc(stars.loc[5,'share'])}. Độ dài quyết định số sao: review 1 từ có {vi(tlen.iloc[0].pct_5star,0)}% 5 sao, review trên 40 từ có hơn 70% 1 sao.</li>
    <li>Trùng: {pc(T['dup_extra_share'])} review là bản lặp của review khác (phần lớn là “tốt”, “ok”); với review trên 3 từ còn {pc(T['dup_extra_share_gt3'])}.</li>
    <li>{pc(lang.loc['có dấu','share'])} viết có dấu; {pc(lang.loc['tiếng Việt không dấu','share'],1)} tiếng Việt không dấu; {pc(lang.loc['tiếng Anh','share'],1)} tiếng Anh; {pc(lang.loc['khác (ngắn, ký hiệu)','share'],1)} ngắn hoặc ký hiệu. {pc(T['emoji_share'],0)} có emoji.</li>
    <li>{pc(T['share_no_aspect'])} review không chạm từ khóa khía cạnh nào (với review trên 5 từ: {pc(T['share_no_aspect_gt5'])}). Ba NH lớn nhất chiếm {pc(T['share_top3_banks'])} số review; PGB chỉ có {vi(T['reviews_min_bank'],0)}. {T['bank_months_bombing']}/{vi(T['bank_months'],0)} NH–tháng có dấu hiệu đánh giá dồn dập (bombing).</li>
  </ul>
  {tbl(["Khía cạnh (từ khóa mồi)", "Review", "Tỷ lệ", "Sao TB", "1 sao", "Trung vị / NH–quý · tỷ lệ NH–quý ≥ 30"], asp_rows, "numt")}
  {tbl(["Cách viết", "Tỷ lệ", "Sao TB"], lang_rows, "numt small")}
  {decision(["Tiền xử lý: bỏ bản trùng khi huấn luyện, chuẩn hóa Unicode, giữ emoji (mang cảm xúc), không bỏ review không dấu. Ưu tiên thử ViSoBERT (học trên văn bản mạng xã hội) cạnh PhoBERT (cần tách từ).",
             "max_len 64 phủ hơn 98% review; 96 là dư.",
             "Nhãn lệch hai cực: báo macro-F1, dùng trọng số lớp. Lấy mẫu gán nhãn phân tầng theo độ dài × số sao × NH, vì review ngắn gần như toàn 5 sao và không có khía cạnh.",
             "Cần lớp “chung/không khía cạnh” trong ABSA.",
             "Khía cạnh tiết kiệm và vay quá thưa để làm chỉ số theo NH–quý. Tầng xếp hạng dùng khía cạnh dịch vụ chung (giao dịch, đăng nhập, tốc độ, CSKH), gộp nhiều quý + co rút Bayes."])}
</section>

<footer class="foot">
  <p>Tái lập: <code>python -m experiments.eda_ml</code> (~3 phút) → <code>data/model/eda_ml/</code>; trang: <code>python reports/eda_ml/make_report.py</code>. Số liệu tài chính tới 2026-Q2; review tới {T['last_year']}.</p>
</footer>
</main>
"""
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(page)
print("ghi", OUT, f"{len(page) / 1024:.0f} KB")
for w in WARN:
    print("CANH BAO:", w)
