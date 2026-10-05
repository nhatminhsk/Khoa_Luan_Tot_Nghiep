"""Chi so gia do la My, chi so gia vang va lam phat co ban -- tu NSO.

Ba chuoi nay nam TRONG CHINH bai cong bo ma crawlers/cpi_nso.py da tai ve moi
thang de boc CPI. Do 600 bai lay duoc qua API: chi so gia do la My xuat hien o
394 bai, chi so gia vang 392 bai, lam phat co ban 315 bai -- cung mot cau truc
cau va cung bo neo "so voi thang truoc / so voi cung ky nam truoc" ma parser CPI
da xu ly duoc. **Chi phi mang de them ba chuoi nay bang khong.**

Vi sao dang lam voi de tai nay: voi mot he thong tu van GUI TIET KIEM, vang va
do la khong phai chi bao vi mo chung chung -- chung la **hai kenh canh tranh
truc tiep** voi tien gui ngan hang. Lam phat co ban thi la bien kiem soat chuan
trong moi mo hinh lai suat.

KHONG sua cpi_nso.py. Parser CPI o do co subject guard rieng (CPI_SUBJECT) va co
NOT_HEADLINE_CPI de **loai tru** dung ba chi tieu nay ra khoi ket qua CPI --
dong vao se de vo mot parser dang dat 103/103 thang. Module nay dung lai
fetch_posts / parse_month / _anchors cua no, chi them buoc cat doan theo chu ngu.

DO PHU THUC TE (do ngay 09/09/2026, tren 103 thang 2018-01..2026-08):

    usd_index_mom       97/103      usd_index_yoy       94/103
    gold_index_mom      90/103      gold_index_yoy      59/103
    core_inflation_mom  73/103      core_inflation_yoy  41/103

Chi so USD gan nhu day. Hai cot yeu KHONG phai loi parser ma la nguon doi cach
viet: tu 2021 tro di ban cong bo phan lon chi con neu **lam phat co ban binh
quan N thang** ("lạm phát cơ bản bình quân 8 tháng năm 2026 tăng 4,24%") chu
khong con neu MoM/YoY tung thang, va chi so gia vang cung bo dan ve YoY
(2022 con 0 thang, 2023 con 1). NOT_MONTHLY co y loai cac con so binh quan do --
tron chung vao se lam hong chuoi. Neu can lam phat co ban day du sau 2020 thi
phai lay tu nguon khac, dung nhap nhem voi so binh quan.

Thieu dung 1 thang so voi cpi.csv: 2025-06.

Cach cat doan: tim vi tri chu ngu ("Chi so gia do la My"...), lay cua so 260 ky
tu tu do, va cat som neu gap chu ngu khac -- de con so cua vang khong bi doc
nham thanh con so cua do la khi hai cau nam sat nhau.

Chay:
    python -m crawlers.price_index_nso
    python -m crawlers.price_index_nso --validate
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone

import pandas as pd

from crawlers import cpi_nso

OUT_PATH = "data/macro/price_indices.csv"
LOG_PATH = "crawl_log.txt"

# Chu ngu cua tung chi tieu. Nguon viet "do la My" theo nhieu kieu dau gach noi.
SUBJECTS = {
    "usd_index": r"[Cc]hỉ số giá đô[\s\-]?la\s+Mỹ",
    "gold_index": r"[Cc]hỉ số giá vàng",
    "core_inflation": r"[Ll]ạm phát cơ bản",
}
SEGMENT_CHARS = 260

# BAY QUAN TRONG NHAT CUA NGUON NAY.
# Bai cong bo dung CUNG mot cum "chi so gia do la My" cho HAI chuoi khac han:
#   (a) "chỉ số giá đô la Mỹ trên thị trường quốc tế đạt mức 98,31 điểm" -> chi so
#       DXY the gioi, la binh luan boi canh;
#   (b) "Chỉ số giá đô la Mỹ tháng Tám giảm 0,38% so với tháng trước"    -> chi so
#       gia USD TRONG NUOC, la thu thuoc ro hang hoa CPI va la thu ta can.
# Vang cung vay: "giá vàng thế giới" vs "chỉ số giá vàng trong nước".
# Cau (a) thuong dung TRUOC cau (b) trong bai, nen "lay lan xuat hien dau tien"
# se doc nham chi so quoc te. Phai loc bo (a) truoc roi moi lay cai dau tien.
INTERNATIONAL = re.compile(
    r"trên thị trường quốc tế"
    r"|thị trường thế giới"
    r"|thế giới"
    r"|quốc tế",
    re.IGNORECASE,
)
LOOKAHEAD_CHARS = 70

# Cac cum bao hieu con so la binh quan nhieu thang / ca nam, khong phai MoM/YoY.
NOT_MONTHLY = re.compile(
    r"bình quân"
    r"|cả năm"
    r"|quý\s+(?:i|ii|iii|iv)\b"
    r"|(?:\d{1,2}|một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười|mười một|mười hai)"
    r"\s+tháng\s+(?:năm|đầu năm)",
    re.IGNORECASE,
)

COLUMNS = [
    "month",
    "usd_index_mom_percent", "usd_index_yoy_percent",
    "gold_index_mom_percent", "gold_index_yoy_percent",
    "core_inflation_mom_percent", "core_inflation_yoy_percent",
    "source_url", "note",
]


def _log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")


def _segments(text):
    """Cat van ban thanh {ten_chi_tieu: doan van} theo chu ngu.

    Bo qua cac lan xuat hien noi ve thi truong quoc te -- xem chu thich o
    INTERNATIONAL. Trong so cac lan con lai, giu lan DAU TIEN: lan sau thuong la
    phan binh quan nhieu thang.
    """
    marks = []
    for key, pattern in SUBJECTS.items():
        for m in re.finditer(pattern, text):
            marks.append((m.start(), m.end(), key))
    marks.sort()

    out = {}
    for i, (start, subject_end, key) in enumerate(marks):
        if key in out:
            continue
        if INTERNATIONAL.search(text[subject_end:subject_end + LOOKAHEAD_CHARS]):
            continue
        end = start + SEGMENT_CHARS
        for next_start, _, _ in marks[i + 1:]:
            if next_start > start:
                end = min(end, next_start)
                break
        out[key] = text[start:end]
    return out


def _grab(segment, anchor):
    candidates = (
        (rf"(?:ổn định|không đổi)\s*so với {anchor}", "zero"),
        (rf"(tăng|giảm)\s+{cpi_nso.ADVERB}([\d.,]+)%\s*so với {anchor}", "signed"),
        (rf"so với {anchor}[^%.]{{0,60}}?(tăng|giảm)\s+{cpi_nso.ADVERB}([\d.,]+)%",
         "signed"),
    )
    hits = []
    for pattern, kind in candidates:
        for m in re.finditer(pattern, segment, re.IGNORECASE):
            window = segment[max(0, m.start() - 45):m.start()]
            if NOT_MONTHLY.search(window):
                continue
            hits.append((m.start(), kind, m))
    if not hits:
        return None
    _, kind, m = min(hits, key=lambda hit: hit[0])
    if kind == "zero":
        return 0.0
    value = cpi_nso._num(m.group(2))
    return -value if m.group(1).lower() == "giảm" else value


def parse_post(content_html, month):
    text = cpi_nso._normalise(cpi_nso._strip_html(content_html))
    mom_anchor, yoy_anchor = cpi_nso._anchors(month)
    out = {}
    for key, segment in _segments(text).items():
        out[f"{key}_mom_percent"] = _grab(segment, mom_anchor)
        out[f"{key}_yoy_percent"] = _grab(segment, yoy_anchor)
    return out


def build_frame(posts):
    rows = {}
    for post in posts:
        title = cpi_nso._strip_html(post["title"]["rendered"])
        month = cpi_nso.parse_month(title, post["slug"], post["date"])
        if month is None:
            continue
        values = parse_post(post["content"]["rendered"], month)
        if not any(v is not None for v in values.values()):
            continue
        row = rows.setdefault(month, {"month": month})
        # Bai dang sau thuong day du hon -- chi bu o con trong, khong ghi de.
        for key, value in values.items():
            if value is not None and row.get(key) is None:
                row[key] = value
        row["source_url"] = post["link"]
        row["note"] = title
    frame = pd.DataFrame(rows.values())
    for col in COLUMNS:
        if col not in frame.columns:
            frame[col] = None
    return frame[COLUMNS].sort_values("month")


def build(since="2018-01", write=True, posts=None):
    posts = posts if posts is not None else cpi_nso.fetch_posts()
    frame = build_frame(posts)
    frame = frame[frame["month"] >= since]

    if write:
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        if os.path.exists(OUT_PATH):
            old = pd.read_csv(OUT_PATH, encoding="utf-8-sig", dtype={"month": str})
            merged = pd.concat([old, frame]).drop_duplicates(
                subset=["month"], keep="last")
            frame = merged.sort_values("month")
        frame.to_csv(OUT_PATH, index=False, encoding="utf-8-sig",
                     lineterminator="\r\n")
        _log(
            f"price_index_nso: {len(frame)} thang "
            f"({frame['month'].min()}..{frame['month'].max()}), "
            f"USD {frame['usd_index_mom_percent'].notna().sum()} thang MoM, "
            f"vang {frame['gold_index_mom_percent'].notna().sum()}, "
            f"lam phat co ban {frame['core_inflation_yoy_percent'].notna().sum()} "
            f"-> {OUT_PATH}"
        )

    value_cols = [c for c in COLUMNS if c.endswith("_percent")]
    return {
        "posts_seen": len(posts),
        "months": len(frame),
        "range": (frame["month"].min(), frame["month"].max()),
        "coverage": {c: int(frame[c].notna().sum()) for c in value_cols},
        "path": OUT_PATH,
    }


def validate():
    frame = pd.read_csv(OUT_PATH, encoding="utf-8-sig", dtype={"month": str})
    value_cols = [c for c in frame.columns if c.endswith("_percent")]
    res = {
        "months": len(frame),
        "range": (frame["month"].min(), frame["month"].max()),
        "coverage": {c: int(frame[c].notna().sum()) for c in value_cols},
    }

    # Thang bi dut trong chuoi -- neu de lot se lam gay dac trung tre.
    months = pd.period_range(frame["month"].min(), frame["month"].max(), freq="M")
    have = set(frame["month"])
    res["missing_months"] = [str(m) for m in months if str(m) not in have]

    # Bien do hop ly: chi so gia thang hiem khi vuot +/-15% MoM.
    outliers = {}
    for col in value_cols:
        if col.endswith("mom_percent"):
            bad = frame[frame[col].abs() > 15][["month", col]].dropna()
            if len(bad):
                outliers[col] = bad.to_dict("records")
    res["mom_outliers_over_15pp"] = outliers

    # Doi chieu voi cpi.csv: cung nguon, cung thang -> phai phu tuong duong.
    cpi_path = "data/macro/cpi.csv"
    if os.path.exists(cpi_path):
        cpi = pd.read_csv(cpi_path, encoding="utf-8-sig", dtype={"month": str})
        res["vs_cpi_csv"] = {
            "cpi_months": len(cpi),
            "months_only_in_cpi": sorted(set(cpi["month"]) - set(frame["month"]))[:12],
            "months_only_here": sorted(set(frame["month"]) - set(cpi["month"]))[:12],
        }
    return res


if __name__ == "__main__":
    import json
    import sys

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--validate" in sys.argv:
        print(json.dumps(validate(), indent=2, ensure_ascii=False, default=str))
    else:
        print(json.dumps(build(), indent=2, ensure_ascii=False, default=str))
