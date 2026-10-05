package vn.kltn.bankadvisor.common.exception;

import java.time.Duration;

/** Vượt giới hạn tần suất (429). Phản hồi kèm header {@code Retry-After} tính bằng giây. */
public class RateLimitedException extends AppException {

    private final Duration retryAfter;

    public RateLimitedException(String message, Duration retryAfter) {
        super(ErrorCode.TOO_MANY_REQUESTS, message);
        this.retryAfter = retryAfter;
    }

    public Duration retryAfter() {
        return retryAfter;
    }

    /** "45 giây", "3 phút" — làm tròn lên để người dùng không thử lại quá sớm. */
    public static String humanize(Duration wait) {
        long seconds = Math.max(1, (wait.toMillis() + 999) / 1000);
        if (seconds < 60) {
            return seconds + " giây";
        }
        return ((seconds + 59) / 60) + " phút";
    }
}
