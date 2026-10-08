package vn.kltn.bankadvisor.module.rate.dto;

import java.math.BigDecimal;

/**
 * Lãi suất cho vay bình quân của một ngân hàng trong một tháng.
 *
 * @param segment nhóm khách hàng của con số: INDIVIDUAL, ALL hoặc UNSPECIFIED (báo không ghi nhóm)
 * @param basis   NEW_LOANS (khoản vay mới trong kỳ), OUTSTANDING (toàn bộ dư nợ) hoặc null (ngân hàng không ghi)
 * @param source  BANK (web ngân hàng) hoặc VIETNAMNET
 */
public record LendingRateResponse(
        String ticker,
        String shortName,
        String month,
        BigDecimal lendingAvgPercent,
        BigDecimal depositAvgPercent,
        String segment,
        String basis,
        String source,
        String sourceUrl
) {
}
