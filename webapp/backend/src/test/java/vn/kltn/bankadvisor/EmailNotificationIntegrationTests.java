package vn.kltn.bankadvisor;

import com.icegreen.greenmail.util.GreenMail;
import com.icegreen.greenmail.util.ServerSetupTest;
import jakarta.mail.Message;
import jakarta.mail.Multipart;
import jakarta.mail.Part;
import jakarta.mail.internet.MimeMessage;
import jakarta.servlet.http.Cookie;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;
import vn.kltn.bankadvisor.module.watchlist.service.NotificationEmailDispatcher;
import vn.kltn.bankadvisor.module.watchlist.service.NotificationService;

import java.time.LocalDate;
import java.util.Arrays;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.greaterThanOrEqualTo;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.security.test.web.servlet.setup.SecurityMockMvcConfigurers.springSecurity;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Gửi email thật qua giao thức SMTP tới một máy chủ thư chạy trong bộ nhớ (GreenMail):
 * xác minh email → bật kênh EMAIL → lãi suất đổi → nhận email gom thông báo.
 */
@SpringBootTest(properties = {
        "APP_ENV_FILE=khong-ton-tai.env",
        "spring.datasource.url=jdbc:h2:mem:bankadvisor-mail;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;DEFAULT_NULL_ORDERING=HIGH;DB_CLOSE_DELAY=-1",
        "app.data-import.dir=src/test/resources/serving",
        "app.jwt.secret=test-secret-that-is-long-enough-for-hs256-signing",
        "app.bootstrap-admin.email=quantri@example.test",
        "app.bootstrap-admin.password=matkhau-quantri1",
        "app.mail.mode=SMTP",
        "app.mail.smtp.starttls=false",
        "app.mail.web-base-url=http://localhost:3000",
        // Lịch quét thưa để test tự gọi dispatchPending(), không chạy chồng với lịch.
        "app.mail.dispatch-delay=1h"
})
class EmailNotificationIntegrationTests {

    private static final GreenMail GREEN_MAIL = new GreenMail(ServerSetupTest.SMTP.dynamicPort());
    private static final Pattern VERIFY_LINK = Pattern.compile("http://localhost:3000/verify-email\\?token=([A-Za-z0-9_.-]+)");
    private static final Pattern RESET_LINK = Pattern.compile("http://localhost:3000/reset-password\\?token=([A-Za-z0-9_.-]+)");

    static {
        // Khởi động trước khi Spring đọc cổng SMTP ở @DynamicPropertySource.
        GREEN_MAIL.start();
    }

    @DynamicPropertySource
    static void smtp(DynamicPropertyRegistry registry) {
        registry.add("app.mail.smtp.host", () -> GREEN_MAIL.getSmtp().getBindTo());
        registry.add("app.mail.smtp.port", () -> GREEN_MAIL.getSmtp().getPort());
    }

    @AfterAll
    static void stopMailServer() {
        GREEN_MAIL.stop();
    }

    @Autowired
    private WebApplicationContext context;

    @Autowired
    private NotificationService notificationService;

    @Autowired
    private NotificationEmailDispatcher dispatcher;

    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        mvc = MockMvcBuilders.webAppContextSetup(context).apply(springSecurity())
                .defaultRequest(get("/").with(TestCsrf.xsrf())).build();
    }

    @Test
    void passwordResetLinkWorksOnceAndEndsOldSessions() throws Exception {
        Cookie session = register("quen-mk@example.test", "Quên mật khẩu");
        mvc.perform(post("/api/v1/auth/password-reset").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"Quen-MK@example.test\"}"))
                .andExpect(status().isOk());
        // Email chưa đăng ký: cùng kết quả, không có thư nào được gửi.
        mvc.perform(post("/api/v1/auth/password-reset").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"chua-dang-ky@example.test\"}"))
                .andExpect(status().isOk());
        assertTrue(messagesTo("chua-dang-ky@example.test").isEmpty());

        List<MimeMessage> mails = messagesTo("quen-mk@example.test");
        assertEquals(1, mails.size());
        assertEquals("Đặt lại mật khẩu BankAdvisor", mails.getFirst().getSubject());
        Matcher link = RESET_LINK.matcher(plainText(mails.getFirst()));
        assertTrue(link.find(), "email phải có link đặt lại mật khẩu");
        String token = link.group(1);

        // Token đặt lại mật khẩu không dùng làm cookie đăng nhập được.
        mvc.perform(get("/api/v1/auth/me").cookie(new Cookie("ba_session", token)))
                .andExpect(status().isUnauthorized());
        String confirm = "{\"token\":\"" + token + "\",\"newPassword\":\"matkhaumoi789\"}";
        mvc.perform(post("/api/v1/auth/password-reset/confirm").contentType(MediaType.APPLICATION_JSON).content(confirm))
                .andExpect(status().isOk());
        mvc.perform(get("/api/v1/auth/me").cookie(session)).andExpect(status().isUnauthorized());
        // Link chỉ dùng được một lần: mật khẩu đã đổi nên dấu vân tay trong token không còn khớp.
        mvc.perform(post("/api/v1/auth/password-reset/confirm").contentType(MediaType.APPLICATION_JSON).content(confirm))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorCode").value("PASSWORD_RESET_INVALID"));
        mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"quen-mk@example.test\",\"password\":\"matkhaumoi789\"}"))
                .andExpect(status().isOk())
                // Bấm được link trong thư nghĩa là nhận được thư ở địa chỉ này.
                .andExpect(jsonPath("$.data.emailVerified").value(true));
    }

    @Test
    void verifiedUserReceivesRateChangeDigestByEmail() throws Exception {
        Cookie session = register("mai@example.test", "Mai");

        mvc.perform(get("/api/v1/me/notification-settings").cookie(session))
                .andExpect(jsonPath("$.data.emailEnabled").value(true))
                .andExpect(jsonPath("$.data.emailVerified").value(false));
        // Chưa xác minh thì chưa chọn được kênh EMAIL.
        mvc.perform(put("/api/v1/me/notification-settings").cookie(session).contentType(MediaType.APPLICATION_JSON)
                        .content(settings("EMAIL")))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.errorCode").value("EMAIL_NOT_VERIFIED"));

        String token = requestVerificationToken(session, "mai@example.test");

        // Gửi lại ngay thì bị giới hạn tần suất.
        mvc.perform(post("/api/v1/me/email-verification").cookie(session))
                .andExpect(status().isTooManyRequests())
                .andExpect(header().exists("Retry-After"));

        // Token xác minh ký bằng khóa khác: không dùng làm cookie đăng nhập được.
        mvc.perform(get("/api/v1/auth/me").cookie(new Cookie("ba_session", token)))
                .andExpect(status().isUnauthorized());
        mvc.perform(post("/api/v1/auth/verify-email").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"token\":\"khong-phai-token\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorCode").value("VERIFICATION_LINK_INVALID"));

        // Link mở ở trình duyệt chưa đăng nhập vẫn xác minh được; bấm lần hai không lỗi.
        for (int i = 0; i < 2; i++) {
            mvc.perform(post("/api/v1/auth/verify-email").contentType(MediaType.APPLICATION_JSON)
                            .content("{\"token\":\"" + token + "\"}"))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.data.email").value("mai@example.test"))
                    .andExpect(jsonPath("$.data.emailVerified").value(true));
        }

        mvc.perform(put("/api/v1/me/notification-settings").cookie(session).contentType(MediaType.APPLICATION_JSON)
                        .content(settings("EMAIL")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.channel").value("EMAIL"));
        mvc.perform(post("/api/v1/me/watchlist").cookie(session).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"ticker\":\"ACB\",\"rateThreshold\":0.1}"))
                .andExpect(status().isCreated());

        // ACB 12 tháng online 5,9 → 6,1 trong bộ CSV mẫu.
        assertTrue(notificationService.notifyRateChanges(LocalDate.parse("2026-09-27")) >= 1);
        NotificationEmailDispatcher.DispatchResult result = dispatcher.dispatchPending();
        assertTrue(result.emailsSent() >= 1);

        List<MimeMessage> mails = messagesTo("mai@example.test");
        MimeMessage digest = mails.getLast();
        assertEquals("ACB thay đổi lãi suất tiết kiệm", digest.getSubject());
        String text = plainText(digest);
        assertTrue(text.contains("12 tháng online 5,90% → 6,10% (+0,20)"), text);
        assertTrue(text.contains("http://localhost:3000/watchlist"), text);
        assertTrue(digest.getContentType().startsWith("multipart/"), "phải có cả bản HTML");

        mvc.perform(get("/api/v1/me/notifications").cookie(session))
                .andExpect(jsonPath("$.data.items[0].emailedAt").exists());

        // Quét lại không gửi trùng.
        dispatcher.dispatchPending();
        assertEquals(mails.size(), messagesTo("mai@example.test").size());

        Cookie admin = login("quantri@example.test", "matkhau-quantri1");
        mvc.perform(get("/api/v1/admin/email-queue").cookie(admin))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.mode").value("SMTP"))
                .andExpect(jsonPath("$.data.sent").value(greaterThanOrEqualTo(1)));
        mvc.perform(get("/api/v1/admin/email-queue").cookie(session))
                .andExpect(status().isForbidden());
    }

    @Test
    void notificationReadInAppBeforeDispatchIsNotEmailed() throws Exception {
        Cookie session = register("lan@example.test", "Lan");
        String token = requestVerificationToken(session, "lan@example.test");
        mvc.perform(post("/api/v1/auth/verify-email").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"token\":\"" + token + "\"}"))
                .andExpect(status().isOk());
        mvc.perform(put("/api/v1/me/notification-settings").cookie(session).contentType(MediaType.APPLICATION_JSON)
                        .content(settings("EMAIL")))
                .andExpect(status().isOk());

        notificationService.notifyNewRanking("2026-Q3");
        mvc.perform(post("/api/v1/me/notifications/read-all").cookie(session)).andExpect(status().isOk());
        dispatcher.dispatchPending();

        assertTrue(messagesTo("lan@example.test").stream().noneMatch(m -> subject(m).contains("2026-Q3")));
        mvc.perform(get("/api/v1/me/notifications").cookie(session))
                .andExpect(jsonPath("$.data.items[0].title").value("Đã có xếp hạng quý 2026-Q3"))
                .andExpect(jsonPath("$.data.items[0].emailedAt").doesNotExist());
    }

    @Test
    void codeFromEmailVerifiesWithoutOpeningTheLink() throws Exception {
        Cookie session = register("minh@example.test", "Minh");
        mvc.perform(post("/api/v1/me/email-verification").cookie(session))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.codeExpiresAt").exists());
        String code = codeFrom(messagesTo("minh@example.test").getLast());
        String wrong = code.equals("000000") ? "111111" : "000000";

        mvc.perform(confirm(session, wrong))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorCode").value("VERIFICATION_CODE_INVALID"))
                .andExpect(jsonPath("$.message", containsString("Còn 4 lần")));
        // Gõ có dấu cách ("123 456") vẫn nhận.
        mvc.perform(confirm(session, code.substring(0, 3) + " " + code.substring(3)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.verified").value(true))
                .andExpect(jsonPath("$.data.codeExpiresAt").doesNotExist());
        mvc.perform(get("/api/v1/me/notification-settings").cookie(session))
                .andExpect(jsonPath("$.data.emailVerified").value(true));
    }

    @Test
    void codeIsCancelledAfterFiveWrongGuessesEvenThoughEachGuessIsRejected() throws Exception {
        Cookie session = register("tam@example.test", "Tâm");
        mvc.perform(post("/api/v1/me/email-verification").cookie(session)).andExpect(status().isOk());
        String code = codeFrom(messagesTo("tam@example.test").getLast());
        String wrong = code.equals("000000") ? "111111" : "000000";

        for (int i = 0; i < 4; i++) {
            mvc.perform(confirm(session, wrong)).andExpect(jsonPath("$.errorCode").value("VERIFICATION_CODE_INVALID"));
        }
        mvc.perform(confirm(session, wrong))
                .andExpect(jsonPath("$.errorCode").value("VERIFICATION_CODE_EXPIRED"))
                .andExpect(jsonPath("$.message", containsString("quá 5 lần")));
        // Số lần sai đã được lưu dù mỗi lần đều trả lỗi: mã đúng giờ cũng không dùng được nữa.
        mvc.perform(confirm(session, code))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorCode").value("VERIFICATION_CODE_EXPIRED"));
    }

    private static org.springframework.test.web.servlet.RequestBuilder confirm(Cookie session, String code) {
        return post("/api/v1/me/email-verification/confirm").cookie(session).contentType(MediaType.APPLICATION_JSON)
                .content("{\"code\":\"" + code + "\"}");
    }

    private static String codeFrom(MimeMessage mail) throws Exception {
        Matcher m = Pattern.compile("Mã xác minh email của bạn: (\\d{6})").matcher(plainText(mail));
        assertTrue(m.find(), "email phải có mã xác minh 6 số");
        return m.group(1);
    }

    /** Xin link xác minh rồi lấy token từ email vừa nhận. */
    private String requestVerificationToken(Cookie session, String email) throws Exception {
        int before = messagesTo(email).size();
        mvc.perform(post("/api/v1/me/email-verification").cookie(session))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.verified").value(false))
                .andExpect(jsonPath("$.data.sentAt").exists())
                .andExpect(jsonPath("$.data.resendAvailableAt").exists());
        List<MimeMessage> mails = messagesTo(email);
        assertEquals(before + 1, mails.size());
        MimeMessage mail = mails.getLast();
        assertEquals("Xác minh email nhận thông báo BankAdvisor", mail.getSubject());
        Matcher link = VERIFY_LINK.matcher(plainText(mail));
        assertTrue(link.find(), "email phải có link xác minh");
        return link.group(1);
    }

    private Cookie register(String email, String name) throws Exception {
        MvcResult result = mvc.perform(post("/api/v1/auth/register").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"" + email + "\",\"displayName\":\"" + name + "\",\"password\":\"matkhau123\"}"))
                .andExpect(status().isCreated())
                .andReturn();
        return result.getResponse().getCookie("ba_session");
    }

    private Cookie login(String email, String password) throws Exception {
        MvcResult result = mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"" + email + "\",\"password\":\"" + password + "\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.role", containsString("ADMIN")))
                .andReturn();
        Cookie cookie = result.getResponse().getCookie("ba_session");
        assertNotNull(cookie);
        return cookie;
    }

    private static String settings(String channel) {
        return "{\"notifyRateChange\":true,\"notifyNewRanking\":true,\"channel\":\"" + channel + "\"}";
    }

    private static List<MimeMessage> messagesTo(String email) {
        return Arrays.stream(GREEN_MAIL.getReceivedMessages())
                .filter(m -> {
                    try {
                        return Arrays.stream(m.getRecipients(Message.RecipientType.TO))
                                .anyMatch(a -> a.toString().equalsIgnoreCase(email));
                    } catch (Exception e) {
                        return false;
                    }
                })
                .toList();
    }

    private static String subject(MimeMessage message) {
        try {
            return message.getSubject();
        } catch (Exception e) {
            return "";
        }
    }

    /** Bản chữ thường của email (đã giải mã quoted-printable/base64). */
    private static String plainText(Part part) throws Exception {
        if (part.isMimeType("text/plain")) {
            return (String) part.getContent();
        }
        if (part.isMimeType("multipart/*")) {
            Multipart multipart = (Multipart) part.getContent();
            for (int i = 0; i < multipart.getCount(); i++) {
                String text = plainText(multipart.getBodyPart(i));
                if (text != null) {
                    return text;
                }
            }
        }
        return null;
    }
}
