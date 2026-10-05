package vn.kltn.bankadvisor.module.dataset.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.kltn.bankadvisor.common.api.ResultStatus;
import vn.kltn.bankadvisor.module.dataset.dto.DatasetsResponse;
import vn.kltn.bankadvisor.module.dataset.dto.ImportRunResponse;
import vn.kltn.bankadvisor.module.dataset.entity.DatasetInfo;
import vn.kltn.bankadvisor.module.dataset.entity.ImportRun;
import vn.kltn.bankadvisor.module.dataset.entity.ImportStatus;
import vn.kltn.bankadvisor.module.dataset.importer.CsvTableLoader;
import vn.kltn.bankadvisor.module.dataset.importer.ServingDatasets;
import vn.kltn.bankadvisor.module.dataset.importer.TableSpec;
import vn.kltn.bankadvisor.module.dataset.repository.DatasetInfoRepository;
import vn.kltn.bankadvisor.module.dataset.repository.ImportRunRepository;

import java.util.Comparator;
import java.util.List;

@Service
@Transactional(readOnly = true)
public class DatasetService {

    private final DatasetInfoRepository infoRepository;
    private final ImportRunRepository runRepository;
    private final CsvTableLoader loader;

    public DatasetService(DatasetInfoRepository infoRepository, ImportRunRepository runRepository,
                          CsvTableLoader loader) {
        this.infoRepository = infoRepository;
        this.runRepository = runRepository;
        this.loader = loader;
    }

    /** Thứ tự hiển thị: dữ liệu người dùng quan tâm hằng ngày lên trước. Tập lạ xếp cuối. */
    private static final List<String> DISPLAY_ORDER = List.of(
            "deposit_rates", "lending_rates", "bank_quarterly", "app_store", "app_reviews_monthly", "programs");

    public List<DatasetsResponse.Source> sources() {
        return infoRepository.findAll().stream()
                .sorted(Comparator.comparingInt((DatasetInfo d) -> {
                    int index = DISPLAY_ORDER.indexOf(d.getDataset());
                    return index < 0 ? Integer.MAX_VALUE : index;
                }).thenComparing(DatasetInfo::getDataset))
                .map(d -> new DatasetsResponse.Source(d.getDataset(), d.getName(), d.getSource(), d.getFrequency(),
                        d.getLastUpdated(), d.getRowCount(), d.getCoverageNote()))
                .toList();
    }

    public DatasetsResponse overview() {
        List<DatasetsResponse.AlgorithmOutput> outputs = ServingDatasets.ALL.stream()
                .filter(spec -> ServingDatasets.ALGORITHM_OUTPUTS.contains(spec.dataset()))
                .map(this::algorithmOutput)
                .toList();
        return new DatasetsResponse(sources(), outputs);
    }

    public List<ImportRunResponse> recentRuns() {
        return runRepository.findTop100ByOrderByStartedAtDesc().stream().map(ImportRunResponse::from).toList();
    }

    private DatasetsResponse.AlgorithmOutput algorithmOutput(TableSpec spec) {
        long rows = loader.count(spec.table());
        return new DatasetsResponse.AlgorithmOutput(spec.dataset(), spec.fileName(),
                rows > 0 ? ResultStatus.AVAILABLE : ResultStatus.NOT_AVAILABLE, rows,
                runRepository.findFirstByDatasetAndStatusOrderByStartedAtDesc(spec.dataset(), ImportStatus.SUCCESS)
                        .map(ImportRun::getFinishedAt).orElse(null));
    }
}
