package vn.kltn.bankadvisor.module.indicator.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vn.kltn.bankadvisor.module.indicator.entity.Indicator;

import java.util.List;

public interface IndicatorRepository extends JpaRepository<Indicator, String> {

    List<Indicator> findAllByOrderByDisplayOrderAsc();
}
