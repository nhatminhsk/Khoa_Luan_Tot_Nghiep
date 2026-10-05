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

/** Lãi suất tiết kiệm niêm yết theo ngày × ngân hàng × kỳ hạn × kênh. Nạp từ deposit_rates.csv. */
@Entity
@Immutable
@Table(name = "deposit_rate")
public class DepositRate {

    @Id
    private Long id;

    @Column(name = "rate_date", nullable = false)
    private LocalDate rateDate;

    @Column(name = "ticker", nullable = false)
    private String ticker;

    @Column(name = "term_months", nullable = false)
    private int termMonths;

    @Enumerated(EnumType.STRING)
    @Column(name = "channel", nullable = false)
    private Channel channel;

    @Column(name = "rate_percent", nullable = false)
    private BigDecimal ratePercent;

    @Column(name = "source")
    private String source;

    protected DepositRate() {
    }

    public LocalDate getRateDate() {
        return rateDate;
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

    public BigDecimal getRatePercent() {
        return ratePercent;
    }

    public String getSource() {
        return source;
    }
}
