package vn.kltn.bankadvisor.module.program.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.module.program.dto.BankProgramResponse;
import vn.kltn.bankadvisor.module.program.dto.ProgramResponse;
import vn.kltn.bankadvisor.module.program.service.ProgramService;

import java.util.List;

@RestController
@RequestMapping("/api/v1")
public class ProgramController {

    private final ProgramService programService;

    public ProgramController(ProgramService programService) {
        this.programService = programService;
    }

    @GetMapping("/programs")
    public ApiResponse<List<ProgramResponse>> all() {
        return ApiResponse.ok(programService.all());
    }

    @GetMapping("/banks/{ticker}/programs")
    public ApiResponse<List<BankProgramResponse>> forBank(@PathVariable String ticker) {
        return ApiResponse.ok(programService.forBank(ticker));
    }
}
