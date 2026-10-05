package vn.kltn.bankadvisor.module.bank.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vn.kltn.bankadvisor.module.bank.entity.BankOwnership;

public interface BankOwnershipRepository extends JpaRepository<BankOwnership, String> {
}
