from typing import Any, Optional, Tuple


def extract_data_from_configuration(configuration_json: Any) -> Tuple[dict, dict]:
    """
    1. Собирает соответствие address -> id для всех объектов конфигурации.
       Учитываются только словари, где address и id находятся на одном уровне.
    2. Получает список controlledSite и преобразует его в словарь controlled_sites_segments
    """
    sensor_ids_by_address: dict[str, int] = {}
    controlled_sites_segments: dict[str, Tuple[Optional[int], Optional[int]]] = {}
    stack = [configuration_json]

    while stack:
        current_element = stack.pop()

        if isinstance(current_element, dict):
            address = current_element.get("address")
            sensor_id = current_element.get("id")
            controlled_sites = current_element.get("controlledSites")

            if isinstance(address, str) and isinstance(sensor_id, int) and sensor_id != 0:
                sensor_ids_by_address[address] = sensor_id

            if isinstance(controlled_sites, list):
                if any(
                    isinstance(item, dict) and "realObjectId" in item and "segments" in item
                    for item in controlled_sites
                ):
                    controlled_sites_segments = build_segments_dict(controlled_sites)

            stack.extend(reversed(current_element.values()))

        elif isinstance(current_element, list):
            stack.extend(reversed(current_element))

    return sensor_ids_by_address, controlled_sites_segments


def build_segments_dict(controlled_sites: list[dict]) -> dict[str, Tuple[Optional[int], Optional[int]]]:
    """
    Преобразует список controlledSites в словарь segments вида:
    {"ЗА 0-3-3 - ЗА 0-1-3": (6006, 6007)}
    """
    segments_dict: dict[str, Tuple[Optional[int], Optional[int]]] = {}

    for controlled_site in controlled_sites:
        controlled_site_id = controlled_site.get("id")
        segments = controlled_site.get("segments", [])
        if not isinstance(segments, list):
            continue
        for segment in segments:
            if not isinstance(segment, dict):
                continue

            segment_name = segment.get("name")
            segment_id = segment.get("id")
            if segment_name is None or segment_id is None:
                continue
            segments_dict[segment_name] = (controlled_site_id, segment_id)
    return segments_dict
