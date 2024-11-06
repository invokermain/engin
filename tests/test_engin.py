from datetime import datetime

import pytest

from engin import AssemblyError, Engin, Entrypoint, Invoke, Provide
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

    def main(c: C) -> None:
        assert isinstance(c, C)

    engin = Engin(Provide(a), Provide(b), Provide(c), Invoke(main))

    await engin.start()


async def test_engin_with_block():
    def main(dt: datetime, floats: list[float]) -> None:
        assert isinstance(dt, datetime)
        assert isinstance(floats, list)
        assert all(isinstance(x, float) for x in floats)

    engin = Engin(ABlock(), Invoke(main))

    await engin.start()


async def test_engin_error_handling():
    async def raise_value_error() -> int:
        raise ValueError("foo")

    async def main(foo: int) -> None:
        return

    engin = Engin(Provide(raise_value_error), Invoke(main))

    with pytest.raises(AssemblyError, match="foo"):
        await engin.run()


async def test_engin_with_entrypoint():
    provider_called = False

    def a() -> A:
        nonlocal provider_called
        provider_called = True
        return A()

    engin = Engin(Provide(a), Entrypoint(A))

    await engin.start()

    assert provider_called
