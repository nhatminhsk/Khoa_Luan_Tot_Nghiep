package vn.kltn.bankadvisor.module.app.dto;

/** Điểm ứng dụng của một ngân hàng trên hai kho; trống nếu kho đó không có dữ liệu. */
public record AppScoreSummary(
        String ticker,
        Double googlePlayScore,
        Long googlePlayRatings,
        Double appStoreScore,
        Long appStoreRatings
) {

    /** Điểm dùng để hiển thị nhanh: ưu tiên Google Play (nhiều lượt chấm hơn), không có thì App Store. */
    public Double preferredScore() {
        return googlePlayScore != null ? googlePlayScore : appStoreScore;
    }
}
