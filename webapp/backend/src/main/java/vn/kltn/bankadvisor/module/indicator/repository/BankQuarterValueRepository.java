package vn.kltn.bankadvisor.module.indicator.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import vn.kltn.bankadvisor.module.indicator.entity.BankQuarterValue;

import java.util.Collection;
import java.util.List;
import java.util.Optional;

public interface BankQuarterValueRepository extends JpaRepository<BankQuarterValue, Long> {

    List<BankQuarterValue> findByIndicatorCodeInOrderByPeriodAsc(Collection<String> indicatorCodes);

    @Query("select max(v.period) from BankQuarterValue v")
    Optional<String> findLatestPeriod();
}
