package vn.kltn.bankadvisor.module.program.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vn.kltn.bankadvisor.module.program.entity.PolicyProgram;

public interface PolicyProgramRepository extends JpaRepository<PolicyProgram, String> {
}
