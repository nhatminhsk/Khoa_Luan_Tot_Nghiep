package vn.kltn.bankadvisor.module.macro.dto;

import vn.kltn.bankadvisor.module.macro.entity.CpiMonth;

import java.util.List;

/**
 * Lạm phát theo tháng, để tính lãi suất thực: lãi niêm yết − lạm phát so cùng kỳ (xấp xỉ Fisher).
 *
 * @param latest    tháng mới nhất đã công bố (null khi chưa nạp dữ liệu)
 * @param sourceUrl thông cáo của Tổng cục Thống kê cho tháng mới nhất
 * @param series    toàn bộ chuỗi, tháng tăng dần
 */
public record InflationResponse(Point latest, String sourceUrl, List<Point> series) {

    /**
     * @param yoyPercent so với cùng tháng năm trước (%)
     * @param momPercent so với tháng trước (%)
     */
    public record Point(String month, double yoyPercent, Double momPercent) {

        public static Point from(CpiMonth m) {
            return new Point(m.getMonth(), m.getYoyPercent(), m.getMomPercent());
        }
    }
}
