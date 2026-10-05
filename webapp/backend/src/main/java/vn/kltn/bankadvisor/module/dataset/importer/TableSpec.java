package vn.kltn.bankadvisor.module.dataset.importer;

import java.util.List;

/**
 * Đặc tả nạp một file CSV vào một bảng.
 *
 * @param dataset      tên tập dữ liệu (khóa trong import_run)
 * @param fileName     tên file trong data/serving
 * @param table        bảng đích
 * @param mode         REPLACE: xóa hết rồi chèn; UPSERT: cập nhật theo khóa, không xóa (bảng tham chiếu có khóa ngoại trỏ tới)
 * @param keyColumns   cột khóa (dùng cho UPSERT)
 * @param markerColumn cột dùng làm "mốc mới nhất" (ví dụ ngày lãi suất) để phát hiện dữ liệu mới; có thể null
 * @param columns      ánh xạ cột CSV → cột bảng
 */
public record TableSpec(
        String dataset,
        String fileName,
        String table,
        LoadMode mode,
        List<String> keyColumns,
        String markerColumn,
        List<ColumnSpec> columns
) {

    public enum LoadMode {
        REPLACE,
        UPSERT
    }

    /** @param required ô trống thì cả tập bị từ chối (cột NOT NULL trong bảng) */
    public record ColumnSpec(String csv, String db, ColumnType type, boolean required) {
    }

    static ColumnSpec req(String csv, String db, ColumnType type) {
        return new ColumnSpec(csv, db, type, true);
    }

    static ColumnSpec req(String name, ColumnType type) {
        return req(name, name, type);
    }

    static ColumnSpec opt(String csv, String db, ColumnType type) {
        return new ColumnSpec(csv, db, type, false);
    }

    static ColumnSpec opt(String name, ColumnType type) {
        return opt(name, name, type);
    }
}
