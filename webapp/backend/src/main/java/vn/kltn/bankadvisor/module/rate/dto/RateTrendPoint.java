package vn.kltn.bankadvisor.module.rate.dto;

import java.math.BigDecimal;
import java.time.LocalDate;

/** Phân bố lãi suất của các ngân hàng tại một ngày (một kỳ hạn, một kênh). */
public record RateTrendPoint(LocalDate date, BigDecimal min, BigDecimal median, BigDecimal max, int bankCount) {
}
