package vn.kltn.bankadvisor.module.dataset.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;

/** Nguồn dữ liệu, ngày cập nhật và độ phủ (datasets.csv) — hiện ở trang Tổng quan và Phương pháp. */
@Entity
@Immutable
@Table(name = "dataset_info")
public class DatasetInfo {

    @Id
    @Column(name = "dataset")
    private String dataset;

    @Column(name = "name", nullable = false)
    private String name;

    @Column(name = "source")
    private String source;

    /** DAILY, MONTHLY, QUARTERLY, SNAPSHOT, IRREGULAR. */
    @Column(name = "frequency", nullable = false)
    private String frequency;

    /** Ngày, tháng hoặc quý mới nhất có số (theo tần suất của nguồn). */
    @Column(name = "last_updated")
    private String lastUpdated;

    @Column(name = "row_count")
    private Integer rowCount;

    @Column(name = "coverage_note")
    private String coverageNote;

    protected DatasetInfo() {
    }

    public String getDataset() {
        return dataset;
    }

    public String getName() {
        return name;
    }

    public String getSource() {
        return source;
    }

    public String getFrequency() {
        return frequency;
    }

    public String getLastUpdated() {
        return lastUpdated;
    }

    public Integer getRowCount() {
        return rowCount;
    }

    public String getCoverageNote() {
        return coverageNote;
    }
}
