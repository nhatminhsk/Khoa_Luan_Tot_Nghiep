package vn.kltn.bankadvisor.security;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.oauth2.server.resource.authentication.JwtGrantedAuthoritiesConverter;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import vn.kltn.bankadvisor.common.config.AppProperties;

import java.util.List;

/**
 * Phân quyền:
 * <ul>
 *   <li>Công khai: mọi GET dữ liệu (tổng quan, lãi suất, hồ sơ ngân hàng...), công cụ tính của trang
 *       gửi tiết kiệm / vay, đăng ký, đăng nhập, đăng xuất, xác minh email bằng link.</li>
 *   <li>Cần đăng nhập: {@code /api/v1/me/**} (nhu cầu, theo dõi, thông báo) và {@code /api/v1/auth/me}.</li>
 *   <li>Quản trị viên: {@code /api/v1/admin/**}.</li>
 * </ul>
 * Không dùng session phía server: mỗi request tự mang JWT trong cookie.
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http, JwtTokenService tokens,
                                            SessionCookieService cookies) throws Exception {
        JsonSecurityErrorHandler errors = new JsonSecurityErrorHandler(cookies);
        http
                // Không dùng token CSRF vì đã có hai lớp chặn request giả mạo từ trang khác:
                // cookie phiên SameSite=Lax (trình duyệt không gửi cookie kèm POST/PUT/DELETE từ site khác), và
                // bộ lọc CORS trả 403 cho mọi request mang header Origin lạ (danh sách app.cors-origins để trống).
                .csrf(AbstractHttpConfigurer::disable)
                .cors(Customizer.withDefaults())
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .headers(h -> h.frameOptions(f -> f.sameOrigin()))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/api/v1/admin/**").hasRole("ADMIN")
                        .requestMatchers("/api/v1/me", "/api/v1/me/**", "/api/v1/auth/me").authenticated()
                        .requestMatchers(HttpMethod.POST,
                                "/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/logout",
                                "/api/v1/auth/verify-email", "/api/v1/advisor/**").permitAll()
                        .requestMatchers(HttpMethod.GET, "/api/v1/**").permitAll()
                        .requestMatchers("/actuator/health", "/h2-console/**", "/error").permitAll()
                        .anyRequest().denyAll())
                .oauth2ResourceServer(rs -> rs
                        .bearerTokenResolver(new SessionTokenResolver(cookies.cookieName()))
                        .authenticationEntryPoint(errors)
                        .accessDeniedHandler(errors)
                        .jwt(jwt -> jwt.decoder(tokens.decoder()).jwtAuthenticationConverter(authenticationConverter())))
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
        config.setAllowedHeaders(List.of("Content-Type", "Authorization"));
        config.setAllowCredentials(true);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", config);
        return source;
    }

    private static JwtAuthenticationConverter authenticationConverter() {
        JwtGrantedAuthoritiesConverter authorities = new JwtGrantedAuthoritiesConverter();
        authorities.setAuthoritiesClaimName(JwtTokenService.CLAIM_ROLES);
        authorities.setAuthorityPrefix("ROLE_");
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(authorities);
        return converter;
    }
}
