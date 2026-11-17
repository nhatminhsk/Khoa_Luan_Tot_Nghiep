package vn.kltn.bankadvisor.module.user.dto;

import vn.kltn.bankadvisor.module.user.entity.AppUser;
import vn.kltn.bankadvisor.module.user.entity.Permission;
import vn.kltn.bankadvisor.module.user.entity.Role;

import java.util.Set;

/** @param permissions quyền của vai trò hiện hành — giao diện dựng menu theo quyền, backend vẫn kiểm lại mỗi request */
public record UserResponse(long id, String email, String displayName, Role role, boolean emailVerified,
                           Set<Permission> permissions) {

    public static UserResponse from(AppUser user) {
        return new UserResponse(user.getId(), user.getEmail(), user.getDisplayName(), user.getRole(),
                user.isEmailVerified(), user.getRole().permissions());
    }
}
