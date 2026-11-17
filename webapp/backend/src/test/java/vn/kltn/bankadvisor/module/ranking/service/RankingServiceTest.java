package vn.kltn.bankadvisor.module.ranking.service;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class RankingServiceTest {

    private static final List<Long> BUCKETS = List.of(100_000_000L, 500_000_000L, 1_000_000_000L, 5_000_000_000L);

    @Test
    void amountPicksLargestBucketNotAboveIt() {
        assertEquals(100_000_000L, RankingService.chooseAmount(BUCKETS, 100_000_000L));
        assertEquals(100_000_000L, RankingService.chooseAmount(BUCKETS, 499_999_999L));
        assertEquals(1_000_000_000L, RankingService.chooseAmount(BUCKETS, 4_000_000_000L));
        assertEquals(5_000_000_000L, RankingService.chooseAmount(BUCKETS, 90_000_000_000L));
    }

    @Test
    void amountBelowEveryBucketUsesSmallestAndMissingAmountUsesDefaultTable() {
        assertEquals(100_000_000L, RankingService.chooseAmount(BUCKETS, 10_000_000L));
        assertNull(RankingService.chooseAmount(BUCKETS, null));
        assertNull(RankingService.chooseAmount(List.of(), 1_000_000_000L));
    }
}
