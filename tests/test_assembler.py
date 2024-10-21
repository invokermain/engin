from engin import Assembler, Invoke, Provide
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
