package vn.kltn.bankadvisor.common.util;

import java.util.Collection;
import java.util.OptionalDouble;

public final class Stats {

    private Stats() {
    }

    /** Trung vị; rỗng nếu không có giá trị. */
    public static OptionalDouble median(Collection<Double> values) {
        double[] sorted = values.stream().filter(v -> v != null && !v.isNaN()).mapToDouble(Double::doubleValue)
                .sorted().toArray();
        if (sorted.length == 0) {
            return OptionalDouble.empty();
        }
        int mid = sorted.length / 2;
        return OptionalDouble.of(sorted.length % 2 == 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2.0);
    }
}
