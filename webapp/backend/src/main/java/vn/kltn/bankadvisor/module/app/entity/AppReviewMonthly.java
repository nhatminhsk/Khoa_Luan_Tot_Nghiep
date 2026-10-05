package vn.kltn.bankadvisor.module.app.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;

/** Tổng hợp review Google Play theo tháng (app_reviews_monthly.csv). */
@Entity
@Immutable
@Table(name = "app_review_monthly")
public class AppReviewMonthly {

    @Id
    private Long id;

    @Column(name = "ticker", nullable = false)
    private String ticker;

    /** Tháng dạng YYYY-MM. */
    @Column(name = "review_month", nullable = false)
    private String month;

    @Column(name = "n_reviews", nullable = false)
    private int reviewCount;

    @Column(name = "mean_score")
    private Double meanScore;

    @Column(name = "pct_1star")
    private Double oneStarShare;

    @Column(name = "pct_5star")
    private Double fiveStarShare;

    /** false khi tháng có quá ít review hoặc bị spam đánh giá — không nên đọc điểm tháng đó. */
    @Column(name = "usable", nullable = false)
    private boolean usable;

    protected AppReviewMonthly() {
    }

    public String getTicker() {
        return ticker;
    }

    public String getMonth() {
        return month;
    }

    public int getReviewCount() {
        return reviewCount;
    }

    public Double getMeanScore() {
        return meanScore;
    }

    public Double getOneStarShare() {
        return oneStarShare;
    }

    public Double getFiveStarShare() {
        return fiveStarShare;
    }

    public boolean isUsable() {
        return usable;
    }
}
