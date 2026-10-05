package vn.kltn.bankadvisor.module.app.dto;

import vn.kltn.bankadvisor.common.api.ResultStatus;
import vn.kltn.bankadvisor.module.app.entity.AppStore;

import java.time.LocalDate;
import java.util.List;

/** Trải nghiệm ứng dụng của một ngân hàng: điểm trên kho ứng dụng, review theo tháng, khía cạnh (NLP). */
public record AppExperienceResponse(
        String ticker,
        List<StoreScore> stores,
        List<MonthlyPoint> monthly,
        AspectBlock aspects
) {

    public record StoreScore(AppStore store, String appName, Double score, Long ratings, LocalDate snapshotDate) {
    }

    /** {@code usable = false}: tháng quá ít review hoặc bị spam, không nên đọc điểm. */
    public record MonthlyPoint(String month, int reviewCount, Double meanScore, Double oneStarShare,
                               Double fiveStarShare, boolean usable) {
    }

    public record AspectBlock(ResultStatus status, List<AspectPoint> items) {
    }

    public record AspectPoint(String period, String aspect, double score, int reviewCount) {
    }
}
