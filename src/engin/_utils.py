from typing import Any


def type_to_key(obj: Any) -> str:
    return f"{obj.__module__}.{obj.__name__}"
