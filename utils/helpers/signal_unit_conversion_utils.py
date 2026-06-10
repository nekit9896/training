import copy
from typing import Any

from constants.enums import MeasureConversionRule
from constants.test_constants import MeasureUnitConstants


def _resolve_unit_mapping(rule: MeasureConversionRule) -> tuple[str, str]:
    if rule == MeasureConversionRule.MPA_MEASURE:
        return MeasureUnitConstants.KG_CM_MEASURE, MeasureUnitConstants.MPA_MEASURE
    if rule == MeasureConversionRule.KG_CM_MEASURE:
        return MeasureUnitConstants.MPA_MEASURE, MeasureUnitConstants.KG_CM_MEASURE
    raise ValueError(f"Неизвестное правило конвертации единиц измерения: {rule}")


def conversion_rules_need_update(rules_json: dict[str, Any], rule: MeasureConversionRule) -> bool:
    """
    Проверяет, есть ли в файле единицы давления, которые нужно заменить по правилу набора.
    """
    source_unit, _ = _resolve_unit_mapping(rule)
    return any(signal.get("OriginUnit") == source_unit for signal in rules_json.get("Signals", []))


def apply_measure_conversion_rule(rules_json: dict[str, Any], rule: MeasureConversionRule) -> dict[str, Any]:
    """
    Возвращает копию rules_json с заменой единиц давления.

    Замена строго по полному совпадению OriginUnit с исходной единицей давления
    (kgf/cm^2 <-> MPa). Остальные единицы (cSt, m^3/h, rpm и т.д.) не затрагиваются.
    """
    source_unit, target_unit = _resolve_unit_mapping(rule)
    result = copy.deepcopy(rules_json)

    for signal in result.get("Signals", []):
        if signal.get("OriginUnit") == source_unit:
            signal["OriginUnit"] = target_unit

    return result
