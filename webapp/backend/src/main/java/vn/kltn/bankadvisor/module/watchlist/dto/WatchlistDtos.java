package vn.kltn.bankadvisor.module.watchlist.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import vn.kltn.bankadvisor.common.mail.MailMode;
import vn.kltn.bankadvisor.module.user.entity.NotifyChannel;
import vn.kltn.bankadvisor.module.watchlist.entity.Notification;
import vn.kltn.bankadvisor.module.watchlist.entity.NotificationType;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

/** DTO của module theo dõi và thông báo. */
public final class WatchlistDtos {

    private WatchlistDtos() {
    }

    public record AddWatchRequest(
            @NotBlank(message = "Chọn ngân hàng") String ticker,
            @DecimalMin(value = "0.05", message = "Ngưỡng tối thiểu 0,05 điểm %")
            @DecimalMax(value = "2.00", message = "Ngưỡng tối đa 2 điểm %") BigDecimal rateThreshold
    ) {
    }

    public record UpdateWatchRequest(
            @NotNull(message = "Nhập ngưỡng")
            @DecimalMin(value = "0.05", message = "Ngưỡng tối thiểu 0,05 điểm %")
            @DecimalMax(value = "2.00", message = "Ngưỡng tối đa 2 điểm %") BigDecimal rateThreshold
    ) {
    }

    /**
     * @param rate12mOnline lãi suất 12 tháng online hôm nay (để người dùng thấy ngay mức hiện tại)
     */
    public record WatchItemResponse(
            String ticker,
            String shortName,
            BigDecimal rateThreshold,
            BigDecimal rate12mOnline,
            BigDecimal change12mOnline,
            Instant createdAt
    ) {
    }

    public record NotificationSettingsRequest(
            boolean notifyRateChange,
            boolean notifyNewRanking,
            @NotNull(message = "Chọn kênh nhận thông báo") NotifyChannel channel
    ) {
    }

    /**
     * @param email         địa chỉ nhận thông báo (email đăng ký)
     * @param emailEnabled  hệ thống có bật gửi email không ({@code app.mail.mode} khác OFF)
     * @param emailVerified người dùng đã xác minh email chưa; kênh EMAIL cần cả hai điều kiện
     */
    public record NotificationSettingsResponse(
            boolean notifyRateChange,
            boolean notifyNewRanking,
            NotifyChannel channel,
            String email,
            boolean emailEnabled,
            boolean emailVerified
    ) {
    }

    /** @param emailedAt thời điểm đã gửi bản sao qua email (null nếu chỉ hiện trong ứng dụng) */
    public record NotificationResponse(
            long id,
            NotificationType type,
            String ticker,
            String title,
            String body,
            Instant createdAt,
            boolean read,
            Instant emailedAt
    ) {

        public static NotificationResponse from(Notification n) {
            return new NotificationResponse(n.getId(), n.getType(), n.getTicker(), n.getTitle(), n.getBody(),
                    n.getCreatedAt(), n.getReadAt() != null, n.getEmailedAt());
        }
    }

    public record UnreadCount(long unread) {
    }

    /** Tình trạng hàng đợi email cho trang Quản trị. */
    public record EmailQueueSummary(
            MailMode mode,
            long pending,
            long sent,
            long failed,
            long skipped,
            List<FailedEmail> recentFailures
    ) {
    }

    /** @param recipient email người nhận đã che bớt */
    public record FailedEmail(long notificationId, String recipient, String title, int attempts, String lastError,
                              Instant createdAt) {
    }

    /** Kết quả khi quản trị viên bấm "Gửi ngay". */
    public record DispatchResponse(int emailsSent, int emailsFailed, int notificationsSkipped) {
    }
}
