package vn.kltn.bankadvisor.module.bank.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;

/** Ngân hàng trong phạm vi đề tài (22 mã niêm yết). Nạp từ banks.csv, chỉ đọc. */
@Entity
@Immutable
@Table(name = "bank")
public class Bank {

    @Id
    @Column(name = "ticker")
    private String ticker;

    @Column(name = "short_name", nullable = false)
    private String shortName;

    @Column(name = "full_name", nullable = false)
    private String fullName;

    protected Bank() {
    }

    public String getTicker() {
        return ticker;
    }

    public String getShortName() {
        return shortName;
    }

    public String getFullName() {
        return fullName;
    }
}
