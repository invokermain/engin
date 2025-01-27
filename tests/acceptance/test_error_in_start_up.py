from contextlib import asynccontextmanager

from starlette.applications import Starlette

from engin import Engin, Invoke, Lifecycle, Provide
from engin.ext.asgi import ASGIEngin, ASGIType


def a(lifecycle: Lifecycle) -> None:
    @asynccontextmanager
    async def _raise_err() -> None:
        raise RuntimeError("Error in Startup!")
        yield

    lifecycle.append(_raise_err())


B_LIFECYCLE_STATE = False


def b(lifecycle: Lifecycle) -> None:
    @asynccontextmanager
    async def _b_startup() -> None:
        global B_LIFECYCLE_STATE
        B_LIFECYCLE_STATE = True
        yield

    lifecycle.append(_b_startup())


async def test_error_in_startup():
    engin = Engin(Invoke(a), Invoke(b))

    await engin.start()
    assert not B_LIFECYCLE_STATE


async def test_error_in_startup_asgi():
    def asgi_type() -> ASGIType:
        return Starlette()

    engin = ASGIEngin(Invoke(a), Invoke(b), Provide(asgi_type))

    await engin.start()
    assert not B_LIFECYCLE_STATE
