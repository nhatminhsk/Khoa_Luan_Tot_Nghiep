package vn.kltn.bankadvisor.module.dataset.importer;

import java.util.List;

import static vn.kltn.bankadvisor.module.dataset.importer.ColumnType.BOOL;
import static vn.kltn.bankadvisor.module.dataset.importer.ColumnType.DATE;
import static vn.kltn.bankadvisor.module.dataset.importer.ColumnType.DECIMAL;
import static vn.kltn.bankadvisor.module.dataset.importer.ColumnType.DOUBLE;
import static vn.kltn.bankadvisor.module.dataset.importer.ColumnType.INDICATOR;
import static vn.kltn.bankadvisor.module.dataset.importer.ColumnType.INT;
import static vn.kltn.bankadvisor.module.dataset.importer.ColumnType.LONG;
import static vn.kltn.bankadvisor.module.dataset.importer.ColumnType.PROGRAM;
import static vn.kltn.bankadvisor.module.dataset.importer.ColumnType.TEXT;
import static vn.kltn.bankadvisor.module.dataset.importer.ColumnType.TICKER;
import static vn.kltn.bankadvisor.module.dataset.importer.TableSpec.LoadMode.REPLACE;
import static vn.kltn.bankadvisor.module.dataset.importer.TableSpec.LoadMode.UPSERT;
import static vn.kltn.bankadvisor.module.dataset.importer.TableSpec.opt;
import static vn.kltn.bankadvisor.module.dataset.importer.TableSpec.req;

/**
 * Hợp đồng dữ liệu với pipeline: mỗi file trong data/serving nạp vào bảng nào. Schema chi tiết ở
 * data/serving/README.md. Thứ tự danh sách là thứ tự nạp (bảng tham chiếu trước).
 */
public final class ServingDatasets {

    public static final String DEPOSIT_RATES = "deposit_rates";
    public static final String RANKINGS = "rankings";

    /** Kết quả thuật toán xếp hạng (serving/rankings.py). */
    public static final List<String> ALGORITHM_OUTPUTS = List.of(RANKINGS);

    public static final List<TableSpec> ALL = List.of(
            new TableSpec("banks", "banks.csv", "bank", UPSERT, List.of("ticker"), null, List.of(
                    req("ticker", TEXT), req("short_name", TEXT), req("full_name", TEXT))),
            new TableSpec("indicators", "indicators.csv", "indicator", UPSERT, List.of("code"), null, List.of(
                    req("code", TEXT), req("name", TEXT), req("camels_group", TEXT), req("unit", TEXT),
                    req("direction", TEXT), opt("description", TEXT), req("display_order", INT))),
            new TableSpec("programs", "programs.csv", "policy_program", UPSERT, List.of("code"), null, List.of(
                    req("program_code", "code", TEXT), req("program_name", "name", TEXT), req("category", TEXT))),

            new TableSpec("bank_quarterly", "bank_quarterly.csv", "bank_quarter_value", REPLACE, List.of(), "period",
                    List.of(req("ticker", TICKER), req("period", TEXT), req("period_end", DATE),
                            req("indicator", "indicator_code", INDICATOR), req("value", "val", DOUBLE))),
            new TableSpec(DEPOSIT_RATES, "deposit_rates.csv", "deposit_rate", REPLACE, List.of(), "rate_date",
                    List.of(req("rate_date", DATE), req("ticker", TICKER), req("term_months", INT),
                            req("channel", TEXT), req("rate_percent", DECIMAL), opt("source", TEXT))),
            new TableSpec("deposit_rate_tiers", "deposit_rate_tiers.csv", "deposit_rate_tier", REPLACE, List.of(),
                    null, List.of(req("ticker", TICKER), req("term_months", INT), req("channel", TEXT),
                    req("min_amount_vnd", LONG), req("rate_percent", DECIMAL), req("base_rate_percent", DECIMAL),
                    req("tier_label", TEXT), opt("valid_from", DATE), opt("source", TEXT))),
            new TableSpec("lending_rates", "lending_rates.csv", "lending_rate", REPLACE, List.of(), "rate_month",
                    List.of(req("month", "rate_month", TEXT), req("ticker", TICKER),
                            req("lending_avg_percent", DECIMAL), opt("deposit_avg_percent", DECIMAL),
                            opt("segment", TEXT), opt("basis", TEXT), opt("source", TEXT),
                            opt("source_url", TEXT))),
            new TableSpec("program_participation", "program_participation.csv", "program_participation", REPLACE,
                    List.of(), null, List.of(req("program_code", PROGRAM), req("ticker", TICKER),
                    req("participates", BOOL), opt("list_as_of", DATE), opt("source_url", TEXT))),
            new TableSpec("program_rates", "program_rates.csv", "program_rate", REPLACE, List.of(), null, List.of(
                    req("program_code", PROGRAM), req("borrower_group", TEXT), opt("valid_from", DATE),
                    opt("valid_to", DATE), opt("rate_pct_year", "rate_percent", DECIMAL),
                    opt("spread_below_avg_min_pct", "spread_min", DECIMAL),
                    opt("spread_below_avg_max_pct", "spread_max", DECIMAL), opt("source_url", TEXT))),
            new TableSpec("macro_cpi", "macro_cpi.csv", "macro_cpi", REPLACE, List.of(), "cpi_month", List.of(
                    req("month", "cpi_month", TEXT), req("cpi_yoy_percent", DOUBLE), opt("cpi_mom_percent", DOUBLE),
                    opt("source_url", TEXT))),
            new TableSpec("bank_ownership", "bank_ownership.csv", "bank_ownership", REPLACE, List.of(), null, List.of(
                    req("ticker", TICKER), req("as_of_date", DATE), opt("state_own_percent", DOUBLE),
                    opt("foreign_own_percent", DOUBLE), opt("foreign_room_percent", DOUBLE), opt("source", TEXT))),
            new TableSpec("datasets", "datasets.csv", "dataset_info", REPLACE, List.of(), null, List.of(
                    req("dataset", TEXT), req("name", TEXT), opt("source", TEXT), req("frequency", TEXT),
                    opt("last_updated", TEXT), opt("row_count", INT), opt("coverage_note", TEXT))),

            new TableSpec(RANKINGS, "rankings.csv", "ranking_result", REPLACE, List.of(), "as_of_period", List.of(
                    req("as_of_period", TEXT), req("purpose", TEXT), opt("term_months", INT), opt("channel", TEXT),
                    opt("amount_vnd", LONG), req("ticker", TICKER), req("rank", "rank_value", INT),
                    opt("rank_low", INT), opt("rank_high", INT), opt("score", DOUBLE), opt("group_label", TEXT),
                    opt("top_positive", TEXT), opt("top_negative", TEXT), opt("method_version", TEXT),
                    opt("p_top1", DOUBLE), opt("p_top3", DOUBLE), opt("rates_as_of", TEXT),
                    opt("uninsured_share", DOUBLE), opt("safety_weight", DOUBLE)))
    );

    private ServingDatasets() {
    }
}
