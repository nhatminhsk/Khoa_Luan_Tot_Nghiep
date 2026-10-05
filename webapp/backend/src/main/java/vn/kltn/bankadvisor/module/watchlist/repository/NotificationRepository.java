package vn.kltn.bankadvisor.module.watchlist.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import vn.kltn.bankadvisor.module.watchlist.entity.EmailStatus;
import vn.kltn.bankadvisor.module.watchlist.entity.Notification;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

public interface NotificationRepository extends JpaRepository<Notification, Long> {

    Page<Notification> findByUserIdOrderByCreatedAtDesc(long userId, Pageable pageable);

    Optional<Notification> findByIdAndUserId(long id, long userId);

    long countByUserIdAndReadAtIsNull(long userId);

    boolean existsByUserIdAndRefKey(long userId, String refKey);

    @Modifying
    @Query("update Notification n set n.readAt = :now where n.userId = :userId and n.readAt is null")
    int markAllRead(@Param("userId") long userId, @Param("now") Instant now);

    /** Email chờ gửi đã tới lượt (lần đầu, hoặc đã qua thời gian chờ sau lần lỗi), gom theo người nhận. */
    @Query("""
            select n from Notification n
            where n.emailStatus = vn.kltn.bankadvisor.module.watchlist.entity.EmailStatus.PENDING
              and n.emailNextAttemptAt <= :now
            order by n.userId, n.id""")
    List<Notification> findDueEmails(@Param("now") Instant now, Pageable pageable);

    long countByEmailStatus(EmailStatus status);

    List<Notification> findTop5ByEmailStatusOrderByIdDesc(EmailStatus status);
}
