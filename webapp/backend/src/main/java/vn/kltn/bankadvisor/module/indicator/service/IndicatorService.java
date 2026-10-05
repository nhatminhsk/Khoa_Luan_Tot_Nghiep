package vn.kltn.bankadvisor.module.indicator.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.exception.AppException;
import vn.kltn.bankadvisor.common.exception.ErrorCode;
import vn.kltn.bankadvisor.common.util.Periods;
import vn.kltn.bankadvisor.common.util.Stats;
import vn.kltn.bankadvisor.module.bank.entity.Bank;
import vn.kltn.bankadvisor.module.bank.service.BankService;
import vn.kltn.bankadvisor.module.indicator.dto.BankIndicatorsResponse;
import vn.kltn.bankadvisor.module.indicator.dto.IndicatorComparisonResponse;
import vn.kltn.bankadvisor.module.indicator.dto.IndicatorResponse;
import vn.kltn.bankadvisor.module.indicator.dto.IndicatorSnapshotResponse;
import vn.kltn.bankadvisor.module.indicator.entity.BankQuarterValue;
import vn.kltn.bankadvisor.module.indicator.entity.Indicator;
import vn.kltn.bankadvisor.module.indicator.repository.BankQuarterValueRepository;
import vn.kltn.bankadvisor.module.indicator.repository.IndicatorRepository;

import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * Chỉ tiêu tài chính theo quý. Mọi phép tính ở đây là mô tả (trung vị, thứ hạng theo từng chỉ tiêu),
 * không phải xếp hạng tổng hợp — xếp hạng tổng hợp do module ranking đọc từ kết quả thuật toán.
 */
@Service
@Transactional(readOnly = true)
public class IndicatorService {

    /** Số gần nhất chỉ dùng nếu cách quý mới nhất không quá 3 quý (tức nằm trong 4 quý cuối). */
    static final int MAX_STALE_QUARTERS = 3;

    private final IndicatorRepository indicatorRepository;
    private final BankQuarterValueRepository valueRepository;
    private final BankService bankService;

    public IndicatorService(IndicatorRepository indicatorRepository, BankQuarterValueRepository valueRepository,
                            BankService bankService) {
        this.indicatorRepository = indicatorRepository;
        this.valueRepository = valueRepository;
        this.bankService = bankService;
    }

    public List<IndicatorResponse> catalog() {
        return indicatorRepository.findAllByOrderByDisplayOrderAsc().stream().map(IndicatorResponse::from).toList();
    }

    public BankIndicatorsResponse bankIndicators(String ticker) {
        Bank bank = bankService.require(ticker);
        List<Indicator> indicators = indicatorRepository.findAllByOrderByDisplayOrderAsc();
        ValueMatrix matrix = load(indicators.stream().map(Indicator::getCode).toList());

        List<BankIndicatorsResponse.IndicatorSeries> series = new ArrayList<>();
        for (Indicator indicator : indicators) {
            Map<String, Map<String, Double>> byPeriod = matrix.byIndicator(indicator.getCode());
            List<BankIndicatorsResponse.Point> points = new ArrayList<>();
            String latestPeriod = null;
            for (Map.Entry<String, Map<String, Double>> entry : byPeriod.entrySet()) {
                Double value = entry.getValue().get(bank.getTicker());
                points.add(new BankIndicatorsResponse.Point(entry.getKey(), value, median(entry.getValue().values())));
                if (value != null) {
                    latestPeriod = entry.getKey();
                }
            }
            BankIndicatorsResponse.Latest latest = null;
            if (latestPeriod != null) {
                Map<String, Double> peers = byPeriod.get(latestPeriod);
                double value = peers.get(bank.getTicker());
                latest = new BankIndicatorsResponse.Latest(latestPeriod, value, median(peers.values()),
                        rankOf(value, peers.values(), indicator), peers.size());
            }
            series.add(new BankIndicatorsResponse.IndicatorSeries(IndicatorResponse.from(indicator), points, latest));
        }
        return new BankIndicatorsResponse(bank.getTicker(), matrix.latestPeriod(), series);
    }

    public IndicatorSnapshotResponse snapshot() {
        List<Indicator> indicators = indicatorRepository.findAllByOrderByDisplayOrderAsc();
        ValueMatrix matrix = load(indicators.stream().map(Indicator::getCode).toList());
        String latestPeriod = matrix.latestPeriod();

        List<IndicatorSnapshotResponse.Row> rows = new ArrayList<>();
        for (Bank bank : bankService.lookup().values().stream()
                .sorted((a, b) -> a.getTicker().compareTo(b.getTicker())).toList()) {
            Map<String, IndicatorSnapshotResponse.Cell> cells = new LinkedHashMap<>();
            for (Indicator indicator : indicators) {
                matrix.byIndicator(indicator.getCode()).entrySet().stream()
                        .filter(e -> e.getValue().containsKey(bank.getTicker()))
                        .reduce((first, second) -> second)
                        .filter(e -> latestPeriod != null
                                && Periods.quartersBetween(e.getKey(), latestPeriod) <= MAX_STALE_QUARTERS)
                        .ifPresent(e -> cells.put(indicator.getCode(),
                                new IndicatorSnapshotResponse.Cell(e.getValue().get(bank.getTicker()), e.getKey())));
            }
            rows.add(new IndicatorSnapshotResponse.Row(bank.getTicker(), bank.getShortName(), cells));
        }
        return new IndicatorSnapshotResponse(latestPeriod,
                indicators.stream().map(IndicatorResponse::from).toList(), rows);
    }

    public IndicatorComparisonResponse compare(String indicatorCode, List<String> tickers) {
        Indicator indicator = indicatorRepository.findById(indicatorCode)
                .orElseThrow(() -> new AppException(ErrorCode.NOT_FOUND, "Không có chỉ tiêu " + indicatorCode));
        List<Bank> banks = tickers.stream().map(bankService::require).distinct().toList();
        Map<String, Map<String, Double>> byPeriod = load(List.of(indicator.getCode())).byIndicator(indicator.getCode());

        List<String> periods = new ArrayList<>(byPeriod.keySet());
        List<IndicatorComparisonResponse.BankSeries> series = banks.stream()
                .map(bank -> new IndicatorComparisonResponse.BankSeries(bank.getTicker(), bank.getShortName(),
                        periods.stream().map(p -> byPeriod.get(p).get(bank.getTicker())).toList()))
                .toList();
        List<Double> medians = periods.stream().map(p -> median(byPeriod.get(p).values())).toList();
        return new IndicatorComparisonResponse(IndicatorResponse.from(indicator), periods, series, medians);
    }

    private ValueMatrix load(Collection<String> codes) {
        return new ValueMatrix(valueRepository.findByIndicatorCodeInOrderByPeriodAsc(codes));
    }

    private static Double median(Collection<Double> values) {
        var median = Stats.median(values);
        return median.isPresent() ? median.getAsDouble() : null;
    }

    static int rankOf(double value, Collection<Double> peers, Indicator indicator) {
        var order = indicator.getDirection().rankingOrder();
        return (int) peers.stream().filter(Objects::nonNull).filter(p -> order.compare(p, value) < 0).count() + 1;
    }

    /** Chỉ tiêu → quý (tăng dần) → mã ngân hàng → giá trị. */
    private static final class ValueMatrix {

        private final Map<String, TreeMap<String, Map<String, Double>>> data = new LinkedHashMap<>();
        private final TreeSet<String> periods = new TreeSet<>();

        ValueMatrix(List<BankQuarterValue> values) {
            for (BankQuarterValue v : values) {
                data.computeIfAbsent(v.getIndicatorCode(), k -> new TreeMap<>())
                        .computeIfAbsent(v.getPeriod(), k -> new LinkedHashMap<>())
                        .put(v.getTicker(), v.getValue());
                periods.add(v.getPeriod());
            }
        }

        Map<String, Map<String, Double>> byIndicator(String code) {
            return new TreeMap<>(data.getOrDefault(code, new TreeMap<>()));
        }

        String latestPeriod() {
            return periods.isEmpty() ? null : periods.last();
        }
    }
}
