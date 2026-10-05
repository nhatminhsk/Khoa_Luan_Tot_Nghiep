package vn.kltn.bankadvisor.module.app.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.api.ResultStatus;
import vn.kltn.bankadvisor.module.app.dto.AppExperienceResponse;
import vn.kltn.bankadvisor.module.app.dto.AppScoreSummary;
import vn.kltn.bankadvisor.module.app.entity.AppAspectScore;
import vn.kltn.bankadvisor.module.app.entity.AppStore;
import vn.kltn.bankadvisor.module.app.entity.AppStoreSnapshot;
import vn.kltn.bankadvisor.module.app.repository.AppAspectScoreRepository;
import vn.kltn.bankadvisor.module.app.repository.AppReviewMonthlyRepository;
import vn.kltn.bankadvisor.module.app.repository.AppStoreSnapshotRepository;
import vn.kltn.bankadvisor.module.bank.entity.Bank;
import vn.kltn.bankadvisor.module.bank.service.BankService;

import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
@Transactional(readOnly = true)
public class AppExperienceService {

    private final AppStoreSnapshotRepository storeRepository;
    private final AppReviewMonthlyRepository monthlyRepository;
    private final AppAspectScoreRepository aspectRepository;
    private final BankService bankService;

    public AppExperienceService(AppStoreSnapshotRepository storeRepository, AppReviewMonthlyRepository monthlyRepository,
                                AppAspectScoreRepository aspectRepository, BankService bankService) {
        this.storeRepository = storeRepository;
        this.monthlyRepository = monthlyRepository;
        this.aspectRepository = aspectRepository;
        this.bankService = bankService;
    }

    public AppExperienceResponse forBank(String ticker) {
        Bank bank = bankService.require(ticker);
        List<AppExperienceResponse.StoreScore> stores = storeRepository.findByTicker(bank.getTicker()).stream()
                .sorted((a, b) -> a.getStore().compareTo(b.getStore()))
                .map(s -> new AppExperienceResponse.StoreScore(s.getStore(), s.getAppName(), s.getScore(),
                        s.getRatings(), s.getSnapshotDate()))
                .toList();
        List<AppExperienceResponse.MonthlyPoint> monthly = monthlyRepository.findByTickerOrderByMonthAsc(bank.getTicker())
                .stream().map(m -> new AppExperienceResponse.MonthlyPoint(m.getMonth(), m.getReviewCount(),
                        m.getMeanScore(), m.getOneStarShare(), m.getFiveStarShare(), m.isUsable()))
                .toList();
        List<AppAspectScore> aspects = aspectRepository.findByTickerOrderByPeriodAscAspectAsc(bank.getTicker());
        AppExperienceResponse.AspectBlock aspectBlock = new AppExperienceResponse.AspectBlock(
                aspects.isEmpty() ? ResultStatus.NOT_AVAILABLE : ResultStatus.AVAILABLE,
                aspects.stream().map(a -> new AppExperienceResponse.AspectPoint(a.getPeriod(), a.getAspect(),
                        a.getScore(), a.getReviewCount())).toList());
        return new AppExperienceResponse(bank.getTicker(), stores, monthly, aspectBlock);
    }

    /** Điểm ứng dụng của mọi ngân hàng, theo mã. */
    public Map<String, AppScoreSummary> scoresByTicker() {
        Map<String, Map<AppStore, AppStoreSnapshot>> grouped = storeRepository.findAll().stream()
                .collect(Collectors.groupingBy(AppStoreSnapshot::getTicker,
                        Collectors.toMap(AppStoreSnapshot::getStore, Function.identity())));
        return bankService.lookup().keySet().stream().collect(Collectors.toMap(Function.identity(), ticker -> {
            Map<AppStore, AppStoreSnapshot> byStore = grouped.getOrDefault(ticker, Map.of());
            AppStoreSnapshot play = byStore.get(AppStore.GOOGLE_PLAY);
            AppStoreSnapshot ios = byStore.get(AppStore.APP_STORE);
            return new AppScoreSummary(ticker,
                    play == null ? null : play.getScore(), play == null ? null : play.getRatings(),
                    ios == null ? null : ios.getScore(), ios == null ? null : ios.getRatings());
        }));
    }

    public List<AppScoreSummary> allScores() {
        return scoresByTicker().values().stream()
                .sorted((a, b) -> a.ticker().compareTo(b.ticker())).toList();
    }
}
