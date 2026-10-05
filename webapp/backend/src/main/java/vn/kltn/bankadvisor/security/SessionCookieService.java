package vn.kltn.bankadvisor.security;

import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseCookie;
import org.springframework.stereotype.Component;
import vn.kltn.bankadvisor.common.config.AppProperties;

import java.time.Duration;

/**
 * Ghi và xóa cookie phiên chứa JWT.
 * <p>
 * httpOnly: JavaScript không đọc được token (chống XSS lấy token).
 * SameSite=Lax: trình duyệt không gửi cookie trong POST từ trang khác (chống CSRF),
 * nên API có thể tắt CSRF token của Spring. Cookie hết hạn cùng lúc với token.
 */
@Component
public class SessionCookieService {

    private final AppProperties.Jwt props;

    public SessionCookieService(AppProperties properties) {
        this.props = properties.jwt();
    }

    public String cookieName() {
        return props.cookieName();
    }

    public void write(HttpServletResponse response, String token) {
        response.addHeader(HttpHeaders.SET_COOKIE, build(token, props.ttl()).toString());
    }

    public void clear(HttpServletResponse response) {
        response.addHeader(HttpHeaders.SET_COOKIE, build("", Duration.ZERO).toString());
    }

    private ResponseCookie build(String value, Duration maxAge) {
        return ResponseCookie.from(props.cookieName(), value)
                .httpOnly(true)
                .secure(props.cookieSecure())
                .sameSite("Lax")
                .path("/")
                .maxAge(maxAge)
                .build();
    }
}
