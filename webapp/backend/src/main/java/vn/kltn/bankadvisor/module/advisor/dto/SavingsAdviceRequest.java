package vn.kltn.bankadvisor.module.advisor.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import vn.kltn.bankadvisor.module.rate.entity.Channel;

/** Nhu cầu gửi tiết kiệm. Không chứa thông tin định danh người dùng. */
public record SavingsAdviceRequest(
        @NotNull(message = "Nhập số tiền gửi")
        @Min(value = 1_000_000, message = "Số tiền tối thiểu 1 triệu đồng")
        @Max(value = 100_000_000_000L, message = "Số tiền tối đa 100 tỷ đồng")
        Long amount,

        @NotNull(message = "Chọn kỳ hạn")
        @Min(value = 1, message = "Kỳ hạn tối thiểu 1 tháng")
        @Max(value = 60, message = "Kỳ hạn tối đa 60 tháng")
        Integer termMonths,

        @NotNull(message = "Chọn kênh gửi")
        Channel channel,

        @Valid
        Weights weights
) {

    /** Mức ưu tiên 0–100 của ba tiêu chí; dùng khi thuật toán xếp hạng hỗ trợ trọng số riêng. */
    public record Weights(
            @Min(0) @Max(100) int rate,
            @Min(0) @Max(100) int safety,
            @Min(0) @Max(100) int app
    ) {
    }
}
