package vn.kltn.bankadvisor.module.overview.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.module.dataset.service.DatasetService;
import vn.kltn.bankadvisor.module.indicator.repository.BankQuarterValueRepository;
import vn.kltn.bankadvisor.module.overview.dto.OverviewResponse;
import vn.kltn.bankadvisor.module.rate.dto.BestRatesResponse;
import vn.kltn.bankadvisor.module.rate.entity.Channel;
import vn.kltn.bankadvisor.module.rate.service.RateService;
import vn.kltn.bankadvisor.module.rate.service.RateSnapshot;
import vn.kltn.bankadvisor.module.ranking.entity.Purpose;
import vn.kltn.bankadvisor.module.ranking.service.RankingService;

import java.math.BigDecimal;
import java.util.Comparator;
import java.util.List;

@Service
@Transactional(readOnly = true)
public class OverviewService {

    static final int REFERENCE_TERM = 12;
    static final int RANKING_PREVIEW = 5;

    private final RateService rateService;
    private final RankingService rankingService;
    private final DatasetService datasetService;
    private final BankQuarterValueRepository quarterValueRepository;

    public OverviewService(RateService rateService, RankingService rankingService, DatasetService datasetService,
                           BankQuarterValueRepository quarterValueRepository) {
        this.rateService = rateService;
        this.rankingService = rankingService;
        this.datasetService = datasetService;
        this.quarterValueRepository = quarterValueRepository;
    }

    public OverviewResponse overview() {
        RateSnapshot snap = rateService.snapshot();
        BestRatesResponse best = rateService.bestRates();
        return new OverviewResponse(
                snap.date(),
                snap.previousDate(),
                market(snap, best, Channel.ONLINE),
                market(snap, best, Channel.COUNTER),
                best.items(),
                rankingService.latest(Purpose.SAVINGS, RANKING_PREVIEW),
                rankingService.latest(Purpose.LOAN, RANKING_PREVIEW),
                quarterValueRepository.findLatestPeriod().orElse(null),
                datasetService.sources());
    }

    private static OverviewResponse.Market market(RateSnapshot snap, BestRatesResponse best, Channel channel) {
        List<RateSnapshot.Key> keys = snap.current().keySet().stream()
                .filter(k -> k.termMonths() == REFERENCE_TERM && k.channel() == channel)
                .toList();
        int raised = 0;
        int lowered = 0;
        int unchanged = 0;
        for (RateSnapshot.Key key : keys) {
            var change = snap.change(key.ticker(), key.termMonths(), key.channel());
            if (change.isEmpty()) {
                continue;
            }
            switch (change.get().signum()) {
                case 1 -> raised++;
                case -1 -> lowered++;
                default -> unchanged++;
            }
        }
        BestRatesResponse.Item reference = best.items().stream()
                .filter(item -> item.termMonths() == REFERENCE_TERM).findFirst().orElse(null);
        BigDecimal lowest = keys.stream().map(k -> snap.current().get(k)).min(Comparator.naturalOrder()).orElse(null);
        boolean online = channel == Channel.ONLINE;
        return new OverviewResponse.Market(REFERENCE_TERM,
                reference == null ? null : online ? reference.medianOnline() : reference.medianCounter(),
                reference == null ? null : online ? reference.online() : reference.counter(),
                lowest, keys.size(), raised, lowered, unchanged);
    }
}
