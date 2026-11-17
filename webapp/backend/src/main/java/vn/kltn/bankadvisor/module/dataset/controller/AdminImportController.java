package vn.kltn.bankadvisor.module.dataset.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.common.exception.AppException;
import vn.kltn.bankadvisor.common.exception.ErrorCode;
import vn.kltn.bankadvisor.module.audit.entity.AdminAction;
import vn.kltn.bankadvisor.module.audit.service.AdminAuditService;
import vn.kltn.bankadvisor.module.dataset.dto.ImportRunResponse;
import vn.kltn.bankadvisor.module.dataset.dto.ImportSummary;
import vn.kltn.bankadvisor.module.dataset.service.DataImportService;
import vn.kltn.bankadvisor.module.dataset.service.DatasetService;
import vn.kltn.bankadvisor.security.AuthUser;
import vn.kltn.bankadvisor.security.CurrentUser;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/** Quản trị dữ liệu (quyền DATA_MANAGE, xem SecurityConfig). Nạp lại bằng tay được ghi nhật ký quản trị. */
@RestController
@RequestMapping("/api/v1/admin/imports")
public class AdminImportController {

    private final DataImportService importService;
    private final DatasetService datasetService;
    private final AdminAuditService audit;

    public AdminImportController(DataImportService importService, DatasetService datasetService, AdminAuditService audit) {
        this.importService = importService;
        this.datasetService = datasetService;
        this.audit = audit;
    }

    @GetMapping
    public ApiResponse<List<ImportRunResponse>> recentRuns() {
        return ApiResponse.ok(datasetService.recentRuns());
    }

    /** Nạp lại data/serving ngay; {@code force=true} nạp cả file không đổi. */
    @PostMapping
    public ApiResponse<ImportSummary> runImport(@CurrentUser AuthUser user, @RequestParam(defaultValue = "false") boolean force) {
        ImportSummary summary;
        try {
            summary = importService.importAll(force);
        } catch (IllegalStateException e) {
            audit.record(user, AdminAction.DATA_IMPORT, null, null, "Lỗi: " + e.getMessage());
            throw new AppException(ErrorCode.IMPORT_FAILED, e.getMessage());
        }
        Map<ImportSummary.Status, Long> counts = summary.outcomes().stream()
                .collect(Collectors.groupingBy(ImportSummary.Outcome::status, Collectors.counting()));
        audit.record(user, AdminAction.DATA_IMPORT, null, null, (force ? "Nạp lại tất cả · " : "")
                + "nạp " + counts.getOrDefault(ImportSummary.Status.IMPORTED, 0L)
                + ", không đổi " + counts.getOrDefault(ImportSummary.Status.UNCHANGED, 0L)
                + ", lỗi " + counts.getOrDefault(ImportSummary.Status.FAILED, 0L));
        return ApiResponse.ok(summary);
    }
}
