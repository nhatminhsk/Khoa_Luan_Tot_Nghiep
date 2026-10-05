package vn.kltn.bankadvisor.module.user.dto;

import vn.kltn.bankadvisor.module.user.entity.AppUser;
import vn.kltn.bankadvisor.module.user.entity.Role;

public record UserResponse(long id, String email, String displayName, Role role, boolean emailVerified) {

    public static UserResponse from(AppUser user) {
        return new UserResponse(user.getId(), user.getEmail(), user.getDisplayName(), user.getRole(),
                user.isEmailVerified());
    }
}
