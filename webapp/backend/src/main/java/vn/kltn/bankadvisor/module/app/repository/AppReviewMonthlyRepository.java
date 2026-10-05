package vn.kltn.bankadvisor.module.app.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vn.kltn.bankadvisor.module.app.entity.AppReviewMonthly;

import java.util.List;

public interface AppReviewMonthlyRepository extends JpaRepository<AppReviewMonthly, Long> {

    List<AppReviewMonthly> findByTickerOrderByMonthAsc(String ticker);
}
