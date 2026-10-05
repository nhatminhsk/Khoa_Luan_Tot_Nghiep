package vn.kltn.bankadvisor.module.user.dto;

import jakarta.validation.constraints.NotBlank;

public record LoginRequest(
        @NotBlank(message = "Nhập email") String email,
        @NotBlank(message = "Nhập mật khẩu") String password
) {
}
