import asyncio
from contextlib import asynccontextmanager

from engin import Engin, Invoke, Lifecycle


def a(lifecycle: Lifecycle) -> None:
    @asynccontextmanager
    async def _raise_err() -> None:
        yield
        raise RuntimeError("Error in Shutdown!")

    lifecycle.append(_raise_err())


B_LIFECYCLE_RAN = False


def b(lifecycle: Lifecycle) -> None:
    @asynccontextmanager
    async def _b_startup() -> None:
        global B_LIFECYCLE_RAN
        yield
        B_LIFECYCLE_RAN = True

    lifecycle.append(_b_startup())


async def test_error_in_startup():
    engin = Engin(Invoke(a), Invoke(b))

    await engin.start()
    await engin.stop()
    assert B_LIFECYCLE_RAN
