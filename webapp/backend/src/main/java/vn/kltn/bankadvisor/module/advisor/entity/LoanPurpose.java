package vn.kltn.bankadvisor.module.advisor.entity;

import java.util.Set;

/**
 * Mục đích vay của khách hàng cá nhân, và các chương trình tín dụng chính sách liên quan.
 * Chương trình cho doanh nghiệp (DNNVV, hạ tầng) nằm ngoài phạm vi đề tài nên không gắn vào đây.
 */
public enum LoanPurpose {
    HOME_PURCHASE(Set.of()),
    SOCIAL_HOUSING(Set.of("NOXH_145K", "NOXH_U35")),
    CONSUMER(Set.of()),
    CAR(Set.of()),
    HOUSEHOLD_BUSINESS(Set.of()),
    AGRICULTURE(Set.of("NLTS_185K", "NLTS_100K", "LTS_15K"));

    private final Set<String> programCodes;

    LoanPurpose(Set<String> programCodes) {
        this.programCodes = programCodes;
    }

    public Set<String> programCodes() {
        return programCodes;
    }
}
