package vn.kltn.bankadvisor.module.app.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;

import java.time.LocalDate;

/** Điểm ứng dụng ngân hàng trên kho ứng dụng tại ngày chụp (app_store.csv). */
@Entity
@Immutable
@Table(name = "app_store_snapshot")
public class AppStoreSnapshot {

    @Id
    private Long id;

    @Column(name = "ticker", nullable = false)
    private String ticker;

    @Enumerated(EnumType.STRING)
    @Column(name = "store", nullable = false)
    private AppStore store;

    @Column(name = "snapshot_date", nullable = false)
    private LocalDate snapshotDate;

    @Column(name = "app_name")
    private String appName;

    @Column(name = "score")
    private Double score;

    @Column(name = "ratings")
    private Long ratings;

    protected AppStoreSnapshot() {
    }

    public String getTicker() {
        return ticker;
    }

    public AppStore getStore() {
        return store;
    }

    public LocalDate getSnapshotDate() {
        return snapshotDate;
    }

    public String getAppName() {
        return appName;
    }

    public Double getScore() {
        return score;
    }

    public Long getRatings() {
        return ratings;
    }
}
