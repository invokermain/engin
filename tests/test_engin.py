from datetime import datetime

from engin import Engin, Invoke, Provide
from tests.deps import AModule


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


async def test_engin_with_module():
    def main(dt: datetime, floats: list[float]) -> None:
        assert isinstance(dt, datetime)
        assert isinstance(floats, list)
        assert all(isinstance(x, float) for x in floats)

    engin = Engin(AModule(), Invoke(main))

    await engin.start()
