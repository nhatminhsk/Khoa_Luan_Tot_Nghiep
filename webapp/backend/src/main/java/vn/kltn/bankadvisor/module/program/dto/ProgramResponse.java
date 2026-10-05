package vn.kltn.bankadvisor.module.program.dto;

import vn.kltn.bankadvisor.module.program.entity.ProgramCategory;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

/** Một chương trình tín dụng chính sách, các ngân hàng tham gia và lãi suất ưu đãi theo giai đoạn. */
public record ProgramResponse(
        String code,
        String name,
        ProgramCategory category,
        List<String> participatingTickers,
        LocalDate listAsOf,
        List<RateTerm> rates
) {

    /** {@code current}: giai đoạn đang hiệu lực hôm nay. */
    public record RateTerm(String borrowerGroup, LocalDate validFrom, LocalDate validTo, BigDecimal ratePercent,
                           BigDecimal spreadMin, BigDecimal spreadMax, boolean current) {
    }
}
