from __future__ import annotations

import csv
import difflib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

if os.environ.get("KL_PYLIB"):
    sys.path.insert(0, os.environ["KL_PYLIB"])
import docx  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402

GOC = Path(__file__).resolve().parents[1]
REPO = GOC.parent
sys.path.insert(0, str(GOC))
sys.path.insert(0, str(GOC / "cong_cu"))
from tai_lieu import TAI_LIEU  # noqa: E402
import build_docx as bd  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
FILE_CHUONG = [("MỞ ĐẦU", "00_mo_dau.md"), ("CHƯƠNG 1", "01_tong_quan.md"), ("CHƯƠNG 2", "02_co_so_ly_thuyet.md"),
               ("CHƯƠNG 3", "03_phuong_phap.md"), ("CHƯƠNG 4", "04_he_thong.md"), ("CHƯƠNG 5", "05_ket_qua.md"),
               ("KẾT LUẬN", "06_ket_luan.md"), ("PHỤ LỤC", "07_phu_luc.md")]
# bảng / hình mới (10/11/2026) chưa có trong Markdown cũ: tiền tố tên → (nhãn, đường dẫn hình)
MOI = {
    "Sơ đồ tổng thể của hệ thống": ("so_do_tong_the", "figures/khoa_luan/so_do/h1_so_do_tong_the.png"),
    "So sánh hai mô hình ra quyết định": ("hai_mo_hinh", None),
    "RMSE và MAPE": ("rmse_mape", None),
    "Độ ổn định của mức giảm MAE": ("on_dinh", None),
    "Phép thử cảnh báo NPL": ("canh_bao", None),
    "Độ nhạy của xếp hạng gửi 12 tháng": ("do_nhay_trong_so", "figures/khoa_luan/chuong4/h_do_nhay_trong_so.png"),
    "Độ nhạy của bảng xếp hạng khi thay đổi": ("do_nhay", None),
    "Kết quả kiểm thử dữ liệu không hợp lệ": ("khong_hop_le", None),
    "Kết quả kiểm thử giao diện": ("giao_dien", None),
    "Kết quả kiểm thử nhiều người dùng": ("dong_thoi", None),
    "Kết quả kiểm thử tình huống lỗi": ("tinh_huong_loi", None),
}


def ky_tu_toan(s: str) -> str:
    out = []
    for ch in s:
        cp = ord(ch)
        out.append(unicodedata.normalize("NFKC", ch) if 0x1D400 <= cp <= 0x1D7FF or ch == "ℎ" else ch)
    return "".join(out).replace("−", "-")


def chuan(s: str) -> str:
    s = re.sub(r"[*“”\"«»]", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def ban_do_trich_dan(doc) -> dict[int, str]:
    tl = {}
    for p in doc.paragraphs:
        m = re.match(r"^\[(\d+)\]\s*(.*)$", p.text.strip())
        if p.style.name == "KL Tai lieu" and m:
            tl[int(m.group(1))] = chuan(m.group(2))
    keys = {k: chuan(v) for k, v in TAI_LIEU.items()}
    out = {}
    for n, txt in tl.items():
        best = max(keys, key=lambda k: difflib.SequenceMatcher(None, keys[k][:120], txt[:120]).ratio())
        r = difflib.SequenceMatcher(None, keys[best][:120], txt[:120]).ratio()
        if r < 0.85:
            raise SystemExit(f"Không khớp tài liệu [{n}] ({r:.2f}): {txt[:80]}")
        out[n] = best
    if len(set(out.values())) != len(out):
        raise SystemExit("Hai số trích dẫn khớp cùng một khóa")
    return out


def md_cu():
    cu = {}
    for _, f in FILE_CHUONG:
        p = GOC / "noi_dung" / f
        if not p.exists():
            continue
        txt = p.read_text(encoding="utf-8")
        bd.DO_RONG.clear()
        kh = bd.doc_khoi(txt)
        cu[f] = dict(fig=[(b[1], b[2], b[3]) for b in kh if b[0] == "fig"],
                     tab=[(b[1], b[2]) for b in kh if b[0] == "tab"],
                     eq=[(b[1], b[2]) for b in kh if b[0] == "eq"])
    return cu


def khop_ten(ten: str, ds: list, da_dung: set):
    ten_c = chuan(ten)
    best, r_best = None, 0.0
    for i, x in enumerate(ds):
        if i in da_dung:
            continue
        r = difflib.SequenceMatcher(None, chuan(bd.CITE.sub("", x[0])), ten_c).ratio()
        if r > r_best:
            best, r_best = i, r
    return best, r_best


class Chuyen:
    def __init__(self, doc, cong_thuc: list, cite: dict[int, str]):
        self.doc, self.ct, self.cite = doc, cong_thuc, cite
        self.i_ct = 0
        self.nhan = {}       # "Bảng 5.9" -> "tab:xxx", "Hình 3.22" -> "fig:yyy", "(2.3)" -> "eq:zzz"

    # ---------------------------------------------------------------- chữ trong đoạn
    def _run_md(self, r) -> str:
        parts = []
        for ch in r:
            if ch.tag == W + "t":
                parts.append(ch.text or "")
            elif ch.tag == W + "tab":
                parts.append("\t")
            elif ch.tag in (W + "br", W + "cr"):
                parts.append(" ")
        s = "".join(parts)
        if not s.strip():
            return s
        rpr = r.find(W + "rPr")

        def bat(tag):
            e = rpr.find(W + tag) if rpr is not None else None
            return e is not None and e.get(W + "val") not in ("0", "false")
        fonts = rpr.find(W + "rFonts") if rpr is not None else None
        code = fonts is not None and "Consolas" in (fonts.get(W + "ascii") or "")
        if code:
            return f"`{s}`"
        lead = s[: len(s) - len(s.lstrip())]
        tail = s[len(s.rstrip()):]
        core = s.strip()
        if bat("b"):
            core = f"**{core}**"
        if bat("i"):
            core = f"*{core}*"
        return lead + core + tail

    def _math(self, om) -> str:
        e = self.ct[self.i_ct]
        self.i_ct += 1
        lin = e["text"]
        lin = re.sub(r"^█\((.*)#\([\d.]+\)\s*\)\s*$", r"\1", lin.strip(), flags=re.S).strip()
        return ky_tu_toan(lin)

    def chu(self, p_el) -> str:
        out = []
        for ch in p_el:
            if ch.tag == W + "r":
                out.append(("t", self._run_md(ch)))
            elif ch.tag == W + "hyperlink":
                for r in ch.findall(W + "r"):
                    out.append(("t", self._run_md(r)))
            elif ch.tag == M + "oMath":
                out.append(("m", "$" + self._math(ch) + "$"))
            elif ch.tag == M + "oMathPara":
                for om in ch.findall(M + "oMath"):
                    out.append(("m", "$" + self._math(om) + "$"))
        s = ""
        for kind, t in out:
            s += t if kind == "m" else self._doi_chu(t)
        s = re.sub(r"\*\*\s*\*\*", "", s)
        s = re.sub(r"`\s*`", "", s)
        s = re.sub(r"`([^`]*)``([^`]*)`", r"`\1\2`", s)
        return re.sub(r"[ \t]+", " ", s).strip()

    def _doi_chu(self, t: str) -> str:
        if t.startswith("`"):
            return t

        def cite(m):
            n = int(m.group(1))
            return f"[@{self.cite[n]}]" if n in self.cite else m.group(0)
        t = re.sub(r"\[(\d{1,2})\]", cite, t)
        return t

    def doi_nhan(self, s: str) -> str:
        def ref(m):
            k = f"{m.group(1).capitalize()} {m.group(2)}"
            if k not in self.nhan:
                return m.group(0)
            kind, lid = self.nhan[k].split(":")
            return f"@{kind.capitalize() if m.group(1)[0].isupper() else kind}:{lid}"
        s = re.sub(r"\b(Bảng|Hình|bảng|hình) (\d+\.\d+)(?!\.\d)(?!\d)", ref, s)

        def eq(m):
            k = f"({m.group(1)})"
            return f"@eq:{self.nhan[k].split(':')[1]}" if k in self.nhan else m.group(0)
        return re.sub(r"\((\d\.\d{1,2})\)", eq, s)


def bang_md(tbl, cv: Chuyen) -> list[list[str]]:
    rows = []
    for tr in tbl.findall(W + "tr"):
        row = []
        for tc in tr.findall(W + "tc"):
            ps = [cv.chu(p) for p in tc.findall(W + "p")]
            cell = " ".join(x for x in ps if x).replace("|", "/")
            if len(rows) == 0:
                cell = cell.replace("**", "")
            row.append(cell)
        rows.append(row)
    return rows


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    src, ct_path = sys.argv[1], sys.argv[2]
    doc = docx.Document(src)
    cong_thuc = json.loads(Path(ct_path).read_text(encoding="utf-8-sig"))
    n_om = sum(1 for _ in doc.element.body.iter(M + "oMath"))
    if n_om != len(cong_thuc):
        raise SystemExit(f"Số công thức lệch: Word {n_om}, JSON {len(cong_thuc)}")
    cite = ban_do_trich_dan(doc)
    cu = md_cu()
    cv = Chuyen(doc, cong_thuc, cite)
    body = list(doc.element.body.iterchildren())

    # lượt 1: gom khối theo file, ghi nhãn cho bảng/hình/công thức
    blocks: dict[str, list] = {}
    cur = None
    in_tltk = False
    started = False
    i = 0
    da_dung = {}
    n_eq = {}

    def style(el):
        s = el.find(f"{W}pPr/{W}pStyle")
        sid = s.get(W + "val") if s is not None else "Normal"
        try:
            return doc.styles.get_by_id(sid, docx.enum.style.WD_STYLE_TYPE.PARAGRAPH).name
        except Exception:
            return sid

    # bỏ qua công thức nằm trước MỞ ĐẦU (không có) nhưng vẫn phải đếm đúng thứ tự
    while i < len(body):
        el = body[i]
        if el.tag == W + "p":
            sn = style(el)
            txt = "".join(t.text or "" for t in el.iter(W + "t")).strip()
            if sn == "1" and txt:
                key = next((f for k, f in FILE_CHUONG if txt.upper().startswith(k)), None)
                if txt.upper().startswith("MỞ ĐẦU"):
                    started = True
                if started:
                    in_tltk = txt.upper().startswith("TÀI LIỆU THAM KHẢO")
                    cur = key
                    if cur:
                        blocks.setdefault(cur, []).append(("h", 1, txt))
                i += 1
                continue
            if not started or in_tltk or cur is None:
                for om in el.iter(M + "oMath"):
                    cv._math(om)   # giữ đúng thứ tự công thức
                i += 1
                continue
            if sn in ("KL Muc 2", "KL Muc phu luc", "KL Muc 3", "KL Muc 4"):
                lv = {"KL Muc 2": 2, "KL Muc phu luc": 2, "KL Muc 3": 3, "KL Muc 4": 4}[sn]
                blocks[cur].append(("h", lv, cv.chu(el)))
            elif sn == "KL Hinh":
                ext = el.find(".//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}extent")
                w_cm = round(int(ext.get("cx")) / 360000, 1) if ext is not None else 15.0
                cap_el = body[i + 1]
                cap = cv.chu(cap_el)
                m = re.match(r"^Hình (\d+\.\d+):\s*(.*)$", cap)
                so, ten = m.group(1), m.group(2)
                ds = cu.get(cur, {}).get("fig", [])
                j, r = khop_ten(ten, ds, da_dung.setdefault((cur, "fig"), set()))
                if j is not None and r >= 0.6:
                    da_dung[(cur, "fig")].add(j)
                    lid, path = ds[j][1], ds[j][2]
                else:
                    lid, path = next((v for k, v in MOI.items() if ten.startswith(k)), (None, None))
                    if lid is None:
                        raise SystemExit(f"Hình {so} không khớp ({r:.2f}): {ten} | gần nhất: "
                                         f"{ds[j][0] if j is not None else '-'}")
                    print(f"  hình mới {so}: {lid}")
                if not (REPO / path).exists():
                    raise SystemExit(f"Thiếu tệp hình {path} (Hình {so})")
                cv.nhan[f"Hình {so}"] = f"fig:{lid}"
                blocks[cur].append(("fig", ten, lid, path, w_cm))
                i += 2
                continue
            elif sn == "Ten bang":
                cap = cv.chu(el)
                m = re.match(r"^Bảng (\d+\.\d+):\s*(.*)$", cap)
                so, ten = m.group(1), m.group(2)
                ds = cu.get(cur, {}).get("tab", [])
                j, r = khop_ten(ten, ds, da_dung.setdefault((cur, "tab"), set()))
                if j is not None and r >= 0.5:
                    da_dung[(cur, "tab")].add(j)
                    lid = ds[j][1]
                else:
                    lid = next((v[0] for k, v in MOI.items() if ten.startswith(k)), None)
                    if lid is None:
                        raise SystemExit(f"Bảng {so} không khớp ({r:.2f}): {ten} | gần nhất: "
                                         f"{ds[j][0] if j is not None else '-'}")
                    print(f"  bảng mới {so}: {lid}")
                cv.nhan[f"Bảng {so}"] = f"tab:{lid}"
                tbl = body[i + 1]
                assert tbl.tag == W + "tbl", cap
                blocks[cur].append(("tab", ten, lid, bang_md(tbl, cv)))
                i += 2
                continue
            elif sn == "KL Cong thuc":
                n_eq[cur] = n_eq.get(cur, 0) + 1
                om = next(el.iter(M + "oMath"))
                raw = cv.ct[cv.i_ct]["text"]
                so = re.search(r"#\(([\d.]+)\)", raw).group(1)
                expr = cv._math(om)
                lid = cu[cur]["eq"][n_eq[cur] - 1][1]
                cv.nhan[f"({so})"] = f"eq:{lid}"
                blocks[cur].append(("eq", expr, lid))
            elif sn == "KL Nguon":
                t = cv.chu(el)
                if t:
                    blocks[cur].append(("src", t))
            elif sn == "KL Gach dau dong" or (sn == "KL Doan" and re.match(r"^-\s", "".join(
                    t.text or "" for t in el.iter(W + "t")))):
                t = cv.chu(el)
                blocks[cur].append(("li", re.sub(r"^-\s*", "", t)))
            else:
                if el.find(".//" + W + "drawing") is not None:
                    raise SystemExit(f"Hình không có kiểu KL Hinh: {txt[:60]}")
                t = cv.chu(el)
                if t:
                    blocks[cur].append(("p", t))
        elif el.tag == W + "tbl" and started and not in_tltk:
            raise SystemExit("Bảng không có tên ngay trên")
        i += 1

    # lượt 2: viết Markdown, đổi số bảng/hình/công thức trong câu thành nhãn
    for f, kh in blocks.items():
        lines = []
        for b in kh:
            k = b[0]
            if k == "h":
                lines += ["#" * b[1] + " " + (cv.doi_nhan(b[2]) if b[1] > 1 else b[2]), ""]
            elif k == "p":
                lines += [cv.doi_nhan(b[1]), ""]
            elif k == "li":
                lines.append("- " + cv.doi_nhan(b[1]))
                lines.append("")
            elif k == "src":
                lines += [("" if b[1].startswith("Nguồn:") else "^ ") + cv.doi_nhan(b[1]), ""]
            elif k == "fig":
                w = "" if abs(b[4] - 15.0) < 0.05 else f" w={b[4]:g}"
                lines += [f"![{cv.doi_nhan(b[1])}]({b[3]}) {{#fig:{b[2]}{w}}}", ""]
            elif k == "tab":
                rows = b[3]
                ncol = max(len(r) for r in rows)
                lines.append(f"Bảng: {cv.doi_nhan(b[1])} {{#tab:{b[2]}}}")
                lines.append("| " + " | ".join(rows[0]) + " |")
                lines.append("|" + "---|" * ncol)
                for r in rows[1:]:
                    lines.append("| " + " | ".join(cv.doi_nhan(c) for c in r) + " |")
                lines.append("")
            elif k == "eq":
                lines += [f"$$ {b[1]} $$ {{#eq:{b[2]}}}", ""]
        # gộp các gạch đầu dòng liền nhau (bỏ dòng trống giữa chúng)
        txt = "\n".join(lines)
        txt = re.sub(r"(\n- [^\n]*)\n\n(?=- )", r"\1\n", txt)
        txt = re.sub(r"(\n- [^\n]*)\n\n(?=- )", r"\1\n", txt)
        (GOC / "noi_dung" / f).write_text(txt.rstrip() + "\n", encoding="utf-8")
        print(f"ghi noi_dung/{f}: {len(kh)} khối")

    # danh mục viết tắt và thông tin bìa, lời cam đoan, lời cảm ơn
    tbl = doc.tables[0]
    with open(GOC / "viet_tat.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["tu_viet_tat", "y_nghia"])
        for r in tbl.rows[1:]:
            a = r.cells[0].text.strip()
            b = " ".join(p.text.strip() for p in r.cells[1].paragraphs if p.text.strip())
            w.writerow([a, b])
    print("ghi viet_tat.csv:", len(tbl.rows) - 1, "dòng")
    info = json.loads((GOC / "thong_tin.json").read_text(encoding="utf-8"))
    ps = doc.paragraphs
    for p in ps[:60]:
        m = re.match(r"^(Tên sinh viên|Mã sinh viên|Lớp|Ngành|Giảng viên hướng dẫn)\s*:\s*(.+)$", p.text.strip())
        if m:
            info[{"Tên sinh viên": "ten_sv", "Mã sinh viên": "ma_sv", "Lớp": "lop", "Ngành": "nganh",
                  "Giảng viên hướng dẫn": "gvhd"}[m.group(1)]] = m.group(2).strip()
    info["_to_vang"] = [k for k in info.get("_to_vang", []) if str(info.get(k, "")).startswith("[")]

    def doan_giua(a, b):
        out, on = [], False
        for p in ps:
            t = p.text.strip()
            if p.style.name == "1" and t.startswith(a):
                on = True
                continue
            if on and p.style.name == "1" and t.startswith(b):
                break
            if on and t and not t.startswith(("Hà Nội, ngày", "Sinh viên", "(ký, ghi rõ")):
                out.append(t)
        return out
    info["loi_cam_doan"] = doan_giua("LỜI CAM ĐOAN", "LỜI CẢM ƠN")
    info["loi_cam_on"] = doan_giua("LỜI CẢM ƠN", "DANH MỤC")
    (GOC / "thong_tin.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ghi thong_tin.json:", {k: info[k] for k in ("ten_sv", "ma_sv", "lop", "nganh", "gvhd")})
    if cv.i_ct != len(cong_thuc):
        print(f"CẢNH BÁO: dùng {cv.i_ct}/{len(cong_thuc)} công thức")


if __name__ == "__main__":
    main()
