package vn.kltn.bankadvisor.module.indicator.dto;

import java.util.List;
import java.util.Map;

/**
 * Số gần nhất của mỗi ngân hàng cho từng chỉ tiêu, chỉ lấy số trong 4 quý cuối (cũ hơn thì để trống).
 * Dùng cho trang danh sách ngân hàng và trang so sánh.
 */
public record IndicatorSnapshotResponse(String latestPeriod, List<IndicatorResponse> indicators, List<Row> rows) {

    public record Row(String ticker, String shortName, Map<String, Cell> values) {
    }

    public record Cell(double value, String period) {
    }
}
