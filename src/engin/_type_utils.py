import typing
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, eq=True)
class TypeId:
    type: type
    multi: bool

    @classmethod
    def from_type(cls, type_: Any) -> "TypeId":
        if is_multi_type(type_):
            inner_obj = typing.get_args(type_)[0]
            return TypeId(type=inner_obj, multi=True)
        else:
            return TypeId(type=type_, multi=False)

    def __str__(self) -> str:
        multi_str = "[]" if self.multi else ""
        return f"{self.type.__module__}.{self.type.__name__}{multi_str}"


def type_id_of(type_: Any) -> TypeId:
    """
    Generates a string TypeId for any type.
    """
    return TypeId.from_type(type_)


def is_multi_type(type_: Any) -> bool:
    """
    Discriminates a type to determine whether it is the return type of a multiprovider.
    """
    return typing.get_origin(type_) is list
