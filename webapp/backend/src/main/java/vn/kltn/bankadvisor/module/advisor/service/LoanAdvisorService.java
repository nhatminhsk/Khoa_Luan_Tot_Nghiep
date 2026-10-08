package vn.kltn.bankadvisor.module.advisor.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.module.advisor.dto.LoanAdviceRequest;
import vn.kltn.bankadvisor.module.advisor.dto.LoanAdviceResponse;
import vn.kltn.bankadvisor.module.program.service.ProgramService;
import vn.kltn.bankadvisor.module.rate.dto.LendingRateResponse;
import vn.kltn.bankadvisor.module.rate.service.RateService;
import vn.kltn.bankadvisor.module.ranking.entity.Purpose;
import vn.kltn.bankadvisor.module.ranking.service.RankingService;

import java.time.YearMonth;
import java.time.temporal.ChronoUnit;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

/**
 * Trang vay: ước tính tiền trả theo lãi suất cho vay bình quân (chỉ để tham khảo), chương trình ưu đãi
 * liên quan, và xếp hạng tổng hợp (thuật toán). Mỗi ngân hàng một số, kèm nhóm khách hàng của số đó
 * (pipeline đã chọn: số cá nhân của ngân hàng → số chung của ngân hàng → VietnamNet).
 */
@Service
@Transactional(readOnly = true)
public class LoanAdvisorService {

    private final RateService rateService;
    private final ProgramService programService;
    private final RankingService rankingService;

    public LoanAdvisorService(RateService rateService, ProgramService programService, RankingService rankingService) {
        this.rateService = rateService;
        this.programService = programService;
        this.rankingService = rankingService;
    }

    public LoanAdviceResponse advise(LoanAdviceRequest request) {
        List<LendingRateResponse> rates = rateService.latestLending();
        String latestMonth = rates.stream().map(LendingRateResponse::month).max(Comparator.naturalOrder()).orElse(null);
        Map<String, List<String>> participation = programService.participationByTicker();

        List<LoanAdviceResponse.Offer> offers = rates.stream()
                .map(rate -> {
                    InterestCalculator.LoanSchedule schedule = InterestCalculator.loan(request.amount(),
                            rate.lendingAvgPercent(), request.termMonths(), request.repayment());
                    List<String> programs = participation.getOrDefault(rate.ticker(), List.of()).stream()
                            .filter(request.purpose().programCodes()::contains).sorted().toList();
                    return new LoanAdviceResponse.Offer(rate.ticker(), rate.shortName(), rate.month(),
                            monthsBetween(rate.month(), latestMonth), rate.lendingAvgPercent(), rate.segment(),
                            rate.basis(), rate.source(), rate.sourceUrl(), schedule.firstPayment(),
                            schedule.lastPayment(), schedule.totalInterest(), schedule.totalPayment(), programs);
                })
                .sorted(Comparator.comparing(LoanAdviceResponse.Offer::lendingAvgPercent)
                        .thenComparing(LoanAdviceResponse.Offer::ticker))
                .toList();

        return new LoanAdviceResponse(latestMonth, request.purpose(), request.amount(), request.termMonths(),
                request.repayment(), offers, programService.byCodes(request.purpose().programCodes()),
                rankingService.latest(Purpose.LOAN, 0));
    }

    static int monthsBetween(String month, String latestMonth) {
        if (month == null || latestMonth == null) {
            return 0;
        }
        return (int) ChronoUnit.MONTHS.between(YearMonth.parse(month), YearMonth.parse(latestMonth));
    }
}
