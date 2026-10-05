package vn.kltn.bankadvisor.module.watchlist.controller;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.module.watchlist.dto.WatchlistDtos.AddWatchRequest;
import vn.kltn.bankadvisor.module.watchlist.dto.WatchlistDtos.UpdateWatchRequest;
import vn.kltn.bankadvisor.module.watchlist.dto.WatchlistDtos.WatchItemResponse;
import vn.kltn.bankadvisor.module.watchlist.service.WatchlistService;
import vn.kltn.bankadvisor.security.AuthUser;
import vn.kltn.bankadvisor.security.CurrentUser;

import java.util.List;

@RestController
@RequestMapping("/api/v1/me/watchlist")
public class WatchlistController {

    private final WatchlistService watchlistService;

    public WatchlistController(WatchlistService watchlistService) {
        this.watchlistService = watchlistService;
    }

    @GetMapping
    public ApiResponse<List<WatchItemResponse>> list(@CurrentUser AuthUser user) {
        return ApiResponse.ok(watchlistService.list(user.id()));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<WatchItemResponse> add(@CurrentUser AuthUser user, @Valid @RequestBody AddWatchRequest request) {
        return ApiResponse.ok(watchlistService.add(user.id(), request));
    }

    @PatchMapping("/{ticker}")
    public ApiResponse<WatchItemResponse> update(@CurrentUser AuthUser user, @PathVariable String ticker,
                                                 @Valid @RequestBody UpdateWatchRequest request) {
        return ApiResponse.ok(watchlistService.update(user.id(), ticker, request));
    }

    @DeleteMapping("/{ticker}")
    public ApiResponse<Void> remove(@CurrentUser AuthUser user, @PathVariable String ticker) {
        watchlistService.remove(user.id(), ticker);
        return ApiResponse.ok(null);
    }
}
