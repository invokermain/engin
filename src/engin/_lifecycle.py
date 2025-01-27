import logging
from contextlib import AbstractAsyncContextManager
from types import TracebackType

LOG = logging.getLogger("engin")


class Lifecycle:
    def __init__(self) -> None:
        self._context_managers: list[AbstractAsyncContextManager] = []

    def append(self, cm: AbstractAsyncContextManager) -> None:
        suppressed_cm = _AExitSuppressingAsyncContextManager(cm)
        self._context_managers.append(suppressed_cm)

    def list(self) -> list[AbstractAsyncContextManager]:
        return self._context_managers[:]


class _AExitSuppressingAsyncContextManager(AbstractAsyncContextManager):
    def __init__(self, cm: AbstractAsyncContextManager) -> None:
        self._cm = cm

    async def __aenter__(self) -> AbstractAsyncContextManager:
        await self._cm.__aenter__()
        return self._cm

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        try:
            await self._cm.__aexit__(exc_type, exc_value, traceback)
        except Exception as err:
            LOG.error("error in lifecycle hook stop, ignoring...", exc_info=err)
