package vn.kltn.bankadvisor.module.rate.dto;

import vn.kltn.bankadvisor.module.rate.entity.Channel;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

/** Bảng lãi suất hôm nay: hàng là ngân hàng, cột là kỳ hạn (tháng). */
public record DepositRateTableResponse(
        LocalDate rateDate,
        LocalDate previousDate,
        Channel channel,
        List<Integer> terms,
        List<Row> rows
) {

    /** {@code cells} theo kỳ hạn; kỳ hạn ngân hàng không niêm yết thì không có khóa. */
    public record Row(String ticker, String shortName, Map<Integer, Cell> cells) {
    }

    /** {@code change}: điểm % so với ngày liền trước, rỗng nếu không so được. */
    public record Cell(BigDecimal rate, BigDecimal change) {
    }
}
