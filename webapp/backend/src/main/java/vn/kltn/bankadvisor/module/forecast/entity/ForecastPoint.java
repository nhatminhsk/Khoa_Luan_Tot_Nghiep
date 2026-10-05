package vn.kltn.bankadvisor.module.forecast.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;

/** Một điểm dự báo (forecasts.csv). Rỗng cho tới khi mô hình dự báo chốt. */
@Entity
@Immutable
@Table(name = "forecast_point")
public class ForecastPoint {

    @Id
    private Long id;

    @Column(name = "ticker", nullable = false)
    private String ticker;

    @Column(name = "indicator_code", nullable = false)
    private String indicatorCode;

    @Column(name = "origin_period", nullable = false)
    private String originPeriod;

    @Column(name = "target_period", nullable = false)
    private String targetPeriod;

    @Column(name = "horizon", nullable = false)
    private int horizon;

    @Column(name = "val", nullable = false)
    private double value;

    @Column(name = "lower_bound")
    private Double lower;

    @Column(name = "upper_bound")
    private Double upper;

    @Column(name = "naive_value")
    private Double naiveValue;

    @Column(name = "method")
    private String method;

    protected ForecastPoint() {
    }

    public String getTicker() {
        return ticker;
    }

    public String getIndicatorCode() {
        return indicatorCode;
    }

    public String getOriginPeriod() {
        return originPeriod;
    }

    public String getTargetPeriod() {
        return targetPeriod;
    }

    public int getHorizon() {
        return horizon;
    }

    public double getValue() {
        return value;
    }

    public Double getLower() {
        return lower;
    }

    public Double getUpper() {
        return upper;
    }

    public Double getNaiveValue() {
        return naiveValue;
    }

    public String getMethod() {
        return method;
    }
}
