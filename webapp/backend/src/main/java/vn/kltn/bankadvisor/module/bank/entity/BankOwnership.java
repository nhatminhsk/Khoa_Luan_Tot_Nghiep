package vn.kltn.bankadvisor.module.bank.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;

import java.time.LocalDate;

/** Cơ cấu sở hữu của một ngân hàng (ảnh chụp mới nhất). Nạp từ bank_ownership.csv, chỉ đọc. */
@Entity
@Immutable
@Table(name = "bank_ownership")
public class BankOwnership {

    @Id
    @Column(name = "ticker")
    private String ticker;

    @Column(name = "as_of_date", nullable = false)
    private LocalDate asOfDate;

    @Column(name = "state_own_percent")
    private Double statePercent;

    @Column(name = "foreign_own_percent")
    private Double foreignPercent;

    @Column(name = "foreign_room_percent")
    private Double foreignRoomPercent;

    @Column(name = "source")
    private String source;

    protected BankOwnership() {
    }

    public String getTicker() {
        return ticker;
    }

    public LocalDate getAsOfDate() {
        return asOfDate;
    }

    public Double getStatePercent() {
        return statePercent;
    }

    public Double getForeignPercent() {
        return foreignPercent;
    }

    public Double getForeignRoomPercent() {
        return foreignRoomPercent;
    }

    public String getSource() {
        return source;
    }
}
