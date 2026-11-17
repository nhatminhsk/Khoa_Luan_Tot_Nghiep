package vn.kltn.bankadvisor.module.user.dto;

import jakarta.validation.constraints.Size;
import vn.kltn.bankadvisor.common.api.PageResponse;
import vn.kltn.bankadvisor.module.user.entity.AppUser;
import vn.kltn.bankadvisor.module.user.entity.Role;
import vn.kltn.bankadvisor.module.user.entity.UserStatus;

import java.time.Instant;

/** DTO của trang quản lý người dùng. Không có nhu cầu đã lưu hay dữ liệu cá nhân khác: quản trị ≠ đọc dữ liệu riêng. */
public final class AdminUserDtos {

    private AdminUserDtos() {
    }

    public record UserSummary(long id, String email, String displayName, Role role, UserStatus status,
                              boolean emailVerified, Instant lastLoginAt, Instant createdAt) {

        public static UserSummary from(AppUser user) {
            return new UserSummary(user.getId(), user.getEmail(), user.getDisplayName(), user.getRole(),
                    user.getStatus(), user.isEmailVerified(), user.getLastLoginAt(), user.getCreatedAt());
        }
    }

    /** Thống kê nhanh đầu trang: tổng, đang hoạt động, bị khóa, quản trị viên, đã xác minh email. */
    public record UserStats(long total, long active, long locked, long admins, long emailVerified) {
    }

    public record UserPage(UserStats stats, PageResponse<UserSummary> users) {
    }

    /**
     * Đổi vai trò và/hoặc trạng thái. Trường null = giữ nguyên.
     *
     * @param reason lý do (bắt buộc khi khóa) — ghi vào log thao tác quản trị
     */
    public record UpdateUserRequest(Role role, UserStatus status, @Size(max = 200) String reason) {
    }
}
