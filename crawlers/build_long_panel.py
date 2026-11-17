from __future__ import annotations

import re
import urllib.parse

import numpy as np
import pandas as pd

from crawlers import ocr_bctc

AQ = "data/credit/asset_quality_2012_2017.csv"
PANEL = "data/model/bank_panel_quarterly.csv"
OUT = "data/model/bank_panel_long_quarterly.csv"
# sap nhap hoan tat trong quy (chuoi NPL/CASA/LDR gay tai day)
EVENTS = {("SHB", "2012-Q3"): "sap nhap Habubank (08/2012)", ("HDB", "2013-Q4"): "sap nhap DaiABank (10/2013)",
          ("BID", "2015-Q2"): "sap nhap MHB (05/2015)", ("MSB", "2015-Q3"): "sap nhap MDB (08/2015)",
          ("STB", "2015-Q4"): "sap nhap Phuong Nam (10/2015)"}


def _kind_from_name(name: str) -> str:
    low = name.lower()
    if "kiemtoan" in low or re.search(r"_\d{4}(_kiemtoan)?(_hopnhat|_congtyme)?\.pdf$", low) and "_q" not in low:
        return "nam"
    if "_6t_" in low or "soatxet" in low:
        return "6T"
    return "quy"


def source_kinds() -> dict:
    kinds = {}
    inv = pd.read_csv(ocr_bctc.INVENTORY_ALL, encoding="utf-8-sig").fillna("")
    ex = pd.read_csv(ocr_bctc.EXTRA, encoding="utf-8-sig")
    for r in pd.concat([ex.sort_values("priority", ascending=False), inv[inv.url != ""]]).itertuples():
        name = f"{r.ticker}_{int(r.year)}Q{int(r.quarter)}.pdf"
        kinds[name] = _kind_from_name(urllib.parse.unquote(r.url).rsplit("/", 1)[-1])
    cat = pd.read_csv(ocr_bctc.CATALOG, encoding="utf-8-sig")
    by_id = dict(zip(cat.file_id.astype(str), cat.kind))
    by_file = dict(zip(cat.file, cat.kind))
    return {"_by_id": by_id, "_by_file": by_file, **kinds}


def _kind(src, kinds: dict) -> str:
    if src != src or not src:
        return ""
    name = str(src).split(":")[0]
    m = re.match(r"[A-Z]+_\d{4}Q\d_(\d+)\.(pdf|docx)$", name)
    if m:
        return {"6T": "6T", "nam": "nam", "9T": "quy"}.get(kinds["_by_id"].get(m.group(1), "quy"), "quy")
    if name in kinds:
        return kinds[name]
    if name in kinds["_by_file"]:
        return {"6T": "6T", "nam": "nam"}.get(kinds["_by_file"][name], "quy")
    return _kind_from_name(name)


def build() -> pd.DataFrame:
    kinds = source_kinds()
    a = pd.read_csv(AQ, encoding="utf-8-sig")
    old = pd.DataFrame({
        "ticker": a.ticker, "period": a.period,
        "npl_percent": a.npl_percent, "loans_g2_percent": a.loans_g2_percent, "casa_percent": a.casa_percent,
        "ldr_computed_percent": a.ldr_net_percent,
        "src_npl": np.where(a.npl_percent.notna(), "ocr_bctc", ""), "src_casa": np.where(a.casa_percent.notna(), "ocr_bctc", ""),
        "src_ldr": np.where(a.ldr_net_percent.notna(), "vndirect", ""),
        "scope_npl": a.npl_scope.fillna(""), "scope_casa": a.casa_scope.fillna(""),
        "kind_npl": [_kind(s, kinds) for s in a.npl_src], "kind_casa": [_kind(s, kinds) for s in a.casa_src],
        "lech_nguon": np.where(a.npl_flag.eq("lech_nguon") | a.casa_flag.eq("lech_nguon"), "x", ""),
        "file_npl": a.npl_src.fillna(""), "file_casa": a.casa_src.fillna(""),
    })
    p = pd.read_csv(PANEL, encoding="utf-8-sig")
    new = pd.DataFrame({
        "ticker": p.ticker, "period": p.period,
        "npl_percent": p.npl_percent, "loans_g2_percent": p.loans_g2_percent, "casa_percent": p.casa_percent,
        "ldr_computed_percent": p.ldr_computed_percent,
        "src_npl": np.where(p.npl_percent.notna(), "vci", ""), "src_casa": np.where(p.casa_percent.notna(), "vci", ""),
        "src_ldr": np.where(p.ldr_computed_percent.notna(), "vci", ""),
        "scope_npl": "Hopnhat", "scope_casa": "Hopnhat", "kind_npl": "vci", "kind_casa": "vci", "lech_nguon": "",
        "file_npl": "", "file_casa": "",
    })
    f = pd.concat([old[old.period < "2018-Q1"], new], ignore_index=True)
    per = sorted(f.period.unique())
    grid = pd.MultiIndex.from_product([sorted(f.ticker.unique()), per], names=["ticker", "period"]).to_frame(index=False)
    f = grid.merge(f, on=["ticker", "period"], how="left")
    f["su_kien"] = [EVENTS.get(k, "") for k in zip(f.ticker, f.period)]
    for c in ("npl_percent", "loans_g2_percent", "casa_percent", "ldr_computed_percent"):
        f[c] = pd.to_numeric(f[c], errors="coerce").round(4)
    return f.sort_values(["ticker", "period"]).reset_index(drop=True)


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    f = build()
    f.to_csv(OUT, index=False, encoding="utf-8-sig")
    pre = f[f.period < "2018-Q1"]
    print(f"-> {OUT}: {f.ticker.nunique()} NH x {f.period.nunique()} quy ({f.period.min()}..{f.period.max()})")
    for c in ("npl_percent", "casa_percent", "ldr_computed_percent"):
        print(f"   {c}: 2012-2017 {pre[c].notna().sum()}/{len(pre)} o, ca chuoi {f[c].notna().sum()}/{len(f)}")
    print("   loai bao cao 2012-2017 (NPL):", pre.kind_npl.replace("", "-").value_counts().to_dict())
    print("   pham vi 2012-2017 (NPL):", pre.loc[pre.npl_percent.notna(), "scope_npl"].replace("", "mot ban").value_counts().to_dict())


if __name__ == "__main__":
    main()
