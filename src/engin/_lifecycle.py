from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, AsyncExitStack


class Lifecycle:
    def __init__(self) -> None:
        self._on_startup: list[Callable[..., None]] = []
        self._on_shutdown: list[Callable[..., None]] = []
        self._context_managers: list[AbstractAsyncContextManager] = []
        self._stack: AsyncExitStack = AsyncExitStack()

    def register_context(self, cm: AbstractAsyncContextManager) -> None:
        self._context_managers.append(cm)

    async def startup(self) -> None:
        self._stack = AsyncExitStack()
        for cm in self._context_managers:
            await self._stack.enter_async_context(cm)

    async def shutdown(self) -> None:
        await self._stack.aclose()
