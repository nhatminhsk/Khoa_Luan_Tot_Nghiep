package vn.kltn.bankadvisor.module.user.service;

import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.api.PageResponse;
import vn.kltn.bankadvisor.common.exception.AppException;
import vn.kltn.bankadvisor.common.exception.ErrorCode;
import vn.kltn.bankadvisor.module.audit.entity.AdminAction;
import vn.kltn.bankadvisor.module.audit.service.AdminAuditService;
import vn.kltn.bankadvisor.module.user.dto.AdminUserDtos.UpdateUserRequest;
import vn.kltn.bankadvisor.module.user.dto.AdminUserDtos.UserPage;
import vn.kltn.bankadvisor.module.user.dto.AdminUserDtos.UserStats;
import vn.kltn.bankadvisor.module.user.dto.AdminUserDtos.UserSummary;
import vn.kltn.bankadvisor.module.user.entity.AppUser;
import vn.kltn.bankadvisor.module.user.entity.Role;
import vn.kltn.bankadvisor.module.user.entity.UserStatus;
import vn.kltn.bankadvisor.module.user.repository.AppUserRepository;
import vn.kltn.bankadvisor.security.AuthUser;

import java.util.Locale;

/**
 * Quản lý người dùng (quyền USER_MANAGE): xem danh sách + thống kê, khóa / mở tài khoản, đổi vai trò, thu hồi phiên.
 * <p>
 * Ràng buộc: không tự khóa / tự đổi vai trò của chính mình; luôn còn ít nhất một quản trị viên đang hoạt động.
 * Mỗi thao tác ghi một dòng nhật ký quản trị ({@link AdminAuditService}) trong cùng transaction.
 */
@Service
public class UserAdminService {

    private static final int MAX_PAGE_SIZE = 100;

    private final AppUserRepository users;
    private final AdminAuditService audit;

    public UserAdminService(AppUserRepository users, AdminAuditService audit) {
        this.users = users;
        this.audit = audit;
    }

    @Transactional(readOnly = true)
    public UserPage list(String query, Role role, UserStatus status, int page, int size) {
        Specification<AppUser> spec = (root, q, cb) -> cb.conjunction();
        if (query != null && !query.isBlank()) {
            String like = "%" + query.strip().toLowerCase(Locale.ROOT) + "%";
            spec = spec.and((root, q, cb) -> cb.or(
                    cb.like(cb.lower(root.get("email")), like),
                    cb.like(cb.lower(root.get("displayName")), like)));
        }
        if (role != null) {
            spec = spec.and((root, q, cb) -> cb.equal(root.get("role"), role));
        }
        if (status != null) {
            spec = spec.and((root, q, cb) -> cb.equal(root.get("status"), status));
        }
        PageRequest request = PageRequest.of(Math.max(page, 0), Math.clamp(size, 1, MAX_PAGE_SIZE),
                Sort.by(Sort.Direction.DESC, "createdAt").and(Sort.by("id")));
        UserStats stats = new UserStats(users.count(), users.countByStatus(UserStatus.ACTIVE),
                users.countByStatus(UserStatus.LOCKED), users.countByRole(Role.ADMIN),
                users.countByEmailVerifiedAtIsNotNull());
        return new UserPage(stats, PageResponse.of(users.findAll(spec, request), UserSummary::from));
    }

    @Transactional
    public UserSummary update(AuthUser actor, long userId, UpdateUserRequest request) {
        AppUser target = users.findById(userId).orElseThrow(() -> new AppException(ErrorCode.NOT_FOUND));
        boolean changesRole = request.role() != null && request.role() != target.getRole();
        boolean changesStatus = request.status() != null && request.status() != target.getStatus();
        if (!changesRole && !changesStatus) {
            return UserSummary.from(target);
        }
        if (target.getId() == actor.id()) {
            throw new AppException(ErrorCode.CANNOT_MODIFY_SELF);
        }
        if (changesStatus && request.status() == UserStatus.LOCKED
                && (request.reason() == null || request.reason().isBlank())) {
            throw new AppException(ErrorCode.BAD_REQUEST, "Nhập lý do khóa tài khoản");
        }
        boolean removesActiveAdmin = target.getRole() == Role.ADMIN && target.isActive()
                && ((changesRole && request.role() != Role.ADMIN) || (changesStatus && request.status() == UserStatus.LOCKED));
        if (removesActiveAdmin && users.lockByRoleAndStatus(Role.ADMIN, UserStatus.ACTIVE).size() <= 1) {
            throw new AppException(ErrorCode.LAST_ADMIN);
        }
        if (changesRole) {
            Role previous = target.getRole();
            target.changeRole(request.role());
            record(actor, AdminAction.ROLE_CHANGE, target, previous + " → " + request.role());
        }
        if (changesStatus) {
            if (request.status() == UserStatus.LOCKED) {
                target.lock();
                record(actor, AdminAction.USER_LOCK, target, "Lý do: " + request.reason().strip());
            } else {
                target.unlock();
                record(actor, AdminAction.USER_UNLOCK, target, null);
            }
        }
        return UserSummary.from(target);
    }

    @Transactional
    public void revokeSessions(AuthUser actor, long userId) {
        AppUser target = users.findById(userId).orElseThrow(() -> new AppException(ErrorCode.NOT_FOUND));
        target.revokeSessions();
        record(actor, AdminAction.SESSIONS_REVOKE, target, null);
    }

    private void record(AuthUser actor, AdminAction action, AppUser target, String detail) {
        audit.record(actor, action, target.getId(), target.getEmail(), detail);
    }
}
