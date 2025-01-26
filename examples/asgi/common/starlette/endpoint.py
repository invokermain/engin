from abc import ABC, abstractmethod
from typing import ClassVar

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.types import Receive, Scope, Send


class Endpoint(ABC):
    """
    Base class for implementing Starlette endpoints in a way that's compatible with DI, as
    HTTPEndpoint does not allow you to control class initialisation.
    """

    ALLOWED_METHODS: ClassVar[list[str]] = [
        "GET",
        "HEAD",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ]

    @abstractmethod
    async def exec(self, request: Request) -> Response: ...

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope, receive=receive)

        if request.method not in self.ALLOWED_METHODS:
            response = await self.method_not_allowed(request)
        else:
            response = await self.exec(request)

        await response(scope, receive, send)

    async def method_not_allowed(self, request: Request) -> Response:
        # If we're running inside a starlette application then raise an
        # exception, so that the configurable exception handler can deal with
        # returning the response. For plain ASGI apps, just return the response.
        headers = {"Allow": ", ".join(self.ALLOWED_METHODS)}
        if "app" in request.scope:
            raise HTTPException(status_code=405, headers=headers)
        return PlainTextResponse("Method Not Allowed", status_code=405, headers=headers)
