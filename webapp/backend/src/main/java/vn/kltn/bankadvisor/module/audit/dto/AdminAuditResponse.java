package vn.kltn.bankadvisor.module.audit.dto;

import vn.kltn.bankadvisor.module.audit.entity.AdminAction;
import vn.kltn.bankadvisor.module.audit.entity.AdminAudit;

import java.time.Instant;

public record AdminAuditResponse(long id, Instant createdAt, String actorEmail, AdminAction action,
                                 Long targetId, String targetEmail, String detail) {

    public static AdminAuditResponse from(AdminAudit audit) {
        return new AdminAuditResponse(audit.getId(), audit.getCreatedAt(), audit.getActorEmail(), audit.getAction(),
                audit.getTargetId(), audit.getTargetEmail(), audit.getDetail());
    }
}
