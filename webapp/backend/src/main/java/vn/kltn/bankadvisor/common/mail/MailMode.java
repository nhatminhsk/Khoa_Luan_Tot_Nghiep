package vn.kltn.bankadvisor.common.mail;

/** Cách gửi email, chọn bằng {@code app.mail.mode}. */
public enum MailMode {
    /** Không gửi email; giao diện ẩn lựa chọn nhận thông báo qua email. */
    OFF,
    /** In email ra log thay vì gửi. Chỉ dùng khi phát triển: link xác minh nằm trong log. */
    LOG,
    /** Gửi thật qua máy chủ SMTP ({@code app.mail.smtp.*}). */
    SMTP
}
