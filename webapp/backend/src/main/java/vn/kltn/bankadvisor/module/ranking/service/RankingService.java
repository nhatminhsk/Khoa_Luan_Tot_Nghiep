package vn.kltn.bankadvisor.module.ranking.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.api.ResultStatus;
import vn.kltn.bankadvisor.module.bank.entity.Bank;
import vn.kltn.bankadvisor.module.bank.service.BankService;
import vn.kltn.bankadvisor.module.rate.entity.Channel;
import vn.kltn.bankadvisor.module.ranking.dto.RankingBlock;
import vn.kltn.bankadvisor.module.ranking.entity.Purpose;
import vn.kltn.bankadvisor.module.ranking.entity.RankingResult;
import vn.kltn.bankadvisor.module.ranking.repository.RankingResultRepository;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

/**
 * Đọc xếp hạng mà pipeline đã tính (MCDM × Monte Carlo trên ảnh chụp số công bố mới nhất). Service này không tự xếp
 * hạng: phần gửi chỉ chọn đúng bảng kỳ hạn × kênh và mốc tiền gần nhất không vượt số tiền người gửi.
 */
@Service
@Transactional(readOnly = true)
public class RankingService {

    /** Bảng gửi mặc định của Tổng quan: trùng mặc định của trang Gửi tiết kiệm. */
    public static final int DEFAULT_TERM = 12;
    public static final Channel DEFAULT_CHANNEL = Channel.ONLINE;

    private final RankingResultRepository repository;
    private final BankService bankService;

    public RankingService(RankingResultRepository repository, BankService bankService) {
        this.repository = repository;
        this.bankService = bankService;
    }

    public Optional<String> latestPeriod(Purpose purpose) {
        return repository.findLatestPeriod(purpose);
    }

    /** Vay: bảng mới nhất. Gửi: bảng 12 tháng trực tuyến ở trọng số mặc định. {@code limit <= 0} là lấy hết. */
    public RankingBlock latest(Purpose purpose, int limit) {
        if (purpose == Purpose.SAVINGS) {
            return savings(DEFAULT_TERM, DEFAULT_CHANNEL, null, limit);
        }
        Optional<String> period = repository.findLatestPeriod(purpose);
        if (period.isEmpty()) {
            return RankingBlock.notAvailable(purpose, RankingBlock.NOT_COMPUTED);
        }
        return block(purpose, period.get(), repository.findByPurposeAndAsOfPeriodOrderByRankAsc(purpose, period.get()),
                limit);
    }

    /**
     * Bảng gửi của kỳ hạn × kênh. {@code amount} null → trọng số mặc định; có số tiền → mốc tiền lớn nhất không vượt
     * số tiền (nhỏ hơn mọi mốc thì lấy mốc nhỏ nhất, vốn đã nằm trong hạn mức bảo hiểm tiền gửi).
     */
    public RankingBlock savings(int termMonths, Channel channel, Long amount, int limit) {
        Optional<String> period = repository.findLatestPeriod(Purpose.SAVINGS);
        if (period.isEmpty()) {
            return RankingBlock.notAvailable(Purpose.SAVINGS, RankingBlock.NOT_COMPUTED);
        }
        List<RankingResult> all = repository.findByPurposeAndAsOfPeriodAndTermMonthsAndChannelOrderByRankAsc(
                Purpose.SAVINGS, period.get(), termMonths, channel);
        if (all.isEmpty()) {
            return RankingBlock.notAvailable(Purpose.SAVINGS, RankingBlock.TERM_NOT_RANKED);
        }
        Long bucket = chooseAmount(all.stream().map(RankingResult::getAmountVnd).filter(Objects::nonNull).distinct()
                .sorted().toList(), amount);
        return block(Purpose.SAVINGS, period.get(),
                all.stream().filter(r -> Objects.equals(r.getAmountVnd(), bucket)).toList(), limit);
    }

    /** Mốc tiền cho {@code amount}; null khi không có số tiền hoặc pipeline không xếp theo mốc tiền. */
    static Long chooseAmount(List<Long> buckets, Long amount) {
        if (amount == null || buckets.isEmpty()) {
            return null;
        }
        return buckets.stream().filter(b -> b <= amount).max(Comparator.naturalOrder()).orElse(buckets.getFirst());
    }

    private RankingBlock block(Purpose purpose, String period, List<RankingResult> results, int limit) {
        if (results.isEmpty()) {
            return RankingBlock.notAvailable(purpose, RankingBlock.TERM_NOT_RANKED);
        }
        Map<String, Bank> banks = bankService.lookup();
        List<RankingBlock.Item> items = results.stream()
                .limit(limit > 0 ? limit : Long.MAX_VALUE)
                .map(r -> new RankingBlock.Item(r.getRank(), r.getRankLow(), r.getRankHigh(), r.getTicker(),
                        banks.containsKey(r.getTicker()) ? banks.get(r.getTicker()).getShortName() : r.getTicker(),
                        r.getScore(), r.getGroupLabel(), r.getTopPositive(), r.getTopNegative(), r.getPTop1(),
                        r.getPTop3()))
                .toList();
        RankingResult first = results.getFirst();
        return new RankingBlock(ResultStatus.AVAILABLE, purpose, period, first.getMethodVersion(), false,
                first.getTermMonths(), first.getChannel(), first.getAmountVnd(), first.getRatesAsOf(),
                first.getUninsuredShare(), first.getSafetyWeight(), null, items);
    }
}
