"""Tao data/credit/loans_by_industry_manual/fill_template.xlsx cho 33 NH-nam con thieu."""
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, r"D:\KLTN")
import os
os.chdir(r"D:\KLTN")
from crawlers.loans_by_industry import GROUP_NAME, load_manual, validate  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/credit/loans_by_industry_manual/fill_template.xlsx")
if OUT.exists() and "--force" not in sys.argv:
    # File nay chua so nguoi dung nhap tay -- khong bao gio ghi de khi chua duoc yeu cau ro rang.
    sys.exit(f"{OUT} da ton tai (co the chua so da nhap). Ghi ra duong dan khac, hoac them --force neu chac chan.")

m = load_manual()
missing = validate()["missing"]

# BCTC nam le y cho ca y (cuoi nam) va y-1 (dau nam) -> it file nhat.
tables = {}
for t, years in missing.items():
    for y in years:
        fy = y if y % 2 == 1 else y + 1
        tables.setdefault((t, fy), []).append(y)

LABEL_FROM = {
    "BAB_2019": "BAB_2018", "BAB_2021": "BAB_2018", "BAB_2025": "BAB_2024",
    "BVB_2023": "BVB_2022", "BVB_2025": "BVB_2022",
    "MSB_2019": "MSB_2020", "NAB_2019": "NAB_2020", "OCB_2019": "OCB_2020", "SSB_2019": "SSB_2021",
    "TPB_2019": "TPB_2024", "TPB_2021": "TPB_2024", "TPB_2023": "TPB_2024",
}
VSIC_FROM = "BAB_2024"  # 21 nhom VSIC day du, dung lam goi y cho LPB, PGB
WHERE = {
    "BAB": "baca-bank.vn → Nhà đầu tư (BCTC 2018 đã tải được từ đây)",
    "BVB": "baovietbank.vn → Nhà đầu tư / Báo cáo tài chính",
    "LPB": "lpbank.com.vn → Nhà đầu tư / Báo cáo tài chính",
    "MSB": "msb.com.vn → Nhà đầu tư / Báo cáo tài chính",
    "NAB": "namabank.com.vn → Quan hệ nhà đầu tư",
    "OCB": "ocb.com.vn → Nhà đầu tư / Báo cáo tài chính",
    "PGB": "pgbank.com.vn → Quan hệ cổ đông",
    "SSB": "seabank.com.vn → Nhà đầu tư / Báo cáo tài chính",
    "TPB": "tpb.vn → Nhà đầu tư / Báo cáo tài chính",
}
WARN = {
    "TPB": "TPB đổi cách phân ngành 2023–2024: bảng cũ có thể nhiều dòng hơn",
    "LPB": "Chưa có bảng nào của LPB: nhãn là 21 nhóm VSIC chung",
    "PGB": "Chưa có bảng nào của PGB: nhãn là 21 nhóm VSIC chung",
    "MSB": "MSB dùng danh mục ngành riêng (33 dòng năm 2020)",
}

FONT = "Arial"
f_norm = Font(name=FONT, size=10)
f_bold = Font(name=FONT, size=10, bold=True)
f_head = Font(name=FONT, size=10, bold=True, color="FFFFFF")
f_title = Font(name=FONT, size=14, bold=True)
f_blue = Font(name=FONT, size=10, color="0000FF")
f_gray = Font(name=FONT, size=9, color="666666")
fill_head = PatternFill("solid", fgColor="44546A")
fill_input = PatternFill("solid", fgColor="FFFF00")
fill_suggest = PatternFill("solid", fgColor="FFF2CC")
fill_formula = PatternFill("solid", fgColor="EDEDED")
thin = Side(style="thin", color="BFBFBF")
thick = Side(style="medium", color="44546A")
wrap = Alignment(wrap_text=True, vertical="top")

wb = Workbook()

# ---------------- huong_dan ----------------
hd = wb.active
hd.title = "huong_dan"
hd.sheet_view.showGridLines = False
hd.column_dimensions["A"].width = 3
hd.column_dimensions["B"].width = 16
hd.column_dimensions["C"].width = 60
for c in "DEFGH":
    hd.column_dimensions[c].width = 16
n_tables = len(tables)
n_by = sum(len(v) for v in tables.values())
lines = [
    ("title", "Dư nợ theo ngành — phần nhập tay còn thiếu"),
    ("progress", '="Tiến độ: "&COUNTIF(bang!E:E,"đã nhập")&"/"&(COUNTA(bang!A:A)-1)&" bảng đã nhập, "'
                 '&COUNTIF(bang!O:O,"KHỚP")&" bảng khớp tổng"'),
    ("", f"{n_tables} bảng BCTC cần đọc, bù {n_by} NH-năm còn thiếu trong data/credit/loans_by_industry_annual.csv "
         "(hiện có 143/176). Mỗi BCTC cho hai năm: cột \"Số cuối năm\" và cột \"Số đầu năm\"."),
    ("", "Nhập xong, 17 ô nông–lâm–thủy sản còn \"chưa có file\" trong agri_loans_fill_template.csv tự được điền theo."),
    ("", ""),
    ("head", "Ô nào được sửa"),
    ("legend_input", "Nền vàng: nhập số (sheet dong, hai cột số) và trạng thái, link, trang PDF (sheet bang)."),
    ("legend_suggest", "Nền vàng nhạt: nhãn và mã nhóm gợi ý, lấy từ BCTC năm gần nhất của cùng ngân hàng. Sửa cho đúng BCTC đang đọc."),
    ("legend_formula", "Nền xám: công thức kiểm tra, không sửa."),
    ("", ""),
    ("head", "Các bước cho mỗi bảng"),
    ("", "1. Sheet bang: xem cột \"Tìm file ở đâu\", tải BCTC hợp nhất kiểm toán của năm ghi ở cột \"Năm BCTC\"."),
    ("", "2. Tìm thuyết minh \"Phân tích dư nợ cho vay theo ngành nghề kinh doanh\" (thường cạnh bảng dư nợ theo nhóm nợ)."),
    ("", "3. Sheet dong: lọc cột \"Mã bảng\". Sửa nhãn cho đúng BCTC; thừa dòng thì xóa dòng, thiếu thì chèn dòng và gõ lại mã bảng."),
    ("", "4. Gõ số đúng như BCTC, đơn vị BCTC ghi (triệu đồng hoặc đồng — script tự nhận). Gõ số liền, không dấu chấm: 12345678. Số âm gõ -123. Ô \"-\" trong BCTC gõ 0. Dòng gợi ý mà BCTC không có: xóa dòng, hoặc để trống cả hai ô số (script bỏ qua)."),
    ("", "5. Dòng tổng cuối bảng để Loại = T. Dòng tổng phụ (không cộng vào tổng) để Loại = S. Mọi dòng ngành để Loại = I."),
    ("", "6. Sheet bang: cột \"Kiểm tra\" phải là KHỚP (tổng các dòng I = dòng T ở cả hai cột). Rồi chọn Trạng thái = đã nhập, dán link, ghi trang PDF (số trang của trình đọc PDF)."),
    ("", "7. Không tìm được file: chọn Trạng thái = không tìm được file, ghi lý do vào Ghi chú. Đổi sang BCTC năm khác: sửa Mã bảng ở cả hai sheet."),
    ("", "8. Lưu file (giữ định dạng .xlsx), rồi chạy:"),
    ("code", "python -m crawlers.loans_by_industry"),
    ("code", "python -m crawlers.agri_loans_manual"),
    ("", "Script chỉ nạp bảng có Trạng thái = đã nhập, và dừng kèm danh sách lỗi nếu tổng lệch, thiếu link/trang, mã nhóm lạ, hoặc mã bảng trùng bảng đã có."),
    ("", ""),
    ("head", "Ví dụ: một bảng đã nhập (NVB, BCTC 2020, lấy từ batch20.txt)"),
]
r = 1
for kind, text in lines:
    cell = hd.cell(row=r, column=2, value=text)
    if kind == "title":
        cell.font = f_title
        hd.row_dimensions[r].height = 24
    elif kind == "progress":
        cell.font = Font(name=FONT, size=11, bold=True, color="006100")
        hd.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
    elif kind == "head":
        cell.font = Font(name=FONT, size=11, bold=True, color="44546A")
    elif kind == "code":
        cell.font = Font(name="Consolas", size=10)
        cell.fill = fill_formula
    elif kind.startswith("legend"):
        swatch = hd.cell(row=r, column=2, value={"legend_input": "Nhập", "legend_suggest": "Gợi ý, sửa được",
                                                 "legend_formula": "Công thức"}[kind])
        swatch.fill = {"legend_input": fill_input, "legend_suggest": fill_suggest, "legend_formula": fill_formula}[kind]
        swatch.font = f_bold
        hd.cell(row=r, column=3, value=text).font = f_norm
    else:
        cell.font = f_norm
    if kind in ("", "code"):
        hd.merge_cells(start_row=r, start_column=2, end_row=r, end_column=8)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        if len(text) > 120:
            hd.row_dimensions[r].height = 28
    r += 1

ex_head = ["Mã bảng", "Loại", "Tên dòng trong BCTC", "Mã nhóm", "Số cuối năm", "Số đầu năm"]
for j, h in enumerate(ex_head):
    c = hd.cell(row=r, column=2 + j, value=h)
    c.font = f_head
    c.fill = fill_head
r += 1
ex = m[m.key == "NVB_2020"]
for row in ex.itertuples():
    vals = [row.key, row.kind, row.label, row.grp, row.v0, row.v1]
    for j, v in enumerate(vals):
        c = hd.cell(row=r, column=2 + j, value=v)
        c.font = f_bold if row.kind == "T" else f_norm
        if j >= 4:
            c.number_format = "#,##0"
    r += 1

# ---------------- nhom ----------------
nh = wb.create_sheet("nhom")
nh.append(["Mã nhóm", "Tên nhóm", "Dùng khi"])
codes = list(GROUP_NAME.items()) + [("TOTAL", "Dòng tổng cuối bảng (Loại T)"), ("SUBTOTAL", "Dòng tổng phụ (Loại S)")]
usage = {k: "Ngành cấp 1 VSIC 2018" for k in "ABCDEFGHIJKLMNOPQRSTU"}
usage.update({k: "BCTC gộp hai ngành vào một dòng" for k in ("DE", "FL", "GC", "GS", "HJ", "IR", "LM")})
usage.update({"SERV": "Dòng \"Dịch vụ\" không rõ gồm những ngành nào", "OTHER": "\"Các ngành khác\", \"Hoạt động khác\"",
              "INDIV": "Cho vay cá nhân không phân ngành (TCB)", "MARGIN": "Cho vay ký quỹ, ứng trước (công ty chứng khoán con)",
              "FOREIGN_BRANCH": "Dư nợ ở chi nhánh/ngân hàng con nước ngoài (MBB)", "TOTAL": "Chỉ cho dòng Loại T",
              "SUBTOTAL": "Chỉ cho dòng Loại S"})
for k, v in codes:
    nh.append([k, v, usage.get(k, "")])
nh.column_dimensions["A"].width = 16
nh.column_dimensions["B"].width = 52
nh.column_dimensions["C"].width = 52
for row in nh.iter_rows():
    for c in row:
        c.font = f_norm
for c in nh[1]:
    c.font = f_head
    c.fill = fill_head
nh.freeze_panes = "A2"
last_code_row = len(codes) + 1

# ---------------- dong ----------------
dg = wb.create_sheet("dong")
dg_head = ["Mã bảng", "STT", "Loại", "Tên dòng trong BCTC", "Mã nhóm", "Tên nhóm (tự hiện)", "Số cuối năm", "Số đầu năm", "Ghi chú dòng"]
dg.append(dg_head)
widths = [11, 5, 6, 62, 12, 34, 17, 17, 28]
for j, w in enumerate(widths):
    dg.column_dimensions["ABCDEFGHI"[j]].width = w
for c in dg[1]:
    c.font = f_head
    c.fill = fill_head
    c.alignment = Alignment(vertical="center", wrap_text=True)
dg.row_dimensions[1].height = 30

order = sorted(tables)
row_i = 2
for t, fy in order:
    key = f"{t}_{fy}"
    src = LABEL_FROM.get(key, VSIC_FROM)
    tpl = m[m.key == src]
    first = True
    for n, x in enumerate(tpl.itertuples(), start=1):
        grp = "SUBTOTAL" if x.kind == "S" else x.grp
        vals = [key, n, x.kind, x.label, grp, None, None, None, None]
        for j, v in enumerate(vals):
            c = dg.cell(row=row_i, column=j + 1, value=v)
            c.font = f_bold if x.kind == "T" else f_norm
            c.border = Border(top=thick if first else thin, bottom=thin)
        dg.cell(row=row_i, column=6, value=f'=IFERROR(INDEX(nhom!$B$2:$B${last_code_row},MATCH(E{row_i},nhom!$A$2:$A${last_code_row},0)),"")')
        dg.cell(row=row_i, column=6).fill = fill_formula
        dg.cell(row=row_i, column=6).font = f_gray
        for col in (4, 5):
            dg.cell(row=row_i, column=col).fill = fill_suggest
        for col in (7, 8):
            c = dg.cell(row=row_i, column=col)
            c.fill = fill_input
            c.number_format = "#,##0"
            c.font = Font(name=FONT, size=10, color="0000FF", bold=x.kind == "T")
        first = False
        row_i += 1
last_dong = row_i - 1
dg.freeze_panes = "D2"
dg.auto_filter.ref = f"A1:I{last_dong}"

dv_kind = DataValidation(type="list", formula1='"I,S,T"', allow_blank=True, showErrorMessage=True,
                         errorTitle="Loại", error="Chỉ nhận I (dòng ngành), S (tổng phụ), T (dòng tổng).")
dv_grp = DataValidation(type="list", formula1=f"=nhom!$A$2:$A${last_code_row}", allow_blank=True, showErrorMessage=True,
                        errorTitle="Mã nhóm", error="Chọn mã trong sheet nhom.")
dg.add_data_validation(dv_kind)
dg.add_data_validation(dv_grp)
dv_kind.add("C2:C2000")
dv_grp.add("E2:E2000")

# ---------------- bang ----------------
bg = wb.create_sheet("bang", 1)
bg_head = ["Mã bảng", "Ngân hàng", "Năm BCTC", "Bù cho năm", "Trạng thái", "Link BCTC", "Trang PDF",
           "Số dòng I có số", "Tổng dòng I — cuối năm", "Dòng T — cuối năm", "Lệch cuối năm",
           "Tổng dòng I — đầu năm", "Dòng T — đầu năm", "Lệch đầu năm", "Kiểm tra",
           "Tìm file ở đâu", "Nhãn gợi ý lấy từ", "Ghi chú"]
bg.append(bg_head)
bw = [11, 9, 9, 30, 18, 40, 9, 8, 17, 17, 12, 17, 17, 12, 16, 44, 40, 36]
for j, w in enumerate(bw):
    bg.column_dimensions[chr(65 + j)].width = w
for c in bg[1]:
    c.font = f_head
    c.fill = fill_head
    c.alignment = Alignment(vertical="center", wrap_text=True)
bg.row_dimensions[1].height = 32

for i, (t, fy) in enumerate(order, start=2):
    key = f"{t}_{fy}"
    need = sorted(tables[(t, fy)], reverse=True)
    parts = []
    for y, col in ((fy, "cuối năm"), (fy - 1, "đầu năm")):
        parts.append(f"{y} ({col}{'' if y in need else ', đã có — đối chiếu'})")
    src = LABEL_FROM.get(key, VSIC_FROM)
    src_txt = f"BCTC {src.replace('_', ' ')}" if key in LABEL_FROM else f"21 nhóm VSIC (theo {src.replace('_', ' ')})"
    if t in WARN:
        src_txt += f". {WARN[t]}"
    D = "dong"
    rng = f"{D}!$A:$A"
    row = [
        key, f"=LEFT(A{i},3)", f"=VALUE(RIGHT(A{i},4))", "; ".join(parts), "chưa nhập", None, None,
        f'=COUNTIFS({rng},A{i},{D}!$C:$C,"I",{D}!$G:$G,"<>")',
        f'=SUMIFS({D}!$G:$G,{rng},A{i},{D}!$C:$C,"I")', f'=SUMIFS({D}!$G:$G,{rng},A{i},{D}!$C:$C,"T")', f"=I{i}-J{i}",
        f'=SUMIFS({D}!$H:$H,{rng},A{i},{D}!$C:$C,"I")', f'=SUMIFS({D}!$H:$H,{rng},A{i},{D}!$C:$C,"T")', f"=L{i}-M{i}",
        (f'=IF(COUNTIFS({rng},A{i},{D}!$C:$C,"T")<>1,"cần 1 dòng T",'
         f'IF(OR(J{i}=0,M{i}=0),"chưa đủ số",IF(AND(ABS(K{i})<=2,ABS(N{i})<=2),"KHỚP","LỆCH")))'),
        WHERE[t], src_txt, None,
    ]
    for j, v in enumerate(row):
        c = bg.cell(row=i, column=j + 1, value=v)
        c.font = f_norm
        c.border = Border(bottom=thin)
        c.alignment = Alignment(vertical="top", wrap_text=j in (3, 15, 16, 17))
        if j in (1, 2, 7, 8, 9, 10, 11, 12, 13, 14):
            c.fill = fill_formula
        if j in (4, 5, 6, 17):
            c.fill = fill_input
            c.font = f_blue
        if j in (8, 9, 10, 11, 12, 13):
            c.number_format = "#,##0;-#,##0;0"
    bg.cell(row=i, column=1).font = f_bold
    bg.cell(row=i, column=15).font = f_bold
last_bang = len(order) + 1
bg.freeze_panes = "B2"
bg.auto_filter.ref = f"A1:R{last_bang}"

dv_status = DataValidation(type="list", formula1='"chưa nhập,đã nhập,không tìm được file"', allow_blank=False,
                           showErrorMessage=True, errorTitle="Trạng thái", error="Chọn trong danh sách.")
bg.add_data_validation(dv_status)
dv_status.add(f"E2:E{last_bang + 20}")
dv_page = DataValidation(type="whole", operator="between", formula1="1", formula2="2000", allow_blank=True,
                         showErrorMessage=True, errorTitle="Trang PDF", error="Số nguyên, số trang của trình đọc PDF.")
bg.add_data_validation(dv_page)
dv_page.add(f"G2:G{last_bang + 20}")

green = PatternFill("solid", fgColor="C6EFCE")
red = PatternFill("solid", fgColor="FFC7CE")
bg.conditional_formatting.add(f"O2:O{last_bang}", FormulaRule(formula=[f'O2="KHỚP"'], fill=green, font=Font(name=FONT, color="006100", bold=True)))
bg.conditional_formatting.add(f"O2:O{last_bang}", FormulaRule(formula=[f'OR(O2="LỆCH",O2="cần 1 dòng T")'], fill=red, font=Font(name=FONT, color="9C0006", bold=True)))
bg.conditional_formatting.add(f"A2:R{last_bang}", FormulaRule(formula=[f'AND($E2="đã nhập",$O2<>"KHỚP")'], fill=red))


wb.move_sheet("dong", offset=-1)
wb.calculation.fullCalcOnLoad = True
OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)
print(OUT, "tables", len(order), "bank_years", n_by, "rows", last_dong - 1)
print(wb.sheetnames)
