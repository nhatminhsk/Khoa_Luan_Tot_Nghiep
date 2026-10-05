package vn.kltn.bankadvisor.module.watchlist.controller;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.common.api.PageResponse;
import vn.kltn.bankadvisor.module.watchlist.dto.WatchlistDtos.NotificationResponse;
import vn.kltn.bankadvisor.module.watchlist.dto.WatchlistDtos.NotificationSettingsRequest;
import vn.kltn.bankadvisor.module.watchlist.dto.WatchlistDtos.NotificationSettingsResponse;
import vn.kltn.bankadvisor.module.watchlist.dto.WatchlistDtos.UnreadCount;
import vn.kltn.bankadvisor.module.watchlist.service.NotificationService;
import vn.kltn.bankadvisor.security.AuthUser;
import vn.kltn.bankadvisor.security.CurrentUser;

@RestController
@RequestMapping("/api/v1/me")
public class NotificationController {

    private final NotificationService notificationService;

    public NotificationController(NotificationService notificationService) {
        this.notificationService = notificationService;
    }

    @GetMapping("/notifications")
    public ApiResponse<PageResponse<NotificationResponse>> list(@CurrentUser AuthUser user,
                                                               @RequestParam(defaultValue = "0") int page,
                                                               @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.ok(notificationService.list(user.id(), page, size));
    }

    @GetMapping("/notifications/unread-count")
    public ApiResponse<UnreadCount> unreadCount(@CurrentUser AuthUser user) {
        return ApiResponse.ok(new UnreadCount(notificationService.unreadCount(user.id())));
    }

    @PostMapping("/notifications/{id}/read")
    public ApiResponse<Void> markRead(@CurrentUser AuthUser user, @PathVariable long id) {
        notificationService.markRead(user.id(), id);
        return ApiResponse.ok(null);
    }

    @PostMapping("/notifications/read-all")
    public ApiResponse<Void> markAllRead(@CurrentUser AuthUser user) {
        notificationService.markAllRead(user.id());
        return ApiResponse.ok(null);
    }

    @GetMapping("/notification-settings")
    public ApiResponse<NotificationSettingsResponse> settings(@CurrentUser AuthUser user) {
        return ApiResponse.ok(notificationService.settings(user.id()));
    }

    @PutMapping("/notification-settings")
    public ApiResponse<NotificationSettingsResponse> updateSettings(@CurrentUser AuthUser user,
                                                                    @Valid @RequestBody NotificationSettingsRequest settings) {
        return ApiResponse.ok(notificationService.updateSettings(user.id(), settings));
    }
}
