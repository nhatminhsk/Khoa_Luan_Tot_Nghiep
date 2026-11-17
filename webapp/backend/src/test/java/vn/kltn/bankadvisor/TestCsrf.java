package vn.kltn.bankadvisor;

import jakarta.servlet.http.Cookie;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

import java.util.Arrays;

/**
 * Gửi token CSRF như trình duyệt: cookie XSRF-TOKEN và header X-XSRF-TOKEN cùng một giá trị (double-submit thật).
 * <p>
 * Không dùng {@code SecurityMockMvcRequestPostProcessors.csrf()}: nó thay kho token của CsrfFilter (bean dùng chung cho
 * cả context) bằng kho giả lưu trong session, nên các test chạy sau không còn nhận cookie XSRF-TOKEN thật.
 */
final class TestCsrf {

    private static final String TOKEN = "token-csrf-cua-test";

    private TestCsrf() {
    }

    static RequestPostProcessor xsrf() {
        return request -> {
            Cookie[] existing = request.getCookies() == null ? new Cookie[0] : request.getCookies();
            Cookie[] cookies = Arrays.copyOf(existing, existing.length + 1);
            cookies[existing.length] = new Cookie("XSRF-TOKEN", TOKEN);
            request.setCookies(cookies);
            request.addHeader("X-XSRF-TOKEN", TOKEN);
            return request;
        };
    }
}
