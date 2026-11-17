package vn.kltn.bankadvisor.module.user.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.config.AppProperties;
import vn.kltn.bankadvisor.common.exception.AppException;
import vn.kltn.bankadvisor.common.exception.ErrorCode;
import vn.kltn.bankadvisor.common.mail.EmailAddresses;
import vn.kltn.bankadvisor.common.mail.EmailDeliveryException;
import vn.kltn.bankadvisor.common.mail.EmailGateway;
import vn.kltn.bankadvisor.common.mail.EmailLayout;
import vn.kltn.bankadvisor.common.mail.EmailMessage;
import vn.kltn.bankadvisor.module.user.dto.PasswordDtos.PasswordResetConfirmRequest;
import vn.kltn.bankadvisor.module.user.entity.AppUser;
import vn.kltn.bankadvisor.module.user.repository.AppUserRepository;
import vn.kltn.bankadvisor.security.PasswordResetTokenService;

import java.time.Clock;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Quên mật khẩu: gửi link đặt lại mật khẩu tới email của tài khoản, rồi đặt mật khẩu mới bằng token trong link.
 * <ul>
 *   <li>Xin link luôn trả cùng một kết quả, dù email có tài khoản, bị khóa hay gửi thư lỗi: không dò được email nào
 *       đã đăng ký.</li>
 *   <li>Mỗi email chỉ được gửi một thư trong {@code resend-cooldown}, để không ai dùng hệ thống gửi dồn thư vào hộp thư
 *       người khác (giới hạn theo IP nằm ở nginx).</li>
 *   <li>Đặt mật khẩu mới thì thu hồi mọi phiên cũ; link chỉ dùng được một lần (xem {@link PasswordResetTokenService}).
 *       Bấm được link trong thư cũng chứng minh người dùng nhận được thư ở địa chỉ đó, nên email được ghi là đã xác minh.</li>
 * </ul>
 */
@Service
public class PasswordResetService {

    private static final Logger log = LoggerFactory.getLogger(PasswordResetService.class);

    private final AppUserRepository users;
    private final EmailGateway emailGateway;
    private final PasswordResetTokenService tokens;
    private final PasswordEncoder passwordEncoder;
    private final LoginThrottle loginThrottle;
    private final AppProperties.Mail mail;
    private final Clock clock;
    /** Lần xin link gần nhất của mỗi email (trong bộ nhớ; khởi động lại thì xóa, chấp nhận được). */
    private final Map<String, Instant> lastRequested = new ConcurrentHashMap<>();

    public PasswordResetService(AppUserRepository users, EmailGateway emailGateway, PasswordResetTokenService tokens,
                                PasswordEncoder passwordEncoder, LoginThrottle loginThrottle, AppProperties properties,
                                Clock clock) {
        this.users = users;
        this.emailGateway = emailGateway;
        this.tokens = tokens;
        this.passwordEncoder = passwordEncoder;
        this.loginThrottle = loginThrottle;
        this.mail = properties.mail();
        this.clock = clock;
    }

    @Transactional(readOnly = true)
    public void request(String rawEmail) {
        if (!emailGateway.isEnabled()) {
            throw new AppException(ErrorCode.EMAIL_DISABLED);
        }
        String email = AuthService.normalizeEmail(rawEmail);
        Instant now = clock.instant();
        lastRequested.values().removeIf(at -> !at.plus(mail.resendCooldown()).isAfter(now));
        if (lastRequested.putIfAbsent(email, now) != null) {
            return;
        }
        users.findByEmail(email).filter(AppUser::isActive).ifPresent(user -> {
            String link = mail.link("/reset-password?token=" + tokens.issue(user.getId(), user.getPasswordHash()));
            try {
                emailGateway.send(compose(user, link));
            } catch (EmailDeliveryException e) {
                log.warn("Gửi thư đặt lại mật khẩu tới {} thất bại: {}", EmailAddresses.mask(user.getEmail()), e.getMessage());
            }
        });
    }

    @Transactional
    public void confirm(PasswordResetConfirmRequest request, String clientIp) {
        AppUser user = tokens.userId(request.token())
                .flatMap(users::findById)
                .filter(AppUser::isActive)
                .filter(u -> tokens.matchesPassword(request.token(), u.getPasswordHash()))
                .orElseThrow(() -> new AppException(ErrorCode.PASSWORD_RESET_INVALID));
        user.changePassword(passwordEncoder.encode(request.newPassword()));
        if (!user.isEmailVerified()) {
            user.markEmailVerified(clock.instant());
        }
        loginThrottle.recordSuccess(user.getEmail(), clientIp);
        log.info("PASSWORD_RESET user={}", EmailAddresses.mask(user.getEmail()));
    }

    EmailMessage compose(AppUser user, String link) {
        String minutes = tokens.ttl().toMinutes() + " phút";
        String text = """
                Chào %s,

                Có yêu cầu đặt lại mật khẩu cho tài khoản BankAdvisor %s.
                Bấm link dưới đây để đặt mật khẩu mới (link có hiệu lực %s và chỉ dùng được một lần):
                %s

                Nếu bạn không yêu cầu, hãy bỏ qua email này; mật khẩu của bạn không thay đổi.

                — BankAdvisor
                """.formatted(user.getDisplayName(), user.getEmail(), minutes, link);
        String html = EmailLayout.page(
                EmailLayout.paragraph("Chào " + user.getDisplayName() + ",")
                        + EmailLayout.paragraph("Có yêu cầu đặt lại mật khẩu cho tài khoản BankAdvisor " + user.getEmail() + ".")
                        + EmailLayout.button(link, "Đặt mật khẩu mới")
                        + EmailLayout.muted("Link có hiệu lực trong " + minutes + " và chỉ dùng được một lần. Nếu nút không "
                        + "bấm được, chép link này vào trình duyệt: " + link),
                EmailLayout.muted("Nếu bạn không yêu cầu, hãy bỏ qua email này; mật khẩu của bạn không thay đổi."));
        return new EmailMessage(user.getEmail(), "Đặt lại mật khẩu BankAdvisor", text, html);
    }
}
