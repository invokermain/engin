import asyncio
from asyncio import Task
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from engin import Engin, Invoke, Lifecycle

B_LIFECYCLE_STATE = False


async def runtime_error():
    raise RuntimeError("You died")


async def update_global():
    global B_LIFECYCLE_STATE
    B_LIFECYCLE_STATE = True


def a(lifecycle: Lifecycle) -> None:
    @asynccontextmanager
    async def _raise_runtime_error_in_task() -> AsyncIterator[Task]:
        task = asyncio.create_task(runtime_error())
        yield task
        del task

    lifecycle.append(_raise_runtime_error_in_task())


def b(lifecycle: Lifecycle) -> None:
    @asynccontextmanager
    async def _b_startup() -> AsyncIterator[None]:
        task = asyncio.create_task(update_global())
        yield
        del task

    lifecycle.append(_b_startup())


async def test_error_in_runtime(caplog):
    """Should log an error when a's tasks fails but b should continue"""
    engin = Engin(Invoke(a), Invoke(b))

    with caplog.at_level("ERROR"):
        await engin.run()

    # a logged an error
    assert any("lifecycle runtime task errored" in record.message for record in caplog.records)

    # b ran successfully
    assert B_LIFECYCLE_STATE
