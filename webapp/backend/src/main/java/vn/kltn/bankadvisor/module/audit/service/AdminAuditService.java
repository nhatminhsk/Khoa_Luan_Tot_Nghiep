package vn.kltn.bankadvisor.module.audit.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.api.PageResponse;
import vn.kltn.bankadvisor.module.audit.dto.AdminAuditResponse;
import vn.kltn.bankadvisor.module.audit.entity.AdminAction;
import vn.kltn.bankadvisor.module.audit.entity.AdminAudit;
import vn.kltn.bankadvisor.module.audit.repository.AdminAuditRepository;
import vn.kltn.bankadvisor.security.AuthUser;

import java.time.Clock;

/**
 * Nhật ký thao tác quản trị (khóa / mở tài khoản, đổi vai trò, thu hồi phiên, nạp lại dữ liệu, gửi email ngay).
 * Ghi trong cùng transaction với thao tác: thao tác thất bại thì không có dòng nhật ký, thao tác thành công thì
 * chắc chắn có. Đồng thời in một dòng log {@code ADMIN_ACTION} để xem cùng log ứng dụng.
 */
@Service
public class AdminAuditService {

    private static final Logger log = LoggerFactory.getLogger(AdminAuditService.class);
    private static final int MAX_PAGE_SIZE = 100;

    private final AdminAuditRepository repository;
    private final Clock clock;

    public AdminAuditService(AdminAuditRepository repository, Clock clock) {
        this.repository = repository;
        this.clock = clock;
    }

    @Transactional
    public void record(AuthUser actor, AdminAction action, Long targetId, String targetEmail, String detail) {
        repository.save(AdminAudit.of(clock.instant(), actor.id(), actor.email(), action, targetId, targetEmail, detail));
        log.info("ADMIN_ACTION action={} actor={} target={} {}", action, actor.email(),
                targetEmail == null ? "-" : targetEmail, detail == null ? "" : detail);
    }

    @Transactional(readOnly = true)
    public PageResponse<AdminAuditResponse> list(int page, int size) {
        PageRequest request = PageRequest.of(Math.max(page, 0), Math.clamp(size, 1, MAX_PAGE_SIZE),
                Sort.by(Sort.Direction.DESC, "createdAt").and(Sort.by(Sort.Direction.DESC, "id")));
        return PageResponse.of(repository.findAll(request), AdminAuditResponse::from);
    }
}
