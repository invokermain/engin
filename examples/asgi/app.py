from pydantic_settings import BaseSettings
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from engin import Module, provide
from engin.extensions.asgi import ASGIType


class AppConfig(BaseSettings):
    debug: bool = False


class HealthCheckEndpoint(HTTPEndpoint):
    async def get(self, _: Request) -> Response:
        return JSONResponse({"ok": True})


class AppModule(Module):
    @provide
    def app_factory(self, routes: list[Route], app_config: AppConfig) -> ASGIType:
        return Starlette(routes=routes, debug=app_config.debug)

    @provide
    def default_routes(self) -> list[Route]:
        return [Route("/health", HealthCheckEndpoint)]

    @provide
    def default_config(self) -> AppConfig:
        return AppConfig()
