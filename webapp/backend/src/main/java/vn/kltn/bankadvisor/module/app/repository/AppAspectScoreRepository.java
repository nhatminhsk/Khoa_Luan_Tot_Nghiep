package vn.kltn.bankadvisor.module.app.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vn.kltn.bankadvisor.module.app.entity.AppAspectScore;

import java.util.List;

public interface AppAspectScoreRepository extends JpaRepository<AppAspectScore, Long> {

    List<AppAspectScore> findByTickerOrderByPeriodAscAspectAsc(String ticker);
}
