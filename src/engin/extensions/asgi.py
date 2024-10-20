import logging
import traceback
import typing
from typing import Any, Protocol, TypeAlias

from engin import Engin, Option

__all__ = ["ASGIEngin", "ASGIType"]

from engin._assembler import AssembledDependency

Scope: TypeAlias = typing.MutableMapping[str, typing.Any]
Message: TypeAlias = typing.MutableMapping[str, typing.Any]
Receive: TypeAlias = typing.Callable[[], typing.Awaitable[Message]]
Send: TypeAlias = typing.Callable[[Message], typing.Awaitable[None]]
ASGIApp: TypeAlias = typing.Callable[[Scope, Receive, Send], typing.Awaitable[None]]


class ASGIType(Protocol):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None: ...


LOG = logging.getLogger(__name__)


class ASGIEngin(Engin, ASGIType):
    _asgi_app: ASGIType

    def __init__(self, *options: Option) -> None:
        super().__init__(*options)

        if not self._assembler.has(ASGIType):
            raise LookupError("A provider for `ASGIType` was expected, none found")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        LOG.info(scope)
        if scope["type"] == "lifespan":
            message = await receive()
            LOG.info(message)
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
        LOG.info("starting up")
        await self.start()
        assembled_dependency: AssembledDependency[ASGIType] = await self._assembler.assemble(
            self._asgi_provider
        )
        self._asgi_app = await assembled_dependency()


class _Rereceive:
    def __init__(self, message: Message) -> None:
        self._message = message

    async def __call__(self, *args, **kwargs) -> Message:
        return self._message
