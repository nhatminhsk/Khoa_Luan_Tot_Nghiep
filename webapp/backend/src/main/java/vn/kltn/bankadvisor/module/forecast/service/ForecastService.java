package vn.kltn.bankadvisor.module.forecast.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.api.ResultStatus;
import vn.kltn.bankadvisor.module.bank.service.BankService;
import vn.kltn.bankadvisor.module.forecast.dto.ForecastBlock;
import vn.kltn.bankadvisor.module.forecast.entity.ForecastPoint;
import vn.kltn.bankadvisor.module.forecast.repository.ForecastPointRepository;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

/** Đọc dự báo pipeline đã tính; không chạy mô hình khi người dùng mở trang. */
@Service
@Transactional(readOnly = true)
public class ForecastService {

    private final ForecastPointRepository repository;
    private final BankService bankService;

    public ForecastService(ForecastPointRepository repository, BankService bankService) {
        this.repository = repository;
        this.bankService = bankService;
    }

    public ForecastBlock forBank(String ticker) {
        String code = bankService.require(ticker).getTicker();
        Optional<String> origin = repository.findLatestOrigin(code);
        if (origin.isEmpty()) {
            return ForecastBlock.notAvailable();
        }
        Map<String, List<ForecastPoint>> byIndicator = repository
                .findByTickerAndOriginPeriodOrderByIndicatorCodeAscHorizonAsc(code, origin.get()).stream()
                .collect(Collectors.groupingBy(ForecastPoint::getIndicatorCode, LinkedHashMap::new, Collectors.toList()));
        List<ForecastBlock.IndicatorForecast> indicators = byIndicator.entrySet().stream()
                .map(e -> new ForecastBlock.IndicatorForecast(e.getKey(), e.getValue().getFirst().getMethod(),
                        e.getValue().stream().map(p -> new ForecastBlock.Point(p.getTargetPeriod(), p.getHorizon(),
                                p.getValue(), p.getLower(), p.getUpper(), p.getNaiveValue())).toList()))
                .toList();
        return new ForecastBlock(ResultStatus.AVAILABLE, origin.get(), indicators);
    }
}
