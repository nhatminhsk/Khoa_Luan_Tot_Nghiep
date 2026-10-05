package vn.kltn.bankadvisor.module.advisor.service;

import vn.kltn.bankadvisor.module.advisor.entity.RepaymentMethod;

import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;

/**
 * Công thức tiền lãi tham khảo. Số tiền làm tròn tới đồng.
 * <p>
 * Đây là ước tính: ngân hàng tính lãi theo số ngày thực tế và có thể áp lãi suất khác khi giao dịch.
 */
public final class InterestCalculator {

    private static final MathContext MC = MathContext.DECIMAL64;
    private static final BigDecimal HUNDRED = BigDecimal.valueOf(100);
    private static final BigDecimal TWELVE = BigDecimal.valueOf(12);

    private InterestCalculator() {
    }

    /** Lãi tiết kiệm trả cuối kỳ: số tiền × lãi suất năm × số tháng / 12. */
    public static long savingsInterest(long amount, BigDecimal annualRatePercent, int termMonths) {
        return BigDecimal.valueOf(amount)
                .multiply(annualRatePercent, MC)
                .divide(HUNDRED, MC)
                .multiply(BigDecimal.valueOf(termMonths), MC)
                .divide(TWELVE, MC)
                .setScale(0, RoundingMode.HALF_UP)
                .longValueExact();
    }

    /** Lịch trả nợ tóm tắt: kỳ đầu, kỳ cuối, tổng lãi, tổng phải trả. */
    public record LoanSchedule(long firstPayment, long lastPayment, long totalInterest, long totalPayment) {
    }

    public static LoanSchedule loan(long amount, BigDecimal annualRatePercent, int months, RepaymentMethod method) {
        if (months <= 0) {
            throw new IllegalArgumentException("Số tháng phải lớn hơn 0");
        }
        BigDecimal principal = BigDecimal.valueOf(amount);
        BigDecimal monthlyRate = annualRatePercent.divide(HUNDRED, MC).divide(TWELVE, MC);
        BigDecimal n = BigDecimal.valueOf(months);
        return switch (method) {
            case DECLINING_BALANCE -> {
                // Gốc chia đều, lãi tính trên dư nợ còn lại: tổng lãi = gốc × lãi tháng × (n + 1) / 2.
                BigDecimal principalPart = principal.divide(n, MC);
                BigDecimal first = principalPart.add(principal.multiply(monthlyRate, MC));
                BigDecimal last = principalPart.add(principalPart.multiply(monthlyRate, MC));
                BigDecimal interest = principal.multiply(monthlyRate, MC)
                        .multiply(n.add(BigDecimal.ONE), MC).divide(BigDecimal.TWO, MC);
                yield schedule(first, last, interest, principal);
            }
            case ANNUITY -> {
                // Trả góp đều: kỳ khoản = gốc × i / (1 − (1 + i)^−n).
                BigDecimal payment = monthlyRate.signum() == 0
                        ? principal.divide(n, MC)
                        : principal.multiply(monthlyRate, MC).divide(
                                BigDecimal.ONE.subtract(BigDecimal.ONE.divide(
                                        BigDecimal.ONE.add(monthlyRate).pow(months, MC), MC)), MC);
                BigDecimal interest = payment.multiply(n, MC).subtract(principal);
                yield schedule(payment, payment, interest, principal);
            }
        };
    }

    private static LoanSchedule schedule(BigDecimal first, BigDecimal last, BigDecimal interest, BigDecimal principal) {
        long totalInterest = round(interest);
        return new LoanSchedule(round(first), round(last), totalInterest, principal.longValueExact() + totalInterest);
    }

    private static long round(BigDecimal value) {
        return value.setScale(0, RoundingMode.HALF_UP).longValueExact();
    }
}
