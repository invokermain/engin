import typing
from dataclasses import dataclass
from typing import Any

_implict_modules = ["builtins", "typing", "collections.abc"]


@dataclass(frozen=True, eq=True, slots=True)
class TypeId:
    """
    Represents information about a Type in the Dependency Injection framework.
    """

    type: type
    multi: bool

    @classmethod
    def from_type(cls, type_: Any) -> "TypeId":
        """
        Construct a TypeId from a given type.

        Args:
            type_: any type.

        Returns:
            The corresponding TypeId for that type.
        """
        if is_multi_type(type_):
            inner_obj = typing.get_args(type_)[0]
            return TypeId(type=inner_obj, multi=True)
        else:
            return TypeId(type=type_, multi=False)

    def __str__(self) -> str:
        module = self.type.__module__
        out = f"{module}." if module not in _implict_modules else ""
        out += _args_to_str(self.type)
        if self.multi:
            out += "[]"
        return out


def _args_to_str(type_: Any) -> str:
    args = typing.get_args(type_)
    if args:
        arg_str = f"{type_.__name__}["
        for idx, arg in enumerate(args):
            if isinstance(arg, list):
                arg_str += "["
                for inner_idx, inner_arg in enumerate(arg):
                    arg_str += _args_to_str(inner_arg)
                    if inner_idx < len(arg) - 1:
                        arg_str += ", "
                arg_str += "]"
            elif typing.get_args(arg):
                arg_str += _args_to_str(arg)
            else:
                arg_str += getattr(arg, "__name__", str(arg))
            if idx < len(args) - 1:
                arg_str += ", "
        arg_str += "]"
    else:
        arg_str = type_.__name__
    return arg_str


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
