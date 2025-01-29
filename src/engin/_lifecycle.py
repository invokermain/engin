import asyncio
import logging
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from types import TracebackType
from typing import TypeAlias

LOG = logging.getLogger("engin")

_AnyContextManager: TypeAlias = AbstractAsyncContextManager | AbstractContextManager


class Lifecycle:
    """
    Allows dependencies to define startup and shutdown tasks for the application.

    Lifecycle tasks are defined using Context Managers, these can be async or sync.

    Lifecycle tasks should generally be defined in Providers as they are tied to the
    construction of a given dependency, but can be used in Invocations. The Lifecycle
    type is provided as a built-in Dependency by the Engin framework.

    Examples:
        Using a type that implements context management.

        ```python
        from httpx import AsyncClient

        def my_provider(lifecycle: Lifecycle) -> AsyncClient:
            client = AsyncClient()

            # AsyncClient is a context manager
            lifecycle.append(client)
        ```

        Defining a custom lifecycle.

        ```python
        def my_provider(lifecycle: Lifecycle) -> str:
            @contextmanager
            def task():
                print("starting up!")
                yield
                print("shutting down!)

            lifecycle.append(task)
        ```
    """

    def __init__(self) -> None:
        self._context_managers: list[AbstractAsyncContextManager] = []

    def append(self, cm: _AnyContextManager, /) -> None:
        """
        Append a Lifecycle task to the list.

        Args:
            cm: a task defined as a ContextManager or AsyncContextManager.
        """
        suppressed_cm = _AExitSuppressingAsyncContextManager(cm)
        self._context_managers.append(suppressed_cm)

    def list(self) -> list[_AnyContextManager]:
        """
        List all the defined tasks.

        Returns:
            A copy of the list of Lifecycle tasks.
        """
        return self._context_managers[:]


class _AExitSuppressingAsyncContextManager(AbstractAsyncContextManager):
    def __init__(self, cm: _AnyContextManager) -> None:
        self._cm = cm
        self._is_async = hasattr(cm, "__aenter__")

    async def __aenter__(self) -> None:
        if self._is_async:
            await self._cm.__aenter__()
        else:
            await asyncio.to_thread(self._cm.__enter__)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        try:
            if self._is_async:
                await self._cm.__aexit__(exc_type, exc_value, traceback)
            else:
                await asyncio.to_thread(self._cm.__exit__, exc_type, exc_value, traceback)
        except Exception as err:
            LOG.error("error in lifecycle hook stop, ignoring...", exc_info=err)
