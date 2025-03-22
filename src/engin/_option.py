from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from engin._engin import Engin


class Option(Protocol):
    @abstractmethod
    def apply(self, engin: "Engin") -> None: ...
