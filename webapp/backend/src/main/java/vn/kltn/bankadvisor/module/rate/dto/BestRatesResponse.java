package vn.kltn.bankadvisor.module.rate.dto;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

/** Lãi suất cao nhất hôm nay theo từng kỳ hạn, kèm trung vị 22 ngân hàng. */
public record BestRatesResponse(LocalDate rateDate, List<Item> items) {

    public record Item(int termMonths, Best online, Best counter, BigDecimal medianOnline, BigDecimal medianCounter) {
    }

    /** {@code tiedCount}: số ngân hàng khác cùng mức cao nhất. */
    public record Best(String ticker, String shortName, BigDecimal rate, int tiedCount) {
    }
}
