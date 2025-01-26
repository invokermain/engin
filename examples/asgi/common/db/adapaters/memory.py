from typing import Any

from examples.asgi.common.db.ports import DatabaseInterface


class InMemoryDatabase(DatabaseInterface):
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def get(self, key: str) -> Any:
        return self._data.get(key)

    def set(self, key: str, value: Any) -> Any:
        self._data[key] = value

    def list(self) -> Any:
        return list(self._data.values())
