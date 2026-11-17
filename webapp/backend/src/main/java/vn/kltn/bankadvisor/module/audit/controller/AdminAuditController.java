package vn.kltn.bankadvisor.module.audit.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.common.api.PageResponse;
import vn.kltn.bankadvisor.module.audit.dto.AdminAuditResponse;
import vn.kltn.bankadvisor.module.audit.service.AdminAuditService;

/** Xem nhật ký thao tác quản trị (quyền USER_MANAGE, xem SecurityConfig). Không có API sửa / xóa nhật ký. */
@RestController
@RequestMapping("/api/v1/admin/audit")
public class AdminAuditController {

    private final AdminAuditService auditService;

    public AdminAuditController(AdminAuditService auditService) {
        this.auditService = auditService;
    }

    @GetMapping
    public ApiResponse<PageResponse<AdminAuditResponse>> list(@RequestParam(defaultValue = "0") int page,
                                                             @RequestParam(defaultValue = "20") int size) {
        return ApiResponse.ok(auditService.list(page, size));
    }
}
