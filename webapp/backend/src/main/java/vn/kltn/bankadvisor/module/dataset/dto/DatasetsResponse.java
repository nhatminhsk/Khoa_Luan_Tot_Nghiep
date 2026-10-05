package vn.kltn.bankadvisor.module.dataset.dto;

import vn.kltn.bankadvisor.common.api.ResultStatus;

import java.time.Instant;
import java.util.List;

/** Nguồn dữ liệu và trạng thái các kết quả thuật toán, cho trang Phương pháp và dữ liệu. */
public record DatasetsResponse(List<Source> sources, List<AlgorithmOutput> algorithmOutputs) {

    public record Source(String dataset, String name, String source, String frequency, String lastUpdated,
                         Integer rowCount, String coverageNote) {
    }

    public record AlgorithmOutput(String dataset, String fileName, ResultStatus status, long rowCount,
                                  Instant lastImportedAt) {
    }
}
