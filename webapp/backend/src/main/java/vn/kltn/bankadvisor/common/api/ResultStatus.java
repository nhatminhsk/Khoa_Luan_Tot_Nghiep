package vn.kltn.bankadvisor.common.api;

/**
 * Trạng thái của một khối kết quả thuật toán (xếp hạng, dự báo, khía cạnh review).
 * NOT_AVAILABLE nghĩa là pipeline chưa ghi kết quả — giao diện hiện "chưa có kết quả", không phải lỗi.
 */
public enum ResultStatus {
    AVAILABLE,
    NOT_AVAILABLE
}
