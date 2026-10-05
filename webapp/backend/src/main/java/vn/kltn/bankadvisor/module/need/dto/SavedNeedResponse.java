package vn.kltn.bankadvisor.module.need.dto;

import vn.kltn.bankadvisor.module.advisor.entity.LoanPurpose;
import vn.kltn.bankadvisor.module.advisor.entity.RepaymentMethod;
import vn.kltn.bankadvisor.module.need.entity.SavedNeed;
import vn.kltn.bankadvisor.module.rate.entity.Channel;
import vn.kltn.bankadvisor.module.ranking.entity.Purpose;

import java.time.Instant;

public record SavedNeedResponse(
        long id,
        Purpose purpose,
        String label,
        long amount,
        int termMonths,
        Channel channel,
        LoanPurpose loanPurpose,
        RepaymentMethod repayment,
        Integer weightRate,
        Integer weightSafety,
        Integer weightApp,
        Instant updatedAt
) {

    public static SavedNeedResponse from(SavedNeed n) {
        return new SavedNeedResponse(n.getId(), n.getPurpose(), n.getLabel(), n.getAmount(), n.getTermMonths(),
                n.getChannel(), n.getLoanPurpose(), n.getRepayment(), n.getWeightRate(), n.getWeightSafety(),
                n.getWeightApp(), n.getUpdatedAt());
    }
}
