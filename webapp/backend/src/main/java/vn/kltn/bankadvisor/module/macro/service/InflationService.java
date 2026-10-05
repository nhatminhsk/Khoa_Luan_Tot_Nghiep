package vn.kltn.bankadvisor.module.macro.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.module.macro.dto.InflationResponse;
import vn.kltn.bankadvisor.module.macro.entity.CpiMonth;
import vn.kltn.bankadvisor.module.macro.repository.CpiMonthRepository;

import java.util.List;

@Service
@Transactional(readOnly = true)
public class InflationService {

    private final CpiMonthRepository repository;

    public InflationService(CpiMonthRepository repository) {
        this.repository = repository;
    }

    public InflationResponse inflation() {
        List<CpiMonth> months = repository.findAllByOrderByMonthAsc();
        if (months.isEmpty()) {
            return new InflationResponse(null, null, List.of());
        }
        CpiMonth latest = months.getLast();
        return new InflationResponse(InflationResponse.Point.from(latest), latest.getSourceUrl(),
                months.stream().map(InflationResponse.Point::from).toList());
    }
}
