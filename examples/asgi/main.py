import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from engin import Provide
from engin.extensions.asgi import ASGIEngin


async def homepage(request):
    return JSONResponse({"hello": "world"})


def route() -> Route:
    return Route("/", homepage)


def app_factory(route: Route) -> Starlette:
    return Starlette(routes=[route])


app = ASGIEngin(Provide(route), Provide(app_factory), asgi_type=Starlette)

uvicorn.run(app)
