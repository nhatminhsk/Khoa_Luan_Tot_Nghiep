package vn.kltn.bankadvisor.module.indicator.entity;

import java.util.Comparator;

/** Chiều "tốt hơn" của chỉ tiêu, nhìn từ độ an toàn của ngân hàng. NEUTRAL: không đánh giá tốt/xấu. */
public enum IndicatorDirection {
    HIGHER_BETTER,
    LOWER_BETTER,
    NEUTRAL;

    /** Thứ tự xếp hạng: phần tử đầu là tốt nhất. NEUTRAL xếp theo giá trị giảm dần. */
    public Comparator<Double> rankingOrder() {
        return this == LOWER_BETTER ? Comparator.naturalOrder() : Comparator.reverseOrder();
    }
}
