"""Du no cho vay khach hang theo nganh nghe kinh doanh -- 22 NH, cuoi nam 2018-2025.

Nguon: bang "Phan tich du no cho vay theo nganh" trong thuyet minh BCTC hop nhat
kiem toan (mau B05/TCTD-HN). vnstock KHONG dung duoc cho bang nay: cac dong nganh
cua VCI cong lai vuot tong 10-93% (mot khoan bi xep vao hai nhom trung nhau) va rong
o phan lon NH truoc 2024.

Cach lam (14/09/2026): tai 81 file BCTC tu static2.vietstock.vn, OCR (Windows OCR) de
dinh vi trang, doc bang tren anh va chep vao data/credit/loans_by_industry_manual/*.txt
theo dang `key|kind|label|grp|v0|v1`:
    key    TICKER_NAMBCTC
    kind   I = dong nganh, S = tong phu (khong cong), T = tong bang
    label  ten dong dung nhu BCTC ghi
    grp    ma nhom: A..U theo VSIC 2018, hoac nhom gop/dac thu (xem GROUP_NAME)
    v0     cot "So cuoi nam" (nam BCTC), v1 cot "So dau nam" (nam truoc); dau cham ngan cach
Kiem: tong cac dong I = dong T o CA HAI cot (81/81 bang khop tuyet doi) va dong T
so voi tong du no theo nhom no cua API (note_long.csv).

Nhap them (33 NH-nam con thieu, BCTC khong co tren Vietstock): mo
data/credit/loans_by_industry_manual/fill_template.xlsx, huong dan o sheet huong_dan.
Chi bang co "Trạng thái" = "đã nhập" duoc nap; nhap sai (tong lech, thieu link/trang,
ma nhom la, trung bang da co) thi script dung va liet ke loi.

Ket qua:
    data/credit/loans_by_industry_annual.csv        1 ban/NH-nam (uu tien BCTC cung nam)
    data/credit/loans_by_industry_all_versions.csv  ca hai cot cua moi BCTC (de xem so trinh bay lai)
    data/credit/loans_by_industry_group_wide.csv    ty trong % theo ma nhom, dang rong

BAY KHI DUNG:
  - Moi NH phan nganh mot kieu. ACB, VCB co dong "Cac nganh khac" chiem 60-65%; BID tu
    2022 chi con 7 nhom; VIB 2018-2021 chi 5 nhom; MSB va VPB (2022+) dung danh muc rieng
    "mot so nganh kinh te"; EIB 2025 la bang "theo muc dich su dung von".
  - TCB tach "Cho vay ca nhan" khong phan nganh; TCB 2023+, MBB, VPB, TPB 2025 co dong
    cho vay ky quy/ung truoc (MARGIN); MBB co dong chi nhanh nuoc ngoai (FOREIGN_BRANCH).
  - So sanh giua NH chi on o nhom A (nong nghiep), F, L va nhom lon; cac nhom nho phu thuoc
    cach phan loai cua tung NH.

Chay:
    python -m crawlers.loans_by_industry
    python -m crawlers.loans_by_industry --validate
"""
from __future__ import annotations

import glob
import unicodedata
from pathlib import Path

import pandas as pd

MANUAL = Path("data/credit/loans_by_industry_manual")
FILL = MANUAL / "fill_template.xlsx"
FILLED = "đã nhập"
OUT_PRIMARY = Path("data/credit/loans_by_industry_annual.csv")
OUT_ALL = Path("data/credit/loans_by_industry_all_versions.csv")
OUT_WIDE = Path("data/credit/loans_by_industry_group_wide.csv")
NOTE_LONG = Path("data/vnstock_financial/note_long.csv")
YEARS = range(2018, 2026)

# Cot "So dau nam" ghi ro "Trinh bay lai" trong BCTC.
RESTATED_PRIOR = {"CTG_2023", "SHB_2025", "VPB_2025"}
TABLE_NOTE = {
    "EIB_2025": "Bảng 'theo mục đích sử dụng vốn'",
    "MSB_2020": "Danh mục ngành riêng của MSB", "MSB_2021": "Danh mục ngành riêng của MSB",
    "MSB_2023": "Danh mục ngành riêng của MSB", "MSB_2025": "Danh mục ngành riêng của MSB",
    "VPB_2022": "Bảng 'theo một số ngành kinh tế của khách hàng'",
    "VPB_2024": "Bảng 'theo một số ngành kinh tế của khách hàng'",
    "VPB_2025": "Bảng 'theo một số ngành kinh tế của khách hàng'",
    "HDB_2025": "Có khối nghiệp vụ thư tín dụng trả chậm trước 01/7/2024 (chỉ năm 2024)",
}

GROUP_NAME = {
    "A": "Nông, lâm nghiệp và thủy sản", "B": "Khai khoáng", "C": "Công nghiệp chế biến, chế tạo",
    "D": "Điện, khí đốt, nước nóng, điều hòa", "E": "Cấp nước, xử lý rác thải", "F": "Xây dựng",
    "G": "Bán buôn, bán lẻ; sửa chữa xe", "H": "Vận tải, kho bãi", "I": "Lưu trú và ăn uống",
    "J": "Thông tin và truyền thông", "K": "Tài chính, ngân hàng, bảo hiểm", "L": "Kinh doanh bất động sản",
    "M": "Chuyên môn, khoa học, công nghệ", "N": "Hành chính và dịch vụ hỗ trợ",
    "O": "Đảng, quản lý nhà nước, an ninh quốc phòng", "P": "Giáo dục và đào tạo",
    "Q": "Y tế và trợ giúp xã hội", "R": "Nghệ thuật, vui chơi, giải trí", "S": "Dịch vụ khác",
    "T": "Hộ gia đình (làm thuê, tự sản xuất tiêu dùng)", "U": "Tổ chức quốc tế",
    "DE": "Điện, khí đốt và nước (gộp D+E)", "FL": "Xây dựng và bất động sản (gộp F+L)",
    "GC": "Thương mại, sản xuất và chế biến (gộp G+C)", "GS": "Thương mại, dịch vụ (gộp G+S)",
    "HJ": "Vận tải, kho bãi và thông tin liên lạc (gộp H+J)", "IR": "Khách sạn, du lịch, vui chơi (gộp I+R)",
    "LM": "Bất động sản và tư vấn (gộp L+M)", "SERV": "Dịch vụ (nhóm gộp, không rõ phạm vi)",
    "INDIV": "Cho vay cá nhân (không phân ngành)", "INDIV_HOUSING": "Cho vay cá nhân mua/xây nhà ở",
    "INDIV_OTHER": "Cá nhân và các ngành khác (gộp)", "MARGIN": "Cho vay ký quỹ, ứng trước cho khách hàng",
    "FOREIGN_BRANCH": "Dư nợ tại chi nhánh/ngân hàng con nước ngoài", "OTHER": "Các ngành khác / không phân loại",
}


def _num(s: str) -> float:
    s = str(s).strip()
    if s in ("", "-"):
        return 0.0
    neg = s.startswith("(")
    v = float(s.strip("()").replace(".", "").replace(",", ""))
    return -v if neg else v


def load_manual() -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(str(MANUAL / "batch*.txt"))):
        for i, line in enumerate(open(f, encoding="utf-8")):
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) != 6:
                raise ValueError(f"{f}:{i + 1} can 6 cot, gap {len(parts)}: {line}")
            key, kind, label, grp, v0, v1 = parts
            rows.append(dict(key=key, kind=kind, label=label, grp=grp, v0=_num(v0), v1=_num(v1), line=i))
    df = pd.DataFrame(rows)
    bad = set(df.loc[df.kind == "I", "grp"]) - set(GROUP_NAME)
    if bad:
        raise ValueError(f"ma nhom khong co trong GROUP_NAME: {bad}")
    fill, _ = load_fill()
    clash = sorted(set(fill.key) & set(df.key)) if len(fill) else []
    if clash:
        raise ValueError(f"{FILL}: ma bang da co trong batch*.txt: {clash}")
    return pd.concat([df, fill], ignore_index=True) if len(fill) else df


def _cell_num(v) -> float:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    return _num(v)


def load_fill(path: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bang 'da nhap' trong fill_template.xlsx -> (dong dang batch, nguon dang sources.csv)."""
    path = path or FILL
    if not path.exists():
        return pd.DataFrame(), pd.DataFrame()
    bang = pd.read_excel(path, sheet_name="bang", dtype=object)
    dong = pd.read_excel(path, sheet_name="dong", dtype=object)
    bang = bang[bang["Mã bảng"].notna()].copy()
    bang["Mã bảng"] = bang["Mã bảng"].astype(str).str.strip()
    bang["Trạng thái"] = bang["Trạng thái"].map(lambda s: unicodedata.normalize("NFC", str(s)).strip().lower())
    keys = set(bang["Mã bảng"])
    errors = []
    stray = set(dong.loc[dong[["Số cuối năm", "Số đầu năm"]].notna().any(axis=1), "Mã bảng"].dropna().astype(str)) - keys
    errors += [f"sheet dong: ma bang {k} co so nhung khong co trong sheet bang" for k in sorted(stray)]
    dup = bang["Mã bảng"][bang["Mã bảng"].duplicated()]
    errors += [f"sheet bang: ma bang {k} lap lai" for k in dup]

    rows, src = [], []
    for b in bang[bang["Trạng thái"] == FILLED].to_dict("records"):
        key = str(b["Mã bảng"]).strip()
        ticker, _, fy = key.partition("_")
        if len(ticker) != 3 or not fy.isdigit():
            errors.append(f"{key}: ma bang phai dang TICKER_NAM, vd LPB_2019")
            continue
        url, page = b["Link BCTC"], b["Trang PDF"]
        if pd.isna(url) or not str(url).strip().startswith("http"):
            errors.append(f"{key}: thieu Link BCTC")
        if pd.isna(page) or not str(page).replace(".0", "").isdigit():
            errors.append(f"{key}: thieu Trang PDF (so nguyen)")
        t = dong[dong["Mã bảng"].astype(str).str.strip() == key]
        # Dong goi y de trong ca hai o so = BCTC khong co dong nay -> bo qua. So 0 phai go 0.
        t = t[t[["Số cuối năm", "Số đầu năm"]].notna().any(axis=1)]
        before = len(errors)
        parsed = []
        for n, r in enumerate(t.to_dict("records"), start=1):
            kind = str(r["Loại"]).strip() if pd.notna(r["Loại"]) else ""
            label = str(r["Tên dòng trong BCTC"]).strip() if pd.notna(r["Tên dòng trong BCTC"]) else ""
            grp = str(r["Mã nhóm"]).strip() if pd.notna(r["Mã nhóm"]) else ""
            if kind not in ("I", "S", "T"):
                errors.append(f"{key} dong {n} '{label}': Loai phai la I, S hoac T")
                continue
            if kind == "I" and grp not in GROUP_NAME:
                errors.append(f"{key} dong {n} '{label}': ma nhom '{grp}' khong co trong sheet nhom")
            if not label:
                errors.append(f"{key} dong {n}: thieu ten dong")
            try:
                v0, v1 = _cell_num(r["Số cuối năm"]), _cell_num(r["Số đầu năm"])
            except ValueError:
                errors.append(f"{key} dong {n} '{label}': so khong doc duoc ({r['Số cuối năm']} / {r['Số đầu năm']})")
                continue
            parsed.append(dict(key=key, kind=kind, label=label, grp="TOTAL" if kind == "T" else grp,
                               v0=v0, v1=v1, line=n))
        if len(errors) > before:
            continue
        p = pd.DataFrame(parsed)
        tot = p[p.kind == "T"] if len(p) else p
        if len(tot) != 1:
            errors.append(f"{key}: can dung 1 dong Loai T, gap {len(tot)}")
            continue
        items = p[p.kind == "I"]
        for col, name in (("v0", "cuoi nam"), ("v1", "dau nam")):
            total = tot[col].iloc[0]
            if total <= 0:
                errors.append(f"{key}: dong T cot {name} trong hoac bang 0")
            elif abs(items[col].sum() - total) > 2:
                errors.append(f"{key}: cot {name} tong dong I {items[col].sum():,.0f} != dong T {total:,.0f}")
            elif total < 1e6:
                errors.append(f"{key}: tong {total:,.0f} qua nho -- BCTC ghi ty dong? nhap theo trieu dong")
        rows += parsed
        src.append(dict(key=key, ticker=ticker, fs_year=int(fy), fs_url=str(url).strip(),
                        pdf_page=int(float(page)) if pd.notna(page) else None,
                        note="" if pd.isna(b["Ghi chú"]) else str(b["Ghi chú"])))
    if errors:
        raise ValueError(f"{path}: {len(errors)} loi nhap\n  " + "\n  ".join(errors))
    return pd.DataFrame(rows), pd.DataFrame(src)


def fill_status(path: Path | None = None) -> dict:
    path = path or FILL
    if not path.exists():
        return {}
    bang = pd.read_excel(path, sheet_name="bang", dtype=object)
    return bang.loc[bang["Mã bảng"].notna(), "Trạng thái"].fillna("(trong)").value_counts().to_dict()


def _sources() -> pd.DataFrame:
    src = pd.read_csv(MANUAL / "sources.csv", encoding="utf-8-sig")
    _, fill = load_fill()
    return (pd.concat([src, fill], ignore_index=True) if len(fill) else src).set_index("key")


def _api_totals() -> dict:
    if not NOTE_LONG.exists():
        return {}
    n = pd.read_csv(NOTE_LONG, encoding="utf-8-sig", dtype={"period": str}, usecols=["ticker", "period", "id", "value"])
    g = n[(n.id == "NT_BS_LOANS_AND_ADVANCES_BY_GRADING") & n.period.str.endswith("Q4")]
    return {(r.ticker, int(r.period[:4])): r.value / 1e6 for r in g.itertuples() if pd.notna(r.value)}


def _versions(m: pd.DataFrame) -> pd.DataFrame:
    src = _sources()
    api = _api_totals()
    out = []
    for key, t in m.groupby("key", sort=False):
        ticker, fy = key.split("_")
        fy = int(fy)
        tot = t[t.kind == "T"]
        if len(tot) != 1:
            raise ValueError(f"{key}: can dung 1 dong T, gap {len(tot)}")
        unit = 1e6 if tot.v0.iloc[0] > 1e12 else 1.0  # OCB ghi don vi dong
        items = t[t.kind == "I"]
        note = TABLE_NOTE.get(key) or src.loc[key].get("note")
        note = note if isinstance(note, str) else ""
        for col, year, column in (("v0", fy, "Số cuối năm"), ("v1", fy - 1, "Số đầu năm")):
            total = tot[col].iloc[0] / unit
            gap = items[col].sum() / unit - total
            a = api.get((ticker, year))
            for order, r in enumerate(items.itertuples(), start=1):
                out.append(dict(
                    ticker=ticker, year=year, as_of_date=f"{year}-12-31", row_order=order,
                    industry_label=r.label, industry_group=r.grp, industry_group_name=GROUP_NAME[r.grp],
                    value_mn_vnd=round(getattr(r, col) / unit, 3), table_total_mn_vnd=round(total, 3),
                    share_pct=round(100 * getattr(r, col) / unit / total, 4) if total else None,
                    source_fs_year=fy, source_column=column,
                    restated=(col == "v1" and key in RESTATED_PRIOR),
                    fs_url=src.loc[key, "fs_url"], pdf_page=int(src.loc[key, "pdf_page"]),
                    sum_check_gap_mn_vnd=round(gap, 3), api_total_ratio=round(total / a, 5) if a else None,
                    table_note=note,
                ))
    return pd.DataFrame(out)


def build() -> dict:
    m = load_manual()
    allv = _versions(m)
    allv = allv[allv.year.isin(YEARS)]
    # Uu tien: BCTC cung nam (cot cuoi nam); khong co thi lay cot dau nam cua BCTC nam sau.
    allv["priority"] = (allv.source_column != "Số cuối năm").astype(int)
    best = (allv.groupby(["ticker", "year"]).priority.min().rename("best").reset_index())
    prim = allv.merge(best, on=["ticker", "year"])
    prim = prim[prim.priority == prim.best].drop(columns=["priority", "best"])
    allv = allv.drop(columns=["priority"])

    wide = (prim.groupby(["ticker", "year", "industry_group"]).value_mn_vnd.sum().unstack("industry_group"))
    totals = prim.groupby(["ticker", "year"]).table_total_mn_vnd.first()
    wide = wide.div(totals, axis=0).mul(100).round(4).add_prefix("share_pct_")
    wide.insert(0, "table_total_mn_vnd", totals)
    wide = wide.reset_index()

    OUT_PRIMARY.parent.mkdir(parents=True, exist_ok=True)
    prim.to_csv(OUT_PRIMARY, index=False, encoding="utf-8-sig")
    allv.to_csv(OUT_ALL, index=False, encoding="utf-8-sig")
    wide.to_csv(OUT_WIDE, index=False, encoding="utf-8-sig")
    return {"tables": int(m.key.nunique()), "rows_primary": len(prim), **validate()}


def validate() -> dict:
    prim = pd.read_csv(OUT_PRIMARY, encoding="utf-8-sig")
    allv = pd.read_csv(OUT_ALL, encoding="utf-8-sig")
    tickers = ["ACB", "BAB", "BID", "BVB", "CTG", "EIB", "HDB", "LPB", "MBB", "MSB", "NAB",
               "NVB", "OCB", "PGB", "SHB", "SSB", "STB", "TCB", "TPB", "VCB", "VIB", "VPB"]
    have = set(zip(prim.ticker, prim.year))
    missing = {t: [y for y in YEARS if (t, y) not in have] for t in tickers}
    sums = allv.groupby(["ticker", "year", "source_fs_year"]).sum_check_gap_mn_vnd.first().abs()
    api = prim.groupby(["ticker", "year"]).api_total_ratio.first().dropna()
    return {
        "bank_years": f"{len(have)}/{len(tickers) * len(YEARS)}",
        "missing": {t: v for t, v in missing.items() if v},
        "sum_check_max_gap_mn_vnd": float(sums.max()),
        "sum_check_fail_versions": int((sums > 2).sum()),
        "api_ratio_outside_0.5pct": {f"{t}_{y}": v for (t, y), v in api[(api - 1).abs() > 0.005].items()},
        "restated_versions_used": int(prim.restated.sum()),
        "fill_template_status": fill_status(),
    }


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        out = validate() if "--validate" in sys.argv else build()
    except ValueError as e:
        print(e)
        sys.exit(1)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
