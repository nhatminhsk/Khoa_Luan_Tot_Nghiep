package vn.kltn.bankadvisor.module.bank.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import vn.kltn.bankadvisor.module.bank.entity.Bank;

import java.util.List;

public interface BankRepository extends JpaRepository<Bank, String> {

    List<Bank> findAllByOrderByTickerAsc();
}
