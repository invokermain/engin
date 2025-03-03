from typing import Annotated

import starlette.testclient
from fastapi import APIRouter, FastAPI

from engin import Provide, Supply
from engin.ext.fastapi import APIRouteDependency, FastAPIEngin, Inject

ROUTER = APIRouter(prefix="")


@ROUTER.get("/")
async def hello_world() -> str:
    return "hello world"


@ROUTER.get("/inject")
async def route_with_dep(some_int: Annotated[int, Inject(int)]) -> int:
    return some_int


def app_factory(routers: list[APIRouter]) -> FastAPI:
    app = FastAPI()
    for router in routers:
        app.include_router(router)
    return app


async def test_fastapi():
    engin = FastAPIEngin(Provide(app_factory), Supply([ROUTER]))

    with starlette.testclient.TestClient(engin) as client:
        result = client.get("http://127.0.0.1:8000/")

    assert result.json() == "hello world"


async def test_inject():
    engin = FastAPIEngin(Provide(app_factory), Supply([ROUTER]), Supply(10))

    with starlette.testclient.TestClient(engin) as client:
        result = client.get("http://127.0.0.1:8000/inject")

    assert result.json() == 10


async def test_graph():
    engin = FastAPIEngin(Provide(app_factory), Supply([ROUTER]), Supply(10))

    nodes = engin.graph()

    assert len(nodes) == 5
    assert len([node for node in nodes if isinstance(node.node, APIRouteDependency)]) == 2
