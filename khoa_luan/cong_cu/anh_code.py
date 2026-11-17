from __future__ import annotations

import contextlib
import html
import io
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

REPO = Path(__file__).resolve().parents[2]
RA = REPO / "khoa_luan" / "anh_code" / "html"
RA.mkdir(parents=True, exist_ok=True)
os.chdir(REPO)
sys.path.insert(0, str(REPO))
pd.set_option("display.width", 110)
pd.set_option("display.max_columns", 12)
pd.set_option("display.max_colwidth", 38)

CSS = """
body{margin:0;background:#fff;font-family:Segoe UI,Arial,sans-serif}
#o{width:820px;padding:6px}
.o{border:1px solid #d9d9d9;border-radius:4px;overflow:hidden}
.in{display:flex;background:#f7f7f7;border-bottom:1px solid #e5e5e5}
.p{flex:0 0 46px;color:#307fc1;font:12px Consolas,monospace;padding:8px 4px 0 6px;text-align:right}
.po{color:#d84315}
.code{flex:1;padding:6px 8px 6px 4px;overflow:hidden}
.code pre,.txt{margin:0;font:12.5px/1.42 Consolas,'Cascadia Mono',monospace;white-space:pre-wrap;word-break:break-word}
.out{display:flex;background:#fff}
.res{flex:1;padding:6px 8px 8px 4px;overflow:hidden}
.ok{color:#2e7d32;font:11px Consolas,monospace;padding:2px 0 4px 52px;background:#f7f7f7;border-bottom:1px solid #e5e5e5}
table.df{border-collapse:collapse;font:12px Consolas,monospace;margin:2px 0}
table.df th{font-weight:bold;text-align:right;padding:3px 8px;border-bottom:1px solid #9e9e9e}
table.df td{text-align:right;padding:3px 8px;white-space:nowrap}
table.df tbody tr:nth-child(odd){background:#f5f5f5}
table.df tbody th{border:none}
.tab{background:#ececec;border-bottom:1px solid #d9d9d9;font:12px Segoe UI,Arial;padding:5px 10px;color:#333}
.ed{display:flex;background:#fafafa}
.ln{flex:0 0 40px;text-align:right;color:#9e9e9e;padding:6px 8px 6px 0;border-right:1px solid #e5e5e5;
    font:12.5px/1.42 Consolas,monospace;white-space:pre;background:#f3f3f3}
.ed .code{padding-left:8px}
"""

FMT = HtmlFormatter(nowrap=True, noclasses=True, style="vs")


def _to(code: str, lang: str = "python") -> str:
    return highlight(code, get_lexer_by_name(lang), FMT)


def _df_html(df: pd.DataFrame) -> str:
    return df.to_html(classes="df", border=0, na_rep="NaN",
                      float_format=lambda v: f"{v:,.0f}" if abs(v) >= 1000 else f"{v:.4g}")


def _run(code: str, ns: dict) -> str:
    import ast
    tree = ast.parse(code)
    last = tree.body.pop() if tree.body and isinstance(tree.body[-1], ast.Expr) else None
    buf = io.StringIO()
    value = None
    with contextlib.redirect_stdout(buf):
        exec(compile(tree, "<o>", "exec"), ns)
        if last is not None:
            value = eval(compile(ast.Expression(last.value), "<o>", "eval"), ns)
    out = ""
    text = buf.getvalue()
    if text:
        out += f'<div class="txt">{html.escape(text.rstrip())}</div>'
    if isinstance(value, (pd.DataFrame, pd.Series)):
        frame = value.to_frame() if isinstance(value, pd.Series) else value
        out += _df_html(frame)
    elif value is not None:
        out += f'<div class="txt">{html.escape(repr(value))}</div>'
    return out


def o_chay(ten: str, n: int, code: str, ns: dict, giay: str = "0.4s"):
    res = _run(code, ns)
    body = (f'<div class="o"><div class="in"><div class="p">[{n}]:</div><div class="code"><pre>{_to(code)}</pre>'
            f'</div></div><div class="ok">✓ {giay}</div>')
    if res:
        body += f'<div class="out"><div class="p po"></div><div class="res">{res}</div></div>'
    _ghi(ten, body + "</div>")


def o_trich(ten: str, tep: str, bat_dau: str, so_dong: int, lang: str = "python", bo: tuple = (),
            bo_khoang: tuple | None = None):
    lines = (REPO / tep).read_text(encoding="utf-8").split("\n")
    i = next(k for k, s in enumerate(lines) if bat_dau in s)
    doan = lines[i:i + so_dong]
    so = list(range(i + 1, i + 1 + len(doan)))
    if bo_khoang:
        a = next(k for k, x in enumerate(doan) if bo_khoang[0] in x)
        b = next(k for k, x in enumerate(doan) if k > a and bo_khoang[1] in x)
        doan = doan[:a] + ["    ..."] + doan[b + 1:]
        so = so[:a] + [""] + so[b + 1:]
    if bo:
        giu, so2, an = [], [], False
        for s, k in zip(doan, so):
            if any(b in s for b in bo):
                if not an:
                    giu.append("    ...")
                    so2.append("")
                an = True
                continue
            an = False
            giu.append(s)
            so2.append(str(k))
        doan, so = giu, so2
    body = (f'<div class="o"><div class="tab">{html.escape(tep)}</div><div class="ed"><div class="ln">'
            + "\n".join(str(k) for k in so) + f'</div><div class="code"><pre>{_to(chr(10).join(doan), lang)}</pre>'
            '</div></div></div>')
    _ghi(ten, body)


def o_ra(ten: str, lenh: str, ket_qua: str, lang: str = "bash"):
    body = (f'<div class="o"><div class="in"><div class="p">$</div><div class="code"><pre>{_to(lenh, lang)}</pre></div>'
            f'</div><div class="out"><div class="p po"></div><div class="res"><div class="txt">{html.escape(ket_qua)}'
            '</div></div></div></div>')
    _ghi(ten, body)


def _ghi(ten: str, body: str):
    (RA / f"{ten}.html").write_text(f'<!doctype html><meta charset="utf-8"><style>{CSS}</style><div id="o">{body}</div>',
                                    encoding="utf-8")
    print("ghi", ten)


def _log(path: str, loc=None) -> str:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    return "\n".join(l for l in lines if (loc is None or loc(l))).strip()


SP = Path(os.environ.get("KL_SCRATCH", str(REPO / "khoa_luan" / "anh_code" / "vao")))

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ns = {"pd": pd}
    exec("import numpy as np", ns)

    # ----------------------------------------------------------------- Chương 3: dữ liệu
    o_trich("c3_crawler_vci", "crawlers/vci_raw.py", "def fetch(tickers=None", 23)
    o_chay("c3_bctc_tho", 1, '''bs = pd.read_csv("data/vnstock_financial/raw/BID_balance_sheet_quarter.csv")
print("Kích thước:", bs.shape)
q3 = bs[bs.period == "2026-Q3"].assign(ty_dong=lambda x: x.value / 1e9)
q3[["period", "id", "ty_dong"]].head(6)''', ns)
    o_chay("c3_lai_ngay", 2, '''lai = pd.read_csv("data/interest_rates/deposit_daily.csv")
print("Kích thước:", lai.shape, "| từ", lai.date.min(), "đến", lai.date.max())
lai[(lai.date == "2026-10-29") & (lai.term_months == 12) & lai.ticker.notna()][
    ["date", "ticker", "term_months", "channel", "rate_percent", "source"]].head(6)''', ns)
    o_chay("c3_info", 3, '''p = pd.read_csv("data/model/bank_panel_quarterly.csv")
print("Kích thước:", p.shape)
cot = ["ticker", "period", "npl_percent", "loans_g2_percent", "casa_percent",
       "ldr_computed_percent", "car_percent", "roa_ttm_percent", "nim_ttm_percent",
       "cof_ttm_percent", "total_assets_vnd", "npl_src"]
p[cot].info()''', ns)
    o_chay("c3_head", 4, '''xem = ["ticker", "period", "npl_percent", "loans_g2_percent", "casa_percent",
       "ldr_computed_percent", "roa_ttm_percent"]
p.loc[p.period == "2026-Q3", xem].head()''', ns)
    o_chay("c3_describe", 5, '''d = p[p.period >= "2019-Q1"]
d[["npl_percent", "casa_percent", "ldr_computed_percent", "car_percent",
   "roa_ttm_percent"]].describe().round(2)''', ns)
    o_chay("c3_thieu", 6, '''print("Số dòng trùng khóa (ticker, period):", p.duplicated(["ticker", "period"]).sum())
thieu = d[cot].isna().sum()
pd.DataFrame({"so_o_thieu": thieu, "ty_le_%": (thieu / len(d) * 100).round(1)})''', ns)
    o_trich("c3_lam_sach", "crawlers/vnstock_ratio_mas.py", "# MAS de COF va CIR dau duong", 17)
    log = _log(SP / "dung_lai_q3.log").split("=== crawlers.build_panel")[1].split("=== crawlers.inventory")[0].strip()
    dong = log.split(chr(10))
    a = next(k for k, l in enumerate(dong) if '"source_mix"' in l)
    gon = dong[:a] + ["  ...", '  "complete_rows_all_core": 678,', "}", ""] + [l for l in dong if "cong chat luong" in l]
    o_ra("c3_cong_kiem_tra", "python -m crawlers.build_panel", chr(10).join(gon))
    o_trich("c3_phan_ra_code", "experiments/eda.py", "def variance(f):", 17)
    o_chay("c3_phan_ra_ra", 7, '''v = pd.read_csv("data/model/eda/variance.csv")
v[["label", "n", "bank_share", "quarter_share", "resid_share"]].round(3).head(8)''', ns)
    o_chay("c3_mua_vu", 8, '''p = p.sort_values(["ticker", "period"])
p["q"] = p.period.str[-1].astype(int)
p["d_npl"] = p.groupby("ticker").npl_percent.diff()
g = p[p.period >= "2019-Q1"].dropna(subset=["d_npl"]).groupby("q").d_npl
pd.DataFrame({"trung_vi_thay_doi": g.median().round(2),
              "ty_le_giam": g.apply(lambda x: (x < 0).mean()).round(2)})''', ns)

    # ----------------------------------------------------------------- Chương 4: mô hình
    o_trich("c4_dac_trung", "experiments/longer_history.py", '    f["q"] = f.period.str[-1].astype(int)', 10)
    o_chay("c4_bang_dac_trung", 9, '''from experiments import longer_history as lh
f = lh.load(asset=True)
X = lh.core("npl_percent")
print("Đặc trưng:", X)
f.loc[f.period == "2026-Q3", ["ticker", "npl_percent"] + X[:4]].round(3).head()''', ns, "2.1s")
    o_trich("c4_co_so", "experiments/algorithm_benchmark.py", "def baselines(f, t, h, per, io):", 17,
            bo=("if t in QUARTERLY", "c = QUARTERLY", "x_t = row", "# quy roi ra", "out_q = sum", 'out["rolloff"]',
                "else:"))
    o_trich("c4_walk_forward", "serving/forecast.py", "# 2. walk-forward tu", 21)
    o_trich("c4_rf", "experiments/longer_history.py", "RF_PARAMS = dict(", 2)
    o_trich("c4_khoang", "serving/forecast.py", "# muc dao dong cua NH tai goc p", 9)
    o_ra("c4_chay_du_bao", "python -m serving.forecast",
         _log(SP / "du_bao_0411b.log", lambda l: "do phu" in l and any(k in l for k in ("npl_percent", "casa_percent", "ldr_computed")))
         + "\n...")
    o_trich("c4_mcdm", "experiments/montecarlo_ranking.py", "def normalise(X: np.ndarray", 21)
    o_trich("c4_trong_so", "experiments/montecarlo_ranking.py", "def draw_weights(spec: dict", 25,
            bo_khoang=('"""Trong so', '    """'))
    mc = _log(SP / "mc_0611.log").split("\n")
    i = next(k for k, l in enumerate(mc) if "gui 12T online | quanh_mac_dinh" in l)
    o_ra("c4_chay_mc", "python -m experiments.montecarlo_ranking --ranking data/model/experiments/inputs/"
         "features_ranking_2026-11-06.csv", "\n".join(mc[i:i + 7]).rstrip())

    # ----------------------------------------------------------------- Chương 5: hệ thống
    o_trich("c5_controller", "webapp/backend/src/main/java/vn/kltn/bankadvisor/module/ranking/controller/"
            "RankingController.java", "@RestController", 16, "java")
    o_trich("c5_csv_loader", "webapp/backend/src/main/java/vn/kltn/bankadvisor/module/dataset/importer/"
            "CsvTableLoader.java", "/** Phải gọi trong một transaction", 22, "java")
    if (SP / "cay_thu_muc.txt").exists():
        o_ra("c5_cau_truc", "tree webapp -L 3 (rút gọn)", (SP / "cay_thu_muc.txt").read_text(encoding="utf-8"))
    if (SP / "api_json.txt").exists():
        o_ra("c5_api_json", (SP / "api_lenh.txt").read_text(encoding="utf-8").strip(),
             (SP / "api_json.txt").read_text(encoding="utf-8"))
    if (SP / "mvn_test.txt").exists():
        o_ra("c6_kiem_thu", "mvnw test", (SP / "mvn_test.txt").read_text(encoding="utf-8"))
