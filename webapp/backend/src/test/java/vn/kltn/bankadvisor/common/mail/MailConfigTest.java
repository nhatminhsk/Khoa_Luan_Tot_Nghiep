package vn.kltn.bankadvisor.common.mail;

import org.junit.jupiter.api.Test;
import org.springframework.mail.javamail.JavaMailSenderImpl;
import vn.kltn.bankadvisor.common.config.AppProperties;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class MailConfigTest {

    @Test
    void gmailAppPasswordPastedWithSpacesIsAccepted() {
        assertEquals("abcdefghijklmnop", MailConfig.normalizePassword("smtp.gmail.com", "abcd efgh ijkl mnop"));
        // Máy chủ khác, hoặc mật khẩu không đúng dạng Mật khẩu ứng dụng: giữ nguyên.
        assertEquals("abcd efgh ijkl mnop", MailConfig.normalizePassword("smtp.example.test", "abcd efgh ijkl mnop"));
        assertEquals("mat khau co dau cach", MailConfig.normalizePassword("smtp.gmail.com", "mat khau co dau cach"));
    }

    @Test
    void smtpWithUsernameButNoPasswordFailsAtStartup() {
        IllegalStateException e = assertThrows(IllegalStateException.class, () -> MailConfig.smtpSender(
                smtp("smtp.gmail.com", "bankadvisor.thongbao@gmail.com", "")));
        assertTrue(e.getMessage().contains("APP_SMTP_PASSWORD"));
    }

    @Test
    void smtpRequiresTlsAndChecksServerIdentity() {
        JavaMailSenderImpl sender = MailConfig.smtpSender(smtp("smtp.gmail.com", "app@example.test", "abcd efgh ijkl mnop"));
        assertEquals("true", sender.getJavaMailProperties().getProperty("mail.smtp.starttls.required"));
        assertEquals("true", sender.getJavaMailProperties().getProperty("mail.smtp.ssl.checkserveridentity"));
        assertEquals("abcdefghijklmnop", sender.getPassword());
    }

    private static AppProperties.Smtp smtp(String host, String username, String password) {
        return new AppProperties.Smtp(host, 587, username, password, true, Duration.ofSeconds(10));
    }
}
