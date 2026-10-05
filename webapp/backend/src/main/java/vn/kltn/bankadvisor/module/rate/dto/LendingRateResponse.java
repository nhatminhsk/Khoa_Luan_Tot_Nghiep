package vn.kltn.bankadvisor.module.rate.dto;

import java.math.BigDecimal;

/** Lãi suất cho vay bình quân của một ngân hàng trong tháng gần nhất có số. */
public record LendingRateResponse(
        String ticker,
        String shortName,
        String month,
        BigDecimal lendingAvgPercent,
        BigDecimal depositAvgPercent,
        String sourceUrl
) {
}
