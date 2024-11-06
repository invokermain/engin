from abc import ABC, abstractmethod
from typing import Any


class DatabaseInterface(ABC):
    @abstractmethod
    def get(self, key: str) -> Any: ...

    @abstractmethod
    def list(self) -> Any: ...

    @abstractmethod
    def set(self, key: str, value: Any) -> Any: ...
