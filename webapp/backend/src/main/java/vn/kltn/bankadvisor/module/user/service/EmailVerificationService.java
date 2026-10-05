package vn.kltn.bankadvisor.module.user.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.config.AppProperties;
import vn.kltn.bankadvisor.common.exception.AppException;
import vn.kltn.bankadvisor.common.exception.ErrorCode;
import vn.kltn.bankadvisor.common.exception.RateLimitedException;
import vn.kltn.bankadvisor.common.mail.EmailAddresses;
import vn.kltn.bankadvisor.common.mail.EmailDeliveryException;
import vn.kltn.bankadvisor.common.mail.EmailGateway;
import vn.kltn.bankadvisor.common.mail.EmailLayout;
import vn.kltn.bankadvisor.common.mail.EmailMessage;
import vn.kltn.bankadvisor.module.user.dto.EmailVerificationResponse;
import vn.kltn.bankadvisor.module.user.dto.UserResponse;
import vn.kltn.bankadvisor.module.user.entity.AppUser;
import vn.kltn.bankadvisor.module.user.repository.AppUserRepository;
import vn.kltn.bankadvisor.security.EmailVerificationTokenService;

import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;

/**
 * Xác minh email trước khi cho chọn kênh EMAIL: chứng minh người đăng ký thật sự nhận được thư ở địa chỉ đó.
 * Mỗi email xác minh có hai cách, dùng cách nào cũng được:
 * <ul>
 *   <li>link có token (hạn {@code verification-ttl}) — bấm trên máy đang dùng BankAdvisor;</li>
 *   <li>mã 6 số (hạn {@code verification-code-ttl}, sai {@value #MAX_CODE_ATTEMPTS} lần thì hủy) — đọc thư trên
 *       điện thoại rồi gõ vào web. Cần khi link không mở được trên thiết bị đọc thư (chạy trên localhost).</li>
 * </ul>
 */
@Service
public class EmailVerificationService {

    private static final Logger log = LoggerFactory.getLogger(EmailVerificationService.class);
    static final int MAX_CODE_ATTEMPTS = 5;

    private final AppUserRepository userRepository;
    private final EmailGateway emailGateway;
    private final EmailVerificationTokenService tokens;
    private final PasswordEncoder passwordEncoder;
    private final AppProperties.Mail mail;
    private final Clock clock;
    private final SecureRandom random = new SecureRandom();

    public EmailVerificationService(AppUserRepository userRepository, EmailGateway emailGateway,
                                    EmailVerificationTokenService tokens, PasswordEncoder passwordEncoder,
                                    AppProperties properties, Clock clock) {
        this.userRepository = userRepository;
        this.emailGateway = emailGateway;
        this.tokens = tokens;
        this.passwordEncoder = passwordEncoder;
        this.mail = properties.mail();
        this.clock = clock;
    }

    @Transactional(readOnly = true)
    public EmailVerificationResponse status(long userId) {
        return toResponse(require(userId));
    }

    /** Gửi (lại) email xác minh gồm link và mã 6 số mới. Giữa hai lần gửi phải cách nhau {@code resend-cooldown}. */
    @Transactional
    public EmailVerificationResponse send(long userId) {
        if (!emailGateway.isEnabled()) {
            throw new AppException(ErrorCode.EMAIL_DISABLED);
        }
        AppUser user = require(userId);
        if (user.isEmailVerified()) {
            return toResponse(user);
        }
        Instant now = clock.instant();
        Instant availableAt = resendAvailableAt(user);
        if (availableAt != null && availableAt.isAfter(now)) {
            Duration wait = Duration.between(now, availableAt);
            throw new RateLimitedException("Email xác minh vừa được gửi. Bạn có thể gửi lại sau "
                    + RateLimitedException.humanize(wait) + ".", wait);
        }
        String link = mail.link("/verify-email?token=" + tokens.issue(user.getId(), user.getEmail()));
        String code = "%06d".formatted(random.nextInt(1_000_000));
        try {
            emailGateway.send(compose(user, link, code));
        } catch (EmailDeliveryException e) {
            log.warn("Gửi email xác minh tới {} thất bại: {}", EmailAddresses.mask(user.getEmail()), e.getMessage());
            throw new AppException(ErrorCode.EMAIL_SEND_FAILED);
        }
        user.recordVerificationSent(now);
        user.issueVerificationCode(passwordEncoder.encode(code), now.plus(mail.verificationCodeTtl()));
        return toResponse(user);
    }

    /** Bấm link trong email. Gọi lại với link đã dùng vẫn thành công (không đổi gì). */
    @Transactional
    public UserResponse verify(String token) {
        EmailVerificationTokenService.Claims claims = tokens.verify(token)
                .orElseThrow(() -> new AppException(ErrorCode.VERIFICATION_LINK_INVALID));
        AppUser user = userRepository.findById(claims.userId())
                .filter(u -> u.getEmail().equals(claims.email()))
                .orElseThrow(() -> new AppException(ErrorCode.VERIFICATION_LINK_INVALID));
        user.markEmailVerified(clock.instant());
        return UserResponse.from(user);
    }

    /**
     * Nhập mã 6 số trong email (người dùng đang đăng nhập). Không rollback khi ném lỗi: số lần nhập sai phải được
     * lưu, nếu không kẻ dò mã được thử vô hạn trong 10^6 khả năng.
     */
    @Transactional(noRollbackFor = AppException.class)
    public EmailVerificationResponse confirmCode(long userId, String rawCode) {
        AppUser user = require(userId);
        if (user.isEmailVerified()) {
            return toResponse(user);
        }
        Instant now = clock.instant();
        if (!user.hasActiveVerificationCode(now)) {
            user.clearVerificationCode();
            throw new AppException(ErrorCode.VERIFICATION_CODE_EXPIRED);
        }
        String code = rawCode == null ? "" : rawCode.replaceAll("\\s", "");
        if (!code.matches("\\d{6}") || !passwordEncoder.matches(code, user.getVerificationCodeHash())) {
            int remaining = user.recordWrongVerificationCode(MAX_CODE_ATTEMPTS);
            if (remaining == 0) {
                throw new AppException(ErrorCode.VERIFICATION_CODE_EXPIRED,
                        "Nhập sai mã quá " + MAX_CODE_ATTEMPTS + " lần nên mã đã bị hủy. Bấm “Gửi lại mã” để nhận mã mới.");
            }
            throw new AppException(ErrorCode.VERIFICATION_CODE_INVALID,
                    "Mã xác minh không đúng. Còn " + remaining + " lần thử.");
        }
        user.markEmailVerified(now);
        return toResponse(user);
    }

    EmailMessage compose(AppUser user, String link, String code) {
        String hours = mail.verificationTtl().toHours() + " giờ";
        String minutes = mail.verificationCodeTtl().toMinutes() + " phút";
        String text = """
                Chào %s,

                Mã xác minh email của bạn: %s
                Nhập mã này ở trang "Theo dõi và thông báo" của BankAdvisor (mã có hiệu lực %s).

                Hoặc bấm link dưới đây trên máy bạn đang dùng BankAdvisor (link có hiệu lực %s):
                %s

                Xác minh xong, bạn có thể chọn nhận thông báo qua email cho địa chỉ %s.
                Nếu bạn không yêu cầu, hãy bỏ qua email này; tài khoản của bạn không thay đổi gì.

                — BankAdvisor
                """.formatted(user.getDisplayName(), code, minutes, hours, link, user.getEmail());
        String html = EmailLayout.page(
                EmailLayout.paragraph("Chào " + user.getDisplayName() + ",")
                        + EmailLayout.paragraph("Mã xác minh email của bạn:")
                        + EmailLayout.code(code)
                        + EmailLayout.muted("Nhập mã này ở trang “Theo dõi và thông báo” của BankAdvisor. Mã có hiệu lực "
                        + minutes + ".")
                        + EmailLayout.paragraph("Hoặc bấm nút dưới đây trên máy bạn đang dùng BankAdvisor:")
                        + EmailLayout.button(link, "Xác minh email")
                        + EmailLayout.muted("Link có hiệu lực trong " + hours + ". Nếu nút không bấm được, "
                        + "chép link này vào trình duyệt: " + link),
                EmailLayout.muted("Nếu bạn không yêu cầu, hãy bỏ qua email này; tài khoản của bạn không thay đổi gì."));
        return new EmailMessage(user.getEmail(), "Xác minh email nhận thông báo BankAdvisor", text, html);
    }

    private EmailVerificationResponse toResponse(AppUser user) {
        Instant now = clock.instant();
        Instant availableAt = user.isEmailVerified() ? null : resendAvailableAt(user);
        if (availableAt != null && !availableAt.isAfter(now)) {
            availableAt = null;
        }
        Instant codeExpiresAt = user.hasActiveVerificationCode(now) ? user.getVerificationCodeExpiresAt() : null;
        return new EmailVerificationResponse(user.getEmail(), user.isEmailVerified(),
                user.getEmailVerificationSentAt(), availableAt, codeExpiresAt);
    }

    private Instant resendAvailableAt(AppUser user) {
        Instant sentAt = user.getEmailVerificationSentAt();
        return sentAt == null ? null : sentAt.plus(mail.resendCooldown());
    }

    private AppUser require(long userId) {
        return userRepository.findById(userId).orElseThrow(() -> new AppException(ErrorCode.UNAUTHORIZED));
    }
}
