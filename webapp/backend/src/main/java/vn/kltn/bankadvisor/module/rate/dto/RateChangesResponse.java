package vn.kltn.bankadvisor.module.rate.dto;

import vn.kltn.bankadvisor.module.rate.entity.Channel;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

/**
 * Các lần ngân hàng đổi lãi suất tiết kiệm niêm yết trong {@code days} ngày gần nhất (tính tới ngày có số mới nhất).
 * Mỗi phần tử so với lần quan sát liền trước của cùng ngân hàng × kỳ hạn × kênh; mới nhất đứng đầu.
 */
public record RateChangesResponse(
        LocalDate latestDate,
        LocalDate fromDate,
        int days,
        List<Change> changes
) {

    /** {@code change} = {@code rate} − {@code previousRate} (điểm %). */
    public record Change(
            LocalDate date,
            LocalDate previousDate,
            String ticker,
            String shortName,
            int termMonths,
            Channel channel,
            BigDecimal previousRate,
            BigDecimal rate,
            BigDecimal change
    ) {
    }
}
