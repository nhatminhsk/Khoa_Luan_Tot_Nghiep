package vn.kltn.bankadvisor.security;

import org.springframework.security.oauth2.jwt.Jwt;

/** Người dùng đang đăng nhập, đọc từ JWT; không truy vấn DB. */
public record AuthUser(long id, String email, String displayName, String role) {

    static AuthUser from(Jwt jwt) {
        return new AuthUser(
                Long.parseLong(jwt.getSubject()),
                jwt.getClaimAsString(JwtTokenService.CLAIM_EMAIL),
                jwt.getClaimAsString(JwtTokenService.CLAIM_NAME),
                jwt.getClaimAsString(JwtTokenService.CLAIM_ROLE));
    }
}
