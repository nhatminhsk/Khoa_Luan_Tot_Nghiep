from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

try:
    from IPython.display import display
except ImportError:  # chạy ngoài notebook
    display = print

LINE = "-" * 100


def _read_one(path: str, encoding: str, sep: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[-1].lower()
    if ext == ".csv":
        return pd.read_csv(path, encoding=encoding, sep=sep, low_memory=False)
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path)
    if ext == ".parquet":
        return pd.read_parquet(path)
    if ext == ".json":
        return pd.read_json(path)
    raise ValueError(f"⚠️ Định dạng file không hỗ trợ: {ext}")


def suspicious_types(df: pd.DataFrame, share: float = 0.9) -> pd.DataFrame:
    """Cột object nhưng >= 90% giá trị đổi được sang số hoặc ngày giờ -> có thể đang sai kiểu."""
    rows = []
    for c in df.select_dtypes(include="object").columns:
        s = df[c].dropna()
        if s.empty:
            continue
        sample = s.sample(min(len(s), 5000), random_state=0)
        num = pd.to_numeric(sample.astype(str).str.strip().str.replace(",", ""), errors="coerce").notna().mean()
        if num >= share:
            rows.append((c, "có thể là SỐ", f"{num:.0%} giá trị đổi được sang số"))
            continue
        with pd.option_context("mode.chained_assignment", None):
            dt = pd.to_datetime(sample, errors="coerce", format="mixed").notna().mean() if sample.astype(str).str.contains(r"\d{4}-\d{2}-\d{2}").mean() > 0.5 else 0
        if dt >= share:
            rows.append((c, "có thể là NGÀY GIỜ", f"{dt:.0%} giá trị đổi được sang datetime"))
    return pd.DataFrame(rows, columns=["cột", "nghi vấn", "căn cứ"])


def inconsistent_categories(df: pd.DataFrame, max_unique: int = 60) -> pd.DataFrame:
    """Giá trị phân loại chỉ khác nhau ở chữ hoa/thường hoặc khoảng trắng."""
    rows = []
    for c in df.select_dtypes(include="object").columns:
        vals = df[c].dropna().unique()
        if len(vals) > max_unique:
            continue
        groups: dict[str, list] = {}
        for v in vals:
            groups.setdefault(str(v).strip().lower(), []).append(v)
        for k, vs in groups.items():
            if len(vs) > 1:
                rows.append((c, k, vs))
    return pd.DataFrame(rows, columns=["cột", "giá trị chuẩn", "các cách viết"])


def read_and_explore_data(
    file_path: str,
    encoding: str = "utf-8-sig",
    sep: str = ",",
    drop_columns: list | None = None,
    target: str | None = None,
    auto_drop_missing: bool = False,
    auto_drop_duplicates: bool = False,
    show: bool = True,
    key_columns: list | None = None,
    pattern: str = "*.csv",
) -> pd.DataFrame:
    """Đọc và khám phá sơ bộ dữ liệu (bản dùng cho notebook, VS Code hoặc Colab).

    Thực hiện:
    - Đọc dữ liệu từ CSV / Excel / Parquet / JSON (một file, hoặc cả thư mục theo `pattern`)
    - Hiển thị thông tin tổng quan, thống kê mô tả, nghi vấn sai kiểu
    - Kiểm tra dữ liệu trùng lặp (cả dòng và khóa), thiếu, phân phối nhãn (nếu có)
    - Loại bỏ cột không cần thiết nếu được chỉ định
    """
    # 1️⃣ Kiểm tra file tồn tại
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ Không tìm thấy file: {file_path}")

    # 2️⃣ Xác định định dạng và đọc dữ liệu
    if os.path.isdir(file_path):
        files = sorted(glob.glob(os.path.join(file_path, pattern)))
        if not files:
            raise FileNotFoundError(f"❌ Thư mục {file_path} không có file khớp {pattern}")
        df = pd.concat([_read_one(f, encoding, sep) for f in files], ignore_index=True)
        source = f"{len(files)} file trong {file_path}"
    else:
        df = _read_one(file_path, encoding, sep)
        source = file_path

    if show:
        print("=" * 100)
        print(f"✅ Đọc dữ liệu thành công: {df.shape[0]:,} dòng, {df.shape[1]} cột  ({source})")
        print("=" * 100)
        display(df.head())

        # 3️⃣ Thông tin tổng quan
        print("📋 Thông tin tổng quan:")
        print(LINE)
        df.info()
        print(LINE)

        # 4️⃣ Thống kê mô tả
        num_cols = df.select_dtypes(include="number")
        obj_cols = df.select_dtypes(include="object")
        if not num_cols.empty:
            print("📈 Thống kê mô tả (cột số):")
            display(num_cols.describe().T)
        else:
            print("⚠️ Không có cột số.")
        print(LINE)
        if not obj_cols.empty:
            print("🔠 Thống kê mô tả (cột phân loại):")
            display(obj_cols.describe(include="object").T)
            bad_type = suspicious_types(df)
            if not bad_type.empty:
                print("⚠️ Cột có thể đang sai kiểu dữ liệu:")
                display(bad_type)
            bad_cat = inconsistent_categories(df)
            if not bad_cat.empty:
                print("⚠️ Giá trị phân loại viết không thống nhất:")
                display(bad_cat)
        else:
            print("⚠️ Không có cột phân loại.")
        print(LINE)

    # 5️⃣ Xóa cột không cần thiết
    if drop_columns:
        existing = [c for c in drop_columns if c in df.columns]
        df = df.drop(columns=existing)
        if show:
            print(f"🗑️ Đã xóa các cột: {existing}")
            print(LINE)

    # 6️⃣ Kiểm tra trùng lặp
    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        print(f"⚠️ Có {dup_count:,} dòng trùng lặp.")
        if auto_drop_duplicates:
            df = df.drop_duplicates().reset_index(drop=True)
            print("🧹 Đã xóa các dòng trùng lặp.")
    elif show:
        print("✅ Không có dòng trùng lặp.")
    if key_columns:
        key_dup = int(df.duplicated(subset=key_columns).sum())
        if key_dup:
            print(f"⚠️ Có {key_dup:,} dòng trùng khóa {key_columns} (không trùng hẳn nhưng trùng khóa).")
        elif show:
            print(f"✅ Khóa {key_columns} là duy nhất.")
    if show:
        print(LINE)

    # 7️⃣ Kiểm tra giá trị thiếu
    missing = df.isnull().sum()
    missing_cols = missing[missing > 0].sort_values(ascending=False)
    if not missing_cols.empty:
        if show:
            print(f"⚠️ {len(missing_cols)} cột có giá trị thiếu (tổng {missing_cols.sum():,} ô, "
                  f"{missing_cols.sum() / df.size:.1%} toàn bảng):")
            display(pd.DataFrame({"số ô thiếu": missing_cols, "tỷ lệ": (missing_cols / len(df)).round(4)}))
        if auto_drop_missing:
            df = df.dropna().reset_index(drop=True)
            print("🧹 Đã xóa các dòng chứa giá trị thiếu.")
    elif show:
        print("✅ Không có giá trị thiếu.")
    if show:
        print(LINE)

    # 8️⃣ Kiểm tra phân phối nhãn (nếu có)
    if target and target in df.columns:
        y = df[target]
        if y.nunique(dropna=True) <= 20:
            print(f"📊 Phân phối nhãn '{target}':")
            counts = y.value_counts(dropna=False).sort_index()
            print(counts)
            print("📊 Tỷ lệ phân phối (%):")
            print((counts / counts.sum() * 100).round(2))
            print(f"   Lớp nhiều nhất / lớp ít nhất: {counts.max() / counts.min():.1f} lần")
        else:
            print(f"📊 '{target}' là biến liên tục (hồi quy), {y.nunique():,} giá trị khác nhau:")
            print(y.describe().round(4))
            print(f"   Độ lệch (skew): {y.skew():.2f} · độ nhọn (kurtosis): {y.kurt():.2f} · thiếu: {y.isna().sum()}")
    elif target:
        print(f"⚠️ Không tìm thấy cột target '{target}'.")

    if show:
        print("=" * 100)
        print("✅ HOÀN TẤT KHÁM PHÁ DỮ LIỆU")
    return df


def quick_profile(paths: dict, key_columns: dict | None = None) -> pd.DataFrame:
    """Bản show=False cho nhiều file: kích thước, cột số/phân loại, trùng, thiếu, nghi vấn sai kiểu."""
    rows = []
    for name, path in paths.items():
        df = read_and_explore_data(path, show=False)
        keys = (key_columns or {}).get(name)
        rows.append({
            "bộ dữ liệu": name,
            "dòng": len(df),
            "cột": df.shape[1],
            "cột số": df.select_dtypes(include="number").shape[1],
            "cột phân loại": df.select_dtypes(include="object").shape[1],
            "dòng trùng": int(df.duplicated().sum()),
            "trùng khóa": int(df.duplicated(subset=keys).sum()) if keys else np.nan,
            "ô thiếu (%)": round(df.isnull().to_numpy().mean() * 100, 2),
            "cột sai kiểu?": ", ".join(suspicious_types(df)["cột"]) or "—",
        })
    return pd.DataFrame(rows)
