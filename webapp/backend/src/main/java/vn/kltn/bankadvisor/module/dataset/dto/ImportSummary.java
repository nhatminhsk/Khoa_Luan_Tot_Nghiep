package vn.kltn.bankadvisor.module.dataset.dto;

import java.util.List;

/** Kết quả một lượt nạp toàn bộ data/serving. */
public record ImportSummary(List<Outcome> outcomes) {

    public enum Status {
        /** Đã nạp. */
        IMPORTED,
        /** File không đổi so với lần nạp thành công gần nhất. */
        UNCHANGED,
        /** Chưa có file (bình thường với kết quả thuật toán chưa chốt). */
        MISSING,
        FAILED
    }

    public record Outcome(String dataset, String fileName, Status status, int loaded, int skipped, String message) {
    }
}
