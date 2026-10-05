package vn.kltn.bankadvisor.module.bank.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.exception.AppException;
import vn.kltn.bankadvisor.common.exception.ErrorCode;
import vn.kltn.bankadvisor.module.bank.dto.BankResponse;
import vn.kltn.bankadvisor.module.bank.entity.Bank;
import vn.kltn.bankadvisor.module.bank.entity.BankOwnership;
import vn.kltn.bankadvisor.module.bank.repository.BankOwnershipRepository;
import vn.kltn.bankadvisor.module.bank.repository.BankRepository;

import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
@Transactional(readOnly = true)
public class BankService {

    private final BankRepository bankRepository;
    private final BankOwnershipRepository ownershipRepository;

    public BankService(BankRepository bankRepository, BankOwnershipRepository ownershipRepository) {
        this.bankRepository = bankRepository;
        this.ownershipRepository = ownershipRepository;
    }

    public List<BankResponse> findAll() {
        Map<String, BankOwnership> ownership = ownershipRepository.findAll().stream()
                .collect(Collectors.toMap(BankOwnership::getTicker, Function.identity()));
        return bankRepository.findAllByOrderByTickerAsc().stream()
                .map(bank -> BankResponse.from(bank, ownership.get(bank.getTicker())))
                .toList();
    }

    public BankResponse get(String ticker) {
        Bank bank = require(ticker);
        return BankResponse.from(bank, ownershipRepository.findById(bank.getTicker()).orElse(null));
    }

    /** Ném BANK_NOT_FOUND nếu mã không thuộc 22 ngân hàng. Mã không phân biệt hoa thường. */
    public Bank require(String ticker) {
        return bankRepository.findById(normalize(ticker)).orElseThrow(() -> new AppException(ErrorCode.BANK_NOT_FOUND));
    }

    /** Bảng tra mã → ngân hàng, dùng khi ghép tên vào kết quả của module khác. */
    public Map<String, Bank> lookup() {
        return bankRepository.findAll().stream().collect(Collectors.toMap(Bank::getTicker, Function.identity()));
    }

    public static String normalize(String ticker) {
        return ticker == null ? null : ticker.trim().toUpperCase();
    }
}
