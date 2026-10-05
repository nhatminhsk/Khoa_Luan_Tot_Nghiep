package vn.kltn.bankadvisor.module.ranking.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import vn.kltn.bankadvisor.common.api.ApiResponse;
import vn.kltn.bankadvisor.module.ranking.dto.RankingBlock;
import vn.kltn.bankadvisor.module.ranking.entity.Purpose;
import vn.kltn.bankadvisor.module.ranking.service.RankingService;

@RestController
@RequestMapping("/api/v1/rankings")
public class RankingController {

    private final RankingService rankingService;

    public RankingController(RankingService rankingService) {
        this.rankingService = rankingService;
    }

    @GetMapping
    public ApiResponse<RankingBlock> latest(@RequestParam Purpose purpose,
                                            @RequestParam(defaultValue = "0") int limit) {
        return ApiResponse.ok(rankingService.latest(purpose, limit));
    }
}
