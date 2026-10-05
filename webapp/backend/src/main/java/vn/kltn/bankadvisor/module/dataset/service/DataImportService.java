package vn.kltn.bankadvisor.module.dataset.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import vn.kltn.bankadvisor.common.config.AppProperties;
import vn.kltn.bankadvisor.module.dataset.dto.ImportSummary;
import vn.kltn.bankadvisor.module.dataset.entity.ImportRun;
import vn.kltn.bankadvisor.module.dataset.entity.ImportStatus;
import vn.kltn.bankadvisor.module.dataset.importer.CsvTableLoader;
import vn.kltn.bankadvisor.module.dataset.importer.ServingDatasets;
import vn.kltn.bankadvisor.module.dataset.importer.TableSpec;
import vn.kltn.bankadvisor.module.dataset.repository.ImportRunRepository;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Nạp các file CSV trong data/serving vào cơ sở dữ liệu.
 * <ul>
 *   <li>Mỗi file một transaction: file hỏng thì bảng đó giữ nguyên, các file khác vẫn nạp.</li>
 *   <li>Chỉ nạp lại file có checksum khác lần nạp thành công gần nhất (trừ khi {@code force}).</li>
 *   <li>Nạp xong phát {@link DatasetImportedEvent} để module thông báo xử lý.</li>
 * </ul>
 */
@Service
public class DataImportService {

    private static final Logger log = LoggerFactory.getLogger(DataImportService.class);

    private final CsvTableLoader loader;
    private final ImportRunRepository runRepository;
    private final TransactionTemplate transaction;
    private final ApplicationEventPublisher events;
    private final Path dataDir;
    private final Clock clock;
    private final ReentrantLock lock = new ReentrantLock();

    public DataImportService(CsvTableLoader loader, ImportRunRepository runRepository, TransactionTemplate transaction,
                             ApplicationEventPublisher events, AppProperties properties, Clock clock) {
        this.loader = loader;
        this.runRepository = runRepository;
        this.transaction = transaction;
        this.events = events;
        this.dataDir = properties.dataImport().path();
        this.clock = clock;
    }

    public Path dataDir() {
        return dataDir;
    }

    /** Nạp mọi file theo thứ tự trong {@link ServingDatasets#ALL}. Chỉ một lượt nạp chạy tại một thời điểm. */
    public ImportSummary importAll(boolean force) {
        if (!lock.tryLock()) {
            throw new IllegalStateException("Đang có một lượt nạp dữ liệu khác chạy");
        }
        try {
            List<ImportSummary.Outcome> outcomes = new ArrayList<>();
            for (TableSpec spec : ServingDatasets.ALL) {
                outcomes.add(importOne(spec, force));
            }
            log.info("Nạp dữ liệu từ {}: {}", dataDir, outcomes.stream()
                    .map(o -> o.dataset() + "=" + o.status()).toList());
            return new ImportSummary(outcomes);
        } finally {
            lock.unlock();
        }
    }

    private ImportSummary.Outcome importOne(TableSpec spec, boolean force) {
        Path file = dataDir.resolve(spec.fileName());
        if (!Files.isRegularFile(file)) {
            return new ImportSummary.Outcome(spec.dataset(), spec.fileName(), ImportSummary.Status.MISSING, 0, 0, null);
        }
        String checksum = sha256(file);
        boolean unchanged = runRepository.findFirstByDatasetAndStatusOrderByStartedAtDesc(spec.dataset(), ImportStatus.SUCCESS)
                .map(run -> checksum.equals(run.getChecksum()))
                .orElse(false);
        if (unchanged && !force) {
            return new ImportSummary.Outcome(spec.dataset(), spec.fileName(), ImportSummary.Status.UNCHANGED, 0, 0, null);
        }

        ImportRun run = runRepository.save(ImportRun.start(spec.dataset(), spec.fileName(), checksum, clock.instant()));
        try {
            List<Map<String, String>> rows = loader.read(file);
            String before = loader.marker(spec);
            CsvTableLoader.LoadResult result = transaction.execute(status -> loader.load(spec, rows));
            String after = loader.marker(spec);
            String message = result.skipped() > 0
                    ? "Bỏ qua " + result.skipped() + " dòng có mã ngoài phạm vi"
                    : null;
            run.succeed(result.loaded(), message, clock.instant());
            runRepository.save(run);
            events.publishEvent(new DatasetImportedEvent(spec.dataset(), before, after));
            return new ImportSummary.Outcome(spec.dataset(), spec.fileName(), ImportSummary.Status.IMPORTED,
                    result.loaded(), result.skipped(), message);
        } catch (RuntimeException e) {
            log.warn("Nạp {} thất bại: {}", spec.fileName(), e.getMessage());
            run.fail(e.getMessage(), clock.instant());
            runRepository.save(run);
            return new ImportSummary.Outcome(spec.dataset(), spec.fileName(), ImportSummary.Status.FAILED, 0, 0,
                    e.getMessage());
        }
    }

    static String sha256(Path file) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (InputStream in = new DigestInputStream(Files.newInputStream(file), digest)) {
                in.transferTo(OutputStream.nullOutputStream());
            }
            return HexFormat.of().formatHex(digest.digest());
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}
