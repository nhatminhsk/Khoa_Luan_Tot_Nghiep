package vn.kltn.bankadvisor.module.dataset.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vn.kltn.bankadvisor.module.dataset.entity.DatasetInfo;

public interface DatasetInfoRepository extends JpaRepository<DatasetInfo, String> {
}
