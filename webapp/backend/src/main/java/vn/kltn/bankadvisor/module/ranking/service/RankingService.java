package vn.kltn.bankadvisor.module.ranking.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.api.ResultStatus;
import vn.kltn.bankadvisor.module.bank.entity.Bank;
import vn.kltn.bankadvisor.module.bank.service.BankService;
import vn.kltn.bankadvisor.module.ranking.dto.RankingBlock;
import vn.kltn.bankadvisor.module.ranking.entity.Purpose;
import vn.kltn.bankadvisor.module.ranking.entity.RankingResult;
import vn.kltn.bankadvisor.module.ranking.repository.RankingResultRepository;

import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Đọc xếp hạng mặc định mà pipeline đã tính. Service này không tự xếp hạng.
 * <p>
 * Khi thuật toán chốt, bước "tính lại theo trọng số người dùng" (bước cuối của TOPSIS trên ma trận
 * tiêu chí dùng chung) sẽ đặt ở đây, và {@link RankingBlock#personalized()} bật thành true.
 */
@Service
@Transactional(readOnly = true)
public class RankingService {

    private final RankingResultRepository repository;
    private final BankService bankService;

    public RankingService(RankingResultRepository repository, BankService bankService) {
        this.repository = repository;
        this.bankService = bankService;
    }

    public Optional<String> latestPeriod(Purpose purpose) {
        return repository.findLatestPeriod(purpose);
    }

    /** Xếp hạng mới nhất; {@code limit <= 0} là lấy hết. */
    public RankingBlock latest(Purpose purpose, int limit) {
        Optional<String> period = repository.findLatestPeriod(purpose);
        if (period.isEmpty()) {
            return RankingBlock.notAvailable(purpose);
        }
        List<RankingResult> results = repository.findByPurposeAndAsOfPeriodOrderByRankAsc(purpose, period.get());
        Map<String, Bank> banks = bankService.lookup();
        List<RankingBlock.Item> items = results.stream()
                .limit(limit > 0 ? limit : Long.MAX_VALUE)
                .map(r -> new RankingBlock.Item(r.getRank(), r.getRankLow(), r.getRankHigh(), r.getTicker(),
                        banks.containsKey(r.getTicker()) ? banks.get(r.getTicker()).getShortName() : r.getTicker(),
                        r.getScore(), r.getGroupLabel(), r.getTopPositive(), r.getTopNegative()))
                .toList();
        String methodVersion = results.isEmpty() ? null : results.getFirst().getMethodVersion();
        return new RankingBlock(ResultStatus.AVAILABLE, purpose, period.get(), methodVersion, false, items);
    }
}
