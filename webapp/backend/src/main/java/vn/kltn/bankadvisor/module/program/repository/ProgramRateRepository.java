package vn.kltn.bankadvisor.module.program.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vn.kltn.bankadvisor.module.program.entity.ProgramRate;

import java.util.List;

public interface ProgramRateRepository extends JpaRepository<ProgramRate, Long> {

    List<ProgramRate> findAllByOrderByProgramCodeAscValidFromAsc();
}
