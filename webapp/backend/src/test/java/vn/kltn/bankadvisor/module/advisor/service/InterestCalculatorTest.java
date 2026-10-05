package vn.kltn.bankadvisor.module.advisor.service;

import org.junit.jupiter.api.Test;
import vn.kltn.bankadvisor.module.advisor.entity.RepaymentMethod;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class InterestCalculatorTest {

    @Test
    void savingsInterestIsSimpleInterestPaidAtMaturity() {
        // 100 triệu, 6%/năm, 12 tháng → 6 triệu; 6 tháng → 3 triệu.
        assertEquals(6_000_000, InterestCalculator.savingsInterest(100_000_000, new BigDecimal("6.0"), 12));
        assertEquals(3_000_000, InterestCalculator.savingsInterest(100_000_000, new BigDecimal("6.0"), 6));
        // 50 triệu, 4,75%/năm, 3 tháng = 593.750 đồng.
        assertEquals(593_750, InterestCalculator.savingsInterest(50_000_000, new BigDecimal("4.75"), 3));
    }

    @Test
    void decliningBalanceSplitsPrincipalEvenly() {
        // 120 triệu, 12%/năm (1%/tháng), 12 tháng: gốc 10 triệu/tháng.
        var s = InterestCalculator.loan(120_000_000, new BigDecimal("12"), 12, RepaymentMethod.DECLINING_BALANCE);
        assertEquals(11_200_000, s.firstPayment());     // 10tr gốc + 1,2tr lãi
        assertEquals(10_100_000, s.lastPayment());      // 10tr gốc + 0,1tr lãi
        assertEquals(7_800_000, s.totalInterest());     // 120tr × 1% × 13 / 2
        assertEquals(127_800_000, s.totalPayment());
    }

    @Test
    void annuityPaysTheSameAmountEveryMonth() {
        // 120 triệu, 12%/năm, 12 tháng: kỳ khoản ≈ 10.661.855 đồng.
        var s = InterestCalculator.loan(120_000_000, new BigDecimal("12"), 12, RepaymentMethod.ANNUITY);
        assertEquals(10_661_855, s.firstPayment());
        assertEquals(s.firstPayment(), s.lastPayment());
        assertEquals(s.totalPayment() - 120_000_000, s.totalInterest());
    }

    @Test
    void annuityWithZeroRateIsPrincipalOverMonths() {
        var s = InterestCalculator.loan(12_000_000, BigDecimal.ZERO, 12, RepaymentMethod.ANNUITY);
        assertEquals(1_000_000, s.firstPayment());
        assertEquals(0, s.totalInterest());
    }

    @Test
    void rejectsNonPositiveTerm() {
        assertThrows(IllegalArgumentException.class,
                () -> InterestCalculator.loan(1_000_000, BigDecimal.ONE, 0, RepaymentMethod.ANNUITY));
    }
}
