package vn.kltn.bankadvisor.module.rate.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;

import java.math.BigDecimal;

/**
 * Lãi suất cho vay bình quân ngân hàng tự công bố theo tháng. Đây là bình quân toàn danh mục,
 * không phải lãi suất một khách hàng cụ thể được duyệt. Nạp từ lending_rates.csv.
 */
@Entity
@Immutable
@Table(name = "lending_rate")
public class LendingRate {

    @Id
    private Long id;

    /** Tháng dạng YYYY-MM. */
    @Column(name = "rate_month", nullable = false)
    private String month;

    @Column(name = "ticker", nullable = false)
    private String ticker;

    @Column(name = "lending_avg_percent", nullable = false)
    private BigDecimal lendingAvgPercent;

    @Column(name = "deposit_avg_percent")
    private BigDecimal depositAvgPercent;

    @Column(name = "source_url")
    private String sourceUrl;

    protected LendingRate() {
    }

    public String getMonth() {
        return month;
    }

    public String getTicker() {
        return ticker;
    }

    public BigDecimal getLendingAvgPercent() {
        return lendingAvgPercent;
    }

    public BigDecimal getDepositAvgPercent() {
        return depositAvgPercent;
    }

    public String getSourceUrl() {
        return sourceUrl;
    }
}
