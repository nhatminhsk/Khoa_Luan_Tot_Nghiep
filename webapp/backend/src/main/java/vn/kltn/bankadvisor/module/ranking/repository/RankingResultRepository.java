package vn.kltn.bankadvisor.module.ranking.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import vn.kltn.bankadvisor.module.rate.entity.Channel;
import vn.kltn.bankadvisor.module.ranking.entity.Purpose;
import vn.kltn.bankadvisor.module.ranking.entity.RankingResult;
import java.util.List;
import java.util.Optional;

public interface RankingResultRepository extends JpaRepository<RankingResult, Long> {

    @Query("select max(r.asOfPeriod) from RankingResult r where r.purpose = :purpose")
    Optional<String> findLatestPeriod(@Param("purpose") Purpose purpose);

    List<RankingResult> findByPurposeAndAsOfPeriodOrderByRankAsc(Purpose purpose, String asOfPeriod);

    /** Mọi mốc tiền của một kỳ hạn × kênh; service chọn mốc. */
    List<RankingResult> findByPurposeAndAsOfPeriodAndTermMonthsAndChannelOrderByRankAsc(
            Purpose purpose, String asOfPeriod, Integer termMonths, Channel channel);
}
