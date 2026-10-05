package vn.kltn.bankadvisor.module.indicator.dto;

import java.util.List;

/**
 * Chuỗi theo quý của mọi chỉ tiêu cho một ngân hàng, kèm trung vị 22 ngân hàng cùng quý.
 *
 * @param latestPeriod quý mới nhất có số trong toàn bộ dữ liệu
 */
public record BankIndicatorsResponse(String ticker, String latestPeriod, List<IndicatorSeries> indicators) {

    public record IndicatorSeries(IndicatorResponse indicator, List<Point> points, Latest latest) {
    }

    /** {@code value} rỗng nếu ngân hàng không có số quý đó. */
    public record Point(String period, Double value, Double median) {
    }

    /**
     * Số gần nhất của ngân hàng và thứ hạng trong các ngân hàng có số cùng quý.
     *
     * @param rank 1 là tốt nhất theo chiều của chỉ tiêu; với chỉ tiêu trung tính, 1 là lớn nhất
     */
    public record Latest(String period, double value, Double median, int rank, int bankCount) {
    }
}
