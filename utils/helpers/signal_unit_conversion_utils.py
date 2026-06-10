from typing import Any

from constants.enums import MeasureConversionRule
from constants.test_constants import MeasureUnitConstants


def apply_measure_conversion_rule(rules_json: dict[str, Any], rule: MeasureConversionRule) -> dict[str, Any]:
    """
    Заменяет единицы измерения давления в signal_unit_conversion_rules.json
  согласно правилу набора данных.
    """
    if rule == MeasureConversionRule.MPA_MEASURE:
        source_unit = MeasureUnitConstants.KG_CM_MEASURE
        target_unit = MeasureUnitConstants.MPA_MEASURE
    elif rule == MeasureConversionRule.KG_CM_MEASURE:
        source_unit = MeasureUnitConstants.MPA_MEASURE
        target_unit = MeasureUnitConstants.KG_CM_MEASURE
    else:
        raise ValueError(f"Неизвестное правило конвертации единиц измерения: {rule}")

    for signal in rules_json.get("Signals", []):
        if signal.get("OriginUnit") == source_unit:
            signal["OriginUnit"] = target_unit

    return rules_json
