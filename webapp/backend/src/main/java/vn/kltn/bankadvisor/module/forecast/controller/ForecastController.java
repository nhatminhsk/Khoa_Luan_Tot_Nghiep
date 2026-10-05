package vn.kltn.bankadvisor.module.forecast.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.module.forecast.dto.ForecastBlock;
import vn.kltn.bankadvisor.module.forecast.service.ForecastService;

@RestController
@RequestMapping("/api/v1/banks/{ticker}/forecasts")
public class ForecastController {

    private final ForecastService forecastService;

    public ForecastController(ForecastService forecastService) {
        this.forecastService = forecastService;
    }

    @GetMapping
    public ApiResponse<ForecastBlock> forBank(@PathVariable String ticker) {
        return ApiResponse.ok(forecastService.forBank(ticker));
    }
}
