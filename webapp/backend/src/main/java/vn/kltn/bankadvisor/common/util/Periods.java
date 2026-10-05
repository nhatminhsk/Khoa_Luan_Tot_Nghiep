package vn.kltn.bankadvisor.common.util;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Xử lý kỳ quý dạng {@code YYYY-Qn}. Chuỗi này so sánh theo thứ tự từ điển là đúng thứ tự thời gian,
 * nên có thể dùng thẳng trong ORDER BY và so sánh chuỗi.
 */
public final class Periods {

    private static final Pattern QUARTER = Pattern.compile("^(\\d{4})-Q([1-4])$");

    private Periods() {
    }

    public static boolean isQuarter(String period) {
        return period != null && QUARTER.matcher(period).matches();
    }

    /** Số quý tính từ năm 0, để trừ hai kỳ cho nhau. */
    public static int index(String period) {
        Matcher m = QUARTER.matcher(period);
        if (!m.matches()) {
            throw new IllegalArgumentException("Kỳ không hợp lệ: " + period);
        }
        return Integer.parseInt(m.group(1)) * 4 + Integer.parseInt(m.group(2)) - 1;
    }

    /** Khoảng cách tính bằng quý, {@code to - from}. */
    public static int quartersBetween(String from, String to) {
        return index(to) - index(from);
    }

    public static String shift(String period, int quarters) {
        int idx = index(period) + quarters;
        return (idx / 4) + "-Q" + (idx % 4 + 1);
    }
}
