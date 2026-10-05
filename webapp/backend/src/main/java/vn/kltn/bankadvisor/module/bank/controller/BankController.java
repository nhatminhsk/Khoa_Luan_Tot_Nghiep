package vn.kltn.bankadvisor.module.bank.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.module.bank.dto.BankResponse;
import vn.kltn.bankadvisor.module.bank.service.BankService;

import java.util.List;

@RestController
@RequestMapping("/api/v1/banks")
public class BankController {

    private final BankService bankService;

    public BankController(BankService bankService) {
        this.bankService = bankService;
    }

    @GetMapping
    public ApiResponse<List<BankResponse>> list() {
        return ApiResponse.ok(bankService.findAll());
    }

    @GetMapping("/{ticker}")
    public ApiResponse<BankResponse> get(@PathVariable String ticker) {
        return ApiResponse.ok(bankService.get(ticker));
    }
}
