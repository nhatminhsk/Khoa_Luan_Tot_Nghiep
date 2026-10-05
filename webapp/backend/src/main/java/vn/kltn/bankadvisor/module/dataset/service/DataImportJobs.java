package vn.kltn.bankadvisor.module.dataset.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import vn.kltn.bankadvisor.common.config.AppProperties;

/**
 * Nạp dữ liệu tự động: một lần khi khởi động, và hằng ngày theo lịch (mặc định 16:00, sau lần crawl 15:30).
 * File không đổi thì bỏ qua, nên chạy nhiều lần không tốn gì.
 */
@Component
@Order(10)
public class DataImportJobs implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(DataImportJobs.class);

    private final DataImportService importService;
    private final boolean onStartup;

    public DataImportJobs(DataImportService importService, AppProperties properties) {
        this.importService = importService;
        this.onStartup = properties.dataImport().onStartup();
    }

    @Override
    public void run(ApplicationArguments args) {
        if (onStartup) {
            runSafely("khởi động");
        }
    }

    @Scheduled(cron = "${app.data-import.cron}", zone = "Asia/Ho_Chi_Minh")
    public void scheduled() {
        runSafely("theo lịch");
    }

    private void runSafely(String trigger) {
        try {
            importService.importAll(false);
        } catch (RuntimeException e) {
            log.warn("Nạp dữ liệu ({}) không chạy: {}", trigger, e.getMessage());
        }
    }
}
