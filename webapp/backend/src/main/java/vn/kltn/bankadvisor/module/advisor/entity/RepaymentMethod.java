package vn.kltn.bankadvisor.module.advisor.entity;

/** Cách trả nợ. */
public enum RepaymentMethod {
    /** Gốc chia đều, lãi tính trên dư nợ giảm dần (phổ biến ở Việt Nam). */
    DECLINING_BALANCE,
    /** Trả góp đều mỗi tháng (gốc + lãi bằng nhau). */
    ANNUITY
}
