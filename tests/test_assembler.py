from typing import Annotated

import pytest

from engin import Assembler, Invoke, Provide
from engin._exceptions import ProviderError
from tests.deps import make_int, make_many_int, make_many_int_alt, make_str


async def test_assembler():
    assembler = Assembler([Provide(make_int), Provide(make_str), Provide(make_many_int)])

    def assert_all(some_int: int, some_str: str, many_ints: list[int]):
        assert isinstance(some_str, str)
        assert isinstance(some_int, int)
        assert all(isinstance(x, int) for x in many_ints)

    assembled_dependency = await assembler.assemble(Invoke(assert_all))

    await assembled_dependency()


async def test_assembler_with_multiproviders():
    assembler = Assembler([Provide(make_many_int), Provide(make_many_int_alt)])

    def assert_all(many_ints: list[int]):
        expected_ints = [*make_many_int(), *make_many_int_alt()]
        assert sorted(many_ints) == sorted(expected_ints)

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


async def test_assembler_with_unknown_type_raises_lookup_error():
    assembler = Assembler([])

    with pytest.raises(LookupError):
        await assembler.get(str)


async def test_assembler_with_unknown_type_raises_assembly_error():
    def make_str() -> str:
        raise RuntimeError("foo")

    assembler = Assembler([Provide(make_str)])

    with pytest.raises(ProviderError):
        await assembler.get(str)


async def test_annotations():
    def make_str_1() -> Annotated[str, "1"]:
        return "bar"

    def make_str_2() -> Annotated[str, "2"]:
        return "foo"

    assembler = Assembler([Provide(make_str_1), Provide(make_str_2)])

    with pytest.raises(LookupError):
        await assembler.get(str)

    assert await assembler.get(Annotated[str, "1"]) == "bar"
    assert await assembler.get(Annotated[str, "2"]) == "foo"
