package vn.kltn.bankadvisor.module.ranking.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;
import vn.kltn.bankadvisor.module.rate.entity.Channel;

/**
 * Xếp hạng tổng hợp do pipeline tính (rankings.csv, serving/rankings.py). Gửi: một bảng mỗi kỳ hạn × kênh × mốc tiền
 * ({@code amountVnd} null = trọng số mặc định); vay: một bảng ({@code termMonths}, {@code channel} null).
 */
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

    @Column(name = "term_months")
    private Integer termMonths;

    @Enumerated(EnumType.STRING)
    @Column(name = "channel")
    private Channel channel;

    @Column(name = "amount_vnd")
    private Long amountVnd;

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

    @Column(name = "p_top1")
    private Double pTop1;

    @Column(name = "p_top3")
    private Double pTop3;

    @Column(name = "rates_as_of")
    private String ratesAsOf;

    @Column(name = "uninsured_share")
    private Double uninsuredShare;

    @Column(name = "safety_weight")
    private Double safetyWeight;

    protected RankingResult() {
    }

    public String getAsOfPeriod() {
        return asOfPeriod;
    }

    public Purpose getPurpose() {
        return purpose;
    }

    public Integer getTermMonths() {
        return termMonths;
    }

    public Channel getChannel() {
        return channel;
    }

    public Long getAmountVnd() {
        return amountVnd;
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

    public Double getPTop1() {
        return pTop1;
    }

    public Double getPTop3() {
        return pTop3;
    }

    public String getRatesAsOf() {
        return ratesAsOf;
    }

    public Double getUninsuredShare() {
        return uninsuredShare;
    }

    public Double getSafetyWeight() {
        return safetyWeight;
    }
}
