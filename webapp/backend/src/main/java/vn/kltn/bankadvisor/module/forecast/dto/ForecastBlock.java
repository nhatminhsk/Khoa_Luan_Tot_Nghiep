package vn.kltn.bankadvisor.module.forecast.dto;

import vn.kltn.bankadvisor.common.api.ResultStatus;

import java.util.List;

/** Dự báo 1–4 quý của một ngân hàng, mỗi chỉ tiêu một chuỗi, kèm vùng sai số và mốc naive. */
public record ForecastBlock(ResultStatus status, String originPeriod, List<IndicatorForecast> indicators) {

    public static ForecastBlock notAvailable() {
        return new ForecastBlock(ResultStatus.NOT_AVAILABLE, null, List.of());
    }

    public record IndicatorForecast(String indicatorCode, String method, List<Point> points) {
    }

    public record Point(String targetPeriod, int horizon, double value, Double lower, Double upper, Double naiveValue) {
    }
}
