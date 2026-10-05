package vn.kltn.bankadvisor.module.app.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vn.kltn.bankadvisor.module.app.entity.AppStoreSnapshot;

import java.util.List;

public interface AppStoreSnapshotRepository extends JpaRepository<AppStoreSnapshot, Long> {

    List<AppStoreSnapshot> findByTicker(String ticker);
}
