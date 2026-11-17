package vn.kltn.bankadvisor.module.advisor.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.module.advisor.dto.SavingsAdviceRequest;
import vn.kltn.bankadvisor.module.advisor.dto.SavingsAdviceResponse;
import vn.kltn.bankadvisor.module.bank.entity.Bank;
import vn.kltn.bankadvisor.module.bank.service.BankService;
import vn.kltn.bankadvisor.module.rate.entity.DepositRateTier;
import vn.kltn.bankadvisor.module.rate.repository.DepositRateTierRepository;
import vn.kltn.bankadvisor.module.rate.service.RateService;
import vn.kltn.bankadvisor.module.rate.service.RateSnapshot;
import vn.kltn.bankadvisor.module.ranking.entity.Purpose;
import vn.kltn.bankadvisor.module.ranking.service.RankingService;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Trang gửi tiết kiệm: lãi suất hôm nay + tiền lãi ước tính (công thức), và xếp hạng tổng hợp lãi + an toàn
 * (MCDM × Monte Carlo do pipeline tính).
 * Lãi áp theo bậc số tiền gửi của ngân hàng có chia bậc (deposit_rate_tier); ngân hàng khác dùng lãi niêm yết.
 */
@Service
@Transactional(readOnly = true)
public class SavingsAdvisorService {

    private final RateService rateService;
    private final BankService bankService;
    private final RankingService rankingService;
    private final DepositRateTierRepository tierRepository;

    public SavingsAdvisorService(RateService rateService, BankService bankService, RankingService rankingService,
                                 DepositRateTierRepository tierRepository) {
        this.rateService = rateService;
        this.bankService = bankService;
        this.rankingService = rankingService;
        this.tierRepository = tierRepository;
    }

    public SavingsAdviceResponse advise(SavingsAdviceRequest request) {
        RateSnapshot snap = rateService.snapshot();
        Map<String, Bank> banks = bankService.lookup();

        Map<String, List<DepositRateTier>> tiers = tierRepository
                .findByTermMonthsAndChannel(request.termMonths(), request.channel()).stream()
                .collect(Collectors.groupingBy(DepositRateTier::getTicker));

        record Quote(String ticker, BigDecimal rate, String tierLabel) {
        }
        List<Quote> quotes = snap.current().entrySet().stream()
                .filter(e -> e.getKey().termMonths() == request.termMonths() && e.getKey().channel() == request.channel())
                .map(e -> {
                    DepositRateTier tier = applicableTier(tiers.get(e.getKey().ticker()), e.getValue(), request.amount(),
                            snap.date());
                    return tier == null
                            ? new Quote(e.getKey().ticker(), e.getValue(), null)
                            : new Quote(e.getKey().ticker(), tier.getRatePercent(), tier.getTierLabel());
                })
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
            offers.add(new SavingsAdviceResponse.Offer(order, q.ticker(),
                    banks.containsKey(q.ticker()) ? banks.get(q.ticker()).getShortName() : q.ticker(),
                    q.rate(), snap.change(q.ticker(), request.termMonths(), request.channel()).orElse(null),
                    interest, request.amount() + interest, q.tierLabel()));
        }
        // Xếp hạng tổng hợp: bảng pipeline tính sẵn cho đúng kỳ hạn × kênh, mốc tiền theo số tiền gửi (trọng số an toàn
        // tăng theo phần tiền vượt hạn mức bảo hiểm tiền gửi). request.weights không còn dùng: giữ để nhu cầu đã lưu chạy.
        return new SavingsAdviceResponse(snap.date(), request.amount(), request.termMonths(), request.channel(),
                offers, rankingService.savings(request.termMonths(), request.channel(), request.amount(), 0));
    }

    /**
     * Bậc cao nhất có ngưỡng ≤ số tiền gửi. Bậc chỉ hợp lệ khi biểu đã có hiệu lực ở ngày lãi đang dùng
     * ({@code validFrom ≤ rateDate}; biểu công bố trước ngày hiệu lực chưa được áp) và lãi niêm yết hôm đó còn bằng lãi
     * bậc thấp nhất lúc đối chiếu biểu ({@code baseRatePercent}): ngân hàng đổi biểu thì bỏ qua bậc cũ, dùng lãi niêm yết.
     */
    static DepositRateTier applicableTier(List<DepositRateTier> tiers, BigDecimal listedRate, long amount,
                                          LocalDate rateDate) {
        if (tiers == null || listedRate == null) {
            return null;
        }
        return tiers.stream()
                .filter(t -> t.getValidFrom() == null || rateDate == null || !t.getValidFrom().isAfter(rateDate))
                .filter(t -> t.getBaseRatePercent().compareTo(listedRate) == 0 && t.getMinAmountVnd() <= amount)
                .max(Comparator.comparingLong(DepositRateTier::getMinAmountVnd))
                .orElse(null);
    }
}
