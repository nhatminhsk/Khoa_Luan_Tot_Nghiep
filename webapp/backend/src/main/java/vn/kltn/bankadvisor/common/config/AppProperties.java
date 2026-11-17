package vn.kltn.bankadvisor.common.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;
import vn.kltn.bankadvisor.common.mail.MailMode;

import java.nio.file.Path;
import java.time.Duration;
import java.util.List;

/** Cấu hình riêng của ứng dụng (khóa {@code app.*} trong application.yml). */
@ConfigurationProperties(prefix = "app")
public record AppProperties(
        DataImport dataImport,
        Jwt jwt,
        BootstrapAdmin bootstrapAdmin,
        @DefaultValue Mail mail,
        @DefaultValue LoginThrottle loginThrottle,
        @DefaultValue List<String> corsOrigins
) {

    /**
     * @param dir       thư mục chứa các file CSV do pipeline ghi (data/serving). Để kiểu String vì bộ chuyển
     *                  đổi String → Path của Spring coi giá trị là resource và từ chối đường dẫn có "..".
     * @param onStartup nạp dữ liệu khi khởi động
     * @param cron      lịch kiểm tra file mới (mặc định sau lần crawl 15:30 hằng ngày)
     */
    public record DataImport(
            String dir,
            @DefaultValue("true") boolean onStartup,
            @DefaultValue("0 0 16 * * *") String cron
    ) {

        public Path path() {
            return Path.of(dir).toAbsolutePath().normalize();
        }
    }

    /**
     * @param secret       khóa ký HS256, tối thiểu 32 byte
     * @param ttl          thời hạn phiên đăng nhập của người dùng thường
     * @param adminTtl     thời hạn phiên của quản trị viên (ngắn hơn: quyền cao hơn, token lộ thì cửa sổ lạm dụng hẹp hơn)
     * @param cookieName   tên cookie chứa token
     * @param cookieSecure bật khi chạy HTTPS
     */
    public record Jwt(
            String secret,
            @DefaultValue("7d") Duration ttl,
            @DefaultValue("8h") Duration adminTtl,
            @DefaultValue("ba_session") String cookieName,
            @DefaultValue("false") boolean cookieSecure
    ) {
    }

    /** Tài khoản quản trị tạo lúc khởi động nếu chưa có; để trống thì bỏ qua. */
    public record BootstrapAdmin(String email, String password) {
    }

    /**
     * Gửi thông báo qua email.
     *
     * @param mode            OFF: không gửi (mặc định); LOG: in email ra log thay vì gửi, để thử khi chưa có máy
     *                        chủ thư; SMTP: gửi thật qua {@code smtp}
     * @param from            người gửi, dạng {@code BankAdvisor <no-reply@ten-mien>}
     * @param webBaseUrl      địa chỉ giao diện web, để dựng link trong email
     * @param smtp            máy chủ thư (chỉ dùng khi mode = SMTP)
     * @param dispatchDelay   khoảng nghỉ giữa hai lần quét hàng đợi email
     * @param retryBackoff    thời gian chờ trước lần thử lại thứ n là n × giá trị này
     * @param maxAttempts     số lần thử gửi một email trước khi đánh dấu lỗi
     * @param verificationTtl hạn của link xác minh email
     * @param verificationCodeTtl hạn của mã xác minh 6 số gửi kèm link (ngắn hơn link vì mã dễ đoán hơn token)
     * @param resendCooldown  thời gian tối thiểu giữa hai lần gửi link xác minh (và giữa hai lần gửi thư đặt lại mật khẩu)
     * @param passwordResetTtl hạn của link đặt lại mật khẩu
     */
    public record Mail(
            @DefaultValue("OFF") MailMode mode,
            @DefaultValue("BankAdvisor <no-reply@bankadvisor.test>") String from,
            @DefaultValue("http://localhost:3000") String webBaseUrl,
            @DefaultValue Smtp smtp,
            @DefaultValue("60s") Duration dispatchDelay,
            @DefaultValue("5m") Duration retryBackoff,
            @DefaultValue("3") int maxAttempts,
            @DefaultValue("24h") Duration verificationTtl,
            @DefaultValue("15m") Duration verificationCodeTtl,
            @DefaultValue("60s") Duration resendCooldown,
            @DefaultValue("30m") Duration passwordResetTtl
    ) {

        /** Link tới một trang của giao diện web, ví dụ {@code link("/watchlist")}. */
        public String link(String path) {
            String base = webBaseUrl.endsWith("/") ? webBaseUrl.substring(0, webBaseUrl.length() - 1) : webBaseUrl;
            return base + path;
        }
    }

    /**
     * @param starttls bắt buộc nâng kết nối lên TLS (STARTTLS, cổng 587). Chỉ tắt khi thử với máy chủ thư nội bộ.
     * @param timeout  thời gian chờ tối đa khi kết nối, đọc, ghi
     */
    public record Smtp(
            String host,
            @DefaultValue("587") int port,
            String username,
            String password,
            @DefaultValue("true") boolean starttls,
            @DefaultValue("10s") Duration timeout
    ) {
    }

    /**
     * Giới hạn đăng nhập sai.
     *
     * @param maxFailures         số lần sai tối đa của một cặp (email, IP) trong {@code window}. Đếm theo cặp để
     *                            người khác không khóa được tài khoản của mình chỉ bằng cách cố tình nhập sai.
     * @param maxFailuresPerEmail số lần sai tối đa của một email từ mọi IP, chặn dò mật khẩu phân tán nhiều máy
     * @param window              cửa sổ đếm, tính từ lần sai đầu tiên; hết cửa sổ thì được thử lại
     */
    public record LoginThrottle(
            @DefaultValue("5") int maxFailures,
            @DefaultValue("20") int maxFailuresPerEmail,
            @DefaultValue("15m") Duration window
    ) {
    }
}
