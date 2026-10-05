package vn.kltn.bankadvisor.module.dataset.service;

/**
 * Phát ra sau khi một tập dữ liệu nạp xong (đã commit). Module khác (ví dụ thông báo) lắng nghe sự kiện này
 * để không phụ thuộc trực tiếp vào module nạp dữ liệu.
 *
 * @param previousMarker giá trị mốc trước khi nạp (ví dụ ngày lãi suất mới nhất), null nếu bảng rỗng
 * @param newMarker      giá trị mốc sau khi nạp
 */
public record DatasetImportedEvent(String dataset, String previousMarker, String newMarker) {

    /** Có dữ liệu mới hơn mốc cũ (so sánh chuỗi đúng thứ tự cho ngày ISO và quý YYYY-Qn). */
    public boolean hasNewerMarker() {
        return newMarker != null && (previousMarker == null || newMarker.compareTo(previousMarker) > 0);
    }
}
