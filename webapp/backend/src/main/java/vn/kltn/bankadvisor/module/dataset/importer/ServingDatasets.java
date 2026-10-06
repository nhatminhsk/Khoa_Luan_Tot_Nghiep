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
    public static final String FORECASTS = "forecasts";
    public static final String APP_ASPECTS = "app_aspects";

    /** Ba tập kết quả thuật toán — rỗng cho tới khi mô hình chốt. */
    public static final List<String> ALGORITHM_OUTPUTS = List.of(RANKINGS, FORECASTS, APP_ASPECTS);

    public static final List<TableSpec> ALL = List.of(
            new TableSpec("banks", "banks.csv", "bank", UPSERT, List.of("ticker"), null, List.of(
                    req("ticker", TEXT), req("short_name", TEXT), req("full_name", TEXT), opt("app_name", TEXT))),
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
                            opt("source_url", TEXT))),
            new TableSpec("app_store", "app_store.csv", "app_store_snapshot", REPLACE, List.of(), null, List.of(
                    req("ticker", TICKER), req("store", TEXT), req("snapshot_date", DATE), opt("app_name", TEXT),
                    opt("score", DOUBLE), opt("ratings", LONG))),
            new TableSpec("app_reviews_monthly", "app_reviews_monthly.csv", "app_review_monthly", REPLACE, List.of(),
                    null, List.of(req("ticker", TICKER), req("month", "review_month", TEXT), req("n_reviews", INT),
                    opt("mean_score", DOUBLE), opt("pct_1star", DOUBLE), opt("pct_5star", DOUBLE),
                    req("usable", BOOL))),
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
                    req("as_of_period", TEXT), req("purpose", TEXT), req("ticker", TICKER),
                    req("rank", "rank_value", INT), opt("rank_low", INT), opt("rank_high", INT),
                    opt("score", DOUBLE), opt("group_label", TEXT), opt("top_positive", TEXT),
                    opt("top_negative", TEXT), opt("method_version", TEXT))),
            new TableSpec(FORECASTS, "forecasts.csv", "forecast_point", REPLACE, List.of(), "origin_period", List.of(
                    req("ticker", TICKER), req("indicator", "indicator_code", INDICATOR),
                    req("origin_period", TEXT), req("target_period", TEXT), req("horizon", INT),
                    req("value", "val", DOUBLE), opt("lower", "lower_bound", DOUBLE),
                    opt("upper", "upper_bound", DOUBLE), opt("naive_value", DOUBLE), opt("method", TEXT))),
            new TableSpec(APP_ASPECTS, "app_aspects.csv", "app_aspect_score", REPLACE, List.of(), "period", List.of(
                    req("ticker", TICKER), req("period", TEXT), req("aspect", TEXT), req("score", DOUBLE),
                    req("n_reviews", INT)))
    );

    private ServingDatasets() {
    }
}
