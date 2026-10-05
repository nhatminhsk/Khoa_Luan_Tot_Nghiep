package vn.kltn.bankadvisor.module.need.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import vn.kltn.bankadvisor.module.advisor.entity.LoanPurpose;
import vn.kltn.bankadvisor.module.advisor.entity.RepaymentMethod;
import vn.kltn.bankadvisor.module.rate.entity.Channel;
import vn.kltn.bankadvisor.module.ranking.entity.Purpose;

import java.time.Instant;

/** Nhu cầu gửi tiết kiệm / vay và trọng số tiêu chí người dùng đã lưu để mở lại nhanh. */
@Entity
@Table(name = "saved_need")
public class SavedNeed {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Enumerated(EnumType.STRING)
    @Column(name = "purpose", nullable = false)
    private Purpose purpose;

    @Column(name = "label", nullable = false)
    private String label;

    @Column(name = "amount", nullable = false)
    private long amount;

    @Column(name = "term_months", nullable = false)
    private int termMonths;

    @Enumerated(EnumType.STRING)
    @Column(name = "channel")
    private Channel channel;

    @Enumerated(EnumType.STRING)
    @Column(name = "loan_purpose")
    private LoanPurpose loanPurpose;

    @Enumerated(EnumType.STRING)
    @Column(name = "repayment")
    private RepaymentMethod repayment;

    @Column(name = "weight_rate")
    private Integer weightRate;

    @Column(name = "weight_safety")
    private Integer weightSafety;

    @Column(name = "weight_app")
    private Integer weightApp;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    protected SavedNeed() {
    }

    public static SavedNeed create(long userId, Instant now) {
        SavedNeed need = new SavedNeed();
        need.userId = userId;
        need.createdAt = now;
        need.updatedAt = now;
        return need;
    }

    public void apply(Purpose purpose, String label, long amount, int termMonths, Channel channel,
                      LoanPurpose loanPurpose, RepaymentMethod repayment,
                      Integer weightRate, Integer weightSafety, Integer weightApp, Instant now) {
        this.purpose = purpose;
        this.label = label;
        this.amount = amount;
        this.termMonths = termMonths;
        // Chỉ giữ trường thuộc đúng mục đích, tránh lưu dữ liệu thừa.
        boolean savings = purpose == Purpose.SAVINGS;
        this.channel = savings ? channel : null;
        this.weightRate = savings ? weightRate : null;
        this.weightSafety = savings ? weightSafety : null;
        this.weightApp = savings ? weightApp : null;
        this.loanPurpose = savings ? null : loanPurpose;
        this.repayment = savings ? null : repayment;
        this.updatedAt = now;
    }

    public Long getId() {
        return id;
    }

    public Long getUserId() {
        return userId;
    }

    public Purpose getPurpose() {
        return purpose;
    }

    public String getLabel() {
        return label;
    }

    public long getAmount() {
        return amount;
    }

    public int getTermMonths() {
        return termMonths;
    }

    public Channel getChannel() {
        return channel;
    }

    public LoanPurpose getLoanPurpose() {
        return loanPurpose;
    }

    public RepaymentMethod getRepayment() {
        return repayment;
    }

    public Integer getWeightRate() {
        return weightRate;
    }

    public Integer getWeightSafety() {
        return weightSafety;
    }

    public Integer getWeightApp() {
        return weightApp;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }
}
