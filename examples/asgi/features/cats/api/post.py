from typing import ClassVar

from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import Response

from examples.asgi.common.db.ports import DatabaseInterface
from examples.asgi.common.starlette.endpoint import Endpoint
from examples.asgi.features.cats.domain import Cat


class PostCatEndpoint(Endpoint):
    ALLOWED_METHODS: ClassVar[list[str]] = ["POST"]

    def __init__(self, db: DatabaseInterface) -> None:
        self._db = db

    async def exec(self, request: Request) -> Response:
        cat_dto = await request.json()

        try:
            cat = Cat.model_validate(cat_dto)
        except ValidationError:
            return Response(status_code=422)

        self._db.set(cat.name, cat.model_dump())

        return Response(status_code=204)
