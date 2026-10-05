package vn.kltn.bankadvisor.module.bank.dto;

import vn.kltn.bankadvisor.module.bank.entity.Bank;
import vn.kltn.bankadvisor.module.bank.entity.BankOwnership;

import java.time.LocalDate;

/** @param ownership cơ cấu sở hữu; null khi chưa có dữ liệu */
public record BankResponse(String ticker, String shortName, String fullName, String appName, Ownership ownership) {

    /**
     * @param statePercent       tỷ lệ sở hữu nhà nước (%)
     * @param foreignPercent     tỷ lệ sở hữu nước ngoài (%)
     * @param foreignRoomPercent trần sở hữu nước ngoài (%)
     */
    public record Ownership(LocalDate asOfDate, Double statePercent, Double foreignPercent, Double foreignRoomPercent,
                            String source) {

        static Ownership from(BankOwnership o) {
            return o == null ? null : new Ownership(o.getAsOfDate(), o.getStatePercent(), o.getForeignPercent(),
                    o.getForeignRoomPercent(), o.getSource());
        }
    }

    public static BankResponse from(Bank bank, BankOwnership ownership) {
        return new BankResponse(bank.getTicker(), bank.getShortName(), bank.getFullName(), bank.getAppName(),
                Ownership.from(ownership));
    }
}
