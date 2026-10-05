package vn.kltn.bankadvisor.module.app.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;

/** Điểm review theo khía cạnh do mô hình NLP tính (app_aspects.csv). Rỗng cho tới khi mô hình chốt. */
@Entity
@Immutable
@Table(name = "app_aspect_score")
public class AppAspectScore {

    @Id
    private Long id;

    @Column(name = "ticker", nullable = false)
    private String ticker;

    @Column(name = "period", nullable = false)
    private String period;

    @Column(name = "aspect", nullable = false)
    private String aspect;

    @Column(name = "score", nullable = false)
    private double score;

    @Column(name = "n_reviews", nullable = false)
    private int reviewCount;

    protected AppAspectScore() {
    }

    public String getTicker() {
        return ticker;
    }

    public String getPeriod() {
        return period;
    }

    public String getAspect() {
        return aspect;
    }

    public double getScore() {
        return score;
    }

    public int getReviewCount() {
        return reviewCount;
    }
}
