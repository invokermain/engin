import traceback
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any, ClassVar, Protocol, TypeAlias

from engin import Engin, Option

__all__ = ["ASGIEngin", "ASGIType"]


_Scope: TypeAlias = MutableMapping[str, Any]
_Message: TypeAlias = MutableMapping[str, Any]
_Receive: TypeAlias = Callable[[], Awaitable[_Message]]
_Send: TypeAlias = Callable[[_Message], Awaitable[None]]


class ASGIType(Protocol):
    async def __call__(self, scope: _Scope, receive: _Receive, send: _Send) -> None: ...


class ASGIEngin(Engin, ASGIType):
    _asgi_type: ClassVar[type[ASGIType]] = ASGIType  # type: ignore[type-abstract]
    _asgi_app: ASGIType

    def __init__(self, *options: Option) -> None:
        super().__init__(*options)

        if not self._assembler.has(self._asgi_type):
            raise LookupError(
                f"A provider for `{self._asgi_type.__name__}` was expected, none found"
            )

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
        self._asgi_app = await self._assembler.get(self._asgi_type)


class _Rereceive:
    def __init__(self, message: _Message) -> None:
        self._message = message

    async def __call__(self, *args: Any, **kwargs: Any) -> _Message:
        return self._message
