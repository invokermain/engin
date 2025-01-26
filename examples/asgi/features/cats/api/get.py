from typing import ClassVar

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from examples.asgi.common.db.ports import DatabaseInterface
from examples.asgi.common.starlette.endpoint import Endpoint
from examples.asgi.features.cats.domain import Cat


class GetCatEndpoint(Endpoint):
    ALLOWED_METHODS: ClassVar[list[str]] = ["GET"]

    def __init__(self, db: DatabaseInterface) -> None:
        self._db = db

    async def exec(self, request: Request) -> Response:
        name = request.path_params.get("name")
        if name is None:
            cat_dtos = self._db.list()
            return JSONResponse(
                content=[Cat.model_validate(cat_dto).model_dump() for cat_dto in cat_dtos]
            )

        cat_dto = self._db.get(name)

        if cat_dto is None:
            return Response(status_code=404)

        cat = Cat.model_validate(cat_dto)

        return JSONResponse(content=cat.model_dump_json())
