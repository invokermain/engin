import re
import typing
from dataclasses import dataclass
from linecache import getline
from types import UnionType
from typing import Any

from engin._introspect import get_first_external_frame

_implict_modules = ["builtins", "typing", "collections.abc", "types"]


@dataclass(frozen=True, slots=True)
class TypeId:
    """
    Represents information about a Type in the Dependency Injection framework.
    """

    type: type
    multi: bool
    alias: str | None

    @classmethod
    def from_type(cls, type_: Any) -> "TypeId":
        """
        Construct a TypeId from a given type.

        Args:
            type_: any type.

        Returns:
            The corresponding TypeId for that type.
        """
        alias = _extract_alias(type_)
        if _is_multi_type(type_):
            inner_obj = typing.get_args(type_)[0]
            return TypeId(type=inner_obj, multi=True, alias=alias)
        else:
            return TypeId(type=type_, multi=False, alias=alias)

    def __str__(self) -> str:
        module = self.type.__module__
        out = f"{module}." if module not in _implict_modules else ""
        out += _args_to_str(self.type)
        if self.multi:
            out += "[]"
        if self.alias:
            return f"Alias[{self.alias}, {out}]"
        return out

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, TypeId):
            return False
        return self.type == other.type and self.multi == other.multi


def _args_to_str(type_: Any) -> str:
    args = typing.get_args(type_)
    if args:
        arg_str = "Union[" if isinstance(type_, UnionType) else f"{type_.__name__}["
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


def _is_multi_type(type_: Any) -> bool:
    """
    Discriminates a type to determine whether it is the return type of a multiprovider.
    """
    return typing.get_origin(type_) is list


_ALIAS_PATTERN = re.compile(r"from_type\((\w+)\)")


def _extract_alias(expected_type: type) -> str | None:
    source_frame = get_first_external_frame()
    source_code = getline(source_frame.filename, source_frame.lineno)

    if alias_match := re.search(_ALIAS_PATTERN, source_code):
        alias = alias_match.group(1)
        if source_frame.frame.f_locals.get(alias) == expected_type:
            return alias
    return None
