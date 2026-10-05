package vn.kltn.bankadvisor.module.advisor.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import vn.kltn.bankadvisor.module.advisor.entity.LoanPurpose;
import vn.kltn.bankadvisor.module.advisor.entity.RepaymentMethod;

/** Nhu cầu vay. Hệ thống không chấm điểm tín dụng cá nhân nên không hỏi thu nhập hay khoản vay hiện có. */
public record LoanAdviceRequest(
        @NotNull(message = "Chọn mục đích vay")
        LoanPurpose purpose,

        @NotNull(message = "Nhập số tiền vay")
        @Min(value = 10_000_000, message = "Số tiền vay tối thiểu 10 triệu đồng")
        @Max(value = 50_000_000_000L, message = "Số tiền vay tối đa 50 tỷ đồng")
        Long amount,

        @NotNull(message = "Nhập thời hạn vay")
        @Min(value = 1, message = "Thời hạn tối thiểu 1 tháng")
        @Max(value = 420, message = "Thời hạn tối đa 35 năm")
        Integer termMonths,

        @NotNull(message = "Chọn cách trả nợ")
        RepaymentMethod repayment
) {
}
