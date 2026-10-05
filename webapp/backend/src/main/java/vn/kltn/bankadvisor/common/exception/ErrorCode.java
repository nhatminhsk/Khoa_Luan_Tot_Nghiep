package vn.kltn.bankadvisor.common.exception;

import org.springframework.http.HttpStatus;

/** Mã lỗi nghiệp vụ. Frontend dựa vào {@code name()} để xử lý, và hiện {@code defaultMessage} cho người dùng. */
public enum ErrorCode {
    VALIDATION_FAILED(HttpStatus.BAD_REQUEST, "Dữ liệu gửi lên không hợp lệ"),
    BAD_REQUEST(HttpStatus.BAD_REQUEST, "Yêu cầu không hợp lệ"),
    UNAUTHORIZED(HttpStatus.UNAUTHORIZED, "Bạn cần đăng nhập để dùng chức năng này"),
    INVALID_CREDENTIALS(HttpStatus.UNAUTHORIZED, "Email hoặc mật khẩu không đúng"),
    WRONG_PASSWORD(HttpStatus.BAD_REQUEST, "Mật khẩu hiện tại không đúng"),
    FORBIDDEN(HttpStatus.FORBIDDEN, "Bạn không có quyền thực hiện thao tác này"),
    NOT_FOUND(HttpStatus.NOT_FOUND, "Không tìm thấy dữ liệu"),
    BANK_NOT_FOUND(HttpStatus.NOT_FOUND, "Không tìm thấy ngân hàng"),
    EMAIL_TAKEN(HttpStatus.CONFLICT, "Email này đã được đăng ký"),
    ALREADY_WATCHED(HttpStatus.CONFLICT, "Ngân hàng này đã có trong danh sách theo dõi"),
    TOO_MANY_REQUESTS(HttpStatus.TOO_MANY_REQUESTS, "Bạn thao tác quá nhanh, vui lòng thử lại sau"),
    EMAIL_DISABLED(HttpStatus.CONFLICT, "Hệ thống chưa bật gửi email"),
    EMAIL_NOT_VERIFIED(HttpStatus.CONFLICT, "Cần xác minh email trước khi nhận thông báo qua email"),
    VERIFICATION_LINK_INVALID(HttpStatus.BAD_REQUEST, "Link xác minh không hợp lệ hoặc đã hết hạn"),
    VERIFICATION_CODE_INVALID(HttpStatus.BAD_REQUEST, "Mã xác minh không đúng"),
    VERIFICATION_CODE_EXPIRED(HttpStatus.BAD_REQUEST, "Mã xác minh đã hết hạn hoặc đã bị hủy. Bấm “Gửi lại mã” để nhận mã mới"),
    EMAIL_SEND_FAILED(HttpStatus.BAD_GATEWAY, "Không gửi được email, vui lòng thử lại sau"),
    IMPORT_FAILED(HttpStatus.INTERNAL_SERVER_ERROR, "Nạp dữ liệu thất bại"),
    INTERNAL_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, "Có lỗi xảy ra, vui lòng thử lại sau");

    private final HttpStatus status;
    private final String defaultMessage;

    ErrorCode(HttpStatus status, String defaultMessage) {
        this.status = status;
        this.defaultMessage = defaultMessage;
    }

    public HttpStatus status() {
        return status;
    }

    public String defaultMessage() {
        return defaultMessage;
    }
}
