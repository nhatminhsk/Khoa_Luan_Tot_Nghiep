package vn.kltn.bankadvisor.module.user.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.config.AppProperties;
import vn.kltn.bankadvisor.module.user.entity.AppUser;
import vn.kltn.bankadvisor.module.user.entity.Role;
import vn.kltn.bankadvisor.module.user.repository.AppUserRepository;

import java.time.Clock;

/**
 * Tạo tài khoản quản trị lúc khởi động nếu có cấu hình {@code app.bootstrap-admin} (lấy từ biến môi trường
 * hoặc file .env, không ghi mật khẩu trong mã nguồn). Tài khoản đã tồn tại thì không đụng tới.
 */
@Component
@Order(1)
public class AdminBootstrap implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(AdminBootstrap.class);

    private final AppUserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final AppProperties.BootstrapAdmin admin;
    private final Clock clock;

    public AdminBootstrap(AppUserRepository userRepository, PasswordEncoder passwordEncoder,
                          AppProperties properties, Clock clock) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.admin = properties.bootstrapAdmin();
        this.clock = clock;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        if (admin == null || isBlank(admin.email()) || isBlank(admin.password())) {
            return;
        }
        String email = AuthService.normalizeEmail(admin.email());
        if (userRepository.existsByEmail(email)) {
            return;
        }
        userRepository.save(AppUser.create(email, passwordEncoder.encode(admin.password()), "Quản trị viên",
                Role.ADMIN, clock.instant()));
        log.info("Đã tạo tài khoản quản trị {}", email);
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }
}
