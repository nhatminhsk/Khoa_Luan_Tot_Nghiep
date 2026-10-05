package vn.kltn.bankadvisor.module.dataset.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vn.kltn.bankadvisor.module.dataset.entity.ImportRun;
import vn.kltn.bankadvisor.module.dataset.entity.ImportStatus;

import java.util.List;
import java.util.Optional;

public interface ImportRunRepository extends JpaRepository<ImportRun, Long> {

    Optional<ImportRun> findFirstByDatasetAndStatusOrderByStartedAtDesc(String dataset, ImportStatus status);

    List<ImportRun> findTop100ByOrderByStartedAtDesc();
}
