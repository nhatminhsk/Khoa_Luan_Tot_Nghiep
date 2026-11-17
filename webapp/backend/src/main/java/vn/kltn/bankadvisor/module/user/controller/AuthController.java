package vn.kltn.bankadvisor.module.user.controller;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.module.user.dto.LoginRequest;
import vn.kltn.bankadvisor.module.user.dto.PasswordDtos.PasswordResetConfirmRequest;
import vn.kltn.bankadvisor.module.user.dto.PasswordDtos.PasswordResetRequest;
import vn.kltn.bankadvisor.module.user.dto.RegisterRequest;
import vn.kltn.bankadvisor.module.user.dto.UserResponse;
import vn.kltn.bankadvisor.module.user.service.AuthService;
import vn.kltn.bankadvisor.module.user.service.PasswordResetService;
import vn.kltn.bankadvisor.security.AuthUser;
import vn.kltn.bankadvisor.security.CurrentUser;
import vn.kltn.bankadvisor.security.SessionCookieService;

/** Token không trả trong body: chỉ nằm trong cookie httpOnly để JavaScript phía trình duyệt không đọc được. */
@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService authService;
    private final PasswordResetService passwordResetService;
    private final SessionCookieService cookies;

    public AuthController(AuthService authService, PasswordResetService passwordResetService,
                          SessionCookieService cookies) {
        this.authService = authService;
        this.passwordResetService = passwordResetService;
        this.cookies = cookies;
    }

    @PostMapping("/register")
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<UserResponse> register(@Valid @RequestBody RegisterRequest request, HttpServletResponse response) {
        AuthService.Session session = authService.register(request);
        cookies.write(response, session.token());
        return ApiResponse.ok(UserResponse.from(session.user()));
    }

    @PostMapping("/login")
    public ApiResponse<UserResponse> login(@Valid @RequestBody LoginRequest request, HttpServletRequest httpRequest,
                                           HttpServletResponse response) {
        AuthService.Session session = authService.login(request, httpRequest.getRemoteAddr());
        cookies.write(response, session.token());
        return ApiResponse.ok(UserResponse.from(session.user()));
    }

    @PostMapping("/logout")
    public ApiResponse<Void> logout(HttpServletResponse response) {
        cookies.clear(response);
        return ApiResponse.ok(null);
    }

    /** Quên mật khẩu: gửi link đặt lại tới email nếu email có tài khoản. Luôn trả cùng một kết quả. */
    @PostMapping("/password-reset")
    public ApiResponse<Void> requestPasswordReset(@Valid @RequestBody PasswordResetRequest request) {
        passwordResetService.request(request.email());
        return ApiResponse.ok(null);
    }

    /** Đặt mật khẩu mới bằng token trong link email. Không tự đăng nhập: người dùng đăng nhập lại bằng mật khẩu mới. */
    @PostMapping("/password-reset/confirm")
    public ApiResponse<Void> confirmPasswordReset(@Valid @RequestBody PasswordResetConfirmRequest request,
                                                  HttpServletRequest httpRequest) {
        passwordResetService.confirm(request, httpRequest.getRemoteAddr());
        return ApiResponse.ok(null);
    }

    @GetMapping("/me")
    public ApiResponse<UserResponse> me(@CurrentUser AuthUser user) {
        return ApiResponse.ok(UserResponse.from(authService.require(user.id())));
    }

    /**
     * Giống /me nhưng không bắt buộc đăng nhập: trả {@code data: null} cho khách. Giao diện gọi endpoint này
     * ở mọi trang để biết trạng thái đăng nhập mà không sinh lỗi 401.
     */
    @GetMapping("/session")
    public ApiResponse<UserResponse> session(Authentication authentication) {
        if (authentication instanceof JwtAuthenticationToken token) {
            return authService.find(Long.parseLong(token.getToken().getSubject()))
                    .map(UserResponse::from)
                    .map(ApiResponse::ok)
                    .orElseGet(() -> ApiResponse.ok(null));
        }
        return ApiResponse.ok(null);
    }
}
