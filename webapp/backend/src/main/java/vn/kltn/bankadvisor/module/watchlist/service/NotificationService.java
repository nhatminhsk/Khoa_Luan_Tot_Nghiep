package vn.kltn.bankadvisor.module.watchlist.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.event.EventListener;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.api.PageResponse;
import vn.kltn.bankadvisor.common.exception.AppException;
import vn.kltn.bankadvisor.common.exception.ErrorCode;
import vn.kltn.bankadvisor.common.mail.EmailGateway;
import vn.kltn.bankadvisor.module.bank.entity.Bank;
import vn.kltn.bankadvisor.module.bank.service.BankService;
import vn.kltn.bankadvisor.module.dataset.importer.ServingDatasets;
import vn.kltn.bankadvisor.module.dataset.service.DatasetImportedEvent;
import vn.kltn.bankadvisor.module.rate.entity.Channel;
import vn.kltn.bankadvisor.module.rate.service.RateService;
import vn.kltn.bankadvisor.module.rate.service.RateSnapshot;
import vn.kltn.bankadvisor.module.user.entity.AppUser;
import vn.kltn.bankadvisor.module.user.entity.NotifyChannel;
import vn.kltn.bankadvisor.module.user.repository.AppUserRepository;
import vn.kltn.bankadvisor.module.watchlist.dto.WatchlistDtos.NotificationResponse;
import vn.kltn.bankadvisor.module.watchlist.dto.WatchlistDtos.NotificationSettingsRequest;
import vn.kltn.bankadvisor.module.watchlist.dto.WatchlistDtos.NotificationSettingsResponse;
import vn.kltn.bankadvisor.module.watchlist.entity.Notification;
import vn.kltn.bankadvisor.module.watchlist.entity.NotificationType;
import vn.kltn.bankadvisor.module.watchlist.entity.WatchItem;
import vn.kltn.bankadvisor.module.watchlist.repository.NotificationRepository;
import vn.kltn.bankadvisor.module.watchlist.repository.WatchItemRepository;

import java.math.BigDecimal;
import java.time.Clock;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * Thông báo trong ứng dụng. Tạo thông báo khi:
 * <ul>
 *   <li>nạp được lãi suất của ngày mới và ngân hàng người dùng theo dõi đổi lãi từ ngưỡng trở lên;</li>
 *   <li>nạp được xếp hạng của quý mới.</li>
 * </ul>
 * Lần nạp đầu tiên (bảng đang rỗng) không tạo thông báo, vì không có mốc để so.
 * <p>
 * Người chọn kênh EMAIL thì thông báo còn vào hàng đợi email; {@link NotificationEmailDispatcher} gửi sau,
 * nên việc nạp dữ liệu không phải chờ máy chủ thư.
 */
@Service
@Transactional
public class NotificationService {

    private static final Logger log = LoggerFactory.getLogger(NotificationService.class);
    private static final int MAX_CHANGES_IN_BODY = 6;
    private static final DateTimeFormatter VN_DATE = DateTimeFormatter.ofPattern("dd/MM/yyyy");

    private final NotificationRepository notificationRepository;
    private final WatchItemRepository watchItemRepository;
    private final AppUserRepository userRepository;
    private final RateService rateService;
    private final BankService bankService;
    private final EmailGateway emailGateway;
    private final Clock clock;

    public NotificationService(NotificationRepository notificationRepository, WatchItemRepository watchItemRepository,
                               AppUserRepository userRepository, RateService rateService, BankService bankService,
                               EmailGateway emailGateway, Clock clock) {
        this.notificationRepository = notificationRepository;
        this.watchItemRepository = watchItemRepository;
        this.userRepository = userRepository;
        this.rateService = rateService;
        this.bankService = bankService;
        this.emailGateway = emailGateway;
        this.clock = clock;
    }

    @Transactional(readOnly = true)
    public PageResponse<NotificationResponse> list(long userId, int page, int size) {
        int safeSize = Math.clamp(size, 1, 50);
        return PageResponse.of(notificationRepository.findByUserIdOrderByCreatedAtDesc(userId,
                PageRequest.of(Math.max(page, 0), safeSize)), NotificationResponse::from);
    }

    @Transactional(readOnly = true)
    public long unreadCount(long userId) {
        return notificationRepository.countByUserIdAndReadAtIsNull(userId);
    }

    public void markRead(long userId, long id) {
        notificationRepository.findByIdAndUserId(id, userId)
                .orElseThrow(() -> new AppException(ErrorCode.NOT_FOUND))
                .markRead(clock.instant());
    }

    public int markAllRead(long userId) {
        return notificationRepository.markAllRead(userId, clock.instant());
    }

    @Transactional(readOnly = true)
    public NotificationSettingsResponse settings(long userId) {
        return toSettings(user(userId));
    }

    /** Chọn kênh EMAIL cần hệ thống bật gửi email và người dùng đã xác minh địa chỉ. */
    public NotificationSettingsResponse updateSettings(long userId, NotificationSettingsRequest request) {
        AppUser user = user(userId);
        if (request.channel() == NotifyChannel.EMAIL && user.getNotifyChannel() != NotifyChannel.EMAIL) {
            if (!emailGateway.isEnabled()) {
                throw new AppException(ErrorCode.EMAIL_DISABLED);
            }
            if (!user.isEmailVerified()) {
                throw new AppException(ErrorCode.EMAIL_NOT_VERIFIED);
            }
        }
        user.updateNotificationSettings(request.notifyRateChange(), request.notifyNewRanking(), request.channel());
        return toSettings(user);
    }

    private NotificationSettingsResponse toSettings(AppUser user) {
        return new NotificationSettingsResponse(user.isNotifyRateChange(), user.isNotifyNewRanking(),
                user.getNotifyChannel(), user.getEmail(), emailGateway.isEnabled(), user.isEmailVerified());
    }

    /** Thông báo mới của người này có vào hàng đợi email không. */
    private boolean queueEmail(AppUser user) {
        return user != null && emailGateway.isEnabled() && user.wantsEmail();
    }

    @EventListener
    public void onDatasetImported(DatasetImportedEvent event) {
        if (!event.hasNewerMarker() || event.previousMarker() == null) {
            return;
        }
        if (ServingDatasets.DEPOSIT_RATES.equals(event.dataset())) {
            int created = notifyRateChanges(LocalDate.parse(event.newMarker()));
            log.info("Lãi suất ngày {}: tạo {} thông báo", event.newMarker(), created);
        } else if (ServingDatasets.RANKINGS.equals(event.dataset())) {
            int created = notifyNewRanking(event.newMarker());
            log.info("Xếp hạng quý {}: tạo {} thông báo", event.newMarker(), created);
        }
    }

    /** Tạo thông báo cho các thay đổi lãi suất ngày {@code date} so với ngày liền trước; trả số thông báo mới. */
    public int notifyRateChanges(LocalDate date) {
        RateSnapshot snap = rateService.snapshotAt(date);
        if (snap.previousDate() == null) {
            return 0;
        }
        Map<String, Bank> banks = bankService.lookup();
        List<WatchItem> items = watchItemRepository.findAllForRateAlerts();
        Map<Long, AppUser> users = userRepository.findAllById(items.stream().map(WatchItem::getUserId).distinct().toList())
                .stream().collect(Collectors.toMap(AppUser::getId, Function.identity()));
        int created = 0;
        for (WatchItem item : items) {
            List<String> changes = describeChanges(snap, item.getTicker(), item.getRateThreshold());
            if (changes.isEmpty()) {
                continue;
            }
            String refKey = "RATE:" + item.getTicker() + ":" + date;
            if (notificationRepository.existsByUserIdAndRefKey(item.getUserId(), refKey)) {
                continue;
            }
            notificationRepository.save(Notification.create(item.getUserId(), NotificationType.RATE_CHANGE,
                    item.getTicker(), rateChangeTitle(banks, item.getTicker()), rateChangeBody(date, changes), refKey, clock.instant(),
                    queueEmail(users.get(item.getUserId()))));
            created++;
        }
        return created;
    }

    public int notifyNewRanking(String period) {
        String refKey = "RANKING:" + period;
        int created = 0;
        for (AppUser user : userRepository.findByNotifyNewRankingTrue()) {
            if (notificationRepository.existsByUserIdAndRefKey(user.getId(), refKey)) {
                continue;
            }
            notificationRepository.save(Notification.create(user.getId(), NotificationType.NEW_RANKING, null,
                    "Đã có xếp hạng quý " + period,
                    "Xếp hạng ngân hàng cho gửi tiết kiệm và vay đã cập nhật theo số liệu quý " + period + ".",
                    refKey, clock.instant(), queueEmail(user)));
            created++;
        }
        return created;
    }

    private static String rateChangeTitle(Map<String, Bank> banks, String ticker) {
        String name = banks.containsKey(ticker) ? banks.get(ticker).getShortName() : ticker;
        return name + " thay đổi lãi suất tiết kiệm";
    }

    /** "Ngày 27/09/2026: 12 tháng online 5,90% → 6,10% (+0,20); ... và 3 kỳ hạn khác." */
    private static String rateChangeBody(LocalDate date, List<String> changes) {
        return "Ngày " + date.format(VN_DATE) + ": "
                + String.join("; ", changes.subList(0, Math.min(changes.size(), MAX_CHANGES_IN_BODY)))
                + (changes.size() > MAX_CHANGES_IN_BODY ? " và " + (changes.size() - MAX_CHANGES_IN_BODY) + " kỳ hạn khác" : "")
                + ".";
    }

    /** Các kỳ hạn/kênh của một ngân hàng đổi lãi từ ngưỡng trở lên, dạng "12 tháng online 5,90% → 6,10% (+0,20)". */
    static List<String> describeChanges(RateSnapshot snap, String ticker, BigDecimal threshold) {
        List<RateSnapshot.Key> keys = snap.current().keySet().stream()
                .filter(k -> k.ticker().equals(ticker))
                .sorted(Comparator.comparing(RateSnapshot.Key::channel).thenComparing(RateSnapshot.Key::termMonths))
                .toList();
        List<String> changes = new ArrayList<>();
        for (RateSnapshot.Key key : keys) {
            snap.change(ticker, key.termMonths(), key.channel())
                    .filter(delta -> delta.abs().compareTo(threshold) >= 0)
                    .ifPresent(delta -> changes.add(String.format(Locale.forLanguageTag("vi-VN"),
                            "%d tháng %s %.2f%% → %.2f%% (%s%.2f)", key.termMonths(),
                            key.channel() == Channel.ONLINE ? "online" : "tại quầy",
                            snap.previous().get(key), snap.current().get(key),
                            delta.signum() > 0 ? "+" : "", delta)));
        }
        return changes;
    }

    private AppUser user(long userId) {
        return userRepository.findById(userId).orElseThrow(() -> new AppException(ErrorCode.UNAUTHORIZED));
    }
}
