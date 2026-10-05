package vn.kltn.bankadvisor.module.rate.service;

import vn.kltn.bankadvisor.module.rate.entity.Channel;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Map;
import java.util.Optional;

/**
 * Lãi suất tiết kiệm của ngày mới nhất và ngày liền trước (để tính thay đổi).
 * Dùng chung cho bảng lãi suất, trang gửi tiết kiệm, trang tổng quan và thông báo.
 */
public record RateSnapshot(
        LocalDate date,
        LocalDate previousDate,
        Map<Key, BigDecimal> current,
        Map<Key, BigDecimal> previous
) {

    public record Key(String ticker, int termMonths, Channel channel) {
    }

    public static RateSnapshot empty() {
        return new RateSnapshot(null, null, Map.of(), Map.of());
    }

    public boolean isEmpty() {
        return current.isEmpty();
    }

    public Optional<BigDecimal> rate(String ticker, int termMonths, Channel channel) {
        return Optional.ofNullable(current.get(new Key(ticker, termMonths, channel)));
    }

    /** Thay đổi so với ngày liền trước (điểm %); rỗng nếu một trong hai ngày không có số. */
    public Optional<BigDecimal> change(String ticker, int termMonths, Channel channel) {
        Key key = new Key(ticker, termMonths, channel);
        BigDecimal now = current.get(key);
        BigDecimal before = previous.get(key);
        return now == null || before == null ? Optional.empty() : Optional.of(now.subtract(before));
    }
}
