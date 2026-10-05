package vn.kltn.bankadvisor.module.app.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.module.app.dto.AppExperienceResponse;
import vn.kltn.bankadvisor.module.app.dto.AppScoreSummary;
import vn.kltn.bankadvisor.module.app.service.AppExperienceService;

import java.util.List;

@RestController
@RequestMapping("/api/v1")
public class AppExperienceController {

    private final AppExperienceService appExperienceService;

    public AppExperienceController(AppExperienceService appExperienceService) {
        this.appExperienceService = appExperienceService;
    }

    @GetMapping("/app-scores")
    public ApiResponse<List<AppScoreSummary>> scores() {
        return ApiResponse.ok(appExperienceService.allScores());
    }

    @GetMapping("/banks/{ticker}/app")
    public ApiResponse<AppExperienceResponse> forBank(@PathVariable String ticker) {
        return ApiResponse.ok(appExperienceService.forBank(ticker));
    }
}
