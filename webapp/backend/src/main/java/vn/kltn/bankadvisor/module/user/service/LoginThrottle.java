package vn.kltn.bankadvisor.module.user.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import vn.kltn.bankadvisor.common.config.AppProperties;
import vn.kltn.bankadvisor.common.exception.RateLimitedException;
import vn.kltn.bankadvisor.common.mail.EmailAddresses;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

/**
 * Chặn dò mật khẩu: đếm số lần đăng nhập sai theo cặp (email, IP) và theo email, trong một cửa sổ thời gian
 * tính từ lần sai đầu tiên. Vượt ngưỡng thì trả 429 cho tới hết cửa sổ, kể cả khi lần sau nhập đúng.
 * <p>
 * Thông báo giống nhau cho email có và không có tài khoản, nên không lộ email nào đã đăng ký. Bộ đếm nằm trong
 * bộ nhớ (một tiến trình backend).
 * <p>
 * IP lấy từ giá trị đầu của X-Forwarded-For (ForwardedHeaderFilter). Next.js chuyển tiếp nguyên header này nếu
 * trình duyệt tự gửi, nên khi triển khai, reverse proxy đứng trước Next.js phải ghi đè nó bằng IP thật
 * (nginx: {@code proxy_set_header X-Forwarded-For $remote_addr;}) và backend không mở cổng ra ngoài. Kể cả khi IP
 * bị giả, ngưỡng theo email ({@code max-failures-per-email}) vẫn giới hạn số lần dò mật khẩu của một tài khoản.
 */
@Component
public class LoginThrottle {

    private static final Logger log = LoggerFactory.getLogger(LoginThrottle.class);

    private final ConcurrentMap<String, Window> failures = new ConcurrentHashMap<>();
    private final AppProperties.LoginThrottle config;
    private final Clock clock;

    public LoginThrottle(AppProperties properties, Clock clock) {
        this.config = properties.loginThrottle();
        this.clock = clock;
    }

    private record Window(Instant start, int count) {
    }

    /** @throws RateLimitedException khi email (hoặc cặp email, IP) đang bị tạm chặn */
    public void checkAllowed(String email, String ip) {
        Instant now = clock.instant();
        check(pairKey(email, ip), config.maxFailures(), now);
        check(emailKey(email), config.maxFailuresPerEmail(), now);
    }

    public void recordFailure(String email, String ip) {
        Instant now = clock.instant();
        int pairCount = increment(pairKey(email, ip), now);
        increment(emailKey(email), now);
        if (pairCount == config.maxFailures()) {
            log.warn("Tạm chặn đăng nhập {} từ {} sau {} lần sai", EmailAddresses.mask(email), ip, pairCount);
        }
    }

    /** Đăng nhập đúng thì xóa bộ đếm của cặp; bộ đếm theo email giữ nguyên tới hết cửa sổ. */
    public void recordSuccess(String email, String ip) {
        failures.remove(pairKey(email, ip));
    }

    /** Dọn các cửa sổ đã hết hạn để bộ nhớ không tăng mãi. */
    @Scheduled(fixedDelay = 10 * 60 * 1000)
    public void evictExpired() {
        Instant now = clock.instant();
        failures.values().removeIf(w -> expired(w, now));
    }

    private void check(String key, int max, Instant now) {
        Window window = failures.get(key);
        if (window != null && !expired(window, now) && window.count() >= max) {
            Duration wait = Duration.between(now, window.start().plus(config.window()));
            throw new RateLimitedException("Đăng nhập sai quá nhiều lần. Vui lòng thử lại sau "
                    + RateLimitedException.humanize(wait) + ".", wait);
        }
    }

    private int increment(String key, Instant now) {
        return failures.compute(key, (k, w) -> w == null || expired(w, now)
                ? new Window(now, 1)
                : new Window(w.start(), w.count() + 1)).count();
    }

    private boolean expired(Window window, Instant now) {
        return !now.isBefore(window.start().plus(config.window()));
    }

    private static String pairKey(String email, String ip) {
        return "pair:" + email + "|" + (ip == null ? "?" : ip);
    }

    private static String emailKey(String email) {
        return "email:" + email;
    }
}
