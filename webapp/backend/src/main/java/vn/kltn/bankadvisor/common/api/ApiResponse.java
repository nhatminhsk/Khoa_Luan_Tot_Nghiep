package vn.kltn.bankadvisor.common.api;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.util.Map;

/**
 * Vỏ bọc thống nhất cho mọi phản hồi của API.
 * <p>
 * Thành công: {@code {"success": true, "data": ...}}.
 * Lỗi: {@code {"success": false, "errorCode": "...", "message": "...", "fieldErrors": {...}}}.
 * Frontend chỉ cần đọc {@code data} khi {@code success = true}, còn lại hiện {@code message}.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ApiResponse<T>(
        boolean success,
        T data,
        String errorCode,
        String message,
        Map<String, String> fieldErrors
) {

    public static <T> ApiResponse<T> ok(T data) {
        return new ApiResponse<>(true, data, null, null, null);
    }

    public static <T> ApiResponse<T> error(String errorCode, String message, Map<String, String> fieldErrors) {
        return new ApiResponse<>(false, null, errorCode, message, fieldErrors);
    }
}
