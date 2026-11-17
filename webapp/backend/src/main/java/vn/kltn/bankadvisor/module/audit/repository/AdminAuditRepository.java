package vn.kltn.bankadvisor.module.audit.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vn.kltn.bankadvisor.module.audit.entity.AdminAudit;

public interface AdminAuditRepository extends JpaRepository<AdminAudit, Long> {
}
