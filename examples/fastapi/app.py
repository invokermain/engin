from fastapi import FastAPI
from pydantic_settings import BaseSettings

from engin import Block, invoke, provide


class AppConfig(BaseSettings):
    debug: bool = False


class AppBlock(Block):
    @provide
    def app_factory(self, app_config: AppConfig) -> FastAPI:
        return FastAPI(debug=app_config.debug)

    @provide
    def default_config(self) -> AppConfig:
        return AppConfig()

    @invoke
    def add_health_endpoint(self, app: FastAPI) -> None:
        async def health() -> dict[str, bool]:
            return {"ok": True}

        app.add_api_route(path="/health", endpoint=health)
