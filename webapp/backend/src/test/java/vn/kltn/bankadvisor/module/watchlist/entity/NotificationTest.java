package vn.kltn.bankadvisor.module.watchlist.entity;

import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.time.Instant;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class NotificationTest {

    private static final Instant NOW = Instant.parse("2026-09-29T09:00:00Z");
    private static final Duration BACKOFF = Duration.ofMinutes(5);

    @Test
    void onlyEmailSubscribersAreQueued() {
        assertNull(create(false).getEmailStatus());
        Notification queued = create(true);
        assertEquals(EmailStatus.PENDING, queued.getEmailStatus());
        assertEquals(NOW, queued.getEmailNextAttemptAt());
    }

    @Test
    void failedDeliveryWaitsLongerEachTimeThenGivesUp() {
        Notification n = create(true);

        n.recordEmailFailure("Connection refused", NOW, 3, BACKOFF);
        assertEquals(EmailStatus.PENDING, n.getEmailStatus());
        assertEquals(NOW.plus(Duration.ofMinutes(5)), n.getEmailNextAttemptAt());

        n.recordEmailFailure("Connection refused", NOW, 3, BACKOFF);
        assertEquals(NOW.plus(Duration.ofMinutes(10)), n.getEmailNextAttemptAt());

        n.recordEmailFailure("x".repeat(800), NOW, 3, BACKOFF);
        assertEquals(EmailStatus.FAILED, n.getEmailStatus());
        assertEquals(3, n.getEmailAttempts());
        assertNull(n.getEmailNextAttemptAt());
        assertEquals(500, n.getEmailLastError().length());
    }

    @Test
    void successClearsPreviousError() {
        Notification n = create(true);
        n.recordEmailFailure("timeout", NOW, 3, BACKOFF);
        n.markEmailed(NOW.plusSeconds(300));
        assertEquals(EmailStatus.SENT, n.getEmailStatus());
        assertEquals(2, n.getEmailAttempts());
        assertNull(n.getEmailLastError());
        assertEquals(NOW.plusSeconds(300), n.getEmailedAt());
    }

    private static Notification create(boolean queueEmail) {
        return Notification.create(1L, NotificationType.RATE_CHANGE, "ACB", "ACB thay đổi lãi suất tiết kiệm",
                "Ngày 27/09/2026: 12 tháng online 5,90% → 6,10% (+0,20).", "RATE:ACB:2026-09-27", NOW, queueEmail);
    }
}
