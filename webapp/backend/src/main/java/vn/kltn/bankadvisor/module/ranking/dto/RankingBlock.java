package vn.kltn.bankadvisor.module.ranking.dto;

import vn.kltn.bankadvisor.common.api.ResultStatus;
import vn.kltn.bankadvisor.module.rate.entity.Channel;
import vn.kltn.bankadvisor.module.ranking.entity.Purpose;
import java.util.List;

/**
 * Khối xếp hạng trả về cho giao diện.
 *
 * @param personalized   true nếu đã tính lại theo trọng số của người dùng; false là bảng pipeline tính sẵn
 * @param termMonths     kỳ hạn của bảng gửi (null với vay)
 * @param channel        kênh của bảng gửi (null với vay)
 * @param amountVnd      mốc tiền của bảng gửi đã chọn theo số tiền người gửi (null = trọng số mặc định)
 * @param ratesAsOf      ngày lãi gửi (YYYY-MM-DD) hoặc tháng lãi vay (YYYY-MM) của ảnh chụp đã xếp
 * @param uninsuredShare phần tiền không được bảo hiểm tiền gửi chi trả ở mốc tiền đó (0–1)
 * @param safetyWeight   trọng số nhóm an toàn tại tâm (0–1) sau khi nhân phần không được bảo hiểm
 * @param reason         lý do khi NOT_AVAILABLE: NOT_COMPUTED (pipeline chưa ghi) | TERM_NOT_RANKED (kỳ hạn × kênh
 *                       không có trong dữ liệu xếp hạng)
 */
public record RankingBlock(
        ResultStatus status,
        Purpose purpose,
        String asOfPeriod,
        String methodVersion,
        boolean personalized,
        Integer termMonths,
        Channel channel,
        Long amountVnd,
        String ratesAsOf,
        Double uninsuredShare,
        Double safetyWeight,
        String reason,
        List<Item> items
) {

    public static final String NOT_COMPUTED = "NOT_COMPUTED";
    public static final String TERM_NOT_RANKED = "TERM_NOT_RANKED";

    public static RankingBlock notAvailable(Purpose purpose, String reason) {
        return new RankingBlock(ResultStatus.NOT_AVAILABLE, purpose, null, null, false, null, null, null, null, null,
                null, reason, List.of());
    }

    /**
     * {@code rankLow}..{@code rankHigh}: khoảng hạng (p05 tốt nhất .. p95 tệ nhất qua 4 thuật toán) khi trọng số đổi.
     * {@code shareTop1}, {@code shareTop3}: tần suất đứng đầu / lọt top 3 trong mô phỏng, không phải xác suất.
     */
    public record Item(
            int rank,
            Integer rankLow,
            Integer rankHigh,
            String ticker,
            String shortName,
            Double score,
            String groupLabel,
            String topPositive,
            String topNegative,
            Double shareTop1,
            Double shareTop3
    ) {
    }
}
