from typing import Any

from typing_extensions import TypeVar

from engin import Engin, Option

T = TypeVar("T")


class ASGIEngin(Engin):
    def __init__(self, *options: Option, asgi_type: type[T]) -> None:
        super().__init__(*options)
        self._asgi_provider = self._dependency_manager.get_provider(asgi_type)
        self._asgi_app: Any = None

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "lifespan":
            message = await receive()
            receive = Rereceive(message)
            if message["type"] == "lifespan.startup":
                await self._startup()
            elif message["type"] == "lifespan.shutdown":
                await self.stop()

        if self._asgi_app is not None:
            return await self._asgi_app(scope, receive, send)

    async def _startup(self) -> None:
        await self.start()
        bind = await self._dependency_manager.bind_arguments(self._asgi_provider.signature)
        self._asgi_app = await self._asgi_provider(*bind.args, **bind.kwargs)


class Rereceive:
    def __init__(self, message: str) -> None:
        self._message = message

    async def __call__(self, *args, **kwargs) -> str:
        return self._message
