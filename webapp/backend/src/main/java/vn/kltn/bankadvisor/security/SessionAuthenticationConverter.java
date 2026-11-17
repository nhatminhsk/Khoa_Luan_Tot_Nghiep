package vn.kltn.bankadvisor.security;

import org.springframework.core.convert.converter.Converter;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import vn.kltn.bankadvisor.module.user.entity.AppUser;
import vn.kltn.bankadvisor.module.user.repository.AppUserRepository;

import java.util.ArrayList;
import java.util.List;

/**
 * Dựng quyền của request từ tài khoản HIỆN HÀNH trong CSDL, không tin vai trò ghi trong JWT. Chữ ký và hạn của token
 * đã được kiểm trước bước này; ở đây kiểm thêm:
 * <ul>
 *   <li>tài khoản còn tồn tại và đang ACTIVE (bị khóa → 403 ACCOUNT_LOCKED);</li>
 *   <li>số phiên bản trong token bằng {@code app_user.token_version} — khóa tài khoản, đổi vai trò hay "đăng xuất mọi
 *       thiết bị" tăng số này, nên token cũ hết hiệu lực ngay ở request kế tiếp.</li>
 * </ul>
 * Quyền = {@code ROLE_<vai trò>} + các {@code PERM_*} của vai trò đó ({@code Role.permissions()}).
 * Chỉ chạy ở các đường dẫn cần đăng nhập (SessionTokenResolver), nên mỗi request có đúng một lần đọc CSDL.
 */
class SessionAuthenticationConverter implements Converter<Jwt, AbstractAuthenticationToken> {

    private final AppUserRepository users;

    SessionAuthenticationConverter(AppUserRepository users) {
        this.users = users;
    }

    @Override
    public AbstractAuthenticationToken convert(Jwt jwt) {
        AppUser user = users.findById(Long.parseLong(jwt.getSubject()))
                .orElseThrow(() -> new SessionRevokedException("Tài khoản không còn tồn tại"));
        if (!user.isActive()) {
            throw new AccountLockedException();
        }
        Object version = jwt.getClaims().get(JwtTokenService.CLAIM_VERSION);
        if (!(version instanceof Number number) || number.intValue() != user.getTokenVersion()) {
            throw new SessionRevokedException("Phiên đăng nhập đã bị thu hồi");
        }
        List<GrantedAuthority> authorities = new ArrayList<>();
        authorities.add(new SimpleGrantedAuthority("ROLE_" + user.getRole().name()));
        user.getRole().permissions().forEach(p -> authorities.add(new SimpleGrantedAuthority(p.authority())));
        return new JwtAuthenticationToken(jwt, authorities, jwt.getSubject());
    }

    /** Token hợp lệ về chữ ký nhưng tài khoản đã bị khóa. */
    static class AccountLockedException extends AuthenticationException {
        AccountLockedException() {
            super("Tài khoản đã bị khóa");
        }
    }

    /** Token hợp lệ về chữ ký nhưng đã bị thu hồi (tài khoản bị xóa, đổi vai trò, đăng xuất mọi thiết bị). */
    static class SessionRevokedException extends AuthenticationException {
        SessionRevokedException(String message) {
            super(message);
        }
    }
}
