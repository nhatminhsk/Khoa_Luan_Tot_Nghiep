package vn.kltn.bankadvisor.module.watchlist.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Duration;
import java.time.Instant;

/**
 * Lịch sử thông báo trong ứng dụng, kiêm hàng đợi gửi email (các cột {@code email_*}).
 * {@code refKey} chống tạo trùng khi nạp lại cùng một dữ liệu.
 */
@Entity
@Table(name = "notification")
public class Notification {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Enumerated(EnumType.STRING)
    @Column(name = "type", nullable = false)
    private NotificationType type;

    @Column(name = "ticker")
    private String ticker;

    @Column(name = "title", nullable = false)
    private String title;

    @Column(name = "body", nullable = false)
    private String body;

    @Column(name = "ref_key", nullable = false)
    private String refKey;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "read_at")
    private Instant readAt;

    @Enumerated(EnumType.STRING)
    @Column(name = "email_status")
    private EmailStatus emailStatus;

    @Column(name = "email_attempts", nullable = false)
    private int emailAttempts;

    @Column(name = "email_next_attempt_at")
    private Instant emailNextAttemptAt;

    @Column(name = "email_last_error")
    private String emailLastError;

    @Column(name = "emailed_at")
    private Instant emailedAt;

    protected Notification() {
    }

    /**
     * @param queueEmail true khi người nhận đang chọn kênh EMAIL (đã xác minh): thông báo vào hàng đợi gửi email
     */
    public static Notification create(long userId, NotificationType type, String ticker, String title, String body,
                                      String refKey, Instant now, boolean queueEmail) {
        Notification n = new Notification();
        n.userId = userId;
        n.type = type;
        n.ticker = ticker;
        n.title = title;
        n.body = body;
        n.refKey = refKey;
        n.createdAt = now;
        if (queueEmail) {
            n.emailStatus = EmailStatus.PENDING;
            n.emailNextAttemptAt = now;
        }
        return n;
    }

    public void markRead(Instant now) {
        if (readAt == null) {
            readAt = now;
        }
    }

    public void markEmailed(Instant now) {
        emailStatus = EmailStatus.SENT;
        emailAttempts++;
        emailedAt = now;
        emailNextAttemptAt = null;
        emailLastError = null;
    }

    /**
     * Ghi một lần gửi lỗi. Còn lượt thì hẹn lần sau, mỗi lần chờ lâu hơn ({@code backoff × số lần đã thử});
     * hết lượt thì chuyển FAILED.
     */
    public void recordEmailFailure(String error, Instant now, int maxAttempts, Duration backoff) {
        emailAttempts++;
        emailLastError = error == null ? null : error.substring(0, Math.min(error.length(), 500));
        if (emailAttempts >= maxAttempts) {
            emailStatus = EmailStatus.FAILED;
            emailNextAttemptAt = null;
        } else {
            emailNextAttemptAt = now.plus(backoff.multipliedBy(emailAttempts));
        }
    }

    public void skipEmail() {
        emailStatus = EmailStatus.SKIPPED;
        emailNextAttemptAt = null;
    }

    public Long getId() {
        return id;
    }

    public Long getUserId() {
        return userId;
    }

    public NotificationType getType() {
        return type;
    }

    public String getTicker() {
        return ticker;
    }

    public String getTitle() {
        return title;
    }

    public String getBody() {
        return body;
    }

    public String getRefKey() {
        return refKey;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getReadAt() {
        return readAt;
    }

    public EmailStatus getEmailStatus() {
        return emailStatus;
    }

    public int getEmailAttempts() {
        return emailAttempts;
    }

    public Instant getEmailNextAttemptAt() {
        return emailNextAttemptAt;
    }

    public String getEmailLastError() {
        return emailLastError;
    }

    public Instant getEmailedAt() {
        return emailedAt;
    }
}
