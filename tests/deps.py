from datetime import UTC, datetime
from typing import TypeAlias

from engin import Block, Provide, provide


def make_int() -> int:
    return 1


def int_provider(val: int = 1, **kwargs) -> Provide[int]:
    def _make_int() -> int:
        return val

    return Provide(_make_int, **kwargs)


def make_str() -> str:
    return "foo"


def make_many_int() -> list[int]:
    return [2, 3, 4]


def make_many_int_alt() -> list[int]:
    return [5, 6, 7]


IntTypeAlias: TypeAlias = int


def make_aliased_int() -> IntTypeAlias:
    return 8


class ABlock(Block):
    @provide
    def make_datetime(self) -> datetime:
        return datetime.now(tz=UTC)

    @provide
    def make_many_float(self) -> list[float]:
        return [1.2, 2.3]
