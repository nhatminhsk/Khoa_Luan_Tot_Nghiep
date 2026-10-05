package vn.kltn.bankadvisor.common.exception;

/** Lỗi nghiệp vụ có mã; service ném ra, {@link GlobalExceptionHandler} đổi thành phản hồi HTTP. */
public class AppException extends RuntimeException {

    private final ErrorCode errorCode;

    public AppException(ErrorCode errorCode) {
        this(errorCode, errorCode.defaultMessage());
    }

    public AppException(ErrorCode errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
    }

    public ErrorCode errorCode() {
        return errorCode;
    }
}
