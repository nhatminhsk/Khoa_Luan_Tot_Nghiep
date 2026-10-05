package vn.kltn.bankadvisor.module.program.dto;

import vn.kltn.bankadvisor.module.program.entity.ProgramCategory;

import java.time.LocalDate;

/** Việc tham gia một chương trình của một ngân hàng. */
public record BankProgramResponse(
        String code,
        String name,
        ProgramCategory category,
        boolean participates,
        LocalDate listAsOf,
        String sourceUrl
) {
}
