from typing import Any


def extract_sensor_ids_by_address(configuration_json: Any) -> dict[str, int]:
    """
    Собирает соответствие address -> id для всех объектов конфигурации.

    Учитываются только словари, где address и id находятся на одном уровне.
    """
    sensor_ids_by_address: dict[str, int] = {}
    stack = [configuration_json]

    while stack:
        current_element = stack.pop()

        if isinstance(current_element, dict):
            address = current_element.get("address")
            sensor_id = current_element.get("id")

            if isinstance(address, str) and isinstance(sensor_id, int) and sensor_id != 0:
                sensor_ids_by_address[address] = sensor_id

            stack.extend(reversed(current_element.values()))
        elif isinstance(current_element, list):
            stack.extend(reversed(current_element))

    return sensor_ids_by_address
