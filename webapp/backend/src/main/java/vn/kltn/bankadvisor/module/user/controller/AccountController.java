package vn.kltn.bankadvisor.module.user.controller;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.module.user.dto.ChangeEmailRequest;
import vn.kltn.bankadvisor.module.user.dto.PasswordDtos.ChangePasswordRequest;
import vn.kltn.bankadvisor.module.user.dto.UserResponse;
import vn.kltn.bankadvisor.module.user.service.AuthService;
import vn.kltn.bankadvisor.security.AuthUser;
import vn.kltn.bankadvisor.security.CurrentUser;
import vn.kltn.bankadvisor.security.SessionCookieService;

/** Thông tin tài khoản của người đang đăng nhập. */
@RestController
@RequestMapping("/api/v1/me")
public class AccountController {

    private final AuthService authService;
    private final SessionCookieService cookies;

    public AccountController(AuthService authService, SessionCookieService cookies) {
        this.authService = authService;
        this.cookies = cookies;
    }

    /** Đổi email; email mới phải xác minh lại trước khi nhận thông báo qua email. */
    @PutMapping("/email")
    public ApiResponse<UserResponse> changeEmail(@CurrentUser AuthUser user, @Valid @RequestBody ChangeEmailRequest request,
                                                 HttpServletRequest httpRequest, HttpServletResponse response) {
        AuthService.Session session = authService.changeEmail(user.id(), request, httpRequest.getRemoteAddr());
        cookies.write(response, session.token());
        return ApiResponse.ok(UserResponse.from(session.user()));
    }

    /** Đổi mật khẩu: thu hồi phiên ở thiết bị khác, trình duyệt này nhận cookie phiên mới. */
    @PutMapping("/password")
    public ApiResponse<UserResponse> changePassword(@CurrentUser AuthUser user, @Valid @RequestBody ChangePasswordRequest request,
                                                    HttpServletRequest httpRequest, HttpServletResponse response) {
        AuthService.Session session = authService.changePassword(user.id(), request, httpRequest.getRemoteAddr());
        cookies.write(response, session.token());
        return ApiResponse.ok(UserResponse.from(session.user()));
    }

    /** Đăng xuất mọi thiết bị: thu hồi mọi phiên của tài khoản (kể cả phiên hiện tại) rồi xóa cookie. */
    @PostMapping("/sessions/revoke-all")
    public ApiResponse<Void> revokeAllSessions(@CurrentUser AuthUser user, HttpServletResponse response) {
        authService.revokeAllSessions(user.id());
        cookies.clear(response);
        return ApiResponse.ok(null);
    }
}
