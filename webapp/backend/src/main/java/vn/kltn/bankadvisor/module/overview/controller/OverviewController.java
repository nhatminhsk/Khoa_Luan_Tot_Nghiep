package vn.kltn.bankadvisor.module.overview.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.module.overview.dto.OverviewResponse;
import vn.kltn.bankadvisor.module.overview.service.OverviewService;

@RestController
@RequestMapping("/api/v1/overview")
public class OverviewController {

    private final OverviewService overviewService;

    public OverviewController(OverviewService overviewService) {
        this.overviewService = overviewService;
    }

    @GetMapping
    public ApiResponse<OverviewResponse> overview() {
        return ApiResponse.ok(overviewService.overview());
    }
}
