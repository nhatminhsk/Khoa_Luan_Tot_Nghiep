package vn.kltn.bankadvisor.module.ranking.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;

/** Xếp hạng mặc định do thuật toán tính (rankings.csv). Rỗng cho tới khi mô hình xếp hạng chốt. */
@Entity
@Immutable
@Table(name = "ranking_result")
public class RankingResult {

    @Id
    private Long id;

    @Column(name = "as_of_period", nullable = false)
    private String asOfPeriod;

    @Enumerated(EnumType.STRING)
    @Column(name = "purpose", nullable = false)
    private Purpose purpose;

    @Column(name = "ticker", nullable = false)
    private String ticker;

    @Column(name = "rank_value", nullable = false)
    private int rank;

    @Column(name = "rank_low")
    private Integer rankLow;

    @Column(name = "rank_high")
    private Integer rankHigh;

    @Column(name = "score")
    private Double score;

    @Column(name = "group_label")
    private String groupLabel;

    @Column(name = "top_positive")
    private String topPositive;

    @Column(name = "top_negative")
    private String topNegative;

    @Column(name = "method_version")
    private String methodVersion;

    protected RankingResult() {
    }

    public String getAsOfPeriod() {
        return asOfPeriod;
    }

    public Purpose getPurpose() {
        return purpose;
    }

    public String getTicker() {
        return ticker;
    }

    public int getRank() {
        return rank;
    }

    public Integer getRankLow() {
        return rankLow;
    }

    public Integer getRankHigh() {
        return rankHigh;
    }

    public Double getScore() {
        return score;
    }

    public String getGroupLabel() {
        return groupLabel;
    }

    public String getTopPositive() {
        return topPositive;
    }

    public String getTopNegative() {
        return topNegative;
    }

    public String getMethodVersion() {
        return methodVersion;
    }
}
