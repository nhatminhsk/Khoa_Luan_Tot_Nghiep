package vn.kltn.bankadvisor.module.overview.dto;

import vn.kltn.bankadvisor.module.dataset.dto.DatasetsResponse;
import vn.kltn.bankadvisor.module.rate.dto.BestRatesResponse;
import vn.kltn.bankadvisor.module.ranking.dto.RankingBlock;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

/** Dữ liệu trang Tổng quan, gộp một lần gọi để trang tải nhanh. */
public record OverviewResponse(
        LocalDate rateDate,
        LocalDate previousRateDate,
        Market market,
        Market counterMarket,
        List<BestRatesResponse.Item> bestRates,
        RankingBlock savingsRanking,
        RankingBlock loanRanking,
        String latestQuarter,
        List<DatasetsResponse.Source> datasets
) {

    /** Tóm tắt lãi suất 12 tháng của một kênh hôm nay so với ngày liền trước ({@code market}: trực tuyến, {@code counterMarket}: tại quầy). */
    public record Market(
            int referenceTermMonths,
            BigDecimal median,
            BestRatesResponse.Best highest,
            BigDecimal lowest,
            int banksQuoted,
            int banksRaised,
            int banksLowered,
            int banksUnchanged
    ) {
    }
}
