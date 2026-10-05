package vn.kltn.bankadvisor.module.rate.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import vn.kltn.bankadvisor.module.rate.entity.Channel;
import vn.kltn.bankadvisor.module.rate.entity.DepositRate;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

public interface DepositRateRepository extends JpaRepository<DepositRate, Long> {

    @Query("select max(r.rateDate) from DepositRate r")
    Optional<LocalDate> findLatestDate();

    @Query("select max(r.rateDate) from DepositRate r where r.rateDate < :date")
    Optional<LocalDate> findLatestDateBefore(@Param("date") LocalDate date);

    List<DepositRate> findByRateDate(LocalDate rateDate);

    List<DepositRate> findByTermMonthsAndChannelOrderByRateDateAsc(int termMonths, Channel channel);

    List<DepositRate> findByTickerOrderByRateDateAsc(String ticker);

    List<DepositRate> findAllByOrderByRateDateAsc();
}
