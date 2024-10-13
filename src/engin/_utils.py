def type_to_key(obj: object) -> str:
    return f"{obj.__module__}.{obj.__name__}"
