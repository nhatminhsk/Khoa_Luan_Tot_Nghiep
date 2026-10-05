package vn.kltn.bankadvisor.common.mail;

/** Gửi email thất bại (máy chủ thư từ chối, hết thời gian chờ, sai cấu hình...). */
public class EmailDeliveryException extends RuntimeException {

    public EmailDeliveryException(String message, Throwable cause) {
        super(message, cause);
    }
}
