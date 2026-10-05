package vn.kltn.bankadvisor.module.user.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record VerifyEmailRequest(
        @NotBlank(message = "Thiếu mã xác minh") @Size(max = 2048, message = "Mã xác minh không hợp lệ") String token
) {
}
