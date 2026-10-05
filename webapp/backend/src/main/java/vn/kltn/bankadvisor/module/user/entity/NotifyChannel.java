package vn.kltn.bankadvisor.module.user.entity;

/** Kênh nhận thông báo. Thông báo luôn hiện trong ứng dụng; EMAIL gửi thêm một bản qua email. */
public enum NotifyChannel {
    IN_APP,
    /** Trong ứng dụng và email. Chỉ chọn được khi hệ thống bật gửi email và người dùng đã xác minh email. */
    EMAIL
}
