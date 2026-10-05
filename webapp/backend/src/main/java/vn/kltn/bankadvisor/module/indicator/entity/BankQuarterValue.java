package vn.kltn.bankadvisor.module.indicator.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;

import java.time.LocalDate;

/** Giá trị một chỉ tiêu của một ngân hàng trong một quý (dạng dài). Nạp từ bank_quarterly.csv. */
@Entity
@Immutable
@Table(name = "bank_quarter_value")
public class BankQuarterValue {

    @Id
    private Long id;

    @Column(name = "ticker", nullable = false)
    private String ticker;

    /** Kỳ dạng YYYY-Qn. */
    @Column(name = "period", nullable = false)
    private String period;

    @Column(name = "period_end", nullable = false)
    private LocalDate periodEnd;

    @Column(name = "indicator_code", nullable = false)
    private String indicatorCode;

    @Column(name = "val", nullable = false)
    private double value;

    protected BankQuarterValue() {
    }

    public String getTicker() {
        return ticker;
    }

    public String getPeriod() {
        return period;
    }

    public LocalDate getPeriodEnd() {
        return periodEnd;
    }

    public String getIndicatorCode() {
        return indicatorCode;
    }

    public double getValue() {
        return value;
    }
}
