from contextlib import asynccontextmanager

from starlette.applications import Starlette

from engin import Engin, Invoke, Lifecycle, Provide
from engin.extensions.asgi import ASGIEngin, ASGIType


def a(lifecycle: Lifecycle) -> None:
    @asynccontextmanager
    async def _raise_err() -> None:
        yield
        raise RuntimeError("Error in Shutdown!")

    lifecycle.append(_raise_err())


B_LIFECYCLE_STATE = 0


def b(lifecycle: Lifecycle) -> None:
    @asynccontextmanager
    async def _b_startup() -> None:
        global B_LIFECYCLE_STATE
        B_LIFECYCLE_STATE = 1
        yield
        B_LIFECYCLE_STATE = 2

    lifecycle.append(_b_startup())


async def test_error_in_shutdown():
    engin = Engin(Invoke(a), Invoke(b))

    await engin.start()
    assert B_LIFECYCLE_STATE == 1

    await engin.stop()
    assert B_LIFECYCLE_STATE == 2


async def test_error_in_shutdown_asgi():
    def asgi_type() -> ASGIType:
        return Starlette()

    engin = ASGIEngin(Invoke(a), Invoke(b), Provide(asgi_type))

    await engin.start()
    assert B_LIFECYCLE_STATE == 1

    await engin.stop()
    assert B_LIFECYCLE_STATE == 2
