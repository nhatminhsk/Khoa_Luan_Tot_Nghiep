package vn.kltn.bankadvisor.module.user.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** Mã xác minh 6 số trong email (cho phép có dấu cách, ví dụ "123 456"). */
public record VerifyCodeRequest(
        @NotBlank(message = "Nhập mã xác minh") @Size(max = 12, message = "Mã xác minh gồm 6 chữ số") String code
) {
}
