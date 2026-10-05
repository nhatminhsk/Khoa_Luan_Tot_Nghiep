package vn.kltn.bankadvisor.module.need.controller;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.module.need.dto.SavedNeedRequest;
import vn.kltn.bankadvisor.module.need.dto.SavedNeedResponse;
import vn.kltn.bankadvisor.module.need.service.SavedNeedService;
import vn.kltn.bankadvisor.security.AuthUser;
import vn.kltn.bankadvisor.security.CurrentUser;

import java.util.List;

@RestController
@RequestMapping("/api/v1/me/needs")
public class SavedNeedController {

    private final SavedNeedService needService;

    public SavedNeedController(SavedNeedService needService) {
        this.needService = needService;
    }

    @GetMapping
    public ApiResponse<List<SavedNeedResponse>> list(@CurrentUser AuthUser user) {
        return ApiResponse.ok(needService.list(user.id()));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<SavedNeedResponse> create(@CurrentUser AuthUser user, @Valid @RequestBody SavedNeedRequest request) {
        return ApiResponse.ok(needService.create(user.id(), request));
    }

    @PutMapping("/{id}")
    public ApiResponse<SavedNeedResponse> update(@CurrentUser AuthUser user, @PathVariable long id,
                                                 @Valid @RequestBody SavedNeedRequest request) {
        return ApiResponse.ok(needService.update(user.id(), id, request));
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@CurrentUser AuthUser user, @PathVariable long id) {
        needService.delete(user.id(), id);
        return ApiResponse.ok(null);
    }
}
