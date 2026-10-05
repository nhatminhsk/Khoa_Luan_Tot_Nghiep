package vn.kltn.bankadvisor.module.rate.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vn.kltn.bankadvisor.module.rate.entity.LendingRate;

import java.util.List;

public interface LendingRateRepository extends JpaRepository<LendingRate, Long> {

    List<LendingRate> findAllByOrderByMonthAsc();

    List<LendingRate> findByTickerOrderByMonthAsc(String ticker);
}
