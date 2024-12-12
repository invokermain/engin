from abc import abstractmethod

from examples.fastapi.routes.cats.domain import Cat


class CatRepository:
    @abstractmethod
    def get(self, cat_id: int) -> Cat: ...

    @abstractmethod
    def set(self, cat: Cat) -> None: ...

    @abstractmethod
    def next_id(self) -> int: ...
