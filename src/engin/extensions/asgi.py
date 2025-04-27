import contextlib
import traceback
from collections.abc import AsyncIterator, Awaitable, Callable, MutableMapping
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any, ClassVar, Protocol, TypeAlias

from engin import Engin, Entrypoint, Option, Supply

__all__ = ["ASGIEngin", "ASGIType", "engin_to_lifespan"]

from engin._graph import DependencyGrapher, Node

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
                    raise

            elif message["type"] == "lifespan.shutdown":
                await self.stop()

        with self._assembler.scope("request"):
            await self._asgi_app(scope, receive, send)

    async def _startup(self) -> None:
        self._asgi_app = await self._assembler.build(self._asgi_type)
        await self.start()

    def graph(self) -> list[Node]:
        grapher = DependencyGrapher({**self._providers, **self._multiproviders})
        return grapher.resolve([Entrypoint(self._asgi_type), *self._invocations])


class _Rereceive:
    def __init__(self, message: _Message) -> None:
        self._message = message

    async def __call__(self, *args: Any, **kwargs: Any) -> _Message:
        return self._message


def engin_to_lifespan(engin: Engin) -> Callable[[ASGIType], AbstractAsyncContextManager[None]]:
    """
    Transforms the Engin instance into an ASGI lifespan task.

    This is to enable users to use the Engin framework with existing ASGI applications,
    where it is not desired to replace the ASGI application with an ASGIEngin.

    Args:
        engin: the engin instance to transform.

    Returns:
        An ASGI lifespan task.
    """

    @asynccontextmanager
    async def engin_lifespan(app: ASGIType) -> AsyncIterator[None]:
        # ensure the Engin
        with contextlib.suppress(ValueError):
            engin.assembler.add(Supply(app))

        app.state.assembler = engin.assembler  # type: ignore[attr-defined]

        await engin.start()
        yield
        await engin.stop()

    return engin_lifespan
