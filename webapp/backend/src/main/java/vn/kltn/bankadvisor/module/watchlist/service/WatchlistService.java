package vn.kltn.bankadvisor.module.watchlist.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.exception.AppException;
import vn.kltn.bankadvisor.common.exception.ErrorCode;
import vn.kltn.bankadvisor.module.bank.entity.Bank;
import vn.kltn.bankadvisor.module.bank.service.BankService;
import vn.kltn.bankadvisor.module.rate.entity.Channel;
import vn.kltn.bankadvisor.module.rate.service.RateService;
import vn.kltn.bankadvisor.module.rate.service.RateSnapshot;
import vn.kltn.bankadvisor.module.watchlist.dto.WatchlistDtos.AddWatchRequest;
import vn.kltn.bankadvisor.module.watchlist.dto.WatchlistDtos.UpdateWatchRequest;
import vn.kltn.bankadvisor.module.watchlist.dto.WatchlistDtos.WatchItemResponse;
import vn.kltn.bankadvisor.module.watchlist.entity.WatchItem;
import vn.kltn.bankadvisor.module.watchlist.repository.WatchItemRepository;

import java.math.BigDecimal;
import java.time.Clock;
import java.util.List;
import java.util.Map;

@Service
@Transactional
public class WatchlistService {

    static final BigDecimal DEFAULT_THRESHOLD = new BigDecimal("0.10");
    private static final int REFERENCE_TERM = 12;

    private final WatchItemRepository repository;
    private final BankService bankService;
    private final RateService rateService;
    private final Clock clock;

    public WatchlistService(WatchItemRepository repository, BankService bankService, RateService rateService,
                            Clock clock) {
        this.repository = repository;
        this.bankService = bankService;
        this.rateService = rateService;
        this.clock = clock;
    }

    @Transactional(readOnly = true)
    public List<WatchItemResponse> list(long userId) {
        RateSnapshot snap = rateService.snapshot();
        Map<String, Bank> banks = bankService.lookup();
        return repository.findByUserIdOrderByCreatedAtAsc(userId).stream()
                .map(item -> toResponse(item, banks, snap))
                .toList();
    }

    public WatchItemResponse add(long userId, AddWatchRequest request) {
        Bank bank = bankService.require(request.ticker());
        if (repository.existsByUserIdAndTicker(userId, bank.getTicker())) {
            throw new AppException(ErrorCode.ALREADY_WATCHED);
        }
        BigDecimal threshold = request.rateThreshold() == null ? DEFAULT_THRESHOLD : request.rateThreshold();
        WatchItem item = repository.save(WatchItem.create(userId, bank.getTicker(), threshold, clock.instant()));
        return toResponse(item, Map.of(bank.getTicker(), bank), rateService.snapshot());
    }

    public WatchItemResponse update(long userId, String ticker, UpdateWatchRequest request) {
        WatchItem item = owned(userId, ticker);
        item.changeThreshold(request.rateThreshold());
        Bank bank = bankService.require(ticker);
        return toResponse(item, Map.of(bank.getTicker(), bank), rateService.snapshot());
    }

    public void remove(long userId, String ticker) {
        repository.delete(owned(userId, ticker));
    }

    private WatchItem owned(long userId, String ticker) {
        return repository.findByUserIdAndTicker(userId, BankService.normalize(ticker))
                .orElseThrow(() -> new AppException(ErrorCode.NOT_FOUND, "Ngân hàng này không có trong danh sách theo dõi"));
    }

    private static WatchItemResponse toResponse(WatchItem item, Map<String, Bank> banks, RateSnapshot snap) {
        Bank bank = banks.get(item.getTicker());
        return new WatchItemResponse(item.getTicker(), bank == null ? item.getTicker() : bank.getShortName(),
                item.getRateThreshold(),
                snap.rate(item.getTicker(), REFERENCE_TERM, Channel.ONLINE).orElse(null),
                snap.change(item.getTicker(), REFERENCE_TERM, Channel.ONLINE).orElse(null),
                item.getCreatedAt());
    }
}
