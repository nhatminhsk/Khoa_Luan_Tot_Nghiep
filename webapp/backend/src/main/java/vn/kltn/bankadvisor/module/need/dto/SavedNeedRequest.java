package vn.kltn.bankadvisor.module.need.dto;

import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import vn.kltn.bankadvisor.module.advisor.entity.LoanPurpose;
import vn.kltn.bankadvisor.module.advisor.entity.RepaymentMethod;
import vn.kltn.bankadvisor.module.rate.entity.Channel;
import vn.kltn.bankadvisor.module.ranking.entity.Purpose;

public record SavedNeedRequest(
        @NotNull(message = "Chọn mục đích") Purpose purpose,
        @NotBlank(message = "Đặt tên cho nhu cầu") @Size(max = 80, message = "Tên tối đa 80 ký tự") String label,
        @NotNull(message = "Nhập số tiền")
        @Min(value = 1_000_000, message = "Số tiền tối thiểu 1 triệu đồng")
        @Max(value = 100_000_000_000L, message = "Số tiền tối đa 100 tỷ đồng") Long amount,
        @NotNull(message = "Nhập kỳ hạn") @Min(1) @Max(420) Integer termMonths,
        Channel channel,
        LoanPurpose loanPurpose,
        RepaymentMethod repayment,
        @Min(0) @Max(100) Integer weightRate,
        @Min(0) @Max(100) Integer weightSafety,
        @Min(0) @Max(100) Integer weightApp
) {

    /** Gửi tiết kiệm cần kênh gửi; vay cần mục đích vay và cách trả. */
    @AssertTrue(message = "Thiếu thông tin theo mục đích: gửi tiết kiệm cần kênh gửi, vay cần mục đích vay và cách trả")
    public boolean isComplete() {
        if (purpose == null) {
            return true;
        }
        return purpose == Purpose.SAVINGS ? channel != null : loanPurpose != null && repayment != null;
    }
}
