package vn.kltn.bankadvisor.module.watchlist.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.common.exception.AppException;
import vn.kltn.bankadvisor.common.exception.ErrorCode;
import vn.kltn.bankadvisor.common.mail.EmailGateway;
import vn.kltn.bankadvisor.module.watchlist.dto.WatchlistDtos.DispatchResponse;
import vn.kltn.bankadvisor.module.watchlist.dto.WatchlistDtos.EmailQueueSummary;
import vn.kltn.bankadvisor.module.watchlist.service.AdminEmailService;
import vn.kltn.bankadvisor.module.watchlist.service.NotificationEmailDispatcher;

/** Theo dõi hàng đợi email thông báo. Chỉ vai trò ADMIN gọi được (xem SecurityConfig). */
@RestController
@RequestMapping("/api/v1/admin/email-queue")
public class AdminEmailController {

    private final AdminEmailService adminEmailService;
    private final NotificationEmailDispatcher dispatcher;
    private final EmailGateway emailGateway;

    public AdminEmailController(AdminEmailService adminEmailService, NotificationEmailDispatcher dispatcher,
                                EmailGateway emailGateway) {
        this.adminEmailService = adminEmailService;
        this.dispatcher = dispatcher;
        this.emailGateway = emailGateway;
    }

    @GetMapping
    public ApiResponse<EmailQueueSummary> summary() {
        return ApiResponse.ok(adminEmailService.summary());
    }

    /** Gửi ngay các email đã tới lượt, không chờ lịch quét. */
    @PostMapping("/dispatch")
    public ApiResponse<DispatchResponse> dispatchNow() {
        if (!emailGateway.isEnabled()) {
            throw new AppException(ErrorCode.EMAIL_DISABLED);
        }
        NotificationEmailDispatcher.DispatchResult result = dispatcher.dispatchPending();
        return ApiResponse.ok(new DispatchResponse(result.emailsSent(), result.emailsFailed(), result.notificationsSkipped()));
    }
}
