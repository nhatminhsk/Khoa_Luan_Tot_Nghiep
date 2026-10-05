package vn.kltn.bankadvisor.module.program.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;

/** Chương trình tín dụng chính sách (nhà ở xã hội, nông lâm thủy sản...). Nạp từ programs.csv. */
@Entity
@Immutable
@Table(name = "policy_program")
public class PolicyProgram {

    @Id
    @Column(name = "code")
    private String code;

    @Column(name = "name", nullable = false)
    private String name;

    @Enumerated(EnumType.STRING)
    @Column(name = "category", nullable = false)
    private ProgramCategory category;

    protected PolicyProgram() {
    }

    public String getCode() {
        return code;
    }

    public String getName() {
        return name;
    }

    public ProgramCategory getCategory() {
        return category;
    }
}
