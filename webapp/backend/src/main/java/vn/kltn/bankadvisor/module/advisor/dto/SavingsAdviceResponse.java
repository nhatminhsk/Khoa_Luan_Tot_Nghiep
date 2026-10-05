package vn.kltn.bankadvisor.module.advisor.dto;

import vn.kltn.bankadvisor.module.rate.entity.Channel;
import vn.kltn.bankadvisor.module.ranking.dto.RankingBlock;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

/**
 * Kết quả trang gửi tiết kiệm.
 *
 * @param offers  lãi suất hôm nay của các ngân hàng cho đúng kỳ hạn và kênh, sắp theo lãi suất giảm dần
 *                (đây là sắp xếp theo một tiêu chí, không phải xếp hạng tổng hợp)
 * @param ranking xếp hạng tổng hợp của thuật toán; NOT_AVAILABLE khi chưa có
 */
public record SavingsAdviceResponse(
        LocalDate rateDate,
        long amount,
        int termMonths,
        Channel channel,
        List<Offer> offers,
        RankingBlock ranking
) {

    /**
     * @param rateOrder thứ tự theo lãi suất (ngân hàng cùng mức lãi có cùng thứ tự)
     * @param appScore  điểm ứng dụng (Google Play, không có thì App Store)
     */
    public record Offer(
            int rateOrder,
            String ticker,
            String shortName,
            BigDecimal ratePercent,
            BigDecimal changeFromPrevious,
            long interest,
            long maturityAmount,
            Double appScore
    ) {
    }
}
