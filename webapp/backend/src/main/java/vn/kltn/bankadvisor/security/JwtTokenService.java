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

import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.List;

/** Phát và kiểm tra JWT (HS256). Token chỉ mang id, email, tên, vai trò; không mang dữ liệu nhạy cảm. */
@Component
public class JwtTokenService {

    static final String ISSUER = "bank-advisor-api";
    static final String CLAIM_EMAIL = "email";
    static final String CLAIM_NAME = "name";
    static final String CLAIM_ROLE = "role";
    static final String CLAIM_ROLES = "roles";

    private final AppProperties.Jwt props;
    private final JwtEncoder encoder;
    private final JwtDecoder decoder;

    public JwtTokenService(AppProperties properties) {
        this.props = properties.jwt();
        SecretKey key = secretKey(props.secret());
        this.encoder = new NimbusJwtEncoder(new ImmutableSecret<>(key));
        this.decoder = NimbusJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build();
    }

    public String issue(long userId, String email, String displayName, String role) {
        Instant now = Instant.now();
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(ISSUER)
                .subject(Long.toString(userId))
                .issuedAt(now)
                .expiresAt(now.plus(props.ttl()))
                .claim(CLAIM_EMAIL, email)
                .claim(CLAIM_NAME, displayName)
                .claim(CLAIM_ROLE, role)
                .claim(CLAIM_ROLES, List.of(role))
                .build();
        JwsHeader header = JwsHeader.with(MacAlgorithm.HS256).build();
        return encoder.encode(JwtEncoderParameters.from(header, claims)).getTokenValue();
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
