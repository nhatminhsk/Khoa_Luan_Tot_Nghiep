package vn.kltn.bankadvisor.common.exception;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.HandlerMethodValidationException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;
import vn.kltn.bankadvisor.common.api.ApiResponse;

import java.util.LinkedHashMap;
import java.util.Map;

/** Đổi mọi ngoại lệ thành {@link ApiResponse} lỗi, để frontend chỉ phải xử lý một định dạng. */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(AppException.class)
    ResponseEntity<ApiResponse<Void>> handleApp(AppException ex) {
        return build(ex.errorCode(), ex.getMessage(), null);
    }

    @ExceptionHandler(RateLimitedException.class)
    ResponseEntity<ApiResponse<Void>> handleRateLimited(RateLimitedException ex) {
        long seconds = Math.max(1, (ex.retryAfter().toMillis() + 999) / 1000);
        return ResponseEntity.status(ex.errorCode().status())
                .header(HttpHeaders.RETRY_AFTER, Long.toString(seconds))
                .body(ApiResponse.error(ex.errorCode().name(), ex.getMessage(), null));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    ResponseEntity<ApiResponse<Void>> handleBodyValidation(MethodArgumentNotValidException ex) {
        Map<String, String> errors = new LinkedHashMap<>();
        for (FieldError error : ex.getBindingResult().getFieldErrors()) {
            errors.putIfAbsent(error.getField(), error.getDefaultMessage());
        }
        ex.getBindingResult().getGlobalErrors()
                .forEach(error -> errors.putIfAbsent(error.getObjectName(), error.getDefaultMessage()));
        return build(ErrorCode.VALIDATION_FAILED, ErrorCode.VALIDATION_FAILED.defaultMessage(), errors);
    }

    @ExceptionHandler(HandlerMethodValidationException.class)
    ResponseEntity<ApiResponse<Void>> handleParamValidation(HandlerMethodValidationException ex) {
        Map<String, String> errors = new LinkedHashMap<>();
        ex.getParameterValidationResults().forEach(result -> errors.putIfAbsent(
                result.getMethodParameter().getParameterName(),
                result.getResolvableErrors().getFirst().getDefaultMessage()));
        return build(ErrorCode.VALIDATION_FAILED, ErrorCode.VALIDATION_FAILED.defaultMessage(), errors);
    }

    @ExceptionHandler(MissingServletRequestParameterException.class)
    ResponseEntity<ApiResponse<Void>> handleMissingParam(MissingServletRequestParameterException ex) {
        return build(ErrorCode.VALIDATION_FAILED, ErrorCode.VALIDATION_FAILED.defaultMessage(),
                Map.of(ex.getParameterName(), "Bắt buộc nhập"));
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    ResponseEntity<ApiResponse<Void>> handleTypeMismatch(MethodArgumentTypeMismatchException ex) {
        return build(ErrorCode.VALIDATION_FAILED, ErrorCode.VALIDATION_FAILED.defaultMessage(),
                Map.of(ex.getName(), "Giá trị không hợp lệ"));
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    ResponseEntity<ApiResponse<Void>> handleUnreadable(HttpMessageNotReadableException ex) {
        return build(ErrorCode.BAD_REQUEST, "Nội dung yêu cầu không đọc được", null);
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    ResponseEntity<ApiResponse<Void>> handleMethod(HttpRequestMethodNotSupportedException ex) {
        return build(ErrorCode.BAD_REQUEST, "Phương thức " + ex.getMethod() + " không được hỗ trợ", null);
    }

    @ExceptionHandler(NoResourceFoundException.class)
    ResponseEntity<ApiResponse<Void>> handleNoResource(NoResourceFoundException ex) {
        return build(ErrorCode.NOT_FOUND, ErrorCode.NOT_FOUND.defaultMessage(), null);
    }

    @ExceptionHandler(AccessDeniedException.class)
    ResponseEntity<ApiResponse<Void>> handleAccessDenied(AccessDeniedException ex) {
        return build(ErrorCode.FORBIDDEN, ErrorCode.FORBIDDEN.defaultMessage(), null);
    }

    @ExceptionHandler(Exception.class)
    ResponseEntity<ApiResponse<Void>> handleUnexpected(Exception ex) {
        log.error("Lỗi không lường trước", ex);
        return build(ErrorCode.INTERNAL_ERROR, ErrorCode.INTERNAL_ERROR.defaultMessage(), null);
    }

    private static ResponseEntity<ApiResponse<Void>> build(ErrorCode code, String message, Map<String, String> fieldErrors) {
        return ResponseEntity.status(code.status()).body(ApiResponse.error(code.name(), message, fieldErrors));
    }
}
