package vn.kltn.bankadvisor.module.watchlist.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.PageRequest;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;
import vn.kltn.bankadvisor.common.config.AppProperties;
import vn.kltn.bankadvisor.common.config.TimeConfig;
import vn.kltn.bankadvisor.common.mail.EmailAddresses;
import vn.kltn.bankadvisor.common.mail.EmailGateway;
import vn.kltn.bankadvisor.common.mail.EmailLayout;
import vn.kltn.bankadvisor.common.mail.EmailMessage;
import vn.kltn.bankadvisor.module.user.entity.AppUser;
import vn.kltn.bankadvisor.module.user.repository.AppUserRepository;
import vn.kltn.bankadvisor.module.watchlist.entity.Notification;
import vn.kltn.bankadvisor.module.watchlist.repository.NotificationRepository;

import java.time.Clock;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * Gửi hàng đợi email thông báo theo lịch ({@code app.mail.dispatch-delay}, mặc định mỗi phút).
 * <p>
 * Mỗi lượt: đọc các thông báo chờ gửi đã tới hạn, gom theo người nhận (mỗi người một email), gửi, rồi ghi kết quả.
 * Việc gửi SMTP nằm ngoài transaction, nên máy chủ thư chậm không giữ khóa CSDL. Gửi lỗi thì thử lại sau
 * {@code retry-backoff × số lần đã thử}, tối đa {@code max-attempts} lần; thông báo vẫn luôn còn trong ứng dụng.
 * <p>
 * Thiết kế cho một tiến trình backend (synchronized chống hai lượt chạy chồng nhau). Chạy nhiều bản thì cần
 * khóa phân tán (ví dụ ShedLock) hoặc {@code SELECT ... FOR UPDATE SKIP LOCKED} trên PostgreSQL.
 */
@Component
public class NotificationEmailDispatcher {

    private static final Logger log = LoggerFactory.getLogger(NotificationEmailDispatcher.class);
    private static final int BATCH_SIZE = 200;
    private static final DateTimeFormatter VN_TIME = DateTimeFormatter.ofPattern("HH:mm dd/MM/yyyy")
            .withZone(TimeConfig.VIETNAM);

    private final NotificationRepository notificationRepository;
    private final AppUserRepository userRepository;
    private final EmailGateway emailGateway;
    private final TransactionTemplate transactions;
    private final AppProperties.Mail mail;
    private final Clock clock;

    public NotificationEmailDispatcher(NotificationRepository notificationRepository, AppUserRepository userRepository,
                                       EmailGateway emailGateway, TransactionTemplate transactions,
                                       AppProperties properties, Clock clock) {
        this.notificationRepository = notificationRepository;
        this.userRepository = userRepository;
        this.emailGateway = emailGateway;
        this.transactions = transactions;
        this.mail = properties.mail();
        this.clock = clock;
    }

    /** Kết quả một lượt quét hàng đợi. */
    public record DispatchResult(int emailsSent, int emailsFailed, int notificationsSkipped) {
    }

    /** Một email gửi cho một người, gồm một hay nhiều thông báo. */
    record Digest(String to, String displayName, List<Item> items) {

        List<Long> ids() {
            return items.stream().map(Item::id).toList();
        }
    }

    record Item(long id, String title, String body, Instant createdAt) {
    }

    private record Batch(List<Digest> digests, int skipped) {
    }

    @Scheduled(fixedDelayString = "${app.mail.dispatch-delay:60s}", initialDelayString = "${app.mail.dispatch-delay:60s}")
    public void scheduled() {
        if (!emailGateway.isEnabled()) {
            return;
        }
        try {
            dispatchPending();
        } catch (RuntimeException e) {
            log.warn("Quét hàng đợi email lỗi: {}", e.getMessage(), e);
        }
    }

    public synchronized DispatchResult dispatchPending() {
        Batch batch = transactions.execute(status -> collect(clock.instant()));
        if (batch == null || (batch.digests().isEmpty() && batch.skipped() == 0)) {
            return new DispatchResult(0, 0, 0);
        }
        int sent = 0;
        int failed = 0;
        for (Digest digest : batch.digests()) {
            try {
                emailGateway.send(compose(digest, mail));
                transactions.executeWithoutResult(status -> notificationRepository.findAllById(digest.ids())
                        .forEach(n -> n.markEmailed(clock.instant())));
                sent++;
            } catch (RuntimeException e) {
                String error = e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage();
                transactions.executeWithoutResult(status -> notificationRepository.findAllById(digest.ids())
                        .forEach(n -> n.recordEmailFailure(error, clock.instant(), mail.maxAttempts(), mail.retryBackoff())));
                failed++;
                log.warn("Gửi email thông báo tới {} lỗi: {}", EmailAddresses.mask(digest.to()), error);
            }
        }
        log.info("Hàng đợi email: gửi {} thư, lỗi {} thư, bỏ qua {} thông báo", sent, failed, batch.skipped());
        return new DispatchResult(sent, failed, batch.skipped());
    }

    /** Trong transaction: lấy thông báo tới hạn, bỏ những cái không cần gửi nữa, gom phần còn lại theo người. */
    private Batch collect(Instant now) {
        List<Notification> due = notificationRepository.findDueEmails(now, PageRequest.of(0, BATCH_SIZE));
        if (due.isEmpty()) {
            return new Batch(List.of(), 0);
        }
        Map<Long, List<Notification>> byUser = due.stream().collect(Collectors.groupingBy(
                Notification::getUserId, LinkedHashMap::new, Collectors.toList()));
        Map<Long, AppUser> users = userRepository.findAllById(byUser.keySet()).stream()
                .collect(Collectors.toMap(AppUser::getId, Function.identity()));
        List<Digest> digests = new ArrayList<>();
        int skipped = 0;
        for (Map.Entry<Long, List<Notification>> entry : byUser.entrySet()) {
            AppUser user = users.get(entry.getKey());
            List<Item> items = new ArrayList<>();
            for (Notification n : entry.getValue()) {
                // Người dùng đã tắt email, hoặc đã đọc thông báo trong ứng dụng trước khi tới lượt gửi.
                if (user == null || !user.wantsEmail() || n.getReadAt() != null) {
                    n.skipEmail();
                    skipped++;
                } else {
                    items.add(new Item(n.getId(), n.getTitle(), n.getBody(), n.getCreatedAt()));
                }
            }
            if (!items.isEmpty()) {
                digests.add(new Digest(user.getEmail(), user.getDisplayName(), List.copyOf(items)));
            }
        }
        return new Batch(digests, skipped);
    }

    static EmailMessage compose(Digest digest, AppProperties.Mail mail) {
        List<Item> items = digest.items();
        String subject = items.size() == 1 ? items.getFirst().title() : items.size() + " thông báo mới từ BankAdvisor";
        String inbox = mail.link("/watchlist#thong-bao");
        String settings = mail.link("/watchlist#cai-dat-thong-bao");

        StringBuilder text = new StringBuilder("Chào ").append(digest.displayName()).append(",\n\n");
        StringBuilder html = new StringBuilder(EmailLayout.paragraph("Chào " + digest.displayName() + ","));
        for (Item item : items) {
            String time = VN_TIME.format(item.createdAt());
            text.append("• ").append(item.title()).append('\n')
                    .append("  ").append(item.body()).append('\n')
                    .append("  (").append(time).append(")\n\n");
            html.append(EmailLayout.item(item.title(), item.body(), time));
        }
        text.append("Xem trong ứng dụng: ").append(inbox).append("\n\n")
                .append("Bạn nhận email này vì đã chọn nhận thông báo qua email. Đổi hoặc tắt tại: ").append(settings).append('\n')
                .append("Số liệu chỉ để tham khảo; lãi suất thực tế do ngân hàng quyết định khi giao dịch.\n");
        html.append(EmailLayout.button(inbox, "Xem trong ứng dụng"));
        String footer = EmailLayout.muted("Bạn nhận email này vì đã chọn nhận thông báo qua email.")
                + "<p style=\"margin:0 0 8px;font-size:13px;color:#6b7280\">"
                + EmailLayout.link(settings, "Đổi hoặc tắt thông báo") + "</p>"
                + EmailLayout.muted("Số liệu chỉ để tham khảo; lãi suất thực tế do ngân hàng quyết định khi giao dịch.");
        return new EmailMessage(digest.to(), subject, text.toString(), EmailLayout.page(html.toString(), footer));
    }
}
