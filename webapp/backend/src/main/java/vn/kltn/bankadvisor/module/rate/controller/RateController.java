package vn.kltn.bankadvisor.module.rate.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.common.exception.AppException;
import vn.kltn.bankadvisor.common.exception.ErrorCode;
import vn.kltn.bankadvisor.module.rate.dto.BankRatesResponse;
import vn.kltn.bankadvisor.module.rate.dto.BestRatesResponse;
import vn.kltn.bankadvisor.module.rate.dto.DepositRateTableResponse;
import vn.kltn.bankadvisor.module.rate.dto.LendingRateResponse;
import vn.kltn.bankadvisor.module.rate.dto.RateChangesResponse;
import vn.kltn.bankadvisor.module.rate.dto.RateTrendPoint;
import vn.kltn.bankadvisor.module.rate.entity.Channel;
import vn.kltn.bankadvisor.module.rate.service.RateService;

import java.util.List;

@RestController
@RequestMapping("/api/v1")
public class RateController {

    private final RateService rateService;

    public RateController(RateService rateService) {
        this.rateService = rateService;
    }

    /** Bảng lãi suất tiết kiệm hôm nay của 22 ngân hàng theo một kênh. */
    @GetMapping("/rates/deposit")
    public ApiResponse<DepositRateTableResponse> depositTable(
            @RequestParam(defaultValue = "ONLINE") Channel channel) {
        return ApiResponse.ok(rateService.depositTable(channel));
    }

    /** Lãi suất cao nhất hôm nay theo từng kỳ hạn. */
    @GetMapping("/rates/deposit/best")
    public ApiResponse<BestRatesResponse> best() {
        return ApiResponse.ok(rateService.bestRates());
    }

    /** Diễn biến lãi suất thị trường: thấp nhất, trung vị, cao nhất theo ngày. */
    @GetMapping("/rates/deposit/trend")
    public ApiResponse<List<RateTrendPoint>> trend(
            @RequestParam(defaultValue = "12") int term,
            @RequestParam(defaultValue = "ONLINE") Channel channel) {
        return ApiResponse.ok(rateService.trend(term, channel));
    }

    /** Các lần ngân hàng đổi lãi suất trong {@code days} ngày gần nhất (1–366), mới nhất trước. */
    @GetMapping("/rates/deposit/changes")
    public ApiResponse<RateChangesResponse> changes(@RequestParam(defaultValue = "30") int days) {
        if (days < 1 || days > 366) {
            throw new AppException(ErrorCode.BAD_REQUEST, "Số ngày phải từ 1 đến 366");
        }
        return ApiResponse.ok(rateService.changes(days));
    }

    /** Lãi suất cho vay bình quân, tháng gần nhất của từng ngân hàng. */
    @GetMapping("/rates/lending")
    public ApiResponse<List<LendingRateResponse>> lending() {
        return ApiResponse.ok(rateService.latestLending());
    }

    @GetMapping("/banks/{ticker}/rates")
    public ApiResponse<BankRatesResponse> bankRates(@PathVariable String ticker) {
        return ApiResponse.ok(rateService.bankRates(ticker));
    }

    @GetMapping("/banks/{ticker}/lending-rates")
    public ApiResponse<List<LendingRateResponse>> bankLending(@PathVariable String ticker) {
        return ApiResponse.ok(rateService.bankLending(ticker));
    }
}
