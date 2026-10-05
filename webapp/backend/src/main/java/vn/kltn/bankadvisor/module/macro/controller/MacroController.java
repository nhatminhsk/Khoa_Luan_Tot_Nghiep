package vn.kltn.bankadvisor.module.macro.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.module.macro.dto.InflationResponse;
import vn.kltn.bankadvisor.module.macro.service.InflationService;

/** Số liệu vĩ mô dùng chung (công khai). */
@RestController
@RequestMapping("/api/v1/macro")
public class MacroController {

    private final InflationService inflationService;

    public MacroController(InflationService inflationService) {
        this.inflationService = inflationService;
    }

    @GetMapping("/inflation")
    public ApiResponse<InflationResponse> inflation() {
        return ApiResponse.ok(inflationService.inflation());
    }
}
