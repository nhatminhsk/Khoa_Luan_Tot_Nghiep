package vn.kltn.bankadvisor.common.mail;

/**
 * Cổng gửi email. Nghiệp vụ chỉ biết interface này; gửi thật qua SMTP, in ra log hay tắt hẳn là do
 * {@code app.mail.mode} quyết định (xem {@link MailConfig}).
 */
public interface EmailGateway {

    MailMode mode();

    /** false khi mode = OFF: không nhận yêu cầu gửi, giao diện ẩn lựa chọn email. */
    default boolean isEnabled() {
        return mode() != MailMode.OFF;
    }

    /**
     * Gửi đồng bộ.
     *
     * @throws EmailDeliveryException khi máy chủ thư từ chối hoặc không kết nối được
     */
    void send(EmailMessage message);
}
