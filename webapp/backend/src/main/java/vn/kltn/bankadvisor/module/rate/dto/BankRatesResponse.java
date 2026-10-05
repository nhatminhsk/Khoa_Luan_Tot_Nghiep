package vn.kltn.bankadvisor.module.rate.dto;

import vn.kltn.bankadvisor.module.rate.entity.Channel;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

/** Lãi suất hiện tại và lịch sử niêm yết của một ngân hàng. */
public record BankRatesResponse(LocalDate rateDate, List<Current> current, List<HistoryPoint> history) {

    public record Current(int termMonths, BigDecimal online, BigDecimal counter,
                          BigDecimal onlineChange, BigDecimal counterChange) {
    }

    public record HistoryPoint(LocalDate date, int termMonths, Channel channel, BigDecimal rate) {
    }
}
