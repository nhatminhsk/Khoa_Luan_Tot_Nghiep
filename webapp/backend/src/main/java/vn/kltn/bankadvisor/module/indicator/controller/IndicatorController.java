package vn.kltn.bankadvisor.module.indicator.controller;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.module.indicator.dto.BankIndicatorsResponse;
import vn.kltn.bankadvisor.module.indicator.dto.IndicatorComparisonResponse;
import vn.kltn.bankadvisor.module.indicator.dto.IndicatorResponse;
import vn.kltn.bankadvisor.module.indicator.dto.IndicatorSnapshotResponse;
import vn.kltn.bankadvisor.module.indicator.service.IndicatorService;

import java.util.List;

@RestController
@RequestMapping("/api/v1")
public class IndicatorController {

    private final IndicatorService indicatorService;

    public IndicatorController(IndicatorService indicatorService) {
        this.indicatorService = indicatorService;
    }

    /** Danh mục chỉ tiêu (tên, nhóm CAMELS, đơn vị, chiều tốt). */
    @GetMapping("/indicators")
    public ApiResponse<List<IndicatorResponse>> catalog() {
        return ApiResponse.ok(indicatorService.catalog());
    }

    /** Số gần nhất của 22 ngân hàng cho mọi chỉ tiêu. */
    @GetMapping("/indicators/snapshot")
    public ApiResponse<IndicatorSnapshotResponse> snapshot() {
        return ApiResponse.ok(indicatorService.snapshot());
    }

    /** Một chỉ tiêu theo quý cho 1–4 ngân hàng, kèm trung vị 22 ngân hàng. */
    @GetMapping("/indicators/{code}/comparison")
    public ApiResponse<IndicatorComparisonResponse> compare(
            @PathVariable String code,
            @RequestParam @NotEmpty(message = "Chọn ít nhất một ngân hàng")
            @Size(max = 4, message = "So sánh tối đa 4 ngân hàng") List<String> tickers) {
        return ApiResponse.ok(indicatorService.compare(code, tickers));
    }

    /** Toàn bộ chuỗi chỉ tiêu của một ngân hàng. */
    @GetMapping("/banks/{ticker}/indicators")
    public ApiResponse<BankIndicatorsResponse> bankIndicators(@PathVariable String ticker) {
        return ApiResponse.ok(indicatorService.bankIndicators(ticker));
    }
}
