package vn.kltn.bankadvisor.module.audit.entity;

/** Loại thao tác quản trị được ghi nhật ký (khớp CHECK của cột {@code admin_audit.action}). */
public enum AdminAction {
    USER_LOCK,
    USER_UNLOCK,
    ROLE_CHANGE,
    SESSIONS_REVOKE,
    DATA_IMPORT,
    EMAIL_DISPATCH
}
