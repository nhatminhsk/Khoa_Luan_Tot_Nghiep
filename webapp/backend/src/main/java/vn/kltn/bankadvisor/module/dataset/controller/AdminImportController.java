package vn.kltn.bankadvisor.module.dataset.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.common.exception.AppException;
import vn.kltn.bankadvisor.common.exception.ErrorCode;
import vn.kltn.bankadvisor.module.dataset.dto.ImportRunResponse;
import vn.kltn.bankadvisor.module.dataset.dto.ImportSummary;
import vn.kltn.bankadvisor.module.dataset.service.DataImportService;
import vn.kltn.bankadvisor.module.dataset.service.DatasetService;

import java.util.List;

/** Quản trị dữ liệu. Chỉ vai trò ADMIN gọi được (xem SecurityConfig). */
@RestController
@RequestMapping("/api/v1/admin/imports")
public class AdminImportController {

    private final DataImportService importService;
    private final DatasetService datasetService;

    public AdminImportController(DataImportService importService, DatasetService datasetService) {
        this.importService = importService;
        this.datasetService = datasetService;
    }

    @GetMapping
    public ApiResponse<List<ImportRunResponse>> recentRuns() {
        return ApiResponse.ok(datasetService.recentRuns());
    }

    /** Nạp lại data/serving ngay; {@code force=true} nạp cả file không đổi. */
    @PostMapping
    public ApiResponse<ImportSummary> runImport(@RequestParam(defaultValue = "false") boolean force) {
        try {
            return ApiResponse.ok(importService.importAll(force));
        } catch (IllegalStateException e) {
            throw new AppException(ErrorCode.IMPORT_FAILED, e.getMessage());
        }
    }
}
