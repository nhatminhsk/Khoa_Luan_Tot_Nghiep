"""Dung trang bao cao dac trung tu cac file trong data/model."""
import html
import os
import sys

import pandas as pd

os.chdir(r"D:\KLTN")
sys.path.insert(0, r"D:\KLTN")
from crawlers import build_features as bf  # noqa: E402

OUT = sys.argv[1]
E = html.escape

inv = pd.read_csv("data/model/data_inventory.csv", encoding="utf-8-sig")
cat = pd.read_csv("data/model/feature_catalog.csv", encoding="utf-8-sig")
res = bf.build(write=False)
clean = res["cleaned_cells"]

TARGETS = ["nim_ttm_percent", "cof_ttm_percent", "npl_percent", "casa_percent", "ldr_computed_percent", "roe_ttm_percent"]
TLABEL = {"nim_ttm_percent": "NIM", "cof_ttm_percent": "COF", "npl_percent": "NPL", "casa_percent": "CASA",
          "ldr_computed_percent": "LDR", "roe_ttm_percent": "ROE"}


def n(x, d=0):
    s = f"{x:,.{d}f}"
    return s.replace(",", "\u202f").replace(".", ",")


# ---------- kiem ke
order = ["Dùng cho mô hình", "Dùng cho xếp hạng / giao diện", "Trung gian (dựng lại được)", "Tham khảo / kiểm chéo",
         "Sản phẩm của bước đặc trưng", "Bỏ — trùng", "Bỏ — lưu trữ"]
g = inv.groupby("decision").agg(files=("file", "size"), rows=("rows", "sum")).reindex(order).dropna()
note = {
    "Dùng cho mô hình": "BCTC, thuyết minh, giá, review, vĩ mô, sở hữu, chi nhánh, tín dụng chính sách",
    "Dùng cho xếp hạng / giao diện": "Lãi suất huy động và cho vay, khe hở lãi suất, điểm store — chỉ phủ vài quý gần nhất",
    "Trung gian (dựng lại được)": "Bảng đã gộp vào panel; chạy lại crawler là có",
    "Tham khảo / kiểm chéo": "Nguồn đối chứng, bộ dữ liệu ngoài hết 2022, số tổng của NHNN",
    "Sản phẩm của bước đặc trưng": "Các file sinh ra ở bước này",
    "Bỏ — trùng": "powerbi/, raw*/ theo mã, deposit_raw/, bản sao nhập tay",
    "Bỏ — lưu trữ": "BCTC tóm tắt cũ trước 14/09/2026, 44 file rỗng",
}
inv_rows = "".join(
    f'<tr class="{"is-drop" if k.startswith("Bỏ") else ""}"><th scope="row">{E(k)}</th><td class="num">{n(v.files)}</td>'
    f'<td class="num">{n(v.rows)}</td><td>{E(note[k])}</td></tr>' for k, v in g.iterrows())
files_total, rows_total = int(inv.shape[0]), int(inv.rows.sum())
model_files = int(g.loc["Dùng cho mô hình", "files"])

# ---------- lam sach
CLEAN = [
    ("cof_ttm_percent_zero_as_missing", "Chi phí vốn bằng đúng 0 trong panel", "Nguồn ghi 0 thay cho ô trống"),
    ("earning_asset_yield_ttm_percent_zero_as_missing", "Lợi suất tài sản sinh lãi bằng 0", "Như trên"),
    ("salary_nonpositive_as_missing", "Chi lương, phụ cấp ≤ 0 (thuyết minh)", "NH không tách dòng thì API ghi 0"),
    ("dep_ins_nonpositive_as_missing", "Phí bảo hiểm tiền gửi ≤ 0", "Như trên"),
    ("dep_int_nonpositive_as_missing", "Trả lãi tiền gửi ≤ 0", "Như trên"),
    ("loan_int_nonpositive_as_missing", "Thu lãi cho vay ≤ 0", "Như trên"),
    ("paper_int_negative_as_missing", "Trả lãi giấy tờ có giá < 0", "Số 0 giữ nguyên: NH không phát hành là thật"),
    ("inv_total_zero_as_missing", "Tổng chứng khoán đầu tư (thuyết minh) = 0", "Mẫu số của tỷ trọng trái phiếu"),
    ("gov_bond_over_total_invsec", "Trái phiếu Chính phủ vượt tổng chứng khoán đầu tư", "Mâu thuẫn nội bộ thuyết minh"),
    ("dividend_payout_ttm_pct", "Tỷ lệ chi cổ tức khi LNST TTM ≤ 0", "Tỷ số trên mẫu âm vô nghĩa"),
    ("cir_ttm_pct", "CIR, tỷ trọng ngoài lãi, tỷ trọng phí khi TNHĐ TTM ≤ 0", "Như trên (mỗi biến 4 ô)"),
    ("price_quarters_below_min_sessions", "Quý có dưới 20 phiên giao dịch", "Quý lên sàn, lợi suất không đại diện"),
    ("app_quarters_below_min_reviews", "Quý có dưới 30 review", "Điểm trung bình dao động theo vài người"),
]
clean_rows = "".join(f'<tr><td>{E(a)}</td><td class="num">{n(clean.get(k, 0))}</td><td>{E(b)}</td></tr>' for k, a, b in CLEAN)

# ---------- tan suat
FREQ = [
    ("Quý — dòng chảy", "Cộng 4 quý gần nhất (TTM); mẫu số là số dư bình quân 5 mốc cuối quý", "KQKD, lưu chuyển tiền, thuyết minh thu–chi"),
    ("Quý — số dư", "Số cuối quý; tăng trưởng so cùng kỳ", "Bảng cân đối, cơ cấu tiền gửi, nhóm nợ"),
    ("Nửa năm", "As-of: H1 → Q2, Q3; H2 → Q4 và Q1 năm sau", "CAR"),
    ("Năm", "As-of: năm Y → Q4/Y và Q1–Q3/Y+1, không dùng số chưa công bố", "Dư nợ theo ngành, nông nghiệp, tăng trưởng tín dụng"),
    ("Tháng", "Trung bình trong quý; review lấy trung bình có trọng số số review", "CPI, chỉ số giá USD/vàng, review app"),
    ("Ngày", "Lợi suất và độ lệch chuẩn trong quý (năm hóa), giá trị giao dịch bình quân", "Giá 22 mã, VN-Index, lãi suất niêm yết"),
    ("Sự kiện", "Giá trị có hiệu lực tại ngày cuối quý", "Lãi suất điều hành, danh sách chương trình, cửa sổ thiên tai"),
    ("Ảnh chụp", "Lặp cho mọi quý, gắn cờ tĩnh", "Sở hữu nhà nước/nước ngoài, mạng lưới chi nhánh"),
]
freq_rows = "".join(f"<tr><th scope=\"row\">{E(a)}</th><td>{E(b)}</td><td>{E(c)}</td></tr>" for a, b, c in FREQ)

# ---------- quy tac chon loc
reason = cat.reason.fillna("")
rule_counts = [
    ("Mức tuyệt đối", "Số tiền đồng hoặc giá trị trên mỗi cổ phiếu — không so được giữa NH lớn và nhỏ",
     int((cat.decision.eq("Loại") & (reason.str.startswith("Mức tuyệt đối") | reason.str.startswith("Tính trên mỗi"))).sum()), "Loại"),
    ("Cùng khái niệm", "Hai cách đo một chỉ tiêu (ROA panel và ROA tự tính r = 0,998) — giữ bản phủ rộng hoặc có công thức rõ",
     int((cat.decision.eq("Loại") & reason.str.startswith("Cùng ")).sum()), "Loại"),
    ("Gần như hằng số", "Một giá trị chiếm ≥ 95% số ô (chương trình DNNVV bắt đầu sau quý cuối cùng)",
     int(reason.str.startswith("Gần như hằng số").sum()), "Loại"),
    ("Phủ thấp", "Dưới 70% trong 748 ô hoặc dưới 20/22 NH",
     int(reason.str.startswith("Phủ thấp").sum()), "Loại"),
    ("Chỉ phủ gần đây", "Phủ thấp nhưng ≥ 20 NH có số trong 4 quý cuối → dùng ảnh chụp cho xếp hạng",
     int(cat.decision.eq("Giữ cho xếp hạng").sum()), "Giữ cho xếp hạng"),
    ("Trùng thông tin", "|Spearman| ≥ 0,90 với biến đã giữ, xét theo thứ tự ưu tiên tiêu chí cốt lõi",
     int(reason.str.startswith("Trùng thông tin").sum()), "Loại"),
]
CHIP = {"Giữ": "keep", "Giữ cho xếp hạng": "rank", "Loại": "drop"}
rule_rows = "".join(
    f'<tr><th scope="row">{E(a)}</th><td>{E(b)}</td><td class="num">{c}</td><td><span class="chip {CHIP[d]}">{E(d)}</span></td></tr>'
    for a, b, c, d in rule_counts)

kept = int(cat.decision.eq("Giữ").sum())
rank = int(cat.decision.eq("Giữ cho xếp hạng").sum())
drop = int(cat.decision.eq("Loại").sum())
core = cat[cat.use.eq("Lõi dự báo")].copy()
n_core = len(core)

# ---------- ma tran lien he
core["n_rel"] = core.relevant_for.fillna("").str.count(",") + 1
core["grp_order"] = core.group
core = core.sort_values(["group", "feature"])
head = "".join(f"<th scope=\"col\" class=\"num\">{TLABEL[t]}</th>" for t in TARGETS)
mrows = []
for r in core.itertuples():
    rel = set(str(r.relevant_for).split(", "))
    cells = []
    for t in TARGETS:
        v = getattr(r, f"rho_next_{t}")
        if pd.isna(v):
            cells.append('<td class="heat empty">—</td>')
            continue
        a = min(abs(v) / 0.5, 1)
        cls = "pos" if v > 0 else "neg"
        hit = " hit" if t in rel else ""
        label = ("−" + n(-v, 2)) if v < 0 else ("+" + n(v, 2))
        cells.append(f'<td class="heat {cls}{hit}" style="--a:{a:.2f}">{label}</td>')
    mrows.append(f'<tr><th scope="row"><code>{E(r.feature)}</code><span class="grp">{E(r.group)}</span></th>{"".join(cells)}</tr>')
matrix_rows = "".join(mrows)

# ---------- catalog
groups = sorted(cat.group.unique())
crow = []
for r in cat.itertuples():
    flags = "" if pd.isna(r.flags) else r.flags
    flag_html = "".join(f'<span class="flag">{E(x)}</span>' for x in flags.split(", ") if x)
    use = "" if pd.isna(r.use) else r.use
    use_html = f'<span class="use">{E(use)}</span>' if use == "Lõi dự báo" else ""
    crow.append(
        f'<tr data-d="{E(r.decision)}" data-g="{E(r.group)}" data-core="{1 if use == "Lõi dự báo" else 0}" '
        f'data-q="{E((r.feature + " " + str(r.formula) + " " + str(r.reason)).lower())}">'
        f'<td><code>{E(r.feature)}</code><div class="formula">{E(str(r.formula))}</div></td>'
        f'<td>{E(r.group)}</td>'
        f'<td><span class="chip {CHIP[r.decision]}">{E(r.decision)}</span>{use_html}</td>'
        f'<td>{E(str(r.reason))}{("<div class=flags>" + flag_html + "</div>") if flag_html else ""}</td>'
        f'<td class="num">{n(r.coverage_pct, 1)}</td></tr>')
catalog_rows = "".join(crow)
group_opts = "".join(f'<option value="{E(x)}">{E(x)}</option>' for x in groups)

tpl = open(os.path.join(os.path.dirname(__file__), "report_template.html"), encoding="utf-8").read()
out = (tpl.replace("{{INV_ROWS}}", inv_rows).replace("{{CLEAN_ROWS}}", clean_rows).replace("{{FREQ_ROWS}}", freq_rows)
       .replace("{{RULE_ROWS}}", rule_rows).replace("{{MATRIX_HEAD}}", head).replace("{{MATRIX_ROWS}}", matrix_rows)
       .replace("{{CATALOG_ROWS}}", catalog_rows).replace("{{GROUP_OPTS}}", group_opts)
       .replace("{{FILES}}", n(files_total)).replace("{{ROWS}}", n(rows_total)).replace("{{MODEL_FILES}}", n(model_files))
       .replace("{{N_FEAT}}", str(len(cat))).replace("{{KEPT}}", str(kept)).replace("{{RANK}}", str(rank))
       .replace("{{DROP}}", str(drop)).replace("{{CORE}}", str(n_core)).replace("{{DESCRIBE}}", str(kept - n_core)))
assert "{{" not in out, "con placeholder"
open(OUT, "w", encoding="utf-8").write(out)
print(OUT, len(out))
