package vn.kltn.bankadvisor.module.indicator.dto;

import java.util.List;

/** Một chỉ tiêu, nhiều ngân hàng, trên cùng trục quý. Các mảng {@code values} thẳng hàng với {@code periods}. */
public record IndicatorComparisonResponse(
        IndicatorResponse indicator,
        List<String> periods,
        List<BankSeries> banks,
        List<Double> median
) {

    public record BankSeries(String ticker, String shortName, List<Double> values) {
    }
}
