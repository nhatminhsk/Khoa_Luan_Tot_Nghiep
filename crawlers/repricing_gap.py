"""Khe ho dinh lai lai suat (repricing gap) theo tung ngan hang -- NHAP TAY tu PDF.

Day la bien dai dien cho chu S (Sensitivity to market risk) cua CAMELS. Khong
nguon API nao co so nay: trong Finance.note() cua VCI, hai dong "Tai san sinh
lai" va "Cong no phai tra lai" rong 0/748 o. So chi co trong thuyet minh "Rui ro
lai suat" cua BCTC kiem toan (nam) va soat xet (ban nien), o dong cuoi bang:

    "Muc chenh nhay cam voi lai suat noi bang"

Moi o tren dong do = tong tai san - tong no phai tra CUA COT KY HAN DO.

DON VI KY LA QUY ('2026-Q1' = chot 31/03/2026), cung khoa voi panel. Bang nay
chac chan co o BCTC nam (Q4) va thuong co o BCTC ban nien (Q2). BCTC quy: ACB CO
in bang trong thuyet minh chon loc quy I/2026 (mau B05a/TCTD-HN); cac NH khac chua
kiem. NH nao khong in bang trong ky do thi
de trong o so va dat nguon=khong_cong_bo: check() tach rieng nhom nay, khong bao
"con thieu" mai. File cu ghi '2025-H2' van doc duoc -- _read() doi H1->Q2, H2->Q4.

LAY COT NAO
  - 6 cot ky han: duoi 1 thang, 1-3T, 3-6T, 6-12T, 1-5 nam, tren 5 nam.
  - Cot "Qua han" va "Khong nhay cam lai suat" KHONG dinh lai lai suat nen khong
    vao khe ho. Van nen nhap de doi chieu tong, xem check().
  - O "Tong cong" = tong tai san - tong no phai tra, xap xi von chu so huu. KHONG
    phai khe ho lai suat, chi dung de doi chieu.
  - BAY DA GAP: mot so NH (ACB) in them hai dong ngay duoi -- "Cac cam ket ngoai
    bang ..." va "Muc chenh nhay cam voi lai suat NOI, NGOAI BANG". KHONG lay dong
    noi ngoai bang: TCB chi in noi bang, nen phai lay noi bang moi so ngang duoc
    giua cac NH. Lay nham thi doi chieu 1 van khop (dong do tu can) nhung doi chieu
    2 lech dung bang tong cam ket ngoai bang (ACB 2026-Q1: +43.037).

MAU SO LA TONG TAI SAN CUA CHINH BANG NAY, khong lay tu bang can doi. Bang
thuyet minh ghi "(*) Khong bao gom cac khoan du phong" nen tong tai san cao hon
bang can doi (TCB 31/12/2025: 1.203.452 ty vs 1.192.344 ty). Tu so va mau so
phai cung mot co so.

CHI SO TINH RA -- ratios()
  gap_12t_percent          khe ho TICH LUY den 12 thang / tong tai san.
                           > 0: tai san dinh lai nhanh hon no, lai suat tang thi
                           thu nhap lai thuan tang; < 0 thi nguoc lai.
  gap_12t_abs_percent      tri tuyet doi. Dung lam tieu chi CHI PHI trong TOPSIS vi
                           ca hai chieu deu la rui ro: am lon thiet khi lai suat
                           tang, duong lon thiet khi lai suat giam.
  gap_max_abs_12t_percent  |tich luy| lon nhat tai cac moc 1/3/6/12 thang. DE XUAT
                           RIENG cua du an, khong phai thuoc do chuan: bat duoc cho
                           lech ma so 12 thang che mat. TCB 31/12/2025: 12 thang chi
                           +1,69%, nhung tich luy 1 thang +7,38% va 6 thang -3,51%
                           -> chi so nay = 7,38.
  delta_nii_1pp            thu nhap lai thuan doi bao nhieu/nam khi lai suat tang
                           1 diem % = gap 12 thang x 1%. Xap xi bac mot, gia dinh
                           moi ky han dich cung muc. Cung don vi voi bang.

FILE LA BANG CONG VIEC, KHONG CHI LA KET QUA. Khung day du 22 NH x moi ky; o chua
co so thi de TRONG chu khong bo dong. Giu so nhap tay theo tung O, cung tinh than
car.py va loan_rates.py:
    - o file cu co gia tri          -> giu nguyen, code KHONG BAO GIO ghi de
    - o file cu trong, DISCLOSED co -> dien vao
    - ca hai co so va LECH nhau     -> bao conflict, van giu file cu
Muon bo mot so trong DISCLOSED thi sua DISCLOSED, xoa o trong CSV khong du vi lan
chay sau code se dien lai.

NHAP SO: dan thang dang in trong PDF cung duoc -- "88.862.676", "(99.974.325)"
(ngoac = so am), "-" (= 0). Nhap nguyen so trong bang, thuong la trieu dong. File
luu bang dau ";" (Excel tieng Viet) hay "," deu doc duoc; write() chuan hoa lai ve
so nguyen va dau ",".

HAI PHEP DOI CHIEU BAT LOI GO -- check()
  1. tong 8 cot khe ho (ke ca qua han, khong nhay cam) == o tong cong
  2. tong tai san - tong no phai tra == o tong cong
Bang TCB 31/12/2025 khop tuyet doi ca hai. Bang in so da lam tron nen cho lech toi
TOL don vi.

Chay (tu thu muc goc D:\\KLTN):
    python -m crawlers.repricing_gap                     # dung khung + ghi CSV + kiem
    python -m crawlers.repricing_gap --check             # chi kiem, thoat ma 1 neu co loi
    python -m crawlers.repricing_gap --ratios            # bang ty le, moi ky
    python -m crawlers.repricing_gap --ratios 2025-Q4    # mot ky
    python -m crawlers.repricing_gap --them-ky 2024-Q4   # them 22 dong cho mot ky
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("data/credit")
MASTER = OUT / "bank_repricing_gap.csv"
VNSTOCK = OUT / "bank_credit_quarterly.csv"

# Ky mac dinh cua khung. TOPSIS xep hang tai MOT thoi diem (2025-Q4, BCTC nam da
# kiem toan); hai quy 2026 de cap nhat khi co bang moi hon. Them ky bang
# --them-ky; ky da co trong file luon duoc giu.
PERIODS = ["2025-Q4", "2026-Q1", "2026-Q2"]
QUARTER_END = {"Q1": "03-31", "Q2": "06-30", "Q3": "09-30", "Q4": "12-31"}
_HALF_TO_Q = {"H1": "Q2", "H2": "Q4"}

BUCKETS_12T = ["gap_duoi_1t", "gap_1_3t", "gap_3_6t", "gap_6_12t"]
BUCKETS = BUCKETS_12T + ["gap_1_5n", "gap_tren_5n"]
ALL_GAPS = ["gap_qua_han", "gap_khong_nhay_cam"] + BUCKETS
NUM_COLS = ALL_GAPS + ["gap_tong_cong", "tong_tai_san", "tong_no_phai_tra"]
TEXT_COLS = ["as_of_date", "co_so", "thuyet_minh", "trang", "nguon",
             "do_tin_cay", "source_url", "note", "ngay_nhap"]
COLUMNS = ["ticker", "period", "as_of_date", "co_so"] + NUM_COLS + [
    "thuyet_minh", "trang", "nguon", "do_tin_cay", "source_url", "note", "ngay_nhap"]
KEYS = ["ticker", "period"]

CO_SO = {"hop_nhat", "rieng_le"}
TOL = 3  # don vi cua bang; bang in so da lam tron

# ---------------------------------------------------------------------------
# So chep tu ban goc. Cot so theo dung dau trong bang: so trong ngoac la AM.
#
# do_tin_cay:
#   cao = so doc ro, hai phep doi chieu khop, co source_url + trang
#   tb  = so doc dung nhung con thieu nguon hoac co_so la suy luan
#         -> kiem lai truoc khi trich luan van
# ---------------------------------------------------------------------------
DISCLOSED: list[dict] = [
    {
        "ticker": "TCB", "period": "2025-Q4", "co_so": "hop_nhat",
        "gap_qua_han": 2_255_548, "gap_khong_nhay_cam": 128_496_739,
        "gap_duoi_1t": 88_862_676, "gap_1_3t": -99_974_325, "gap_3_6t": -31_188_035,
        "gap_6_12t": 62_653_580, "gap_1_5n": 5_358_449, "gap_tren_5n": 34_144_640,
        "gap_tong_cong": 190_609_272,
        "tong_tai_san": 1_203_451_967, "tong_no_phai_tra": 1_012_842_695,
        "thuyet_minh": "45.1", "trang": "", "nguon": "nhap_tay", "do_tin_cay": "tb",
        "source_url": "",
        "note": "Chep tu anh chup thuyet minh 45.1 'Rui ro lai suat' nguoi dung gui "
                "11/09/2026; hai phep doi chieu khop tuyet doi. co_so=hop_nhat la SUY "
                "LUAN: tien gui KH 618.911.535 khop tuyet doi panel TCB 2025-Q4 (VCI "
                "dung so hop nhat) va bang co dong cho vay ky quy chung khoan. Thieu "
                "source_url va so trang -- bo sung truoc khi trich luan van.",
        "ngay_nhap": "2026-09-11",
    },
]


# ---------------------------------------------------------------------------
# Doc / ghi
# ---------------------------------------------------------------------------
_DASHES = {"-", "\u2013", "\u2014"}


def _to_number(x):
    """Doc mot o so theo dang in trong PDF hoac dang Excel/pandas ghi ra.

    "88.862.676" -> 88862676 · "(99.974.325)" -> -99974325 · "-" -> 0 · "" -> NA
    "-99974325" -> -99974325 · "1203451967.0" -> 1203451967

    Bang thuyet minh chi co SO NGUYEN, nen "." va "," o day la dau phan nhom hang
    nghin. Ngoai le duy nhat: duoi thap phan KHONG dung 3 chu so ("4360.0") -- dang
    do pandas/Excel ghi ra, doc nhu so thuc. Phan thap phan khac 0 thi bao loi
    thay vi doan.
    """
    if x is None or x is pd.NA or (isinstance(x, float) and np.isnan(x)):
        return pd.NA
    if isinstance(x, (int, np.integer)):
        return int(x)
    s = str(x).strip().replace("\xa0", "").replace(" ", "")
    if s == "" or s.lower() == "nan":
        return pd.NA
    if s in _DASHES:
        return 0
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg, s = True, s[1:-1]
    if s[:1] in ("-", "\u2212"):
        neg, s = True, s[1:]
    m = re.fullmatch(r"(\d+)[.,](\d{1,2}|\d{4,})", s)
    if m:
        v = float(f"{m.group(1)}.{m.group(2)}")
        if v != int(v):
            raise ValueError(f"co phan thap phan {x!r} -- bang thuyet minh chi co so nguyen")
        v = int(v)
    else:
        digits = s.replace(".", "").replace(",", "")
        if not digits.isdigit():
            raise ValueError(f"khong doc duoc so {x!r}")
        v = int(digits)
    return -v if neg else v


def _read(path: Path | None = None) -> pd.DataFrame:
    """Doc file cong viec, chap nhan dau ";" hoac "," va so dang PDF."""
    path = path or MASTER
    with open(path, encoding="utf-8-sig") as f:
        header = f.readline()
    sep = ";" if header.count(";") > header.count(",") else ","
    df = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]

    extra = [c for c in df.columns if c not in COLUMNS]
    if extra:
        print(f"  !! bo qua cot la trong {path}: {extra}")
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS].copy()
    df["ticker"] = df["ticker"].str.strip().str.upper()
    df["period"] = df["period"].str.strip().str.upper()
    df = df[(df["ticker"] != "") & (df["period"] != "")].copy()  # dong trang Excel de lai
    df["period"] = df["period"].map(norm_period)
    dup = df[df.duplicated(KEYS, keep=False)]
    if len(dup):
        pairs = sorted(set(zip(dup["ticker"], dup["period"])))
        raise ValueError(f"{path}: trung khoa ticker+period {pairs} -- vi du vua co "
                         f"'2025-H2' vua co '2025-Q4'; gop lai thanh mot dong")

    for col in NUM_COLS:
        values = []
        for tic, per, raw in zip(df["ticker"], df["period"], df[col]):
            try:
                values.append(_to_number(raw))
            except ValueError as exc:
                raise ValueError(f"{path}: {tic} {per} cot {col}: {exc}") from None
        df[col] = pd.array(values, dtype="Int64")
    return df


def _f(s: pd.Series) -> np.ndarray:
    return s.astype("Float64").to_numpy(dtype="float64", na_value=np.nan)


def tickers() -> list[str]:
    return sorted(pd.read_csv(VNSTOCK, encoding="utf-8-sig")["ticker"].unique())


def norm_period(p: str) -> str:
    """'2026-Q1' giu nguyen; '2025-H2' -> '2025-Q4' (dang cu cua file, va cho de go)."""
    s = str(p).strip().upper()
    m = re.fullmatch(r"(\d{4})-(Q[1-4]|H[12])", s)
    if not m:
        raise ValueError(f"ky {p!r} sai dang -- dung '2026-Q1'")
    year, k = m.groups()
    return f"{year}-{_HALF_TO_Q.get(k, k)}"


def period_end(period: str) -> str:
    return f"{period[:4]}-{QUARTER_END[period[-2:]]}"


def full_grid(periods: list[str]) -> pd.DataFrame:
    """Khung 22 NH x moi ky, o so de TRONG (khac voi 0: trong = chua nhap)."""
    rows = []
    for t in tickers():
        for p in periods:
            row = {c: "" for c in COLUMNS}
            row.update(ticker=t, period=p, as_of_date=period_end(p), co_so="hop_nhat")
            rows.append(row)
    df = pd.DataFrame(rows, columns=COLUMNS)
    for col in NUM_COLS:
        df[col] = pd.array([pd.NA] * len(df), dtype="Int64")
    return df


def _blank(v) -> bool:
    return v is pd.NA or v is None or (isinstance(v, float) and np.isnan(v)) or v == ""


def build(extra_periods: tuple[str, ...] = ()) -> tuple[pd.DataFrame, list, int]:
    """Khung day du, dien DISCLOSED, roi phu file cu len theo tung o."""
    extra = {norm_period(p) for p in extra_periods}
    today = datetime.now().date().isoformat()
    for p in sorted(extra | set(PERIODS)):
        if period_end(p) > today:
            raise ValueError(f"ky {p} chot ngay {period_end(p)}, chua toi -- chua co BCTC")

    old = _read() if MASTER.exists() else None
    periods = set(PERIODS) | extra
    if old is not None:
        periods |= set(old["period"])
    grid = full_grid(sorted(periods)).set_index(KEYS)

    for rec in DISCLOSED:
        key = (rec["ticker"], rec["period"])
        if key not in grid.index:
            continue
        for col, v in rec.items():
            if col not in KEYS:
                grid.at[key, col] = v

    conflicts, kept = [], 0
    if old is not None:
        old = old.set_index(KEYS)
        for key in old.index:
            if key not in grid.index:  # NH ngoai danh sach 22: van giu
                grid.loc[key] = old.loc[key]
                continue
            for col in NUM_COLS + TEXT_COLS:
                o, n = old.at[key, col], grid.at[key, col]
                if _blank(o):
                    continue
                if col in NUM_COLS:
                    kept += 1
                    if not _blank(n) and int(o) != int(n):
                        conflicts.append((key, col, int(o), int(n)))
                grid.at[key, col] = o

    df = grid.reset_index()[COLUMNS].sort_values(["period", "ticker"]).reset_index(drop=True)
    for col in NUM_COLS:
        df[col] = df[col].astype("Int64")
    return df, conflicts, kept


def write(extra_periods: tuple[str, ...] = ()) -> pd.DataFrame:
    OUT.mkdir(parents=True, exist_ok=True)
    df, conflicts, kept = build(extra_periods)
    try:
        df.to_csv(MASTER, index=False, encoding="utf-8-sig")
    except PermissionError:
        raise SystemExit(f"!! khong ghi duoc {MASTER} -- dong file trong Excel roi chay lai")

    filled = df[BUCKETS_12T + ["tong_tai_san"]].notna().all(axis=1)
    msg = (f"repricing_gap: {len(df)} dong ({df['ticker'].nunique()} NH x "
           f"{df['period'].nunique()} ky), du so tinh gap 12T={int(filled.sum())}, "
           f"o so giu tu file cu={kept}, conflicts={len(conflicts)}")
    with open("crawl_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg} -> {MASTER}\n")
    print(f"ghi {MASTER}\n  {msg}")
    if conflicts:
        print("  !! O LECH giua file va DISCLOSED (GIU FILE, khong tu sua):")
        for (tic, per), col, o, n in conflicts:
            print(f"     {tic} {per} {col}: file={o:,} vs code={n:,}")
    return df


# ---------------------------------------------------------------------------
# Kiem dinh va chi so
# ---------------------------------------------------------------------------
def _doi_chieu(r: pd.Series) -> tuple[str, list[str], list[str]]:
    """Hai phep doi chieu cho mot bang: (trang thai, loi, canh bao).

    trang thai: 'khop' = ca hai phep deu chay va khop · 'lech' = co phep lech ·
    'chua_du' = thieu o de chay mot trong hai phep (so co the van dung).
    """
    errors, warns, ran = [], [], 0
    if all(pd.notna(r[c]) for c in ALL_GAPS + ["gap_tong_cong"]):
        ran += 1
        diff = int(sum(int(r[c]) for c in ALL_GAPS)) - int(r["gap_tong_cong"])
        if abs(diff) > TOL:
            errors.append(f"tong 8 cot khe ho lech o tong cong {diff:+,} "
                          f"-- go sai mot o, hoac quen dau ngoac (so am)")
    else:
        warns.append("chua du 8 cot + tong cong, bo qua doi chieu 1")

    if all(pd.notna(r[c]) for c in ["tong_tai_san", "tong_no_phai_tra", "gap_tong_cong"]):
        ran += 1
        diff = int(r["tong_tai_san"]) - int(r["tong_no_phai_tra"]) - int(r["gap_tong_cong"])
        if abs(diff) > TOL:
            errors.append(f"tong tai san - tong no lech o tong cong {diff:+,}")
    else:
        warns.append("thieu tong no hoac tong cong, bo qua doi chieu 2")

    status = "lech" if errors else ("khop" if ran == 2 else "chua_du")
    return status, errors, warns


def check(df: pd.DataFrame | None = None) -> bool:
    """Doi chieu tung bang da nhap. Tra False neu co LOI (khong tinh canh bao)."""
    if df is None:
        df = _read()
    errors, warns = [], []

    started = df[NUM_COLS].notna().any(axis=1)
    for _, r in df[started].iterrows():
        tag = f"{r['ticker']} {r['period']}"
        missing = [c for c in BUCKETS_12T + ["tong_tai_san"] if pd.isna(r[c])]
        if missing:
            errors.append(f"{tag}: thieu {missing} -- chua tinh duoc gap 12 thang")
        if r["co_so"] not in CO_SO:
            errors.append(f"{tag}: co_so={r['co_so']!r}, phai la hop_nhat hoac rieng_le")

        _, e, w = _doi_chieu(r)
        errors += [f"{tag}: {m}" for m in e]
        warns += [f"{tag}: {m}" for m in w]

        if pd.notna(r["tong_tai_san"]) and int(r["tong_tai_san"]) <= 0:
            errors.append(f"{tag}: tong_tai_san <= 0")
        if not str(r["source_url"]).strip():
            warns.append(f"{tag}: chua co source_url -- can truoc khi trich luan van")

    print(f"{len(df)} dong, {df['ticker'].nunique()} NH, ky: {sorted(df['period'].unique())}")
    for per, g in df.groupby("period"):
        ok = g[BUCKETS_12T + ["tong_tai_san"]].notna().all(axis=1)
        # khong_cong_bo = da tim va NH khong in bang ky nay; khac voi chua nhap
        kcb = (g["nguon"].str.strip() == "khong_cong_bo") & ~ok
        thieu = g.loc[~ok & ~kcb, "ticker"]
        mix = set(g.loc[ok, "co_so"])
        print(f"  {per}: du so {int(ok.sum())}/{len(g)} NH"
              + (f", khong cong bo {int(kcb.sum())}" if kcb.any() else "")
              + (f" -- con thieu: {', '.join(thieu)}" if len(thieu) else ""))
        if len(mix) > 1:
            warns.append(f"{per}: tron {sorted(mix)} -- so sanh cheo can cung mot co so")

    for w in warns:
        print(f"  canh bao  {w}")
    for e in errors:
        print(f"  !! LOI    {e}")
    print("khong co loi" if not errors else f"{len(errors)} loi -- sua truoc khi dung")
    return not errors


def ratios(period: str | None = None, df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Ty le khe ho cho moi bang du so. O thieu KHONG coi la 0 -- bang do bi bo.

    Cot doi_chieu mang ket qua _doi_chieu() theo tung dong: bang 'lech' van duoc
    tinh de nguoi dung thay so, nhung KHONG duoc dua vao xep hang.
    """
    if df is None:
        df = _read()
    if period:
        df = df[df["period"] == norm_period(period)]
    df = df[df[BUCKETS_12T + ["tong_tai_san"]].notna().all(axis=1)]

    ta = _f(df["tong_tai_san"])
    cum = np.cumsum(np.column_stack([_f(df[c]) for c in BUCKETS_12T]), axis=1)
    out = pd.DataFrame({
        "ticker": df["ticker"].to_numpy(),
        "period": df["period"].to_numpy(),
        "co_so": df["co_so"].to_numpy(),
        "cum_1t_percent": 100 * cum[:, 0] / ta,
        "cum_3t_percent": 100 * cum[:, 1] / ta,
        "cum_6t_percent": 100 * cum[:, 2] / ta,
        "gap_12t_percent": 100 * cum[:, 3] / ta,
    })
    out["gap_12t_abs_percent"] = out["gap_12t_percent"].abs()
    out["gap_max_abs_12t_percent"] = 100 * np.abs(cum).max(axis=1) / ta
    out["delta_nii_1pp"] = cum[:, 3] * 0.01
    out["doi_chieu"] = [_doi_chieu(r)[0] for _, r in df.iterrows()]
    return out.sort_values(["period", "gap_12t_abs_percent"]).reset_index(drop=True)


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if "--check" in sys.argv:
        raise SystemExit(0 if check() else 1)
    elif "--ratios" in sys.argv:
        i = sys.argv.index("--ratios")
        ky = norm_period(sys.argv[i + 1]) if len(sys.argv) > i + 1 else None
        table = ratios(ky)
        with pd.option_context("display.width", 200, "display.float_format", "{:,.2f}".format):
            print(table.to_string(index=False) if len(table) else "chua co bang nao du so")
    elif "--them-ky" in sys.argv:
        i = sys.argv.index("--them-ky")
        ky = sys.argv[i + 1] if len(sys.argv) > i + 1 else ""
        check(write((ky,)))
    else:
        check(write())
