package vn.kltn.bankadvisor.security;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.MediaType;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.oauth2.server.resource.InvalidBearerTokenException;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.security.web.csrf.CsrfException;
import vn.kltn.bankadvisor.common.exception.ErrorCode;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/**
 * Trả lỗi 401/403 cùng định dạng {@code ApiResponse} như các lỗi khác.
 * Token hỏng, hết hạn, bị thu hồi, hoặc tài khoản bị khóa thì xóa luôn cookie để lần gọi sau không gửi lại.
 */
class JsonSecurityErrorHandler implements AuthenticationEntryPoint, AccessDeniedHandler {

    private final SessionCookieService cookies;

    JsonSecurityErrorHandler(SessionCookieService cookies) {
        this.cookies = cookies;
    }

    @Override
    public void commence(HttpServletRequest request, HttpServletResponse response,
                         AuthenticationException ex) throws IOException {
        if (ex instanceof SessionAuthenticationConverter.AccountLockedException) {
            cookies.clear(response);
            write(response, ErrorCode.ACCOUNT_LOCKED);
            return;
        }
        if (ex instanceof InvalidBearerTokenException || ex instanceof SessionAuthenticationConverter.SessionRevokedException) {
            cookies.clear(response);
        }
        write(response, ErrorCode.UNAUTHORIZED);
    }

    @Override
    public void handle(HttpServletRequest request, HttpServletResponse response,
                       AccessDeniedException ex) throws IOException {
        // Thiếu / sai token CSRF: mã riêng để giao diện đọc lại cookie XSRF-TOKEN (vừa được cấp mới) và thử lại một lần.
        write(response, ex instanceof CsrfException ? ErrorCode.CSRF_TOKEN_INVALID : ErrorCode.FORBIDDEN);
    }

    private static void write(HttpServletResponse response, ErrorCode code) throws IOException {
        response.setStatus(code.status().value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        // Thông điệp là hằng số trong ErrorCode (không có dấu nháy), nên ghép chuỗi JSON trực tiếp là an toàn.
        response.getWriter().write("{\"success\":false,\"errorCode\":\"" + code.name()
                + "\",\"message\":\"" + code.defaultMessage() + "\"}");
    }
}
