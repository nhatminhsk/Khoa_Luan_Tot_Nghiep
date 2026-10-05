package vn.kltn.bankadvisor.module.rate.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.util.Stats;
import vn.kltn.bankadvisor.module.bank.entity.Bank;
import vn.kltn.bankadvisor.module.bank.service.BankService;
import vn.kltn.bankadvisor.module.rate.dto.BankRatesResponse;
import vn.kltn.bankadvisor.module.rate.dto.BestRatesResponse;
import vn.kltn.bankadvisor.module.rate.dto.DepositRateTableResponse;
import vn.kltn.bankadvisor.module.rate.dto.LendingRateResponse;
import vn.kltn.bankadvisor.module.rate.dto.RateChangesResponse;
import vn.kltn.bankadvisor.module.rate.dto.RateTrendPoint;
import vn.kltn.bankadvisor.module.rate.entity.Channel;
import vn.kltn.bankadvisor.module.rate.entity.DepositRate;
import vn.kltn.bankadvisor.module.rate.entity.LendingRate;
import vn.kltn.bankadvisor.module.rate.repository.DepositRateRepository;
import vn.kltn.bankadvisor.module.rate.repository.LendingRateRepository;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.stream.Collectors;

@Service
@Transactional(readOnly = true)
public class RateService {

    private final DepositRateRepository depositRepository;
    private final LendingRateRepository lendingRepository;
    private final BankService bankService;

    public RateService(DepositRateRepository depositRepository, LendingRateRepository lendingRepository,
                       BankService bankService) {
        this.depositRepository = depositRepository;
        this.lendingRepository = lendingRepository;
        this.bankService = bankService;
    }

    /** Lãi suất ngày mới nhất và ngày liền trước. */
    public RateSnapshot snapshot() {
        Optional<LocalDate> latest = depositRepository.findLatestDate();
        if (latest.isEmpty()) {
            return RateSnapshot.empty();
        }
        LocalDate previous = depositRepository.findLatestDateBefore(latest.get()).orElse(null);
        return new RateSnapshot(latest.get(), previous, byKey(depositRepository.findByRateDate(latest.get())),
                previous == null ? Map.of() : byKey(depositRepository.findByRateDate(previous)));
    }

    /** Snapshot tại một ngày cụ thể so với ngày liền trước nó (dùng khi tạo thông báo). */
    public RateSnapshot snapshotAt(LocalDate date) {
        LocalDate previous = depositRepository.findLatestDateBefore(date).orElse(null);
        return new RateSnapshot(date, previous, byKey(depositRepository.findByRateDate(date)),
                previous == null ? Map.of() : byKey(depositRepository.findByRateDate(previous)));
    }

    public DepositRateTableResponse depositTable(Channel channel) {
        RateSnapshot snap = snapshot();
        Map<String, Bank> banks = bankService.lookup();
        TreeSet<Integer> terms = new TreeSet<>();
        Map<String, Map<Integer, DepositRateTableResponse.Cell>> rows = new TreeMap<>();
        snap.current().forEach((key, rate) -> {
            if (key.channel() != channel) {
                return;
            }
            terms.add(key.termMonths());
            BigDecimal change = snap.change(key.ticker(), key.termMonths(), channel).orElse(null);
            rows.computeIfAbsent(key.ticker(), t -> new TreeMap<>())
                    .put(key.termMonths(), new DepositRateTableResponse.Cell(rate, change));
        });
        List<DepositRateTableResponse.Row> result = rows.entrySet().stream()
                .map(e -> new DepositRateTableResponse.Row(e.getKey(), shortName(banks, e.getKey()), e.getValue()))
                .toList();
        return new DepositRateTableResponse(snap.date(), snap.previousDate(), channel, List.copyOf(terms), result);
    }

    public BestRatesResponse bestRates() {
        RateSnapshot snap = snapshot();
        Map<String, Bank> banks = bankService.lookup();
        TreeSet<Integer> terms = snap.current().keySet().stream().map(RateSnapshot.Key::termMonths)
                .collect(Collectors.toCollection(TreeSet::new));
        List<BestRatesResponse.Item> items = new ArrayList<>();
        for (int term : terms) {
            Map<String, BigDecimal> online = ratesFor(snap, term, Channel.ONLINE);
            Map<String, BigDecimal> counter = ratesFor(snap, term, Channel.COUNTER);
            items.add(new BestRatesResponse.Item(term, best(online, banks), best(counter, banks),
                    median(online.values()), median(counter.values())));
        }
        return new BestRatesResponse(snap.date(), items);
    }

    public List<RateTrendPoint> trend(int termMonths, Channel channel) {
        Map<LocalDate, List<BigDecimal>> byDate = depositRepository
                .findByTermMonthsAndChannelOrderByRateDateAsc(termMonths, channel).stream()
                .collect(Collectors.groupingBy(DepositRate::getRateDate, TreeMap::new,
                        Collectors.mapping(DepositRate::getRatePercent, Collectors.toList())));
        return byDate.entrySet().stream().map(e -> new RateTrendPoint(
                e.getKey(),
                e.getValue().stream().min(Comparator.naturalOrder()).orElseThrow(),
                median(e.getValue()),
                e.getValue().stream().max(Comparator.naturalOrder()).orElseThrow(),
                e.getValue().size())).toList();
    }

    /**
     * Các lần đổi lãi suất trong {@code days} ngày gần nhất, tính lùi từ ngày có số mới nhất (không phải hôm nay,
     * để dữ liệu cập nhật trễ vẫn có kết quả). So với lần quan sát liền trước của cùng ngân hàng × kỳ hạn × kênh,
     * nên ngày bị thiếu số không tạo ra thay đổi giả; kỳ hạn mới xuất hiện lần đầu không tính là thay đổi.
     */
    public RateChangesResponse changes(int days) {
        Optional<LocalDate> latest = depositRepository.findLatestDate();
        if (latest.isEmpty()) {
            return new RateChangesResponse(null, null, days, List.of());
        }
        LocalDate from = latest.get().minusDays(days - 1L);
        Map<String, Bank> banks = bankService.lookup();
        Map<RateSnapshot.Key, DepositRate> last = new HashMap<>();
        List<RateChangesResponse.Change> changes = new ArrayList<>();
        for (DepositRate r : depositRepository.findAllByOrderByRateDateAsc()) {
            RateSnapshot.Key key = new RateSnapshot.Key(r.getTicker(), r.getTermMonths(), r.getChannel());
            DepositRate before = last.put(key, r);
            if (before == null || r.getRateDate().isBefore(from)
                    || before.getRatePercent().compareTo(r.getRatePercent()) == 0) {
                continue;
            }
            changes.add(new RateChangesResponse.Change(r.getRateDate(), before.getRateDate(), r.getTicker(),
                    shortName(banks, r.getTicker()), r.getTermMonths(), r.getChannel(), before.getRatePercent(),
                    r.getRatePercent(), r.getRatePercent().subtract(before.getRatePercent())));
        }
        changes.sort(Comparator.comparing(RateChangesResponse.Change::date).reversed()
                .thenComparing(RateChangesResponse.Change::ticker)
                .thenComparing(RateChangesResponse.Change::channel)
                .thenComparingInt(RateChangesResponse.Change::termMonths));
        return new RateChangesResponse(latest.get(), from, days, changes);
    }

    public BankRatesResponse bankRates(String ticker) {
        Bank bank = bankService.require(ticker);
        RateSnapshot snap = snapshot();
        TreeSet<Integer> terms = snap.current().keySet().stream()
                .filter(k -> k.ticker().equals(bank.getTicker())).map(RateSnapshot.Key::termMonths)
                .collect(Collectors.toCollection(TreeSet::new));
        List<BankRatesResponse.Current> current = terms.stream().map(term -> new BankRatesResponse.Current(
                term,
                snap.rate(bank.getTicker(), term, Channel.ONLINE).orElse(null),
                snap.rate(bank.getTicker(), term, Channel.COUNTER).orElse(null),
                snap.change(bank.getTicker(), term, Channel.ONLINE).orElse(null),
                snap.change(bank.getTicker(), term, Channel.COUNTER).orElse(null))).toList();
        List<BankRatesResponse.HistoryPoint> history = depositRepository.findByTickerOrderByRateDateAsc(bank.getTicker())
                .stream().map(r -> new BankRatesResponse.HistoryPoint(r.getRateDate(), r.getTermMonths(),
                        r.getChannel(), r.getRatePercent())).toList();
        return new BankRatesResponse(snap.date(), current, history);
    }

    /** Tháng gần nhất có số của từng ngân hàng (các ngân hàng công bố không đều nhau). */
    public List<LendingRateResponse> latestLending() {
        Map<String, Bank> banks = bankService.lookup();
        Map<String, LendingRate> latest = new TreeMap<>();
        for (LendingRate rate : lendingRepository.findAllByOrderByMonthAsc()) {
            latest.put(rate.getTicker(), rate);
        }
        return latest.values().stream().map(r -> toResponse(r, banks)).toList();
    }

    public List<LendingRateResponse> bankLending(String ticker) {
        Bank bank = bankService.require(ticker);
        Map<String, Bank> banks = Map.of(bank.getTicker(), bank);
        return lendingRepository.findByTickerOrderByMonthAsc(bank.getTicker()).stream()
                .map(r -> toResponse(r, banks)).toList();
    }

    private static LendingRateResponse toResponse(LendingRate r, Map<String, Bank> banks) {
        return new LendingRateResponse(r.getTicker(), shortName(banks, r.getTicker()), r.getMonth(),
                r.getLendingAvgPercent(), r.getDepositAvgPercent(), r.getSourceUrl());
    }

    private static Map<RateSnapshot.Key, BigDecimal> byKey(List<DepositRate> rates) {
        Map<RateSnapshot.Key, BigDecimal> map = new LinkedHashMap<>();
        for (DepositRate r : rates) {
            map.put(new RateSnapshot.Key(r.getTicker(), r.getTermMonths(), r.getChannel()), r.getRatePercent());
        }
        return map;
    }

    private static Map<String, BigDecimal> ratesFor(RateSnapshot snap, int term, Channel channel) {
        Map<String, BigDecimal> rates = new TreeMap<>();
        snap.current().forEach((key, rate) -> {
            if (key.termMonths() == term && key.channel() == channel) {
                rates.put(key.ticker(), rate);
            }
        });
        return rates;
    }

    private static BestRatesResponse.Best best(Map<String, BigDecimal> rates, Map<String, Bank> banks) {
        if (rates.isEmpty()) {
            return null;
        }
        BigDecimal max = rates.values().stream().max(Comparator.naturalOrder()).orElseThrow();
        List<String> leaders = rates.entrySet().stream().filter(e -> e.getValue().compareTo(max) == 0)
                .map(Map.Entry::getKey).sorted().toList();
        String ticker = leaders.getFirst();
        return new BestRatesResponse.Best(ticker, shortName(banks, ticker), max, leaders.size() - 1);
    }

    static BigDecimal median(Collection<BigDecimal> values) {
        var median = Stats.median(values.stream().map(BigDecimal::doubleValue).toList());
        return median.isPresent()
                ? BigDecimal.valueOf(median.getAsDouble()).setScale(2, RoundingMode.HALF_UP)
                : null;
    }

    private static String shortName(Map<String, Bank> banks, String ticker) {
        Bank bank = banks.get(ticker);
        return bank == null ? ticker : bank.getShortName();
    }
}
