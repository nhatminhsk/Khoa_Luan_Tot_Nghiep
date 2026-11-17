package vn.kltn.bankadvisor.security;

import com.nimbusds.jose.jwk.source.ImmutableSecret;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;
import org.springframework.stereotype.Component;
import vn.kltn.bankadvisor.common.config.AppProperties;
import vn.kltn.bankadvisor.module.user.entity.AppUser;
import vn.kltn.bankadvisor.module.user.entity.Role;

import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;

/**
 * Phát và kiểm tra JWT (HS256). Token chỉ mang id, email, tên, vai trò và số phiên bản phiên; không mang dữ liệu nhạy
 * cảm. Quyền của mỗi request KHÔNG đọc từ token mà từ CSDL (SessionAuthenticationConverter).
 */
@Component
public class JwtTokenService {

    static final String ISSUER = "bank-advisor-api";
    static final String CLAIM_EMAIL = "email";
    static final String CLAIM_NAME = "name";
    static final String CLAIM_ROLE = "role";
    /** Số phiên bản phiên ({@code app_user.token_version}) lúc phát token. */
    static final String CLAIM_VERSION = "ver";

    /** Token vừa phát và thời hạn của nó (cookie hết hạn cùng lúc). */
    public record IssuedToken(String value, Duration ttl) {
    }

    private final AppProperties.Jwt props;
    private final JwtEncoder encoder;
    private final JwtDecoder decoder;

    public JwtTokenService(AppProperties properties) {
        this.props = properties.jwt();
        SecretKey key = secretKey(props.secret());
        this.encoder = new NimbusJwtEncoder(new ImmutableSecret<>(key));
        this.decoder = NimbusJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build();
    }

    public IssuedToken issue(AppUser user) {
        Instant now = Instant.now();
        Duration ttl = ttlFor(user.getRole());
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(ISSUER)
                .subject(Long.toString(user.getId()))
                .issuedAt(now)
                .expiresAt(now.plus(ttl))
                .claim(CLAIM_EMAIL, user.getEmail())
                .claim(CLAIM_NAME, user.getDisplayName())
                .claim(CLAIM_ROLE, user.getRole().name())
                .claim(CLAIM_VERSION, user.getTokenVersion())
                .build();
        JwsHeader header = JwsHeader.with(MacAlgorithm.HS256).build();
        return new IssuedToken(encoder.encode(JwtEncoderParameters.from(header, claims)).getTokenValue(), ttl);
    }

    /** Quản trị viên có phiên ngắn hơn người dùng thường. */
    Duration ttlFor(Role role) {
        return role == Role.ADMIN ? props.adminTtl() : props.ttl();
    }

    JwtDecoder decoder() {
        return decoder;
    }

    static SecretKey secretKey(String secret) {
        if (secret == null || secret.getBytes(StandardCharsets.UTF_8).length < 32) {
            throw new IllegalStateException(
                    "Thiếu app.jwt.secret (tối thiểu 32 ký tự). Đặt biến môi trường APP_JWT_SECRET hoặc khai báo trong file .env");
        }
        return new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
    }
}
