import typing
from collections import defaultdict
from typing import Any

if typing.TYPE_CHECKING:
    from engin import Invoke, Provide, TypeId


class Container:
    """
    A Container holds the various Options that Engin can work with.
    """

    __slots__ = ("invocations", "multiproviders", "providers")

    def __init__(self) -> None:
        self.providers: dict[TypeId, Provide[Any]] = {}
        self.invocations: list[Invoke] = []
        self.multiproviders: defaultdict[TypeId, list[Provide[list[Any]]]] = defaultdict(list)
