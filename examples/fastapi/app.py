from fastapi import APIRouter, FastAPI
from pydantic_settings import BaseSettings

from engin import Block, provide


class AppConfig(BaseSettings):
    debug: bool = False


class AppBlock(Block):
    @provide
    def default_config(self) -> AppConfig:
        return AppConfig()

    @provide
    def app_factory(self, app_config: AppConfig, routers: list[APIRouter]) -> FastAPI:
        app = FastAPI(debug=app_config.debug)

        for router in routers:
            app.include_router(router)

        app.add_api_route(path="/health", endpoint=_health)

        return app


async def _health() -> dict[str, bool]:
    return {"ok": True}
