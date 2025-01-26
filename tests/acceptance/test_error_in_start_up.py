from contextlib import asynccontextmanager

from engin import Engin, Invoke, Lifecycle


def a(lifecycle: Lifecycle) -> None:
    @asynccontextmanager
    async def _raise_err() -> None:
        raise RuntimeError("Error in Startup!")
        yield

    lifecycle.append(_raise_err())


B_LIFECYCLE_RAN = False


def b(lifecycle: Lifecycle) -> None:
    @asynccontextmanager
    async def _b_startup() -> None:
        global B_LIFECYCLE_RAN
        B_LIFECYCLE_RAN = True
        yield

    lifecycle.append(_b_startup())


async def test_error_in_startup():
    engin = Engin(Invoke(a), Invoke(b))

    await engin.start()
    assert not B_LIFECYCLE_RAN
