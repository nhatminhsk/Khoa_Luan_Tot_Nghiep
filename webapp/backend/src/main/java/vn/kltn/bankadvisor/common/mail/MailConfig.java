package vn.kltn.bankadvisor.common.mail;

import jakarta.mail.internet.AddressException;
import jakarta.mail.internet.InternetAddress;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.mail.javamail.JavaMailSenderImpl;
import vn.kltn.bankadvisor.common.config.AppProperties;

import java.util.Properties;

/**
 * Chọn cách gửi email theo {@code app.mail.mode}. Không dùng cấu hình {@code spring.mail.*} của Spring Boot:
 * cấu hình đó bật máy gửi thư ngay khi có khóa {@code host}, kể cả khi giá trị rỗng, và kéo theo phép kiểm tra
 * sức khỏe kết nối SMTP ở mỗi lần gọi /actuator/health.
 */
@Configuration
public class MailConfig {

    private static final Logger log = LoggerFactory.getLogger(MailConfig.class);

    @Bean
    EmailGateway emailGateway(AppProperties properties) {
        AppProperties.Mail mail = properties.mail();
        return switch (mail.mode()) {
            case OFF -> new DisabledEmailGateway();
            case LOG -> {
                log.warn("app.mail.mode=LOG: email chỉ in ra log, không gửi thật. Chỉ dùng khi phát triển.");
                yield new LoggingEmailGateway();
            }
            case SMTP -> {
                JavaMailSenderImpl sender = smtpSender(mail.smtp());
                log.info("Gửi email qua SMTP {}:{} (STARTTLS {})", sender.getHost(), sender.getPort(),
                        mail.smtp().starttls() ? "bắt buộc" : "tắt");
                yield new SmtpEmailGateway(sender, parseFrom(mail.from()));
            }
        };
    }

    static JavaMailSenderImpl smtpSender(AppProperties.Smtp smtp) {
        if (smtp == null || isBlank(smtp.host())) {
            throw new IllegalStateException(
                    "app.mail.mode=SMTP nhưng thiếu máy chủ thư. Đặt APP_SMTP_HOST (và APP_SMTP_PORT, APP_SMTP_USERNAME, "
                            + "APP_SMTP_PASSWORD) trong biến môi trường hoặc file .env");
        }
        JavaMailSenderImpl sender = new JavaMailSenderImpl();
        sender.setHost(smtp.host().strip());
        sender.setPort(smtp.port());
        sender.setDefaultEncoding("UTF-8");
        boolean auth = !isBlank(smtp.username());
        if (auth) {
            if (isBlank(smtp.password())) {
                throw new IllegalStateException("app.mail.mode=SMTP và có APP_SMTP_USERNAME nhưng thiếu APP_SMTP_PASSWORD. "
                        + "Với Gmail, dùng Mật khẩu ứng dụng 16 ký tự (không phải mật khẩu đăng nhập).");
            }
            sender.setUsername(smtp.username().strip());
            sender.setPassword(normalizePassword(sender.getHost(), smtp.password()));
            if (!smtp.starttls()) {
                log.warn("SMTP có đăng nhập nhưng tắt STARTTLS: mật khẩu sẽ đi dạng rõ trên mạng");
            }
        }
        Properties props = sender.getJavaMailProperties();
        props.put("mail.transport.protocol", "smtp");
        props.put("mail.smtp.auth", String.valueOf(auth));
        // Bắt buộc TLS và kiểm tra chứng chỉ đúng tên máy chủ; không tin chứng chỉ tự ký, không nới thuật toán TLS.
        props.put("mail.smtp.starttls.enable", String.valueOf(smtp.starttls()));
        props.put("mail.smtp.starttls.required", String.valueOf(smtp.starttls()));
        props.put("mail.smtp.ssl.checkserveridentity", "true");
        String timeoutMs = String.valueOf(smtp.timeout().toMillis());
        props.put("mail.smtp.connectiontimeout", timeoutMs);
        props.put("mail.smtp.timeout", timeoutMs);
        props.put("mail.smtp.writetimeout", timeoutMs);
        return sender;
    }

    static InternetAddress parseFrom(String from) {
        try {
            InternetAddress address = new InternetAddress(from, true);
            address.validate();
            return address;
        } catch (AddressException e) {
            throw new IllegalStateException("app.mail.from không phải địa chỉ email hợp lệ: " + from, e);
        }
    }

    /**
     * Google hiển thị Mật khẩu ứng dụng dạng "abcd efgh ijkl mnop"; người dùng thường dán nguyên cả dấu cách.
     * Chỉ bỏ dấu cách khi đúng dạng đó và máy chủ là Gmail, để không đụng tới mật khẩu có dấu cách thật.
     */
    static String normalizePassword(String host, String password) {
        String trimmed = password.strip();
        if (host.equalsIgnoreCase("smtp.gmail.com") && trimmed.matches("[a-zA-Z]{4}( [a-zA-Z]{4}){3}")) {
            return trimmed.replace(" ", "");
        }
        return password;
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    /** mode = OFF. */
    static final class DisabledEmailGateway implements EmailGateway {

        @Override
        public MailMode mode() {
            return MailMode.OFF;
        }

        @Override
        public void send(EmailMessage message) {
            throw new IllegalStateException("Gửi email đang tắt (app.mail.mode=OFF)");
        }
    }

    /** mode = LOG: in nguyên email ra log để thử luồng xác minh và thông báo mà không cần máy chủ thư. */
    static final class LoggingEmailGateway implements EmailGateway {

        private static final Logger mailLog = LoggerFactory.getLogger("vn.kltn.bankadvisor.mail");

        @Override
        public MailMode mode() {
            return MailMode.LOG;
        }

        @Override
        public void send(EmailMessage message) {
            mailLog.info("[email LOG] Tới: {} | Tiêu đề: {}\n{}", message.to(), message.subject(), message.text());
        }
    }
}
