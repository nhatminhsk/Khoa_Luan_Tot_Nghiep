package vn.kltn.bankadvisor.module.watchlist.entity;

/** Trạng thái gửi email của một thông báo. Thông báo chỉ hiện trong ứng dụng có trạng thái {@code null}. */
public enum EmailStatus {
    PENDING,
    SENT,
    /** Hết số lần thử. */
    FAILED,
    /** Không gửi nữa: người dùng đã đọc trong ứng dụng, hoặc đã tắt email trước khi tới lượt gửi. */
    SKIPPED
}
