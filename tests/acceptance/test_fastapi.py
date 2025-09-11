import asyncio
from typing import Annotated

import pytest
import starlette.testclient
from fastapi import APIRouter, FastAPI
from starlette.websockets import WebSocket

from engin import Engin, Provide, Supply
from engin.extensions.asgi import engin_to_lifespan
from engin.extensions.fastapi import APIRouteDependency, FastAPIEngin, Inject

ROUTER = APIRouter(prefix="")


@ROUTER.get("/")
async def hello_world() -> str:
    return "hello world"


@ROUTER.get("/inject")
async def route_with_dep(some_int: Annotated[int, Inject(int)]) -> int:
    return some_int


@ROUTER.websocket("/websocket")
async def websocket_with_dep(
    websocket: WebSocket, some_int: Annotated[int, Inject(int)]
) -> None:
    await websocket.accept()
    for i in range(5):
        await websocket.send_text(str(i + some_int))
    await websocket.close()


@ROUTER.get("/inject2")
async def route_with_dep_2(
    some_int: Annotated[int, Inject(int)], some_str: Annotated[str, Inject(str)]
) -> int:
    assert some_int == int(some_str)
    return some_int


def app_factory(routers: list[APIRouter]) -> FastAPI:
    app = FastAPI()
    for router in routers:
        app.include_router(router)
    return app


def test_fastapi():
    engin = FastAPIEngin(Provide(app_factory), Supply([ROUTER]))

    with starlette.testclient.TestClient(engin) as client:
        result = client.get("http://127.0.0.1:8000/")

    assert result.status_code == 200
    assert result.json() == "hello world"


def test_inject():
    engin = FastAPIEngin(Provide(app_factory), Supply([ROUTER]), Supply(10))

    with starlette.testclient.TestClient(engin) as client:
        result = client.get("/inject")

    assert result.json() == 10


def test_inject_websocket():
    engin = FastAPIEngin(Provide(app_factory), Supply([ROUTER]), Supply(10))

    with (
        starlette.testclient.TestClient(engin) as client,
        client.websocket_connect("/websocket") as ws,
    ):
        data = ws.receive_text()
        assert data == "10"


async def test_graph():
    engin = FastAPIEngin(Provide(app_factory), Supply([ROUTER]), Supply(10), Supply("a"))

    nodes = engin.graph()

    assert len(nodes) == 8
    assert len([node for node in nodes if isinstance(node.node, APIRouteDependency)]) == 3


async def test_invalid_engin():
    with pytest.raises(LookupError, match="FastAPI"):
        FastAPIEngin()


async def test_engin_to_lifespan():
    engin = Engin(Supply(10))

    app = FastAPI(lifespan=engin_to_lifespan(engin))
    app.include_router(ROUTER)

    with starlette.testclient.TestClient(app) as client:
        result = client.get("http://127.0.0.1:8000/inject")

    assert result.json() == 10


async def test_asgi_request_scope():
    factory_call_count = 0

    def scoped_factory() -> int:
        nonlocal factory_call_count
        factory_call_count += 1
        return factory_call_count

    def child_factory(some: int) -> str:
        return str(some)

    app = FastAPIEngin(
        Provide(app_factory),
        Provide(scoped_factory, scope="request"),
        Provide(child_factory),
        Supply([ROUTER]),
    )

    async def _request() -> int:
        result = await asyncio.to_thread(client.get, "http://127.0.0.1:8000/inject")
        return result.json()

    with starlette.testclient.TestClient(app) as client:
        results = await asyncio.gather(*[_request() for _ in range(100)])

        # every result should be unique as the factory is request scoped to each request
        assert len(set(results)) == len(results)
        # we expect the factory to have been called 100 times
        assert factory_call_count == 100

        client.get("http://127.0.0.1:8000/inject2")
