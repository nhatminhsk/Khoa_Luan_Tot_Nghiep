package vn.kltn.bankadvisor.module.advisor.controller;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.module.advisor.dto.LoanAdviceRequest;
import vn.kltn.bankadvisor.module.advisor.dto.LoanAdviceResponse;
import vn.kltn.bankadvisor.module.advisor.dto.SavingsAdviceRequest;
import vn.kltn.bankadvisor.module.advisor.dto.SavingsAdviceResponse;
import vn.kltn.bankadvisor.module.advisor.service.LoanAdvisorService;
import vn.kltn.bankadvisor.module.advisor.service.SavingsAdvisorService;

/**
 * Công cụ chọn ngân hàng. Dùng POST vì đầu vào là một nhu cầu (nhiều trường, có trọng số), không phải
 * một tài nguyên; không lưu gì — muốn lưu nhu cầu thì gọi /api/v1/me/needs.
 */
@RestController
@RequestMapping("/api/v1/advisor")
public class AdvisorController {

    private final SavingsAdvisorService savingsAdvisorService;
    private final LoanAdvisorService loanAdvisorService;

    public AdvisorController(SavingsAdvisorService savingsAdvisorService, LoanAdvisorService loanAdvisorService) {
        this.savingsAdvisorService = savingsAdvisorService;
        this.loanAdvisorService = loanAdvisorService;
    }

    @PostMapping("/savings")
    public ApiResponse<SavingsAdviceResponse> savings(@Valid @RequestBody SavingsAdviceRequest request) {
        return ApiResponse.ok(savingsAdvisorService.advise(request));
    }

    @PostMapping("/loans")
    public ApiResponse<LoanAdviceResponse> loans(@Valid @RequestBody LoanAdviceRequest request) {
        return ApiResponse.ok(loanAdvisorService.advise(request));
    }
}
