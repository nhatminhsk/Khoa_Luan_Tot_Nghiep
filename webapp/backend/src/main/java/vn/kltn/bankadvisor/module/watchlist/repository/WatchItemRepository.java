package vn.kltn.bankadvisor.module.watchlist.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import vn.kltn.bankadvisor.module.watchlist.entity.WatchItem;

import java.util.List;
import java.util.Optional;

public interface WatchItemRepository extends JpaRepository<WatchItem, Long> {

    List<WatchItem> findByUserIdOrderByCreatedAtAsc(long userId);

    Optional<WatchItem> findByUserIdAndTicker(long userId, String ticker);

    boolean existsByUserIdAndTicker(long userId, String ticker);

    /** Mục theo dõi của những người còn bật "báo khi lãi suất đổi". */
    @Query("select w from WatchItem w where w.userId in (select u.id from AppUser u where u.notifyRateChange = true)")
    List<WatchItem> findAllForRateAlerts();
}
