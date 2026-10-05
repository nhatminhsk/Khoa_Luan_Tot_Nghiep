package vn.kltn.bankadvisor.module.user.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record RegisterRequest(
        @NotBlank(message = "Nhập email")
        @Email(message = "Email không hợp lệ")
        @Size(max = 160, message = "Email quá dài")
        String email,

        @NotBlank(message = "Nhập tên hiển thị")
        @Size(max = 80, message = "Tên tối đa 80 ký tự")
        String displayName,

        // BCrypt chỉ dùng 72 byte đầu, nên giới hạn độ dài để không ai tưởng mật khẩu dài hơn an toàn hơn.
        @NotBlank(message = "Nhập mật khẩu")
        @Size(min = 8, max = 72, message = "Mật khẩu dài 8–72 ký tự")
        @Pattern(regexp = "^(?=.*\\p{L})(?=.*\\d).+$", message = "Mật khẩu cần có cả chữ và số")
        String password
) {
}
