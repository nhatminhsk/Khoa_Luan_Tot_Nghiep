package vn.kltn.bankadvisor.module.indicator.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;

/** Danh mục chỉ tiêu tài chính hiển thị trên giao diện (nhóm theo CAMELS). Nạp từ indicators.csv. */
@Entity
@Immutable
@Table(name = "indicator")
public class Indicator {

    @Id
    @Column(name = "code")
    private String code;

    @Column(name = "name", nullable = false)
    private String name;

    /** C, A, M, E, L theo CAMELS; G là quy mô và tăng trưởng. */
    @Column(name = "camels_group", nullable = false)
    private String camelsGroup;

    @Enumerated(EnumType.STRING)
    @Column(name = "unit", nullable = false)
    private IndicatorUnit unit;

    @Enumerated(EnumType.STRING)
    @Column(name = "direction", nullable = false)
    private IndicatorDirection direction;

    @Column(name = "description")
    private String description;

    @Column(name = "display_order", nullable = false)
    private int displayOrder;

    protected Indicator() {
    }

    public String getCode() {
        return code;
    }

    public String getName() {
        return name;
    }

    public String getCamelsGroup() {
        return camelsGroup;
    }

    public IndicatorUnit getUnit() {
        return unit;
    }

    public IndicatorDirection getDirection() {
        return direction;
    }

    public String getDescription() {
        return description;
    }

    public int getDisplayOrder() {
        return displayOrder;
    }
}
