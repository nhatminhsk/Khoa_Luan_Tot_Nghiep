package vn.kltn.bankadvisor.module.user.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/** Đổi mật khẩu (đang đăng nhập) và đặt lại mật khẩu qua email (quên mật khẩu). */
public final class PasswordDtos {

    private PasswordDtos() {
    }

    /** Đổi mật khẩu: phải nhập mật khẩu hiện tại. Quy tắc mật khẩu mới giống lúc đăng ký. */
    public record ChangePasswordRequest(
            @NotBlank(message = "Nhập mật khẩu hiện tại")
            @Size(max = 72, message = "Mật khẩu không đúng")
            String currentPassword,

            @NotBlank(message = "Nhập mật khẩu mới")
            @Size(min = 8, max = 72, message = "Mật khẩu dài 8–72 ký tự")
            @Pattern(regexp = "^(?=.*\\p{L})(?=.*\\d).+$", message = "Mật khẩu cần có cả chữ và số")
            String newPassword
    ) {
    }

    /** Xin link đặt lại mật khẩu. Trả cùng một kết quả dù email có tài khoản hay không. */
    public record PasswordResetRequest(
            @NotBlank(message = "Nhập email")
            @Email(message = "Email không hợp lệ")
            @Size(max = 160, message = "Email quá dài")
            String email
    ) {
    }

    /** Đặt mật khẩu mới bằng token trong link email. */
    public record PasswordResetConfirmRequest(
            @NotBlank(message = "Thiếu mã trong link")
            @Size(max = 2000, message = "Link không hợp lệ")
            String token,

            @NotBlank(message = "Nhập mật khẩu mới")
            @Size(min = 8, max = 72, message = "Mật khẩu dài 8–72 ký tự")
            @Pattern(regexp = "^(?=.*\\p{L})(?=.*\\d).+$", message = "Mật khẩu cần có cả chữ và số")
            String newPassword
    ) {
    }
}
