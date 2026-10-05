package vn.kltn.bankadvisor.module.advisor.dto;

import vn.kltn.bankadvisor.module.advisor.entity.LoanPurpose;
import vn.kltn.bankadvisor.module.advisor.entity.RepaymentMethod;
import vn.kltn.bankadvisor.module.program.dto.ProgramResponse;
import vn.kltn.bankadvisor.module.ranking.dto.RankingBlock;

import java.math.BigDecimal;
import java.util.List;

/**
 * Kết quả trang vay.
 *
 * @param latestMonth tháng mới nhất có số lãi suất cho vay bình quân trong dữ liệu
 * @param offers      ước tính tiền trả theo lãi suất cho vay bình quân của từng ngân hàng, sắp tăng dần
 * @param programs    chương trình tín dụng chính sách liên quan tới mục đích vay
 */
public record LoanAdviceResponse(
        String latestMonth,
        LoanPurpose purpose,
        long amount,
        int termMonths,
        RepaymentMethod repayment,
        List<Offer> offers,
        List<ProgramResponse> programs,
        RankingBlock ranking
) {

    /**
     * @param month        tháng của số lãi suất ngân hàng này (các ngân hàng công bố không đều)
     * @param monthsBehind số tháng cũ hơn {@code latestMonth}
     * @param programCodes chương trình liên quan mà ngân hàng này tham gia
     */
    public record Offer(
            String ticker,
            String shortName,
            String month,
            int monthsBehind,
            BigDecimal lendingAvgPercent,
            long firstPayment,
            long lastPayment,
            long totalInterest,
            long totalPayment,
            List<String> programCodes
    ) {
    }
}
