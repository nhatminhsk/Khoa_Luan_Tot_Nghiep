package vn.kltn.bankadvisor.module.program.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vn.kltn.bankadvisor.module.program.entity.ProgramParticipation;

import java.util.List;

public interface ProgramParticipationRepository extends JpaRepository<ProgramParticipation, Long> {

    List<ProgramParticipation> findByTicker(String ticker);

    List<ProgramParticipation> findByParticipatesTrue();
}
