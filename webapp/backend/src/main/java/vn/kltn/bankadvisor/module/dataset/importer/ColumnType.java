package vn.kltn.bankadvisor.module.dataset.importer;

/**
 * Kiểu của một cột CSV khi nạp vào bảng.
 * TICKER / INDICATOR / PROGRAM là chuỗi phải tồn tại trong bảng tham chiếu; dòng có mã lạ bị bỏ qua (không lỗi),
 * vì pipeline có thể xuất cả ngân hàng ngoài phạm vi.
 */
public enum ColumnType {
    TEXT,
    INT,
    LONG,
    DOUBLE,
    DECIMAL,
    DATE,
    BOOL,
    TICKER,
    INDICATOR,
    PROGRAM
}
