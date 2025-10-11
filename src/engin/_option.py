from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from engin._container import Container


class Option(Protocol):
    @abstractmethod
    def register(self, container: "Container") -> None: ...
