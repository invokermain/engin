from datetime import datetime

from engin import Module, provide


def make_int() -> int:
    return 1


def make_str() -> str:
    return "foo"


def make_many_int() -> list[int]:
    return [2, 3, 4]


def make_many_int_alt() -> list[int]:
    return [5, 6, 7]


class AModule(Module):
    @provide
    def make_datetime(self) -> datetime:
        return datetime.now()

    @provide
    def make_many_float(self) -> list[float]:
        return [1.2, 2.3]
