import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from inspect import iscoroutinefunction
from types import TracebackType
from typing import TypeAlias, TypeGuard, cast

LOG = logging.getLogger("engin")

_AnyContextManager: TypeAlias = AbstractAsyncContextManager | AbstractContextManager
_ParameterlessCallable: TypeAlias = Callable[[], None | Awaitable[None]]


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

        Defining a custom lifecycle using a LifecycleHook.

        ```python
        def my_provider(lifecycle: Lifecycle) -> str:
            connection_pool = ConnectionPool()

            lifecycle.hook(
                on_start=connection_pool.connect,
                on_stop=connection_pool.close,
            )
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

    def hook(
        self,
        *,
        on_start: _ParameterlessCallable | None = None,
        on_stop: _ParameterlessCallable | None = None,
    ) -> None:
        """
        Append a hook to the Lifecycle.

        At least one of `on_start` or `on_stop` must be provided.

        Args:
            on_start: a callable to be executed on Lifecycle startup.
            on_stop: a callable to be executed on Lifecycle shutdown.
        """
        if on_start is None and on_stop is None:
            raise ValueError("At least one of on_start or on_stop must be provided")
        self.append(LifecycleHook(on_start=on_start, on_stop=on_stop))

    def list(self) -> list[AbstractAsyncContextManager]:
        """
        List all the defined tasks.

        Returns:
            A copy of the list of Lifecycle tasks.
        """
        return self._context_managers[:]


class LifecycleHook(AbstractAsyncContextManager):
    def __init__(
        self,
        on_start: _ParameterlessCallable | None = None,
        on_stop: _ParameterlessCallable | None = None,
    ) -> None:
        self._on_start = on_start
        self._on_stop = on_stop

    async def __aenter__(self) -> None:
        if self._on_start is not None:
            func = self._on_start
            if iscoroutinefunction(func):
                await func()
            else:
                await asyncio.to_thread(func)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        if self._on_stop is not None:
            func = self._on_stop
            if iscoroutinefunction(func):
                await func()
            else:
                await asyncio.to_thread(func)


class _AExitSuppressingAsyncContextManager(AbstractAsyncContextManager):
    def __init__(self, cm: _AnyContextManager) -> None:
        self._cm = cm

    async def __aenter__(self) -> None:
        if self._is_async_cm(self._cm):
            await self._cm.__aenter__()
        else:
            await asyncio.to_thread(cast("AbstractContextManager", self._cm).__enter__)

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
                    cast("AbstractContextManager", self._cm).__exit__,
                    exc_type,
                    exc_value,
                    traceback,
                )
        except Exception as err:
            LOG.error("error in lifecycle hook stop, ignoring...", exc_info=err)

    @staticmethod
    def _is_async_cm(cm: _AnyContextManager) -> TypeGuard[AbstractAsyncContextManager]:
        return hasattr(cm, "__aenter__")
