from fastapi import FastAPI

from engin import Block, invoke, provide
from examples.fastapi.routes.cats.adapters.repository import InMemoryCatRepository
from examples.fastapi.routes.cats.api import router
from examples.fastapi.routes.cats.ports import CatRepository


class CatBlock(Block):
    @provide
    def cat_repository(self) -> CatRepository:
        return InMemoryCatRepository()

    @invoke
    def attach_router(self, app: FastAPI) -> None:
        app.include_router(router)
