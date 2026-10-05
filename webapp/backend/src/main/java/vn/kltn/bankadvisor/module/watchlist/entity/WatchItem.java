package vn.kltn.bankadvisor.module.watchlist.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.math.BigDecimal;
import java.time.Instant;

/** Một ngân hàng trong danh sách theo dõi của người dùng, kèm ngưỡng báo khi lãi suất đổi. */
@Entity
@Table(name = "watch_item")
public class WatchItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "ticker", nullable = false)
    private String ticker;

    /** Báo khi lãi suất một kỳ hạn thay đổi từ mức này trở lên (điểm %). */
    @Column(name = "rate_threshold", nullable = false)
    private BigDecimal rateThreshold;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    protected WatchItem() {
    }

    public static WatchItem create(long userId, String ticker, BigDecimal threshold, Instant now) {
        WatchItem item = new WatchItem();
        item.userId = userId;
        item.ticker = ticker;
        item.rateThreshold = threshold;
        item.createdAt = now;
        return item;
    }

    public void changeThreshold(BigDecimal threshold) {
        this.rateThreshold = threshold;
    }

    public Long getId() {
        return id;
    }

    public Long getUserId() {
        return userId;
    }

    public String getTicker() {
        return ticker;
    }

    public BigDecimal getRateThreshold() {
        return rateThreshold;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}
