package vn.kltn.bankadvisor.module.user.entity;

import java.util.Collections;
import java.util.EnumSet;
import java.util.Set;

/**
 * Vai trò của tài khoản (mỗi người một vai trò) và tập quyền của nó. Đây là ma trận phân quyền của hệ thống:
 * <pre>
 *                   PERSONAL_DATA  DATA_MANAGE  USER_MANAGE  EMAIL_MANAGE
 *   USER                 ✓
 *   ADMIN                ✓              ✓            ✓             ✓
 * </pre>
 * Quyền nằm trong mã (không có bảng role/permission): ít vai trò, ít người vận hành, đổi quyền là đổi mã có review.
 */
public enum Role {
    USER(EnumSet.of(Permission.PERSONAL_DATA)),
    ADMIN(EnumSet.allOf(Permission.class));

    private final Set<Permission> permissions;

    Role(Set<Permission> permissions) {
        this.permissions = Collections.unmodifiableSet(permissions);
    }

    public Set<Permission> permissions() {
        return permissions;
    }
}
