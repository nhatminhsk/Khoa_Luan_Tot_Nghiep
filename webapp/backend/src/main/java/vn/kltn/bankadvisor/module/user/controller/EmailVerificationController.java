package vn.kltn.bankadvisor.module.user.controller;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.module.user.dto.EmailVerificationResponse;
import vn.kltn.bankadvisor.module.user.dto.UserResponse;
import vn.kltn.bankadvisor.module.user.dto.VerifyCodeRequest;
import vn.kltn.bankadvisor.module.user.dto.VerifyEmailRequest;
import vn.kltn.bankadvisor.module.user.service.EmailVerificationService;
import vn.kltn.bankadvisor.security.AuthUser;
import vn.kltn.bankadvisor.security.CurrentUser;

@RestController
@RequestMapping("/api/v1")
public class EmailVerificationController {

    private final EmailVerificationService verificationService;

    public EmailVerificationController(EmailVerificationService verificationService) {
        this.verificationService = verificationService;
    }

    @GetMapping("/me/email-verification")
    public ApiResponse<EmailVerificationResponse> status(@CurrentUser AuthUser user) {
        return ApiResponse.ok(verificationService.status(user.id()));
    }

    @PostMapping("/me/email-verification")
    public ApiResponse<EmailVerificationResponse> send(@CurrentUser AuthUser user) {
        return ApiResponse.ok(verificationService.send(user.id()));
    }

    /** Nhập mã 6 số trong email: dùng khi đọc thư trên thiết bị khác (link không mở được). */
    @PostMapping("/me/email-verification/confirm")
    public ApiResponse<EmailVerificationResponse> confirm(@CurrentUser AuthUser user,
                                                          @Valid @RequestBody VerifyCodeRequest request) {
        return ApiResponse.ok(verificationService.confirmCode(user.id(), request.code()));
    }

    /** Công khai: link trong email có thể được mở ở trình duyệt chưa đăng nhập. Token tự chứng minh người dùng. */
    @PostMapping("/auth/verify-email")
    public ApiResponse<UserResponse> verify(@Valid @RequestBody VerifyEmailRequest request) {
        return ApiResponse.ok(verificationService.verify(request.token()));
    }
}
