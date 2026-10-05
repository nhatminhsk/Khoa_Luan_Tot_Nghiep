package vn.kltn.bankadvisor.module.dataset.dto;

import vn.kltn.bankadvisor.module.dataset.entity.ImportRun;
import vn.kltn.bankadvisor.module.dataset.entity.ImportStatus;

import java.time.Instant;

public record ImportRunResponse(
        long id,
        String dataset,
        String fileName,
        ImportStatus status,
        Integer rowCount,
        String message,
        Instant startedAt,
        Instant finishedAt
) {

    public static ImportRunResponse from(ImportRun run) {
        return new ImportRunResponse(run.getId(), run.getDataset(), run.getFileName(), run.getStatus(),
                run.getRowCount(), run.getMessage(), run.getStartedAt(), run.getFinishedAt());
    }
}
