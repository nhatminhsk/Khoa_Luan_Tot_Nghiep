package vn.kltn.bankadvisor.security;

import com.nimbusds.jose.jwk.source.ImmutableSecret;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2TokenValidatorResult;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.security.oauth2.jwt.JwtException;
import org.springframework.security.oauth2.jwt.JwtValidators;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;
import org.springframework.stereotype.Component;
import vn.kltn.bankadvisor.common.config.AppProperties;

import javax.crypto.Mac;
import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Optional;

/**
 * Token trong link xác minh email (JWT HS256, hạn {@code app.mail.verification-ttl}).
 * <p>
 * Ký bằng một khóa riêng suy ra từ khóa phiên (HMAC(khóa phiên, "email-verification")), nên bộ giải mã phiên
 * không chấp nhận token này: ai có link trong email cũng không dùng nó làm cookie đăng nhập được. Ngược lại,
 * token phiên cũng không dùng làm link xác minh được.
 */
@Component
public class EmailVerificationTokenService {

    private static final String KEY_LABEL = "email-verification";
    private static final String CLAIM_PURPOSE = "purpose";
    private static final String CLAIM_EMAIL = "email";
    private static final String PURPOSE = "verify-email";

    private final JwtEncoder encoder;
    private final NimbusJwtDecoder decoder;
    private final Duration ttl;
    private final Clock clock;

    public EmailVerificationTokenService(AppProperties properties, Clock clock) {
        SecretKey key = deriveKey(JwtTokenService.secretKey(properties.jwt().secret()));
        this.encoder = new NimbusJwtEncoder(new ImmutableSecret<>(key));
        this.decoder = NimbusJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build();
        OAuth2TokenValidator<Jwt> purpose = jwt -> PURPOSE.equals(jwt.getClaimAsString(CLAIM_PURPOSE))
                ? OAuth2TokenValidatorResult.success()
                : OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token", "Sai mục đích token", null));
        this.decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(
                JwtValidators.createDefaultWithIssuer(JwtTokenService.ISSUER), purpose));
        this.ttl = properties.mail().verificationTtl();
        this.clock = clock;
    }

    /** Người dùng và email mà token xác nhận. */
    public record Claims(long userId, String email) {
    }

    public String issue(long userId, String email) {
        Instant now = clock.instant();
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(JwtTokenService.ISSUER)
                .subject(Long.toString(userId))
                .issuedAt(now)
                .expiresAt(now.plus(ttl))
                .claim(CLAIM_PURPOSE, PURPOSE)
                .claim(CLAIM_EMAIL, email)
                .build();
        return encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).build(), claims))
                .getTokenValue();
    }

    /** Rỗng khi token sai chữ ký, hết hạn, sai định dạng hoặc không phải token xác minh email. */
    public Optional<Claims> verify(String token) {
        if (token == null || token.isBlank()) {
            return Optional.empty();
        }
        try {
            Jwt jwt = decoder.decode(token.strip());
            return Optional.of(new Claims(Long.parseLong(jwt.getSubject()), jwt.getClaimAsString(CLAIM_EMAIL)));
        } catch (JwtException | NumberFormatException e) {
            return Optional.empty();
        }
    }

    private static SecretKey deriveKey(SecretKey sessionKey) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(sessionKey);
            byte[] derived = mac.doFinal(KEY_LABEL.getBytes(StandardCharsets.UTF_8));
            return new SecretKeySpec(derived, "HmacSHA256");
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("Không tạo được khóa ký link xác minh email", e);
        }
    }
}
