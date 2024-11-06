import traceback
import typing
from typing import Protocol, TypeAlias

from engin import Engin, Option

__all__ = ["ASGIEngin", "ASGIType"]


_Scope: TypeAlias = typing.MutableMapping[str, typing.Any]
_Message: TypeAlias = typing.MutableMapping[str, typing.Any]
_Receive: TypeAlias = typing.Callable[[], typing.Awaitable[_Message]]
_Send: TypeAlias = typing.Callable[[_Message], typing.Awaitable[None]]


class ASGIType(Protocol):
    async def __call__(self, scope: _Scope, receive: _Receive, send: _Send) -> None: ...


class ASGIEngin(Engin, ASGIType):
    _asgi_app: ASGIType

    def __init__(self, *options: Option) -> None:
        super().__init__(*options)

        if not self._assembler.has(ASGIType):
            raise LookupError("A provider for `ASGIType` was expected, none found")

    async def __call__(self, scope: _Scope, receive: _Receive, send: _Send) -> None:
        if scope["type"] == "lifespan":
            message = await receive()
            receive = _Rereceive(message)
            if message["type"] == "lifespan.startup":
                try:
                    await self._startup()
                except Exception as err:
                    exc = "".join(traceback.format_exception(err))
                    await send({"type": "lifespan.startup.failed", "message": exc})

            elif message["type"] == "lifespan.shutdown":
                await self.stop()

        await self._asgi_app(scope, receive, send)

    async def _startup(self) -> None:
        await self.start()
        self._asgi_app = await self._assembler.get(ASGIType)


class _Rereceive:
    def __init__(self, message: _Message) -> None:
        self._message = message

    async def __call__(self, *args, **kwargs) -> _Message:
        return self._message
