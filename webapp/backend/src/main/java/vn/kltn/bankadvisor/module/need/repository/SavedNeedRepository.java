package vn.kltn.bankadvisor.module.need.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vn.kltn.bankadvisor.module.need.entity.SavedNeed;

import java.util.List;
import java.util.Optional;

public interface SavedNeedRepository extends JpaRepository<SavedNeed, Long> {

    List<SavedNeed> findByUserIdOrderByUpdatedAtDesc(long userId);

    Optional<SavedNeed> findByIdAndUserId(long id, long userId);

    long countByUserId(long userId);
}
