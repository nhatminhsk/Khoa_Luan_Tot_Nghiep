from __future__ import annotations

import csv
import json
import os
import re
import sys
from pathlib import Path

if os.environ.get("KL_PYLIB"):
    sys.path.insert(0, os.environ["KL_PYLIB"])

import docx  # noqa: E402
from docx.enum.style import WD_STYLE_TYPE  # noqa: E402
from docx.enum.table import WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX, WD_TAB_ALIGNMENT  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

GOC = Path(__file__).resolve().parents[1]          # khoa_luan/
REPO = GOC.parent                                   # D:/KLTN
MAU = GOC / "cong_cu" / "mau_fit_neu.docx"
NOI_DUNG = GOC / "noi_dung"
# KL_DAU_RA: ghi ra chỗ khác (dựng thử), vì từ 07/11/2026 file Word trong dau_ra/ là bản gốc sửa tay
DAU_RA = Path(os.environ.get("KL_DAU_RA", GOC / "dau_ra" / "khoa_luan.docx"))

sys.path.insert(0, str(GOC))
from tai_lieu import TAI_LIEU  # noqa: E402

# Thứ tự chương; file nào chưa có thì bỏ qua.
CAC_FILE = [
    "00_mo_dau.md",
    "01_tong_quan.md",
    "02_co_so_ly_thuyet.md",
    "03_phuong_phap.md",
    "04_he_thong.md",
    "05_ket_qua.md",
    "06_ket_luan.md",
    "07_phu_luc.md",
]

# ---------------------------------------------------------------- tiện ích XML

def _fld(paragraph, instr: str, placeholder: str = "") -> None:
    def run_with(child):
        r = OxmlElement("w:r")
        r.append(child)
        paragraph._p.append(r)
        return r
    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin"); b.set(qn("w:dirty"), "true")
    run_with(b)
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = f" {instr} "
    run_with(it)
    s = OxmlElement("w:fldChar"); s.set(qn("w:fldCharType"), "separate")
    run_with(s)
    t = OxmlElement("w:t"); t.text = placeholder or "(Mở file bằng Word, bấm F9 để cập nhật)"
    run_with(t)
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end")
    run_with(e)


def _set_outline(style, level: int | None) -> None:
    ppr = style.element.get_or_add_pPr()
    for old in ppr.findall(qn("w:outlineLvl")):
        ppr.remove(old)
    if level is not None:
        o = OxmlElement("w:outlineLvl"); o.set(qn("w:val"), str(level)); ppr.append(o)


def _style(doc, name: str, base: str = "Normal"):
    try:
        return doc.styles[name]
    except KeyError:
        s = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        s.base_style = doc.styles[base]
        return s


def _font(style_or_run, size=13, bold=None, italic=None):
    f = style_or_run.font
    f.name = "Times New Roman"
    f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    rpr = style_or_run.element.get_or_add_rPr() if hasattr(style_or_run, "element") else None
    if rpr is not None:
        fonts = rpr.find(qn("w:rFonts"))
        if fonts is None:
            fonts = OxmlElement("w:rFonts"); rpr.insert(0, fonts)
        for k in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            fonts.set(qn(k), "Times New Roman")
        for k in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
            if fonts.get(qn(k)) is not None:
                del fonts.attrib[qn(k)]
        col = rpr.find(qn("w:color"))
        if col is not None:
            rpr.remove(col)


def chuan_bi_style(doc) -> None:
    ch = doc.styles["1"]                       # tên chương của mẫu: 18, đậm, giữa
    _font(ch, 18, bold=True)
    _set_outline(ch, 0)
    ch.paragraph_format.keep_with_next = True
    ch.paragraph_format.space_before = Pt(0)
    ch.paragraph_format.space_after = Pt(12)
    ch.paragraph_format.first_line_indent = Cm(0)

    for name, lvl, italic in (("KL Muc 2", 1, False), ("KL Muc 3", 2, False), ("KL Muc 4", 3, True)):
        s = _style(doc, name)
        _font(s, 13, bold=True, italic=italic)
        s.paragraph_format.keep_with_next = True
        s.paragraph_format.first_line_indent = Cm(0)
        s.paragraph_format.left_indent = Cm(0)
        s.paragraph_format.space_before = Pt(6)
        s.paragraph_format.space_after = Pt(0)
        s.paragraph_format.line_spacing = 1.3
        s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        _set_outline(s, lvl)

    body = _style(doc, "KL Doan")
    _font(body, 13)
    pf = body.paragraph_format
    pf.first_line_indent = Cm(1)
    pf.line_spacing = 1.3
    pf.space_before = Pt(6)
    pf.space_after = Pt(0)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    pl = _style(doc, "KL Muc phu luc", "KL Muc 2")   # mục của phụ lục: như mục cấp 2 nhưng không vào mục lục
    _set_outline(pl, 9)
    gach = _style(doc, "KL Gach dau dong", "KL Doan")
    gach.paragraph_format.first_line_indent = Cm(-0.5)
    gach.paragraph_format.left_indent = Cm(1.5)

    for name, italic, bold in (("Ten bang", False, True), ("Ten hinh", True, False)):
        s = _style(doc, name)
        _font(s, 13, bold=bold, italic=italic)
        s.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        s.paragraph_format.first_line_indent = Cm(0)
        s.paragraph_format.space_before = Pt(6)
        s.paragraph_format.space_after = Pt(6)
        s.paragraph_format.keep_with_next = name == "Ten bang"

    ng = _style(doc, "KL Nguon")
    _font(ng, 12, italic=True)
    ng.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    ng.paragraph_format.first_line_indent = Cm(0)
    ng.paragraph_format.space_before = Pt(3)
    ng.paragraph_format.space_after = Pt(6)

    o = _style(doc, "KL O bang")
    _font(o, 12)
    o.paragraph_format.first_line_indent = Cm(0)
    o.paragraph_format.line_spacing = 1.0
    o.paragraph_format.space_before = Pt(3)
    o.paragraph_format.space_after = Pt(3)
    o.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    h = _style(doc, "KL Hinh")
    h.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    h.paragraph_format.first_line_indent = Cm(0)
    h.paragraph_format.keep_with_next = True
    h.paragraph_format.line_spacing = 1.0

    eq = _style(doc, "KL Cong thuc")
    _font(eq, 13)
    eq.paragraph_format.first_line_indent = Cm(0)
    eq.paragraph_format.tab_stops.add_tab_stop(Cm(8), WD_TAB_ALIGNMENT.CENTER)
    eq.paragraph_format.tab_stops.add_tab_stop(Cm(16), WD_TAB_ALIGNMENT.RIGHT)

    tl = _style(doc, "KL Tai lieu")
    _font(tl, 13)
    tl.paragraph_format.first_line_indent = Cm(-1)
    tl.paragraph_format.left_indent = Cm(1)
    # căn trái như các khóa luận mẫu: căn đều làm giãn chữ ở dòng có URL dài
    tl.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

# ------------------------------------------------------------ chữ trong đoạn

INLINE = re.compile(r"(\$[^$]+\$|\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")


def them_chu(paragraph, text: str, size=None, highlight=False) -> None:
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("$") and part.endswith("$") and len(part) > 2:
            # công thức nội dòng: hoan_thien_word.ps1 dựng lại bằng Word
            r = paragraph.add_run("EQ{{" + part[1:-1].strip() + "}}EQ")
        elif part.startswith("**") and part.endswith("**"):
            r = paragraph.add_run(part[2:-2]); r.bold = True
        elif part.startswith("*") and part.endswith("*"):
            r = paragraph.add_run(part[1:-1]); r.italic = True
        elif part.startswith("`") and part.endswith("`"):
            r = paragraph.add_run(part[1:-1]); r.font.name = "Consolas"
            if size is None:
                r.font.size = Pt(12)
        else:
            r = paragraph.add_run(part)
        if size:
            r.font.size = Pt(size)
        if highlight:
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW

# ------------------------------------------------------- trích dẫn và nhãn

class SoHieu:
    def __init__(self):
        self.cite_order: list[str] = []
        self.labels: dict[str, str] = {}   # "fig:id" -> "1.2"

    def so_trich(self, key: str) -> int:
        if key not in TAI_LIEU:
            raise SystemExit(f"Thiếu tài liệu '{key}' trong tai_lieu.py")
        if key not in self.cite_order:
            self.cite_order.append(key)
        return self.cite_order.index(key) + 1


def _gop_day_so(nums: list[int]) -> str:
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        if j - i >= 2:
            out.append(f"[{nums[i]}]–[{nums[j]}]")
        else:
            out.extend(f"[{n}]" for n in nums[i:j + 1])
        i = j + 1
    return ", ".join(out)


CITE = re.compile(r"\[(@[^\]]+)\]")
REF = re.compile(r"@(fig|Fig|tab|Tab|eq):([A-Za-z0-9_\-]+)")


def thay_trich_dan(text: str, sh: SoHieu) -> str:
    def cite(m):
        keys = [k.strip().lstrip("@") for k in m.group(1).split(";")]
        return _gop_day_so([sh.so_trich(k) for k in keys])
    text = CITE.sub(cite, text)

    def ref(m):
        kind, lid = m.group(1), m.group(2)
        key = f"{kind.lower()}:{lid}"
        if key not in sh.labels:
            raise SystemExit(f"Gọi nhãn chưa khai báo: {key}")
        num = sh.labels[key]
        if kind.lower() == "eq":
            return f"({num})"
        word = {"fig": "hình", "tab": "bảng"}[kind.lower()]
        if kind[0].isupper():
            word = word.capitalize()
        return f"{word} {num}"
    return REF.sub(ref, text)

# ------------------------------------------------------------- đọc Markdown

LABEL = re.compile(r"\s*\{#(fig|tab|eq):([A-Za-z0-9_\-]+)(?:\s+w=([\d.]+))?\}\s*$")
DO_RONG: dict[str, float] = {}   # nhãn hình -> độ rộng (cm) khi khai báo {#fig:id w=11}


def doc_khoi(text: str):
    lines = text.splitlines()
    i, out, para = 0, [], []

    def flush():
        if para:
            out.append(("p", " ".join(s.strip() for s in para)))
            para.clear()

    while i < len(lines):
        ln = lines[i].rstrip()
        s = ln.strip()
        if s.startswith("<!--"):
            while "-->" not in lines[i]:
                i += 1
            i += 1
            continue
        if not s:
            flush(); i += 1; continue
        if s == "\\newpage":
            flush(); out.append(("pagebreak",)); i += 1; continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            flush(); out.append(("h", len(m.group(1)), m.group(2).strip())); i += 1; continue
        if s.startswith("- "):
            flush(); out.append(("li", s[2:].strip())); i += 1; continue
        if s.startswith("Bảng:"):
            flush()
            cap = s[len("Bảng:"):]
            lm = LABEL.search(cap); label = lm.group(2) if lm else None
            cap = LABEL.sub("", cap).strip()
            i += 1
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            out.append(("tab", cap, label, rows)); continue
        m = re.match(r"^!\[(.*)\]\((.*)\)(.*)$", s)
        if m:
            flush()
            lm = LABEL.search(m.group(3)); label = lm.group(2) if lm else None
            if lm and lm.group(3):
                DO_RONG[label] = float(lm.group(3))
            out.append(("fig", m.group(1).strip(), label, m.group(2).strip())); i += 1; continue
        m = re.match(r"^\$\$(.*)\$\$(.*)$", s)
        if m:
            flush()
            lm = LABEL.search(m.group(2)); label = lm.group(2) if lm else None
            out.append(("eq", m.group(1).strip(), label)); i += 1; continue
        if s.startswith("Nguồn:"):
            flush(); out.append(("src", s)); i += 1; continue
        if s.startswith("^ "):
            flush(); out.append(("src", s[2:].strip())); i += 1; continue
        para.append(s); i += 1
    flush()
    return out

# ------------------------------------------------------------------ dựng

def danh_so(cac_khoi_theo_file, sh: SoHieu) -> None:
    chuong = 0
    dem = {"tab": 0, "fig": 0, "eq": 0}
    for khoi in cac_khoi_theo_file:
        for b in khoi:
            if b[0] == "h" and b[1] == 1:
                m = re.match(r"CHƯƠNG\s+(\d+)", b[2])
                if m:
                    chuong = int(m.group(1)); dem = {k: 0 for k in dem}
                elif b[2].upper().startswith("PHỤ LỤC"):
                    chuong = "A"; dem = {k: 0 for k in dem}
            elif b[0] in ("tab", "fig", "eq"):
                dem[b[0]] += 1
                num = f"{chuong}.{dem[b[0]]}"
                b_label = b[2]
                if b_label:
                    key = f"{b[0]}:{b_label}"
                    if key in sh.labels:
                        raise SystemExit(f"Nhãn trùng: {key}")
                    sh.labels[key] = num
                sh.labels[f"__{id(b)}"] = num


def _borders(table) -> None:
    tblPr = table._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:space"), "0"); e.set(qn("w:color"), "000000")
        b.append(e)
    tblPr.append(b)


def _repeat_header(row) -> None:
    trPr = row._tr.get_or_add_trPr()
    h = OxmlElement("w:tblHeader"); h.set(qn("w:val"), "true"); trPr.append(h)


def _xoa_than_mau(doc) -> None:
    body = doc.element.body
    start = None
    for el in list(body.iterchildren()):
        if el.tag == qn("w:p"):
            txt = "".join(t.text or "" for t in el.iter(qn("w:t"))).strip()
            if txt == "MỞ ĐẦU" and start is None:
                start = el
        if start is not None and el.tag != qn("w:sectPr"):
            body.remove(el)


def _thay_text(par, new: str, highlight=False) -> None:
    runs = par.runs
    if not runs:
        r = par.add_run(new)
    else:
        runs[0].text = new
        for r in runs[1:]:
            r.text = ""
        r = runs[0]
    if highlight:
        r.font.highlight_color = WD_COLOR_INDEX.YELLOW


def dien_bia_va_danh_muc(doc, info: dict, sh_ref) -> None:
    ps = doc.paragraphs
    hl = info.get("_to_vang", [])
    def nhan_gia_tri(p, nhan, key):
        _thay_text(p, nhan)
        r = p.add_run(info[key])
        r.bold = p.runs[0].bold
        r.font.size = p.runs[0].font.size
        if key in hl:
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW

    def bo_dong_trong(p, truoc, sau):
        for huong, n in (("previous", truoc), ("next", sau)):
            for _ in range(n):
                el = p._p.getprevious() if huong == "previous" else p._p.getnext()
                if el is None or el.tag != qn("w:p"):
                    break
                txt = "".join(t.text or "" for t in el.iter(qn("w:t"))).strip()
                if txt or el.find(f".//{qn('w:sectPr')}") is not None or el.find(f".//{qn('w:drawing')}") is not None \
                        or el.find(f".//{qn('w:pict')}") is not None:
                    break
                el.getparent().remove(el)

    for p in ps:
        t = p.text.strip()
        if t == "Tên đề tài":
            _thay_text(p, info["ten_de_tai"].upper())
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(18)
            bo_dong_trong(p, 1, 3)
        elif t.startswith("Tên sinh viên"):
            nhan_gia_tri(p, "Tên sinh viên\t\t: ", "ten_sv")
        elif t.startswith("Giảng viên hướng dẫn"):
            nhan_gia_tri(p, "Giảng viên hướng dẫn\t: ", "gvhd")
            bo_dong_trong(p, 0, 2)
        elif t.startswith("Mã sinh viên"):
            nhan_gia_tri(p, "Mã sinh viên\t\t: ", "ma_sv")
        elif t.startswith("Lớp"):
            nhan_gia_tri(p, "Lớp\t\t\t\t: ", "lop")
        elif t.startswith("Ngành"):
            nhan_gia_tri(p, "Ngành \t\t\t: ", "nganh")
        elif t.startswith("Hà Nội,") and "202" in t:
            _thay_text(p, f"Hà Nội, {info['thang_nam']}")
    # Gáy (khung chữ bên trái bìa): chỉ biết năm học.kỳ; các ô còn lại sinh viên tự điền.
    for t in doc.element.body.iter(qn("w:t")):
        if t.text and t.text.strip() == "Năm học, kỳ học":
            t.text = info.get("gay_nam_hoc", "2026-2027.1")

    # Mục lục và danh mục: thay bảng tĩnh của mẫu bằng trường tự động.
    body = doc.element.body
    paras = list(doc.paragraphs)

    def idx(text):
        for k, p in enumerate(paras):
            if p.text.strip() == text:
                return k
        raise SystemExit(f"Không thấy '{text}' trong mẫu")

    def xoa_giua(a_text, b_text, them):
        a, b = idx(a_text), idx(b_text)
        for p in paras[a + 1:b]:
            if p._p.find(f".//{qn('w:sectPr')}") is None and p._p.find(f".//{qn('w:tbl')}") is None:
                p._p.getparent().remove(p._p)
        anchor = paras[a]
        new_p = them(anchor)
        return new_p

    def chen_sau(anchor, builder):
        newp = OxmlElement("w:p")
        anchor._p.addnext(newp)
        p = docx.text.paragraph.Paragraph(newp, anchor._parent)
        builder(p)
        return p

    # MỤC LỤC
    xoa_giua("MỤC LỤC", "LỜI CAM ĐOAN", lambda a: chen_sau(a, lambda p: _fld(p, 'TOC \\h \\z \\t "1,1,KL Muc 2,2,KL Muc 3,3,KL Muc 4,4"')))
    paras = list(doc.paragraphs)
    # LỜI CAM ĐOAN
    def cam_doan(a):
        last = a
        for line in info["loi_cam_doan"]:
            last = chen_sau(last, lambda p, line=line: (setattr(p, "style", doc.styles["KL Doan"]), them_chu(p, line, highlight=line.startswith("["))))
        for line, align in ((f"Hà Nội, ngày      tháng {info['thang_nam'].split('/')[0]} năm {info['thang_nam'].split('/')[-1]}", 2),
                            ("Sinh viên", 2), ("(ký, ghi rõ họ tên)", 2), ("", 2), ("", 2), (info["ten_sv"], 2)):
            last = chen_sau(last, lambda p, line=line: (them_chu(p, line, highlight=(line == info["ten_sv"] and "ten_sv" in hl))))
            last.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        return last
    xoa_giua("LỜI CAM ĐOAN", "LỜI CẢM ƠN", cam_doan)
    paras = list(doc.paragraphs)
    def cam_on(a):
        last = a
        for line in info["loi_cam_on"]:
            last = chen_sau(last, lambda p, line=line: (setattr(p, "style", doc.styles["KL Doan"]), them_chu(p, line, highlight=line.startswith("["))))
        return last
    xoa_giua("LỜI CẢM ƠN", "DANH MỤC CÁC TỪ VIẾT TẮT", cam_on)
    paras = list(doc.paragraphs)
    xoa_giua("DANH MỤC BẢNG", "DANH MỤC HÌNH", lambda a: chen_sau(a, lambda p: _fld(p, 'TOC \\h \\z \\t "Ten bang,1"')))
    paras = list(doc.paragraphs)
    # DANH MỤC HÌNH: tới đoạn mang sectPr
    k = idx("DANH MỤC HÌNH")
    for p in paras[k + 1:]:
        if p._p.find(f".//{qn('w:sectPr')}") is not None:
            break
        p._p.getparent().remove(p._p)
    chen_sau(paras[k], lambda p: _fld(p, 'TOC \\h \\z \\t "Ten hinh,1"'))
    # Mỗi phần của trang đầu sang trang mới.
    for p in doc.paragraphs:
        if p.style.name == "1" and p.text.strip() in ("LỜI CAM ĐOAN", "LỜI CẢM ƠN", "DANH MỤC CÁC TỪ VIẾT TẮT",
                                                      "DANH MỤC BẢNG", "DANH MỤC HÌNH"):
            p.paragraph_format.page_break_before = True

    # Danh mục từ viết tắt: điền bảng của mẫu.
    tbl = doc.tables[0]
    rows = []
    with open(GOC / "viet_tat.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append((r["tu_viet_tat"], r["y_nghia"]))
    rows.sort(key=lambda x: x[0].upper())
    while len(tbl.rows) > 1:
        tbl._tbl.remove(tbl.rows[-1]._tr)
    hdr = tbl.rows[0].cells
    for c, t in zip(hdr, ("Từ viết tắt", "Ý nghĩa")):
        for p in c.paragraphs[1:]:
            p._p.getparent().remove(p._p)
        _thay_text(c.paragraphs[0], t)
        for r in c.paragraphs[0].runs:
            r.bold = True
    for a, b in rows:
        cells = tbl.add_row().cells
        cells[0].paragraphs[0].text = ""
        them_chu(cells[0].paragraphs[0], a)
        cells[1].paragraphs[0].text = ""
        them_chu(cells[1].paragraphs[0], b)
        for c in cells:
            c.paragraphs[0].style = doc.styles["KL O bang"]
            c.paragraphs[0].paragraph_format.space_before = Pt(4)
            c.paragraphs[0].paragraph_format.space_after = Pt(4)


def dung_than(doc, cac_khoi_theo_file, sh: SoHieu) -> None:
    body = doc.element.body
    sectPr = body.find(qn("w:sectPr"))
    first_chapter = [True]

    def new_par(style="KL Doan"):
        p = doc.add_paragraph(style=style)
        # add_paragraph thêm trước sectPr cuối: đúng chỗ.
        return p

    def la_phu_luc(khoi):
        return bool(khoi) and khoi[0][0] == "h" and khoi[0][1] == 1 and khoi[0][2].upper().startswith("PHỤ LỤC")

    def dung(khoi):
        phu_luc = la_phu_luc(khoi)
        for b in khoi:
            kind = b[0]
            if kind == "h":
                level, text = b[1], b[2]
                if level == 2 and phu_luc:
                    p = new_par("KL Muc phu luc")
                    them_chu(p, thay_trich_dan(text, sh))
                elif level == 1:
                    p = new_par("1")
                    p.paragraph_format.page_break_before = not first_chapter[0]
                    first_chapter[0] = False
                    them_chu(p, text.upper())
                else:
                    p = new_par({2: "KL Muc 2", 3: "KL Muc 3", 4: "KL Muc 4"}[level])
                    them_chu(p, thay_trich_dan(text, sh))
            elif kind == "pagebreak":
                p = new_par()
                p.add_run().add_break(docx.enum.text.WD_BREAK.PAGE)
            elif kind == "p":
                p = new_par()
                them_chu(p, thay_trich_dan(b[1], sh))
            elif kind == "li":
                p = new_par("KL Gach dau dong")
                them_chu(p, "-\t" + thay_trich_dan(b[1], sh))
                p.paragraph_format.tab_stops.add_tab_stop(Cm(1.5))
            elif kind == "src":
                p = new_par("KL Nguon")
                them_chu(p, thay_trich_dan(b[1], sh))
            elif kind == "tab":
                cap, label, rows = b[1], b[2], b[3]
                num = sh.labels[f"__{id(b)}"]
                p = new_par("Ten bang")
                them_chu(p, f"Bảng {num}: {thay_trich_dan(cap, sh)}")
                ncol = max(len(r) for r in rows)
                t = doc.add_table(rows=len(rows), cols=ncol)
                t.alignment = WD_TABLE_ALIGNMENT.CENTER
                _borders(t)
                for ri, row in enumerate(rows):
                    for ci in range(ncol):
                        cell = t.cell(ri, ci)
                        cp = cell.paragraphs[0]
                        cp.style = doc.styles["KL O bang"]
                        them_chu(cp, thay_trich_dan(row[ci] if ci < len(row) else "", sh))
                        if ri == 0:
                            for r in cp.runs:
                                r.bold = True
                            cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    if ri == 0:
                        _repeat_header(t.rows[0])
            elif kind == "fig":
                cap, label, path = b[1], b[2], b[3]
                num = sh.labels[f"__{id(b)}"]
                p = new_par("KL Hinh")
                img = (REPO / path) if not Path(path).is_absolute() else Path(path)
                if img.exists():
                    p.add_run().add_picture(str(img), width=Cm(DO_RONG.get(label, 15)))
                else:
                    them_chu(p, f"[THIẾU HÌNH: {path}]", highlight=True)
                c = new_par("Ten hinh")
                them_chu(c, f"Hình {num}: {thay_trich_dan(cap, sh)}")
            elif kind == "eq":
                expr, label = b[1], b[2]
                num = sh.labels[f"__{id(b)}"]
                p = new_par("KL Cong thuc")
                # Word (hoan_thien_word.ps1) dựng công thức từ phần giữa hai dấu mốc; "#(n)" là cú pháp
                # đánh số công thức của Word: công thức hiển thị riêng dòng, số căn lề phải.
                p.add_run(f"EQ{{{{{expr}#({num})}}}}EQ")

    for khoi in cac_khoi_theo_file:
        if not la_phu_luc(khoi):
            dung(khoi)
    # TÀI LIỆU THAM KHẢO
    p = new_par("1"); p.paragraph_format.page_break_before = True
    them_chu(p, "TÀI LIỆU THAM KHẢO")
    for k, key in enumerate(sh.cite_order, 1):
        p = new_par("KL Tai lieu")
        them_chu(p, f"[{k}]\t{TAI_LIEU[key]}")
        p.paragraph_format.tab_stops.add_tab_stop(Cm(1))
    # PHỤ LỤC đặt sau tài liệu tham khảo
    for khoi in cac_khoi_theo_file:
        if la_phu_luc(khoi):
            dung(khoi)


def main() -> None:
    info = json.loads((GOC / "thong_tin.json").read_text(encoding="utf-8"))
    doc = docx.Document(str(MAU))
    chuan_bi_style(doc)
    cac_khoi = []
    for name in CAC_FILE:
        f = NOI_DUNG / name
        if f.exists():
            cac_khoi.append(doc_khoi(f.read_text(encoding="utf-8")))
    sh = SoHieu()
    danh_so(cac_khoi, sh)
    dien_bia_va_danh_muc(doc, info, sh)
    _xoa_than_mau(doc)
    dung_than(doc, cac_khoi, sh)
    # Không ghi tên tác giả máy vào thuộc tính tài liệu.
    cp = doc.core_properties
    cp.author = info["ten_sv"] if not info["ten_sv"].startswith("[") else ""
    cp.last_modified_by = cp.author
    cp.title = info["ten_de_tai"]
    cp.comments = ""
    cp.keywords = ""
    cp.subject = ""
    DAU_RA.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(DAU_RA))
    unused = sorted(set(TAI_LIEU) - set(sh.cite_order))
    print(f"Đã ghi {DAU_RA}")
    print(f"Tài liệu được trích: {len(sh.cite_order)}; có trong tai_lieu.py nhưng chưa trích: {len(unused)}")
    if unused:
        print("  " + ", ".join(unused))


if __name__ == "__main__":
    main()
