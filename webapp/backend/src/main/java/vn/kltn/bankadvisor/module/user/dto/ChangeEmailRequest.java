package vn.kltn.bankadvisor.module.user.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** Đổi email đăng nhập (ví dụ lỡ gõ nhầm "@gamil.com" khi đăng ký). Phải nhập lại mật khẩu hiện tại. */
public record ChangeEmailRequest(
        @NotBlank(message = "Nhập email mới")
        @Email(message = "Email không hợp lệ")
        @Size(max = 160, message = "Email quá dài")
        String newEmail,

        @NotBlank(message = "Nhập mật khẩu hiện tại")
        @Size(max = 72, message = "Mật khẩu không đúng")
        String currentPassword
) {
}
