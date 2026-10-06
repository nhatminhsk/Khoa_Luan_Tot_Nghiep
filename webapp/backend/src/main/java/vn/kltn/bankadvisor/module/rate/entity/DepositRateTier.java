package vn.kltn.bankadvisor.module.rate.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * Một bậc lãi suất theo số tiền gửi (trên bậc thấp nhất) của ngân hàng × kỳ hạn × kênh. Nạp từ
 * deposit_rate_tiers.csv; chỉ áp khi lãi ngày mới nhất trong deposit_rate còn bằng {@code baseRatePercent}.
 */
@Entity
@Immutable
@Table(name = "deposit_rate_tier")
public class DepositRateTier {

    @Id
    private Long id;

    @Column(name = "ticker", nullable = false)
    private String ticker;

    @Column(name = "term_months", nullable = false)
    private int termMonths;

    @Enumerated(EnumType.STRING)
    @Column(name = "channel", nullable = false)
    private Channel channel;

    @Column(name = "min_amount_vnd", nullable = false)
    private long minAmountVnd;

    @Column(name = "rate_percent", nullable = false)
    private BigDecimal ratePercent;

    @Column(name = "base_rate_percent", nullable = false)
    private BigDecimal baseRatePercent;

    @Column(name = "tier_label", nullable = false)
    private String tierLabel;

    @Column(name = "valid_from")
    private LocalDate validFrom;

    @Column(name = "source")
    private String source;

    protected DepositRateTier() {
    }

    public String getTicker() {
        return ticker;
    }

    public int getTermMonths() {
        return termMonths;
    }

    public Channel getChannel() {
        return channel;
    }

    public long getMinAmountVnd() {
        return minAmountVnd;
    }

    public BigDecimal getRatePercent() {
        return ratePercent;
    }

    public BigDecimal getBaseRatePercent() {
        return baseRatePercent;
    }

    public String getTierLabel() {
        return tierLabel;
    }

    public LocalDate getValidFrom() {
        return validFrom;
    }

    public String getSource() {
        return source;
    }
}
