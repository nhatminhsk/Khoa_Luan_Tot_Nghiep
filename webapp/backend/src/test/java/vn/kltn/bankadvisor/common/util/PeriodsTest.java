package vn.kltn.bankadvisor.common.util;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PeriodsTest {

    @Test
    void countsQuartersAcrossYears() {
        assertEquals(3, Periods.quartersBetween("2025-Q3", "2026-Q2"));
        assertEquals(0, Periods.quartersBetween("2026-Q2", "2026-Q2"));
    }

    @Test
    void shiftsPeriods() {
        assertEquals("2027-Q1", Periods.shift("2026-Q4", 1));
        assertEquals("2025-Q4", Periods.shift("2026-Q1", -1));
    }

    @Test
    void validatesFormat() {
        assertTrue(Periods.isQuarter("2019-Q1"));
        assertFalse(Periods.isQuarter("2019-Q5"));
        assertFalse(Periods.isQuarter("2019Q1"));
    }
}
