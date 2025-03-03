import starlette.testclient
from fastapi import APIRouter, FastAPI

from engin import Provide, Supply
from engin.ext.fastapi import FastAPIEngin

ROUTER = APIRouter(prefix="")


@ROUTER.get("/")
async def hello_world() -> str:
    return "hello world"


async def test_fastapi():
    def app_factory(routers: list[APIRouter]) -> FastAPI:
        app = FastAPI()
        for router in routers:
            app.include_router(router)
        return app

    engin = FastAPIEngin(Provide(app_factory), Supply([ROUTER]))

    with starlette.testclient.TestClient(engin) as client:
        result = client.get("http://127.0.0.1:8000/")

    assert result.json() == "hello world"
