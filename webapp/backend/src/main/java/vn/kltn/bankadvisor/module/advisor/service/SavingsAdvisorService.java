package vn.kltn.bankadvisor.module.advisor.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.module.advisor.dto.SavingsAdviceRequest;
import vn.kltn.bankadvisor.module.advisor.dto.SavingsAdviceResponse;
import vn.kltn.bankadvisor.module.app.dto.AppScoreSummary;
import vn.kltn.bankadvisor.module.app.service.AppExperienceService;
import vn.kltn.bankadvisor.module.bank.entity.Bank;
import vn.kltn.bankadvisor.module.bank.service.BankService;
import vn.kltn.bankadvisor.module.rate.service.RateService;
import vn.kltn.bankadvisor.module.rate.service.RateSnapshot;
import vn.kltn.bankadvisor.module.ranking.entity.Purpose;
import vn.kltn.bankadvisor.module.ranking.service.RankingService;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

/**
 * Trang gửi tiết kiệm: lãi suất hôm nay + tiền lãi ước tính (công thức), và xếp hạng tổng hợp (thuật toán).
 */
@Service
@Transactional(readOnly = true)
public class SavingsAdvisorService {

    private final RateService rateService;
    private final BankService bankService;
    private final AppExperienceService appExperienceService;
    private final RankingService rankingService;

    public SavingsAdvisorService(RateService rateService, BankService bankService,
                                 AppExperienceService appExperienceService, RankingService rankingService) {
        this.rateService = rateService;
        this.bankService = bankService;
        this.appExperienceService = appExperienceService;
        this.rankingService = rankingService;
    }

    public SavingsAdviceResponse advise(SavingsAdviceRequest request) {
        RateSnapshot snap = rateService.snapshot();
        Map<String, Bank> banks = bankService.lookup();
        Map<String, AppScoreSummary> appScores = appExperienceService.scoresByTicker();

        record Quote(String ticker, BigDecimal rate) {
        }
        List<Quote> quotes = snap.current().entrySet().stream()
                .filter(e -> e.getKey().termMonths() == request.termMonths() && e.getKey().channel() == request.channel())
                .map(e -> new Quote(e.getKey().ticker(), e.getValue()))
                .sorted(Comparator.comparing(Quote::rate).reversed().thenComparing(Quote::ticker))
                .toList();

        List<SavingsAdviceResponse.Offer> offers = new ArrayList<>();
        int order = 0;
        BigDecimal previousRate = null;
        for (int i = 0; i < quotes.size(); i++) {
            Quote q = quotes.get(i);
            if (previousRate == null || q.rate().compareTo(previousRate) != 0) {
                order = i + 1;
                previousRate = q.rate();
            }
            long interest = InterestCalculator.savingsInterest(request.amount(), q.rate(), request.termMonths());
            AppScoreSummary app = appScores.get(q.ticker());
            offers.add(new SavingsAdviceResponse.Offer(order, q.ticker(),
                    banks.containsKey(q.ticker()) ? banks.get(q.ticker()).getShortName() : q.ticker(),
                    q.rate(), snap.change(q.ticker(), request.termMonths(), request.channel()).orElse(null),
                    interest, request.amount() + interest, app == null ? null : app.preferredScore()));
        }
        // Trọng số người dùng (request.weights) sẽ dùng khi thuật toán xếp hạng hỗ trợ tính lại theo trọng số.
        return new SavingsAdviceResponse(snap.date(), request.amount(), request.termMonths(), request.channel(),
                offers, rankingService.latest(Purpose.SAVINGS, 0));
    }
}
