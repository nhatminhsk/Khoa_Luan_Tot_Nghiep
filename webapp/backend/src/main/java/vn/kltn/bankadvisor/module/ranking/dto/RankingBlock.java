package vn.kltn.bankadvisor.module.ranking.dto;

import vn.kltn.bankadvisor.common.api.ResultStatus;
import vn.kltn.bankadvisor.module.ranking.entity.Purpose;

import java.util.List;

/**
 * Khối xếp hạng trả về cho giao diện.
 *
 * @param personalized true nếu đã tính lại theo trọng số của người dùng; false là xếp hạng mặc định
 */
public record RankingBlock(
        ResultStatus status,
        Purpose purpose,
        String asOfPeriod,
        String methodVersion,
        boolean personalized,
        List<Item> items
) {

    public static RankingBlock notAvailable(Purpose purpose) {
        return new RankingBlock(ResultStatus.NOT_AVAILABLE, purpose, null, null, false, List.of());
    }

    /** {@code rankLow}..{@code rankHigh}: khoảng hạng (tốt nhất..tệ nhất) khi dữ liệu thiếu hoặc trọng số đổi. */
    public record Item(
            int rank,
            Integer rankLow,
            Integer rankHigh,
            String ticker,
            String shortName,
            Double score,
            String groupLabel,
            String topPositive,
            String topNegative
    ) {
    }
}
