import asyncio
from collections.abc import Iterable
from contextlib import asynccontextmanager
from datetime import datetime

import pytest

from engin import Engin, Entrypoint, Invoke, Lifecycle, Provide
from engin.exceptions import ProviderError
from tests.deps import ABlock


class A:
    def __init__(self): ...


class B:
    def __init__(self): ...


class C:
    def __init__(self): ...


async def test_engin():
    def a() -> A:
        return A()

    def b(_: A) -> B:
        return B()

    def c(_: B) -> C:
        return C()

    def multi_a() -> list[A]:
        return [A()]

    def multi_a_2() -> list[A]:
        return [A(), A()]

    def main(c: C, multi_a: list[A]) -> None:
        assert isinstance(c, C)
        assert len(multi_a) == 3

    engin = Engin(
        Provide(a), Provide(b), Provide(c), Provide(multi_a), Provide(multi_a_2), Invoke(main)
    )

    await engin.start()
    await engin.stop()


async def test_engin_with_block():
    def main(dt: datetime, floats: list[float]) -> None:
        assert isinstance(dt, datetime)
        assert isinstance(floats, list)
        assert all(isinstance(x, float) for x in floats)

    engin = Engin(ABlock(), Invoke(main))

    await engin.start()
    await engin.stop()


async def test_engin_error_handling():
    async def raise_value_error() -> int:
        raise ValueError("foo")

    async def main(foo: int) -> None:
        return

    engin = Engin(Provide(raise_value_error), Invoke(main))

    with pytest.raises(ProviderError, match="foo"):
        await engin.run()


async def test_engin_with_entrypoint():
    provider_called = False

    def a() -> A:
        nonlocal provider_called
        provider_called = True
        return A()

    engin = Engin(Provide(a), Entrypoint(A))

    await engin.start()
    await engin.stop()

    assert provider_called


async def test_engin_with_lifecycle():
    state = 0

    @asynccontextmanager
    async def lifespan_task() -> Iterable[None]:
        nonlocal state
        state = 1
        yield
        state = 2

    def foo(lifecycle: Lifecycle) -> None:
        lifecycle.append(lifespan_task())

    engin = Engin(Invoke(foo))

    await engin.start()
    assert state == 1

    await engin.stop()
    assert state == 2


async def test_engin_with_lifecycle_using_run():
    state = 0

    @asynccontextmanager
    async def lifespan_task() -> Iterable[None]:
        nonlocal state
        state = 1
        yield
        state = 2

    def foo(lifecycle: Lifecycle) -> None:
        lifecycle.append(lifespan_task())

    engin = Engin(Invoke(foo))

    async def _stop_task():
        await asyncio.sleep(0.25)
        # lifecycle should have started by now
        assert state == 1
        await engin.stop()

    await asyncio.gather(engin.run(), _stop_task())
    # lifecycle should have stopped by now
    assert state == 2


def test_engin_graph():
    def a() -> A:
        return A()

    def b(_: A) -> B:
        return B()

    def c(_: B) -> C:
        return C()

    def main(c: C) -> None:
        assert isinstance(c, C)

    engin = Engin(Provide(a), Provide(b), Provide(c), Invoke(main))

    graph = engin.graph()

    assert len(graph) == 3
