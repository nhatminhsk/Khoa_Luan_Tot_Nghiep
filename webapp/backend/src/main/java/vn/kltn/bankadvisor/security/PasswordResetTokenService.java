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
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
import java.util.Optional;

/**
 * Token trong link đặt lại mật khẩu (JWT HS256, hạn {@code app.mail.password-reset-ttl}), không cần bảng lưu token.
 * <ul>
 *   <li>Ký bằng khóa riêng suy ra từ khóa phiên (nhãn "password-reset"): không dùng làm cookie phiên hay link xác minh
 *       email được, và ngược lại.</li>
 *   <li>Mang dấu vân tay của mật khẩu đang dùng (HMAC của hash mật khẩu): đổi mật khẩu xong thì dấu vân tay đổi, nên
 *       mỗi link chỉ dùng được một lần, và mọi link cũ hết hiệu lực khi mật khẩu đã đổi bằng cách khác.</li>
 * </ul>
 */
@Component
public class PasswordResetTokenService {

    private static final String KEY_LABEL = "password-reset";
    private static final String CLAIM_PURPOSE = "purpose";
    private static final String CLAIM_FINGERPRINT = "pwd";
    private static final String PURPOSE = "reset-password";

    private final SecretKey key;
    private final JwtEncoder encoder;
    private final NimbusJwtDecoder decoder;
    private final Duration ttl;
    private final Clock clock;

    public PasswordResetTokenService(AppProperties properties, Clock clock) {
        this.key = EmailVerificationTokenService.deriveKey(JwtTokenService.secretKey(properties.jwt().secret()), KEY_LABEL);
        this.encoder = new NimbusJwtEncoder(new ImmutableSecret<>(key));
        this.decoder = NimbusJwtDecoder.withSecretKey(key).macAlgorithm(MacAlgorithm.HS256).build();
        OAuth2TokenValidator<Jwt> purpose = jwt -> PURPOSE.equals(jwt.getClaimAsString(CLAIM_PURPOSE))
                ? OAuth2TokenValidatorResult.success()
                : OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token", "Sai mục đích token", null));
        this.decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(
                JwtValidators.createDefaultWithIssuer(JwtTokenService.ISSUER), purpose));
        this.ttl = properties.mail().passwordResetTtl();
        this.clock = clock;
    }

    public Duration ttl() {
        return ttl;
    }

    public String issue(long userId, String passwordHash) {
        Instant now = clock.instant();
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(JwtTokenService.ISSUER)
                .subject(Long.toString(userId))
                .issuedAt(now)
                .expiresAt(now.plus(ttl))
                .claim(CLAIM_PURPOSE, PURPOSE)
                .claim(CLAIM_FINGERPRINT, fingerprint(passwordHash))
                .build();
        return encoder.encode(JwtEncoderParameters.from(JwsHeader.with(MacAlgorithm.HS256).build(), claims))
                .getTokenValue();
    }

    /** Id người dùng nếu token đúng chữ ký, còn hạn, đúng mục đích; chưa so dấu vân tay mật khẩu. */
    public Optional<Long> userId(String token) {
        return decode(token).map(jwt -> Long.parseLong(jwt.getSubject()));
    }

    /** Token còn khớp mật khẩu đang dùng (chưa đặt lại lần nào kể từ khi gửi link). */
    public boolean matchesPassword(String token, String passwordHash) {
        return decode(token)
                .map(jwt -> jwt.getClaimAsString(CLAIM_FINGERPRINT))
                .filter(fp -> MessageDigest.isEqual(fp.getBytes(StandardCharsets.UTF_8),
                        fingerprint(passwordHash).getBytes(StandardCharsets.UTF_8)))
                .isPresent();
    }

    private Optional<Jwt> decode(String token) {
        if (token == null || token.isBlank()) {
            return Optional.empty();
        }
        try {
            Jwt jwt = decoder.decode(token.strip());
            Long.parseLong(jwt.getSubject());
            return Optional.of(jwt);
        } catch (JwtException | NumberFormatException e) {
            return Optional.empty();
        }
    }

    /** 16 byte đầu của HMAC(khóa, hash mật khẩu): không lộ hash, đủ để biết mật khẩu đã đổi chưa. */
    private String fingerprint(String passwordHash) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(key);
            byte[] digest = mac.doFinal(passwordHash.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest, 0, 16);
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("Không tính được dấu vân tay mật khẩu", e);
        }
    }
}
