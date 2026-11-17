package vn.kltn.bankadvisor.security;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.ObjectPostProcessor;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.csrf.CookieCsrfTokenRepository;
import org.springframework.security.web.csrf.CsrfFilter;
import org.springframework.security.web.util.matcher.RequestMatcher;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import vn.kltn.bankadvisor.common.config.AppProperties;
import vn.kltn.bankadvisor.module.user.entity.Permission;
import vn.kltn.bankadvisor.module.user.repository.AppUserRepository;

import java.util.List;
import java.util.Set;

/**
 * Phân quyền:
 * <ul>
 *   <li>Công khai: các nhóm GET dữ liệu liệt kê trong {@link #PUBLIC_GET} (tổng quan, lãi suất, hồ sơ ngân hàng...) và
 *       các POST trong {@link #PUBLIC_POST} (công cụ tính, đăng ký, đăng nhập, quên mật khẩu...). Đường dẫn khác bị chặn.</li>
 *   <li>Cần quyền PERSONAL_DATA (mọi tài khoản đang hoạt động): {@code /api/v1/me/**} (nhu cầu, theo dõi, thông báo)
 *       và {@code /api/v1/auth/me}.</li>
 *   <li>Quản trị: {@code /admin/users} và {@code /admin/audit} cần USER_MANAGE, {@code /admin/imports} cần DATA_MANAGE,
 *       {@code /admin/email-queue} cần EMAIL_MANAGE; đường dẫn quản trị khác bị chặn.</li>
 *   <li>Quyền của mỗi request đọc từ tài khoản hiện hành trong CSDL (SessionAuthenticationConverter): tài khoản bị khóa
 *       hoặc phiên bị thu hồi thì token cũ hết hiệu lực ngay.</li>
 *   <li>Đóng hẳn: {@code /api/v1/internal/**} (dành cho pipeline gọi bằng token dịch vụ, chưa làm).</li>
 * </ul>
 * Không dùng session phía server: mỗi request tự mang JWT trong cookie. Request đổi trạng thái cần token CSRF.
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    /** GET công khai, liệt kê từng nhóm: API mới mặc định bị chặn cho tới khi được thêm vào đây hoặc vào nhóm cần quyền. */
    static final String[] PUBLIC_GET = {
            "/api/v1/auth/session", "/api/v1/overview", "/api/v1/datasets",
            "/api/v1/banks", "/api/v1/banks/**", "/api/v1/rates/**", "/api/v1/indicators", "/api/v1/indicators/**",
            "/api/v1/macro/**", "/api/v1/programs", "/api/v1/rankings"
    };

    /** POST không cần đăng nhập: tài khoản (đăng ký, đăng nhập, quên mật khẩu...) và công cụ tính của trang gửi / vay. */
    static final String[] PUBLIC_POST = {
            "/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/logout", "/api/v1/auth/verify-email",
            "/api/v1/auth/password-reset", "/api/v1/auth/password-reset/confirm",
            "/api/v1/advisor/savings", "/api/v1/advisor/loans"
    };

    /** Phương thức không đổi trạng thái: không cần token CSRF. */
    private static final Set<String> SAFE_METHODS = Set.of("GET", "HEAD", "TRACE", "OPTIONS");

    /**
     * Request phải kèm token CSRF. oauth2ResourceServer mặc định bỏ kiểm tra CSRF cho mọi request mà BearerTokenResolver
     * đọc được token, nhưng ở đây token nằm trong cookie phiên (trình duyệt tự gửi) nên phải kiểm lại; chỉ bỏ qua khi
     * token đi qua header Authorization (curl, script: trang ở site khác không tự gắn được header này). Kiểm thử bổ sung
     * ngày 10/11/2026 phát hiện POST /api/v1/me/** có cookie phiên nhưng thiếu header X-XSRF-TOKEN vẫn được nhận.
     */
    static final RequestMatcher CSRF_REQUIRED = request -> {
        String uri = request.getRequestURI();
        return !SAFE_METHODS.contains(request.getMethod())
                && request.getHeader(HttpHeaders.AUTHORIZATION) == null
                // Công cụ tính chỉ đọc dữ liệu, không đổi trạng thái; H2 console chỉ bật khi phát triển.
                && !uri.startsWith("/api/v1/advisor/")
                && !uri.startsWith("/h2-console");
    };

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http, JwtTokenService tokens, SessionCookieService cookies,
                                            AppUserRepository users, AppProperties properties) throws Exception {
        JsonSecurityErrorHandler errors = new JsonSecurityErrorHandler(cookies);
        // Token CSRF kiểu "double-submit cookie" cho SPA: cookie XSRF-TOKEN (JavaScript đọc được) được đặt ở mọi response;
        // request đổi trạng thái phải gửi lại giá trị đó trong header X-XSRF-TOKEN. Trang ở site khác không đọc được cookie
        // nên không giả được header. Đây là lớp thứ ba, thêm vào cookie phiên SameSite=Lax và bộ lọc CORS chặn Origin lạ.
        CookieCsrfTokenRepository csrfTokens = CookieCsrfTokenRepository.withHttpOnlyFalse();
        csrfTokens.setCookieCustomizer(cookie -> cookie.path("/").sameSite("Lax").secure(properties.jwt().cookieSecure()));
        http
                .csrf(csrf -> csrf.spa()
                        .csrfTokenRepository(csrfTokens)
                        // Đặt lại bộ so khớp sau cùng để quy tắc bỏ qua của oauth2ResourceServer không thắng (xem CSRF_REQUIRED).
                        .withObjectPostProcessor(new ObjectPostProcessor<CsrfFilter>() {
                            @Override
                            public <O extends CsrfFilter> O postProcess(O filter) {
                                filter.setRequireCsrfProtectionMatcher(CSRF_REQUIRED);
                                return filter;
                            }
                        }))
                .addFilterAfter(new CsrfCookieFilter(), CsrfFilter.class)
                .cors(Customizer.withDefaults())
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                // HSTS đặt ở nginx (HSTS_MAX_AGE): mặc định của Spring (1 năm, khi chạy sau HTTPS) sẽ ép mọi cổng của
                // localhost sang HTTPS khi thử bằng chứng chỉ tự ký.
                .headers(h -> h.frameOptions(f -> f.sameOrigin()).httpStrictTransportSecurity(hsts -> hsts.disable()))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/api/v1/internal/**").denyAll()
                        // Quản trị: mỗi nhóm endpoint một quyền (Role → Permission ở enum Role); nhóm lạ bị chặn.
                        .requestMatchers("/api/v1/admin/users", "/api/v1/admin/users/**",
                                "/api/v1/admin/audit", "/api/v1/admin/audit/**")
                        .hasAuthority(Permission.USER_MANAGE.authority())
                        .requestMatchers("/api/v1/admin/imports", "/api/v1/admin/imports/**")
                        .hasAuthority(Permission.DATA_MANAGE.authority())
                        .requestMatchers("/api/v1/admin/email-queue", "/api/v1/admin/email-queue/**")
                        .hasAuthority(Permission.EMAIL_MANAGE.authority())
                        .requestMatchers("/api/v1/admin/**").denyAll()
                        .requestMatchers("/api/v1/me", "/api/v1/me/**", "/api/v1/auth/me")
                        .hasAuthority(Permission.PERSONAL_DATA.authority())
                        .requestMatchers(HttpMethod.POST, PUBLIC_POST).permitAll()
                        .requestMatchers(HttpMethod.GET, PUBLIC_GET).permitAll()
                        .requestMatchers("/actuator/health", "/h2-console/**", "/error").permitAll()
                        .anyRequest().denyAll())
                .oauth2ResourceServer(rs -> rs
                        .bearerTokenResolver(new SessionTokenResolver(cookies.cookieName()))
                        .authenticationEntryPoint(errors)
                        .accessDeniedHandler(errors)
                        .jwt(jwt -> jwt.decoder(tokens.decoder())
                                .jwtAuthenticationConverter(new SessionAuthenticationConverter(users))))
                .exceptionHandling(e -> e.authenticationEntryPoint(errors).accessDeniedHandler(errors));
        return http.build();
    }

    @Bean
    JwtDecoder jwtDecoder(JwtTokenService tokens) {
        return tokens.decoder();
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }

    /**
     * Trình duyệt gọi API qua rewrite của Next.js (cùng origin) nên không cần CORS.
     * Danh sách này chỉ để gọi thẳng từ origin khác khi cần (ví dụ app.cors-origins=http://localhost:3000).
     */
    @Bean
    CorsConfigurationSource corsConfigurationSource(AppProperties properties) {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOrigins(properties.corsOrigins());
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE"));
        config.setAllowedHeaders(List.of("Content-Type", "Authorization", "X-XSRF-TOKEN"));
        config.setAllowCredentials(true);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", config);
        return source;
    }
}
