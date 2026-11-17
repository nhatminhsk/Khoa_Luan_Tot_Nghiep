package vn.kltn.bankadvisor.module.audit.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;

/** Một dòng nhật ký thao tác quản trị. Chỉ thêm, không sửa, không xóa. */
@Entity
@Table(name = "admin_audit")
public class AdminAudit {

    private static final int MAX_DETAIL = 300;

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "actor_id", nullable = false, updatable = false)
    private long actorId;

    @Column(name = "actor_email", nullable = false, updatable = false)
    private String actorEmail;

    @Enumerated(EnumType.STRING)
    @Column(name = "action", nullable = false, updatable = false)
    private AdminAction action;

    @Column(name = "target_id", updatable = false)
    private Long targetId;

    @Column(name = "target_email", updatable = false)
    private String targetEmail;

    @Column(name = "detail", updatable = false)
    private String detail;

    protected AdminAudit() {
    }

    public static AdminAudit of(Instant now, long actorId, String actorEmail, AdminAction action,
                                Long targetId, String targetEmail, String detail) {
        AdminAudit audit = new AdminAudit();
        audit.createdAt = now;
        audit.actorId = actorId;
        audit.actorEmail = actorEmail;
        audit.action = action;
        audit.targetId = targetId;
        audit.targetEmail = targetEmail;
        audit.detail = detail == null || detail.isBlank() ? null
                : detail.length() > MAX_DETAIL ? detail.substring(0, MAX_DETAIL) : detail;
        return audit;
    }

    public Long getId() {
        return id;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public long getActorId() {
        return actorId;
    }

    public String getActorEmail() {
        return actorEmail;
    }

    public AdminAction getAction() {
        return action;
    }

    public Long getTargetId() {
        return targetId;
    }

    public String getTargetEmail() {
        return targetEmail;
    }

    public String getDetail() {
        return detail;
    }
}
