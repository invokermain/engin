import time
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
    def scoped_factory() -> int:
        return time.time_ns()

    def child_factory(some: int) -> str:
        return str(some)

    app = FastAPIEngin(
        Provide(app_factory),
        Provide(scoped_factory, scope="request"),
        Provide(child_factory),
        Supply([ROUTER]),
    )

    with starlette.testclient.TestClient(app) as client:
        first_call = client.get("http://127.0.0.1:8000/inject").json()
        second_call = client.get("http://127.0.0.1:8000/inject").json()

        # these should differ as the factory is request scoped to each request
        assert first_call != second_call

        client.get("http://127.0.0.1:8000/inject2")
