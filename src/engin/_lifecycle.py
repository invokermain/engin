import asyncio
import logging
from asyncio import Task
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from types import TracebackType
from typing import TypeAlias, TypeGuard, cast

LOG = logging.getLogger("engin")

_AnyContextManager: TypeAlias = AbstractAsyncContextManager | AbstractContextManager


class Lifecycle:
    """
    Allows dependencies to define startup and shutdown tasks for the application.

    Lifecycle tasks are defined using Context Managers, these can be async or sync.

    Lifecycle tasks should generally be defined in Providers as they are tied to the
    construction of a given dependency, but can be used in Invocations. The Lifecycle
    type is provided as a built-in Dependency by the Engin framework.
    """

    def __init__(self) -> None:
        self._context_managers: list[AbstractAsyncContextManager] = []

    def on_start(self, f: Callable[[], None], /, *, background: bool = False) -> None:
        """
        Add a Startup task to the application's lifecycle.

        Args:
            f: a callable without parameters.
            background: (optional) if True, the hook will be ran as a background task.
        """
        self._context_managers.append(_OnStartHook(f, background))

    def on_stop(self, f: Callable[[], None], /) -> None:
        """
        Add a Shutdown task to the application's lifecycle.

        Args:
            f: a callable without parameters.
        """
        self._context_managers.append(_OnStopHook(f))

    def append(self, cm: _AnyContextManager, /) -> None:
        """
        Append a Lifecycle task to the list.

        Args:
            cm: a task defined as a ContextManager or AsyncContextManager.


        Examples:
            Using a type that implements context management.

            ```python
            from httpx import AsyncClient

            def my_provider(lifecycle: Lifecycle) -> AsyncClient:
                client = AsyncClient()

                # AsyncClient is a context manager
                lifecycle.append(client)
            ```

            Defining a custom task.

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
        suppressed_cm = _AExitSuppressingAsyncContextManager(cm)
        self._context_managers.append(suppressed_cm)

    def list(self) -> list[AbstractAsyncContextManager]:
        """
        List all the defined tasks.

        Returns:
            A copy of the list of Lifecycle tasks.
        """
        return self._context_managers[:]


class _AExitSuppressingAsyncContextManager(AbstractAsyncContextManager):
    def __init__(self, cm: _AnyContextManager) -> None:
        self._cm = cm

    async def __aenter__(self) -> None:
        if self._is_async_cm(self._cm):
            await self._cm.__aenter__()
        else:
            await asyncio.to_thread(cast(AbstractContextManager, self._cm).__enter__)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        try:
            if self._is_async_cm(self._cm):
                await self._cm.__aexit__(exc_type, exc_value, traceback)
            else:
                await asyncio.to_thread(
                    cast(AbstractContextManager, self._cm).__exit__,
                    exc_type,
                    exc_value,
                    traceback,
                )
        except Exception as err:
            LOG.error("error in lifecycle hook stop, ignoring...", exc_info=err)

    @staticmethod
    def _is_async_cm(cm: _AnyContextManager) -> TypeGuard[AbstractAsyncContextManager]:
        return hasattr(cm, "__aenter__")


class _OnStartHook(AbstractAsyncContextManager):
    def __init__(self, f: Callable[[], None], background: bool = False) -> None:
        self._func = f
        self._task: Task | None = None
        self._background = background

    async def __aenter__(self) -> None:
        if asyncio.iscoroutinefunction(self._func):
            if self._background:
                self._task = asyncio.create_task(self._func())
            else:
                await self._func()
        else:
            if self._background:
                self._task = asyncio.create_task(asyncio.to_thread(self._func))
            else:
                self._func()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        return
        if self._task:
            self._task.cancel()


class _OnStopHook(AbstractAsyncContextManager):
    def __init__(self, f: Callable[[], None]) -> None:
        self._func = f
        self._task: Task | None = None

    async def __aenter__(self) -> None:
        return None

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        try:
            if asyncio.iscoroutinefunction(self._func):
                await self._func()
            else:
                self._func()
        except Exception as err:
            LOG.error("error in lifecycle hook stop, ignoring...", exc_info=err)
