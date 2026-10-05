package vn.kltn.bankadvisor.module.watchlist.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.mail.EmailAddresses;
import vn.kltn.bankadvisor.common.mail.EmailGateway;
import vn.kltn.bankadvisor.module.user.entity.AppUser;
import vn.kltn.bankadvisor.module.user.repository.AppUserRepository;
import vn.kltn.bankadvisor.module.watchlist.dto.WatchlistDtos.EmailQueueSummary;
import vn.kltn.bankadvisor.module.watchlist.dto.WatchlistDtos.FailedEmail;
import vn.kltn.bankadvisor.module.watchlist.entity.EmailStatus;
import vn.kltn.bankadvisor.module.watchlist.entity.Notification;
import vn.kltn.bankadvisor.module.watchlist.repository.NotificationRepository;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/** Việc của quản trị viên với email: xem tình trạng hàng đợi gửi thông báo. */
@Service
public class AdminEmailService {

    private final NotificationRepository notificationRepository;
    private final AppUserRepository userRepository;
    private final EmailGateway emailGateway;

    public AdminEmailService(NotificationRepository notificationRepository, AppUserRepository userRepository,
                             EmailGateway emailGateway) {
        this.notificationRepository = notificationRepository;
        this.userRepository = userRepository;
        this.emailGateway = emailGateway;
    }

    @Transactional(readOnly = true)
    public EmailQueueSummary summary() {
        List<Notification> failures = notificationRepository.findTop5ByEmailStatusOrderByIdDesc(EmailStatus.FAILED);
        Map<Long, String> emails = userRepository.findAllById(failures.stream().map(Notification::getUserId).distinct().toList())
                .stream().collect(Collectors.toMap(AppUser::getId, AppUser::getEmail));
        return new EmailQueueSummary(emailGateway.mode(),
                notificationRepository.countByEmailStatus(EmailStatus.PENDING),
                notificationRepository.countByEmailStatus(EmailStatus.SENT),
                notificationRepository.countByEmailStatus(EmailStatus.FAILED),
                notificationRepository.countByEmailStatus(EmailStatus.SKIPPED),
                failures.stream().map(n -> new FailedEmail(n.getId(), EmailAddresses.mask(emails.get(n.getUserId())),
                        n.getTitle(), n.getEmailAttempts(), n.getEmailLastError(), n.getCreatedAt())).toList());
    }
}
