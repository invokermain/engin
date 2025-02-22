from typing import ClassVar

from engin import Block, Invoke, Provide, Supply, provide
from examples.fastapi.routes.cats.adapters.repository import InMemoryCatRepository
from examples.fastapi.routes.cats.api import router
from examples.fastapi.routes.cats.ports import CatRepository


class CatBlock(Block):
    options: ClassVar[list[Provide | Invoke]] = [Supply([router])]

    @provide
    def cat_repository(self) -> CatRepository:
        return InMemoryCatRepository()
