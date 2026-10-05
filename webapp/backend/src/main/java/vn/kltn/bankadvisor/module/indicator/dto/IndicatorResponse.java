package vn.kltn.bankadvisor.module.indicator.dto;

import vn.kltn.bankadvisor.module.indicator.entity.Indicator;
import vn.kltn.bankadvisor.module.indicator.entity.IndicatorDirection;
import vn.kltn.bankadvisor.module.indicator.entity.IndicatorUnit;

public record IndicatorResponse(
        String code,
        String name,
        String camelsGroup,
        IndicatorUnit unit,
        IndicatorDirection direction,
        String description
) {

    public static IndicatorResponse from(Indicator indicator) {
        return new IndicatorResponse(indicator.getCode(), indicator.getName(), indicator.getCamelsGroup(),
                indicator.getUnit(), indicator.getDirection(), indicator.getDescription());
    }
}
