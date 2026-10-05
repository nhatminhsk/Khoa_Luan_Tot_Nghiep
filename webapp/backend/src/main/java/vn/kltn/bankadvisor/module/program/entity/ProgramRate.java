package vn.kltn.bankadvisor.module.program.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * Lãi suất ưu đãi của chương trình theo giai đoạn. Có chương trình ghi lãi suất cố định
 * ({@code ratePercent}), có chương trình chỉ ghi mức thấp hơn lãi bình quân ({@code spreadMin..spreadMax}).
 */
@Entity
@Immutable
@Table(name = "program_rate")
public class ProgramRate {

    @Id
    private Long id;

    @Column(name = "program_code", nullable = false)
    private String programCode;

    @Column(name = "borrower_group", nullable = false)
    private String borrowerGroup;

    @Column(name = "valid_from")
    private LocalDate validFrom;

    @Column(name = "valid_to")
    private LocalDate validTo;

    @Column(name = "rate_percent")
    private BigDecimal ratePercent;

    @Column(name = "spread_min")
    private BigDecimal spreadMin;

    @Column(name = "spread_max")
    private BigDecimal spreadMax;

    @Column(name = "source_url")
    private String sourceUrl;

    protected ProgramRate() {
    }

    public String getProgramCode() {
        return programCode;
    }

    public String getBorrowerGroup() {
        return borrowerGroup;
    }

    public LocalDate getValidFrom() {
        return validFrom;
    }

    public LocalDate getValidTo() {
        return validTo;
    }

    public BigDecimal getRatePercent() {
        return ratePercent;
    }

    public BigDecimal getSpreadMin() {
        return spreadMin;
    }

    public BigDecimal getSpreadMax() {
        return spreadMax;
    }

    public String getSourceUrl() {
        return sourceUrl;
    }

    public boolean isValidOn(LocalDate date) {
        return (validFrom == null || !date.isBefore(validFrom)) && (validTo == null || !date.isAfter(validTo));
    }
}
