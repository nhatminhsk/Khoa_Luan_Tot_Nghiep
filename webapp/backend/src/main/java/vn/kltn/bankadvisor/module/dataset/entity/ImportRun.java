package vn.kltn.bankadvisor.module.dataset.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;

/** Một lần nạp một file CSV: dùng để hiện nhật ký cho quản trị viên và để bỏ qua file không đổi (checksum). */
@Entity
@Table(name = "import_run")
public class ImportRun {

    private static final int MAX_MESSAGE = 1000;

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "dataset", nullable = false)
    private String dataset;

    @Column(name = "file_name", nullable = false)
    private String fileName;

    @Column(name = "checksum")
    private String checksum;

    @Column(name = "row_count")
    private Integer rowCount;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false)
    private ImportStatus status;

    @Column(name = "message")
    private String message;

    @Column(name = "started_at", nullable = false)
    private Instant startedAt;

    @Column(name = "finished_at")
    private Instant finishedAt;

    protected ImportRun() {
    }

    public static ImportRun start(String dataset, String fileName, String checksum, Instant now) {
        ImportRun run = new ImportRun();
        run.dataset = dataset;
        run.fileName = fileName;
        run.checksum = checksum;
        run.status = ImportStatus.RUNNING;
        run.startedAt = now;
        return run;
    }

    public void succeed(int rowCount, String message, Instant now) {
        this.status = ImportStatus.SUCCESS;
        this.rowCount = rowCount;
        this.message = truncate(message);
        this.finishedAt = now;
    }

    public void fail(String message, Instant now) {
        this.status = ImportStatus.FAILED;
        this.message = truncate(message);
        this.finishedAt = now;
    }

    private static String truncate(String text) {
        return text == null || text.length() <= MAX_MESSAGE ? text : text.substring(0, MAX_MESSAGE);
    }

    public Long getId() {
        return id;
    }

    public String getDataset() {
        return dataset;
    }

    public String getFileName() {
        return fileName;
    }

    public String getChecksum() {
        return checksum;
    }

    public Integer getRowCount() {
        return rowCount;
    }

    public ImportStatus getStatus() {
        return status;
    }

    public String getMessage() {
        return message;
    }

    public Instant getStartedAt() {
        return startedAt;
    }

    public Instant getFinishedAt() {
        return finishedAt;
    }
}
