package vn.kltn.bankadvisor.module.rate.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vn.kltn.bankadvisor.module.rate.entity.Channel;
import vn.kltn.bankadvisor.module.rate.entity.DepositRateTier;

import java.util.List;

public interface DepositRateTierRepository extends JpaRepository<DepositRateTier, Long> {

    List<DepositRateTier> findByTermMonthsAndChannel(int termMonths, Channel channel);
}
