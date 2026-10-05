package vn.kltn.bankadvisor.module.macro.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vn.kltn.bankadvisor.module.macro.entity.CpiMonth;

import java.util.List;

public interface CpiMonthRepository extends JpaRepository<CpiMonth, String> {

    List<CpiMonth> findAllByOrderByMonthAsc();
}
