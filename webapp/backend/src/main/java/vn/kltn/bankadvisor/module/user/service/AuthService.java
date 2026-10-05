package vn.kltn.bankadvisor.module.user.service;

import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.exception.AppException;
import vn.kltn.bankadvisor.common.exception.ErrorCode;
import vn.kltn.bankadvisor.module.user.dto.ChangeEmailRequest;
import vn.kltn.bankadvisor.module.user.dto.LoginRequest;
import vn.kltn.bankadvisor.module.user.dto.RegisterRequest;
import vn.kltn.bankadvisor.module.user.entity.AppUser;
import vn.kltn.bankadvisor.module.user.entity.Role;
import vn.kltn.bankadvisor.module.user.repository.AppUserRepository;
import vn.kltn.bankadvisor.security.JwtTokenService;

import java.time.Clock;
import java.util.Locale;
import java.util.Optional;

@Service
public class AuthService {

    private final AppUserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenService tokenService;
    private final LoginThrottle loginThrottle;
    private final Clock clock;
    /** Hash giả để so sánh khi email không tồn tại, giúp thời gian phản hồi không lộ email nào đã đăng ký. */
    private final String dummyHash;

    public AuthService(AppUserRepository userRepository, PasswordEncoder passwordEncoder,
                       JwtTokenService tokenService, LoginThrottle loginThrottle, Clock clock) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.tokenService = tokenService;
        this.loginThrottle = loginThrottle;
        this.clock = clock;
        this.dummyHash = passwordEncoder.encode("dummy-password-for-timing");
    }

    /** Người dùng và token phiên vừa phát. */
    public record Session(AppUser user, String token) {
    }

    @Transactional
    public Session register(RegisterRequest request) {
        String email = normalizeEmail(request.email());
        if (userRepository.existsByEmail(email)) {
            throw new AppException(ErrorCode.EMAIL_TAKEN);
        }
        AppUser user = userRepository.save(AppUser.create(email, passwordEncoder.encode(request.password()),
                request.displayName().strip(), Role.USER, clock.instant()));
        return new Session(user, issue(user));
    }

    /** @param clientIp IP người dùng (đã qua ForwardedHeaderFilter), để giới hạn số lần đăng nhập sai */
    @Transactional(readOnly = true)
    public Session login(LoginRequest request, String clientIp) {
        String email = normalizeEmail(request.email());
        loginThrottle.checkAllowed(email, clientIp);
        Optional<AppUser> user = userRepository.findByEmail(email);
        String hash = user.map(AppUser::getPasswordHash).orElse(dummyHash);
        boolean matches = passwordEncoder.matches(request.password(), hash);
        if (user.isEmpty() || !matches) {
            loginThrottle.recordFailure(email, clientIp);
            throw new AppException(ErrorCode.INVALID_CREDENTIALS);
        }
        loginThrottle.recordSuccess(email, clientIp);
        return new Session(user.get(), issue(user.get()));
    }

    /**
     * Đổi email đăng nhập, cần mật khẩu hiện tại. Nhập sai mật khẩu tính vào giới hạn đăng nhập sai (chống dò mật
     * khẩu qua endpoint này). Trả phiên mới vì token cũ còn mang email cũ.
     */
    @Transactional
    public Session changeEmail(long userId, ChangeEmailRequest request, String clientIp) {
        AppUser user = find(userId).orElseThrow(() -> new AppException(ErrorCode.UNAUTHORIZED));
        loginThrottle.checkAllowed(user.getEmail(), clientIp);
        if (!passwordEncoder.matches(request.currentPassword(), user.getPasswordHash())) {
            loginThrottle.recordFailure(user.getEmail(), clientIp);
            throw new AppException(ErrorCode.WRONG_PASSWORD);
        }
        String email = normalizeEmail(request.newEmail());
        if (email.equals(user.getEmail())) {
            throw new AppException(ErrorCode.BAD_REQUEST, "Email mới trùng với email đang dùng");
        }
        if (userRepository.existsByEmail(email)) {
            throw new AppException(ErrorCode.EMAIL_TAKEN);
        }
        user.changeEmail(email);
        return new Session(user, issue(user));
    }

    @Transactional(readOnly = true)
    public AppUser require(long userId) {
        return find(userId).orElseThrow(() -> new AppException(ErrorCode.UNAUTHORIZED));
    }

    @Transactional(readOnly = true)
    public Optional<AppUser> find(long userId) {
        return userRepository.findById(userId);
    }

    private String issue(AppUser user) {
        return tokenService.issue(user.getId(), user.getEmail(), user.getDisplayName(), user.getRole().name());
    }

    public static String normalizeEmail(String email) {
        return email.strip().toLowerCase(Locale.ROOT);
    }
}
