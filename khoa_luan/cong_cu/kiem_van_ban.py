from __future__ import annotations

import re
import statistics
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
GOC = Path(__file__).resolve().parents[1] / "noi_dung"

AN = {
    "​": "", "‌": "", "‍": "", "‎": "", "‏": "", "⁠": "", "⁢": "",
    "⁣": "", "⁤": "", "﻿": "", "­": "", "‪": "", "‫": "", "‬": "",
    "‭": "", "‮": "", "⁦": "", "⁧": "", "⁨": "", "⁩": "", "️": "",
    "—": ", ",          # gạch dài: không dùng trong văn bản này
    "“": '"', "”": '"', "‘": "'", "’": "'",
    " ": " ", " ": " ",
}

CUM_TU = [
    "đóng vai trò", "không chỉ", "mà còn", "góp phần", "then chốt", "mạnh mẽ", "toàn diện", "tối ưu hóa",
    "nâng cao", "đáng chú ý", "đáng lưu ý", "điều này cho thấy", "nhìn chung", "tóm lại", "có thể thấy",
    "bức tranh", "khía cạnh", "hành trình", "liền mạch", "hiện thực hóa", "đột phá", "vững chắc",
    "trong bối cảnh", "ngày càng", "sâu sắc", "minh chứng", "nhấn mạnh", "bên cạnh đó", "hơn nữa",
    "đặc biệt là", "một cách", "vô cùng", "cực kỳ", "hệ sinh thái", "kỷ nguyên", "chìa khóa", "nổi bật",
    "tiềm năng", "đa dạng", "linh hoạt", "hiệu quả", "quan trọng", "rõ ràng", "giải pháp", "trải nghiệm",
    "thực sự", "thật sự", "cung cấp cái nhìn", "đặt nền móng", "mở ra", "không thể phủ nhận",
]


def bo_phan_khong_phai_van(s: str) -> str:
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"^\$\$.*$", " ", s, flags=re.M)
    s = re.sub(r"\$[^$]+\$", "X", s)
    s = re.sub(r"\{#[^}]+\}", "", s)
    s = re.sub(r"\[@[^\]]+\]", "", s)
    s = re.sub(r"^\|.*$", " ", s, flags=re.M)           # bảng
    s = re.sub(r"^(#+|Bảng:|Nguồn:|!\[).*$", " ", s, flags=re.M)
    return s


def cau(s: str) -> list[str]:
    s = re.sub(r"\s+", " ", s)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ỹ\"(@0-9])", s)
    return [p.strip() for p in parts if len(p.split()) >= 3]


def main(sua: bool) -> None:
    tong = []
    for f in sorted(GOC.glob("*.md")):
        raw = f.read_text(encoding="utf-8")
        bad = {ch: raw.count(ch) for ch in AN if ch in raw}
        if bad:
            print(f"{f.name}: ký tự cần xử lý {{{', '.join(f'U+{ord(c):04X}×{n}' for c, n in bad.items())}}}")
            if sua:
                for ch, rep in AN.items():
                    raw = raw.replace(ch, rep)
                f.write_text(raw, encoding="utf-8")
                print("   đã sửa")
        text = bo_phan_khong_phai_van(raw)
        low = text.lower()
        hits = {k: low.count(k) for k in CUM_TU if low.count(k)}
        cs = cau(text)
        lens = [len(c.split()) for c in cs]
        words = sum(lens)
        tong += lens
        cv = statistics.pstdev(lens) / statistics.mean(lens) if lens else 0
        print(f"\n{f.name}: {words} từ, {len(lens)} câu, TB {statistics.mean(lens):.1f} từ/câu, CV {cv:.2f}, "
              f"ngắn nhất {min(lens)}, dài nhất {max(lens)}")
        if hits:
            print("   cụm từ cần xem lại:", ", ".join(f"{k}×{v}" for k, v in sorted(hits.items(), key=lambda x: -x[1])))
        dai = [c for c in cs if len(c.split()) > 45]
        for c in dai:
            print(f"   câu dài ({len(c.split())} từ): {c[:110]}...")
    if tong:
        cv = statistics.pstdev(tong) / statistics.mean(tong)
        print(f"\nTOÀN BỘ: {sum(tong)} từ, {len(tong)} câu, CV độ dài câu {cv:.2f}")


if __name__ == "__main__":
    main("--sua" in sys.argv)
