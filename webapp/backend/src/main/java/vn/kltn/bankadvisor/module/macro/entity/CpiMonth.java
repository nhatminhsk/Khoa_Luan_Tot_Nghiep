package vn.kltn.bankadvisor.module.macro.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;

/** Lạm phát một tháng theo thông cáo của Tổng cục Thống kê. Nạp từ macro_cpi.csv, chỉ đọc. */
@Entity
@Immutable
@Table(name = "macro_cpi")
public class CpiMonth {

    /** Dạng "2026-08". */
    @Id
    @Column(name = "cpi_month")
    private String month;

    /** CPI so với cùng tháng năm trước (%). */
    @Column(name = "cpi_yoy_percent", nullable = false)
    private double yoyPercent;

    /** CPI so với tháng trước (%). */
    @Column(name = "cpi_mom_percent")
    private Double momPercent;

    @Column(name = "source_url")
    private String sourceUrl;

    protected CpiMonth() {
    }

    public String getMonth() {
        return month;
    }

    public double getYoyPercent() {
        return yoyPercent;
    }

    public Double getMomPercent() {
        return momPercent;
    }

    public String getSourceUrl() {
        return sourceUrl;
    }
}
