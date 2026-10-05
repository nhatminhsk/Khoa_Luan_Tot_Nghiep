package vn.kltn.bankadvisor.security;

import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.security.oauth2.server.resource.web.BearerTokenResolver;
import org.springframework.security.oauth2.server.resource.web.DefaultBearerTokenResolver;

import java.util.List;

/**
 * Lấy token từ cookie phiên (trình duyệt) hoặc header {@code Authorization: Bearer} (công cụ như curl).
 * <p>
 * Chỉ đọc token ở các đường dẫn cần đăng nhập. Trang công khai bỏ qua token, nên một cookie đã hết hạn
 * không làm hỏng trang công khai (resource server sẽ trả 401 ngay khi gặp token hỏng, kể cả ở endpoint permitAll).
 */
class SessionTokenResolver implements BearerTokenResolver {

    static final List<String> AUTHENTICATED_PREFIXES = List.of("/api/v1/me/", "/api/v1/admin/");
    /** /auth/session không bắt buộc đăng nhập nhưng cần đọc token để biết ai đang đăng nhập. */
    static final List<String> AUTHENTICATED_PATHS = List.of("/api/v1/auth/me", "/api/v1/auth/session", "/api/v1/me");

    private final String cookieName;
    private final DefaultBearerTokenResolver headerResolver = new DefaultBearerTokenResolver();

    SessionTokenResolver(String cookieName) {
        this.cookieName = cookieName;
    }

    @Override
    public String resolve(HttpServletRequest request) {
        if (!needsAuthentication(request.getRequestURI())) {
            return null;
        }
        String fromHeader = headerResolver.resolve(request);
        if (fromHeader != null) {
            return fromHeader;
        }
        Cookie[] cookies = request.getCookies();
        if (cookies == null) {
            return null;
        }
        for (Cookie cookie : cookies) {
            if (cookieName.equals(cookie.getName()) && !cookie.getValue().isBlank()) {
                return cookie.getValue();
            }
        }
        return null;
    }

    static boolean needsAuthentication(String uri) {
        return AUTHENTICATED_PATHS.contains(uri) || AUTHENTICATED_PREFIXES.stream().anyMatch(uri::startsWith);
    }
}
