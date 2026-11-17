from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.parse
from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd

from crawlers import ocr_bctc as o

AUDIT_DIR = "data/bctc_pdf/audit_2021"
CATALOG = f"{AUDIT_DIR}/vietstock_documents_2021_2026.csv"
OUT = "data/credit/audit_npl_bctc_2021_2026.csv"
PANEL = "data/model/bank_panel_quarterly.csv"
TOL_NPL, TOL_G2 = 0.05, 0.10
o.ALT_DIR = f"{AUDIT_DIR}/files"  # dat o muc module: tien trinh con (spawn tren Windows) import lai file nay


def candidates(cat: pd.DataFrame, t: str, period: str) -> list[dict]:
    c = cat[(cat.ticker == t) & (cat.period == period) & cat.kind.isin(["quy", "6T"])].copy()
    if c.empty:
        return []
    c["rank"] = ((c.kind != "quy") * 2 + c.scope.map({"Hopnhat": 0, "": 1, "Congtyme": 3}).fillna(2)
                 + c.tags.fillna("").str.contains("DieuChinh") * 0.5)
    return c.sort_values(["rank", "file_id"], ascending=[True, False]).to_dict("records")


def _job(args):
    t, period, ref, cands = args
    y, q = int(period[:4]), int(period[-1])
    t0, best, tried = time.time(), None, []
    for c in cands:
        if best and best.get("loans_status") == "ok":
            break
        try:
            # danh muc 2021+ tra URL da ma hoa (%20); _fetch_doc tu quote lai -> giai ma truoc, khong thi 404
            path = o._fetch_doc(urllib.parse.unquote(c["url"]), f"{t}_{y}Q{q}_{c['file_id']}")
            if path is None:
                tried.append(f"{c['file']}: khong doc duoc")
                continue
            r = o.process(t, y, q, ref, path=path)
            r.update(file=c["file"], scope=c["scope"] or "-", kind=c["kind"])
            tried.append(f"{c['file']}: {r.get('loans_status')}")
            if best is None or o.L_RANK.get(r.get("loans_status"), 9) < o.L_RANK.get(best.get("loans_status"), 9):
                best = r
        except Exception as e:  # mot file hong khong lam dung o
            tried.append(f"{c['file']}: loi {type(e).__name__}: {e}"[:160])
    best = best or dict(ticker=t, period=period, loans_status="khong_co_file")
    best.update(tried=" | ".join(tried), seconds=round(time.time() - t0))
    return best


def compare(res: pd.DataFrame) -> pd.DataFrame:
    p = pd.read_csv(PANEL, encoding="utf-8-sig").set_index(["ticker", "period"])[["npl_percent", "loans_g2_percent"]]
    res = res.drop(columns=[c for c in res.columns if c.startswith(("panel_", "lech_")) or c == "ket_luan"])
    res = res.reindex(columns=list(dict.fromkeys([*res.columns, "npl_percent", "loans_g2_percent", "scope", "loans_status"])))
    r = res.set_index(["ticker", "period"]).join(p.add_prefix("panel_"))
    r["lech_npl"] = r.npl_percent - r.panel_npl_percent
    r["lech_g2"] = r.loans_g2_percent - r.panel_loans_g2_percent
    ok = r.loans_status.eq("ok")
    r["ket_luan"] = "chua_doc_duoc"
    # khop_chinh_xac: lech <= 0,001 diem; khop_duoi_nguong: con khac (thuong do mau so VCI khac BCTC, vd ACB 2021 ~0,9%)
    r.loc[ok, "ket_luan"] = "khop_duoi_nguong"
    r.loc[ok & (r.lech_npl.abs() <= 1e-3) & (r.lech_g2.abs() <= 1e-3), "ket_luan"] = "khop_chinh_xac"
    r.loc[ok & ((r.lech_npl.abs() > TOL_NPL) | (r.lech_g2.abs() > TOL_G2)), "ket_luan"] = "LECH"
    r.loc[ok & r.scope.eq("Congtyme"), "ket_luan"] += "_cong_ty_me"
    return r.reset_index()


def run(keys: list[tuple[str, str]], workers: int, resume: bool) -> pd.DataFrame:
    cat = pd.read_csv(CATALOG, encoding="utf-8-sig")
    vnd = pd.read_csv(o.VND, encoding="utf-8-sig").set_index(["ticker", "period"])
    res = []
    if resume and os.path.exists(OUT):
        res = pd.read_csv(OUT, encoding="utf-8-sig").to_dict("records")
    done = {(r["ticker"], r["period"]) for r in res if str(r.get("loans_status")) == "ok"}
    res = [r for r in res if (r["ticker"], r["period"]) in done]
    jobs = [(t, p, o._ref(vnd, t, p), candidates(cat, t, p)) for t, p in keys if (t, p) not in done]
    print(f"{len(jobs)} bao cao can chay, {len(done)} da co", flush=True)
    os.makedirs(o.ALT_DIR, exist_ok=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_job, j) for j in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            res.append(r)
            out = compare(pd.DataFrame(res)).sort_values(["ticker", "period"])
            o._save(out, OUT)
            row = out.set_index(["ticker", "period"]).loc[(r["ticker"], r["period"])]
            print(f"[{i}/{len(jobs)}] {r['ticker']} {r['period']}: {r.get('loans_status')} NPL {r.get('npl_percent')} "
                  f"(panel {row.panel_npl_percent}) nhom2 {r.get('loans_g2_percent')} (panel {row.panel_loans_g2_percent}) "
                  f"-> {row.ket_luan}, {r['seconds']}s | {r.get('tried', '')[:160]}", flush=True)
    return compare(pd.DataFrame(res))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", action="store_true")
    ap.add_argument("--sample")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    if a.catalog:
        os.makedirs(AUDIT_DIR, exist_ok=True)
        o.CATALOG = CATALOG
        o.catalog(years=range(2021, 2027))
        return
    if a.all:
        keys = [(t, f"{y}-Q{q}") for t in o.ALL_BANKS for y in range(2021, 2027) for q in (1, 2, 3, 4)
                if f"{y}-Q{q}" <= "2026-Q2"]
    else:
        s = pd.read_csv(a.sample, encoding="utf-8-sig")
        keys = list(dict.fromkeys(zip(s.ticker, s.period)))
    r = run(keys, a.workers, a.resume)
    print(r.ket_luan.value_counts().to_string())


if __name__ == "__main__":
    main()
