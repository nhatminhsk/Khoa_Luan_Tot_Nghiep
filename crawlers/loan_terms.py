from __future__ import annotations

import re
import sys

import pandas as pd

PATH = "data/loan_rates/loan_terms.csv"
TICKERS = ["ACB", "BAB", "BID", "BVB", "CTG", "EIB", "HDB", "LPB", "MBB", "MSB", "NAB",
           "NVB", "OCB", "PGB", "SHB", "SSB", "STB", "TCB", "TPB", "VCB", "VIB", "VPB"]
TRUONG = {"phi_tra_truoc", "lai_co_so", "lai_tham_chieu", "bien_do", "lai_uu_dai", "thoi_gian_co_dinh_toi_da",
          "ty_le_cho_vay_toi_da", "thoi_han_toi_da", "bao_hiem_bat_buoc",
          "phi_tra_truoc_toi_thieu"}  # muc toi thieu bang dong (VIB chi cong bo muc nay, khong cong bo %)
MUC_NGUON = {"van_ban_goc", "trang_chinh_thuc", "hoi_truc_tiep", "bao_chi"}
NO_DATA = {"không công bố", "không tìm thấy"}
DATE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")
# Cot cua bang do phu: truong -> nhan
COVERAGE = {"phi_tra_truoc": "phí trả trước", "lai_co_so": "lãi cơ sở", "bien_do": "biên độ",
            "lai_uu_dai": "lãi ưu đãi", "ty_le_cho_vay_toi_da": "tỷ lệ cho vay", "thoi_han_toi_da": "thời hạn"}


def read(path: str = PATH) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df["muc_quang_cao"] = df["muc_quang_cao"].astype(int)
    df["so"] = pd.to_numeric(df["gia_tri"], errors="coerce")  # so neu gia_tri la so, NaN neu la chu/khoang
    df["het_han"] = (df["hieu_luc_den"] != "") & (df["hieu_luc_den"] < df["ngay_lay"])
    # Goi uu dai bat dau qua 12 thang ma khong ghi ngay ket thuc ("den khi co thong bao moi"): coi la cu.
    # Bieu phi / lai co so (goi trong) thi khong ap quy tac nay - van la ban dang dang tren web.
    year_ago = (pd.to_datetime(df["ngay_lay"]) - pd.DateOffset(months=12)).dt.strftime("%Y-%m-%d")
    df["cu"] = (df["goi"] != "") & (df["hieu_luc_den"] == "") & (df["hieu_luc_tu"] != "") & (df["hieu_luc_tu"] < year_ago)
    return df


def validate(df: pd.DataFrame) -> list[str]:
    errors = []
    for i, r in df.iterrows():
        where = f"dong {i + 2} ({r.ticker} {r.truong})"
        if r.ticker not in TICKERS:
            errors.append(f"{where}: ticker la")
        if r.truong not in TRUONG:
            errors.append(f"{where}: truong la '{r.truong}'")
        if r.muc_nguon not in MUC_NGUON:
            errors.append(f"{where}: muc_nguon la '{r.muc_nguon}'")
        for col in ("hieu_luc_tu", "hieu_luc_den", "ngay_lay"):
            if r[col] and not DATE.match(r[col]):
                errors.append(f"{where}: {col} '{r[col]}' khong dung dang YYYY-MM[-DD]")
        if r.hieu_luc_tu and r.hieu_luc_den and r.hieu_luc_den < r.hieu_luc_tu:
            errors.append(f"{where}: hieu_luc_den truoc hieu_luc_tu")
        if not r.url.startswith("http"):
            errors.append(f"{where}: thieu url nguon")
        if r.gia_tri in NO_DATA:
            continue
        if pd.isna(r.so) and r.truong in {"phi_tra_truoc", "lai_co_so", "bien_do", "ty_le_cho_vay_toi_da", "thoi_han_toi_da"} \
                and not re.match(r"^[\d.]+–[\d.]+$", r.gia_tri) and r.don_vi:
            errors.append(f"{where}: gia_tri '{r.gia_tri}' khong phai so")
        if r.truong in {"lai_co_so", "bien_do", "lai_uu_dai"} and r.so > 30:
            errors.append(f"{where}: lai {r.so}%/nam ngoai khoang hop ly")
    dup = df[df.duplicated(["ticker", "san_pham", "goi", "truong", "dieu_kien", "hieu_luc_tu"], keep=False)]
    errors += [f"trung khoa: {r.ticker} {r.goi} {r.truong} {r.dieu_kien}" for r in dup.itertuples()]
    return errors


def coverage(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df.san_pham.isin(["vay_mua_nha", "vay_khcn"])]
    out = pd.DataFrame(index=TICKERS, columns=list(COVERAGE.values()), dtype=object)
    for t in TICKERS:
        for field, label in COVERAGE.items():
            sub = df[(df.ticker == t) & (df.truong == field)]
            is_num = sub.gia_tri.str.match(r"^[\d.]")
            numeric = sub[is_num & ~sub.het_han & ~sub.cu]
            if len(numeric):
                out.loc[t, label] = "so*" if numeric.muc_quang_cao.astype(bool).all() else "so"
            elif (is_num & (sub.het_han | sub.cu)).any():
                out.loc[t, label] = "het han"
            elif len(sub):
                out.loc[t, label] = "khong"
            else:
                out.loc[t, label] = ""
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    data = read()
    problems = validate(data)
    print(f"{PATH}: {len(data)} dong, {data.ticker.nunique()}/22 NH; loi schema: {len(problems)}")
    for p in problems:
        print("  -", p)
    print("\nDo phu (so = co so con hieu luc; so* = chi co muc 'tu X%' khong ngay; het han = chi co goi da het;"
          " khong = NH khong cong bo / khong tim thay; trong = chua ghi nhan)")
    print(coverage(data).to_string())
