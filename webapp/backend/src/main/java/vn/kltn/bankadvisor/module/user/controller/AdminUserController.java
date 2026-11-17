package vn.kltn.bankadvisor.module.user.controller;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.module.user.dto.AdminUserDtos.UpdateUserRequest;
import vn.kltn.bankadvisor.module.user.dto.AdminUserDtos.UserPage;
import vn.kltn.bankadvisor.module.user.dto.AdminUserDtos.UserSummary;
import vn.kltn.bankadvisor.module.user.entity.Role;
import vn.kltn.bankadvisor.module.user.entity.UserStatus;
import vn.kltn.bankadvisor.module.user.service.UserAdminService;
import vn.kltn.bankadvisor.security.AuthUser;
import vn.kltn.bankadvisor.security.CurrentUser;

/** Quản lý người dùng — cần quyền USER_MANAGE (kiểm ở SecurityConfig). */
@RestController
@RequestMapping("/api/v1/admin/users")
public class AdminUserController {

    private final UserAdminService service;

    public AdminUserController(UserAdminService service) {
        this.service = service;
    }

    @GetMapping
    public ApiResponse<UserPage> list(@RequestParam(required = false) String q,
                                      @RequestParam(required = false) Role role,
                                      @RequestParam(required = false) UserStatus status,
                                      @RequestParam(defaultValue = "0") int page,
                                      @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.ok(service.list(q, role, status, page, size));
    }

    /** Khóa / mở tài khoản, đổi vai trò. Mọi thay đổi đều thu hồi phiên đang mở của người đó. */
    @PatchMapping("/{id}")
    public ApiResponse<UserSummary> update(@CurrentUser AuthUser actor, @PathVariable long id,
                                           @Valid @RequestBody UpdateUserRequest request) {
        return ApiResponse.ok(service.update(actor, id, request));
    }

    @PostMapping("/{id}/revoke-sessions")
    public ApiResponse<Void> revokeSessions(@CurrentUser AuthUser actor, @PathVariable long id) {
        service.revokeSessions(actor, id);
        return ApiResponse.ok(null);
    }
}
