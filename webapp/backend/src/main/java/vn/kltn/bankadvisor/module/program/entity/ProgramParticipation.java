package vn.kltn.bankadvisor.module.program.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;

import java.time.LocalDate;

/** Ngân hàng có tham gia chương trình hay không, theo danh sách công bố tại một ngày. */
@Entity
@Immutable
@Table(name = "program_participation")
public class ProgramParticipation {

    @Id
    private Long id;

    @Column(name = "program_code", nullable = false)
    private String programCode;

    @Column(name = "ticker", nullable = false)
    private String ticker;

    @Column(name = "participates", nullable = false)
    private boolean participates;

    @Column(name = "list_as_of")
    private LocalDate listAsOf;

    @Column(name = "source_url")
    private String sourceUrl;

    protected ProgramParticipation() {
    }

    public String getProgramCode() {
        return programCode;
    }

    public String getTicker() {
        return ticker;
    }

    public boolean isParticipates() {
        return participates;
    }

    public LocalDate getListAsOf() {
        return listAsOf;
    }

    public String getSourceUrl() {
        return sourceUrl;
    }
}
