import typing
from typing import Any

from engin._types import TypeId


def type_id_of(obj: Any) -> TypeId:
    if typing.get_origin(obj) is list:
        inner_obj = typing.get_args(obj)[0]
        return f"{inner_obj.__module__}.{inner_obj.__name__}[]"
    else:
        return f"{obj.__module__}.{obj.__name__}"
