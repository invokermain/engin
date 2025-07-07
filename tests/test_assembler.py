import time
from typing import Annotated

import pytest

from engin import Assembler, Entrypoint, Invoke, Provide
from engin.exceptions import NotInScopeError, ProviderError
from tests.deps import int_provider, make_many_int, make_many_int_alt, make_str


async def test_assembler():
    assembler = Assembler([int_provider(), Provide(make_str), Provide(make_many_int)])

    def assert_all(some_int: int, some_str: str, many_ints: list[int]):
        assert isinstance(some_str, str)
        assert isinstance(some_int, int)
        assert all(isinstance(x, int) for x in many_ints)

    assembled_dependency = await assembler.assemble(Invoke(assert_all))

    await assembled_dependency()


async def test_assembler_with_multiproviders():
    # catch any non-deterministic ordering bugs
    for _ in range(10):
        assembler = Assembler([Provide(make_many_int), Provide(make_many_int_alt)])

        def assert_all(many_ints: list[int]):
            expected_ints = [*make_many_int(), *make_many_int_alt()]
            assert many_ints == expected_ints

        assembled_dependency = await assembler.assemble(Invoke(assert_all))

        await assembled_dependency()


async def test_assembler_providers_only_called_once():
    _count = 0

    def count() -> int:
        nonlocal _count
        _count += 1
        return _count

    def assert_singleton(some: int) -> None:
        assert some == 1

    assembler = Assembler([Provide(count)])

    assembled_dependency = await assembler.assemble(Invoke(assert_singleton))
    await assembled_dependency()

    assembled_dependency = await assembler.assemble(Invoke(assert_singleton))
    await assembled_dependency()


def test_assembler_with_duplicate_provider_errors():
    with pytest.raises(RuntimeError):
        Assembler([int_provider(), int_provider()])


async def test_assembler_get():
    assembler = Assembler([int_provider(), Provide(make_many_int)])

    assert await assembler.build(int)
    assert await assembler.build(list[int])


async def test_assembler_with_unknown_type_raises_lookup_error():
    assembler = Assembler([])

    with pytest.raises(LookupError):
        await assembler.build(str)

    with pytest.raises(LookupError):
        await assembler.build(list[str])

    with pytest.raises(LookupError):
        await assembler.assemble(Entrypoint(str))


async def test_assembler_with_erroring_provider_raises_provider_error():
    def make_str() -> str:
        raise RuntimeError("foo")

    def make_many_str() -> list[str]:
        raise RuntimeError("foo")

    assembler = Assembler([Provide(make_str), Provide(make_many_str)])

    with pytest.raises(ProviderError):
        await assembler.build(str)

    with pytest.raises(ProviderError):
        await assembler.build(list[str])


async def test_annotations():
    def make_str_1() -> Annotated[str, "1"]:
        return "bar"

    def make_str_2() -> Annotated[str, "2"]:
        return "foo"

    assembler = Assembler([Provide(make_str_1), Provide(make_str_2)])

    with pytest.raises(LookupError):
        await assembler.build(str)

    assert await assembler.build(Annotated[str, "1"]) == "bar"
    assert await assembler.build(Annotated[str, "2"]) == "foo"


async def test_assembler_has():
    def make_str() -> str:
        raise RuntimeError("foo")

    assembler = Assembler([Provide(make_str)])

    assert assembler.has(str)
    assert not assembler.has(int)
    assert not assembler.has(list[str])


async def test_assembler_has_multi():
    def make_str() -> list[str]:
        raise RuntimeError("foo")

    assembler = Assembler([Provide(make_str)])

    assert assembler.has(list[str])
    assert not assembler.has(int)
    assert not assembler.has(str)


async def test_assembler_add():
    assembler = Assembler([])
    assembler.add(int_provider())
    assembler.add(Provide(make_many_int))

    assert assembler.has(int)
    assert assembler.has(list[int])

    # can always add more multiproviders
    assembler.add(Provide(make_many_int))


async def test_assembler_add_overrides():
    def str_provider_a(val: int) -> str:
        return f"a{val}"

    def str_provider_b(val: int) -> str:
        return f"b{val}"

    assembler = Assembler([int_provider(1), Provide(str_provider_a)])

    assert await assembler.build(str) == "a1"

    assembler.add(int_provider(2))
    assembler.add(Provide(str_provider_b))

    assert await assembler.build(str) == "b2"


async def test_assembler_add_clears_caches():
    def make_str(val: int) -> str:
        return str(val)

    assembler = Assembler([int_provider(1), Provide(make_str)])

    assert await assembler.build(int) == 1
    assert await assembler.build(str) == "1"

    assembler.add(int_provider(2))

    assert await assembler.build(int) == 2
    assert await assembler.build(str) == "2"


async def test_assembler_provider_not_in_scope():
    def scoped_provider() -> int:
        return time.time_ns()

    assembler = Assembler([Provide(scoped_provider, scope="foo")])

    with pytest.raises(NotInScopeError):
        await assembler.build(int)


async def test_assembler_provider_scope():
    def scoped_provider() -> int:
        return time.time_ns()

    assembler = Assembler([Provide(scoped_provider, scope="foo")])

    with assembler.scope("foo"):
        await assembler.build(int)

    with pytest.raises(NotInScopeError):
        await assembler.build(int)


async def test_assembler_provider_multi_scope():
    def scoped_provider() -> int:
        return time.time_ns()

    def scoped_provider_2() -> str:
        return "bar"

    assembler = Assembler(
        [Provide(scoped_provider, scope="foo"), Provide(scoped_provider_2, scope="bar")]
    )

    with assembler.scope("foo"):
        await assembler.build(int)
        with assembler.scope("bar"):
            await assembler.build(int)
            await assembler.build(str)
        await assembler.build(int)
