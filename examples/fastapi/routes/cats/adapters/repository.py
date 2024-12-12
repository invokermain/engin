from examples.fastapi.routes.cats.domain import Cat
from examples.fastapi.routes.cats.ports import CatRepository


class InMemoryCatRepository(CatRepository):
    def __init__(self) -> None:
        self._cats: dict[int, Cat] = {}

    def get(self, cat_id: int) -> Cat:
        if cat_id in self._cats:
            return self._cats[cat_id]
        raise LookupError(f"No cat found for id: {cat_id}")

    def set(self, cat: Cat) -> None:
        self._cats[cat.id] = cat

    def next_id(self) -> int:
        return len(self._cats)
