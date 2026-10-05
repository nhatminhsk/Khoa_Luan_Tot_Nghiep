package vn.kltn.bankadvisor.module.forecast.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import vn.kltn.bankadvisor.module.forecast.entity.ForecastPoint;

import java.util.List;
import java.util.Optional;

public interface ForecastPointRepository extends JpaRepository<ForecastPoint, Long> {

    @Query("select max(f.originPeriod) from ForecastPoint f where f.ticker = :ticker")
    Optional<String> findLatestOrigin(@Param("ticker") String ticker);

    List<ForecastPoint> findByTickerAndOriginPeriodOrderByIndicatorCodeAscHorizonAsc(String ticker, String originPeriod);
}
