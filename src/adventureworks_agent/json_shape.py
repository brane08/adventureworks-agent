from typing import Any


def shape(obj: Any) -> Any:
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if value is None or value is False:
                continue
            clean_key = key.replace("[]", "")
            result[clean_key] = shape(value)
        return result
    if isinstance(obj, list):
        return [shape(item) for item in obj]
    if isinstance(obj, float):
        return round(obj, 2)
    return obj
