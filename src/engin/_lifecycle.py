import functools
import logging
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import TypeAlias

LOG = logging.getLogger("engin")


class Lifecycle:
    def __init__(self) -> None:
        self._context_managers: list[AbstractAsyncContextManager] = []

    def append(self, cm: AbstractAsyncContextManager) -> None:
        cm.__aexit__ = _suppress_exit_errors(cm.__aexit__)
        self._context_managers.append(cm)

    def list(self) -> list[AbstractAsyncContextManager]:
        return self._context_managers[:]


_AExitSig: TypeAlias = Callable[
    [type[BaseException] | None, BaseException | None, TracebackType | None], Awaitable[None]
]


def _suppress_exit_errors(func: _AExitSig) -> _AExitSig:
    # @functools.wraps(func)
    async def wrapped(exc_type, exc_value, traceback) -> None:
        try:
            return await func(exc_type, exc_value, traceback)
        except Exception as err:
            LOG.error(f"error in lifecycle hook stop, ignoring...", exc_info=err)

    return wrapped
