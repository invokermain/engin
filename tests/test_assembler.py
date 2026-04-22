import asyncio
import time
from typing import Annotated

import pytest

from engin import Assembler, Entrypoint, Invoke, Provide, Supply
from engin.exceptions import NotInScopeError, ProviderError, TypeNotProvidedError
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

    with pytest.raises(TypeNotProvidedError):
        await assembler.build(str)

    with pytest.raises(TypeNotProvidedError):
        await assembler.build(list[str])

    with pytest.raises(TypeNotProvidedError):
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

    with pytest.raises(TypeNotProvidedError):
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


async def test_assembler_does_not_modify_multiprovider_values():
    def multidependency_user(values: list[int]) -> int:
        return 42

    provider = Provide(multidependency_user)
    providers = [Supply([1]), Supply([2]), provider]

    assembler1 = Assembler(providers)
    assembler2 = Assembler(providers)
    await assembler1.assemble(providers[2])
    await assembler2.assemble(providers[2])

    assert providers[0]._value == [1]
    assert providers[1]._value == [2]


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


async def test_assembler_scoped_provider_reused_in_child_scope():
    call_count = 0

    def scoped_provider() -> int:
        nonlocal call_count
        call_count += 1
        return call_count

    assembler = Assembler([Provide(scoped_provider, scope="foo")])

    with assembler.scope("foo"):
        outer = await assembler.build(int)
        with assembler.scope("bar"):
            inner = await assembler.build(int)

    assert outer is inner, "scoped provider was rebuilt in child scope instead of being reused"
    assert call_count == 1, f"expected 1 provider call, got {call_count}"


async def test_assembler_scoped_transitive_dep_isolated_across_concurrent_tasks():
    """Scoped types resolved as transitive deps (via _satisfy) must also be task-local."""
    call_count = 0

    def scoped_dep() -> int:
        nonlocal call_count
        call_count += 1
        return call_count

    def dependent_service(dep: int) -> str:
        return f"service-{dep}"

    assembler = Assembler(
        [Provide(scoped_dep, scope="request"), Provide(dependent_service, scope="request")]
    )

    task_a_has_built = asyncio.Event()
    a_dep: int | None = None
    b_dep: int | None = None

    async def task_a() -> None:
        nonlocal a_dep
        with assembler.scope("request"):
            svc = await assembler.build(str)
            a_dep = int(svc.split("-")[1])
            task_a_has_built.set()
            await asyncio.sleep(0)

    async def task_b() -> None:
        nonlocal b_dep
        await task_a_has_built.wait()
        with assembler.scope("request"):
            svc = await assembler.build(str)
            b_dep = int(svc.split("-")[1])

    await asyncio.gather(task_a(), task_b())

    assert call_count == 2, f"expected 2 provider calls, got {call_count}"
    assert a_dep != b_dep, "scoped transitive dep was shared across concurrent tasks"


async def test_assembler_scoped_provider_isolated_across_concurrent_tasks():
    call_count = 0

    def scoped_provider() -> int:
        nonlocal call_count
        call_count += 1
        return call_count

    assembler = Assembler([Provide(scoped_provider, scope="request")])

    task_a_has_built = asyncio.Event()
    a_value: int | None = None
    b_value: int | None = None

    async def task_a() -> None:
        nonlocal a_value
        with assembler.scope("request"):
            a_value = await assembler.build(int)
            task_a_has_built.set()
            # Yield while still in scope — this is the race window where task_b runs.
            await asyncio.sleep(0)

    async def task_b() -> None:
        nonlocal b_value
        # Wait until task_a has built but not yet exited its scope.
        await task_a_has_built.wait()
        with assembler.scope("request"):
            b_value = await assembler.build(int)

    await asyncio.gather(task_a(), task_b())

    assert call_count == 2, f"expected 2 provider calls, got {call_count}"
    assert a_value != b_value, "scoped provider was shared across concurrent tasks"


async def test_assembler_with_modifier():
    def make_str() -> str:
        return "foo"

    def add_prefix(value: str) -> str:
        return f"prefix_{value}"

    from engin import Modify

    assembler = Assembler.from_mapped_providers(
        providers={},
        multiproviders={},
        modifiers={},
    )
    assembler.add(Provide(make_str))
    assembler._modifiers[Modify(add_prefix).modifies_type_id] = Modify(add_prefix)

    result = await assembler.build(str)
    assert result == "prefix_foo"


async def test_assembler_modifier_is_cached():
    call_count = 0

    def make_str() -> str:
        return "foo"

    def add_prefix(value: str) -> str:
        nonlocal call_count
        call_count += 1
        return f"prefix_{value}"

    from engin import Modify

    modifier = Modify(add_prefix)

    assembler = Assembler.from_mapped_providers(
        providers={},
        multiproviders={},
        modifiers={modifier.modifies_type_id: modifier},
    )
    assembler.add(Provide(make_str))

    await assembler.build(str)
    await assembler.build(str)

    assert call_count == 1


async def test_assembler_modifier_receives_provider_output():
    received_value = None

    def make_str() -> str:
        return "original"

    def capture_modifier(value: str) -> str:
        nonlocal received_value
        received_value = value
        return f"modified_{value}"

    from engin import Modify

    modifier = Modify(capture_modifier)

    assembler = Assembler.from_mapped_providers(
        providers={},
        multiproviders={},
        modifiers={modifier.modifies_type_id: modifier},
    )
    assembler.add(Provide(make_str))

    result = await assembler.build(str)

    assert received_value == "original"
    assert result == "modified_original"


async def test_assembler_add_clears_modified_cache():
    def make_str() -> str:
        return "foo"

    def make_str_v2() -> str:
        return "bar"

    def add_prefix(value: str) -> str:
        return f"prefix_{value}"

    from engin import Modify

    modifier = Modify(add_prefix)

    assembler = Assembler.from_mapped_providers(
        providers={},
        multiproviders={},
        modifiers={modifier.modifies_type_id: modifier},
    )
    assembler.add(Provide(make_str))

    result1 = await assembler.build(str)
    assert result1 == "prefix_foo"

    assembler.add(Provide(make_str_v2))

    result2 = await assembler.build(str)
    assert result2 == "prefix_bar"


async def test_assembler_modifier_with_multiprovider():
    def make_ints_a() -> list[int]:
        return [1, 2]

    def make_ints_b() -> list[int]:
        return [3, 4]

    def double_all(values: list[int]) -> list[int]:
        return [v * 2 for v in values]

    from engin import Modify

    modifier = Modify(double_all)

    assembler = Assembler([Provide(make_ints_a), Provide(make_ints_b)])
    assembler._modifiers[modifier.modifies_type_id] = modifier

    result = await assembler.build(list[int])
    assert result == [2, 4, 6, 8]


async def test_modified_scoped_values_isolated_across_concurrent_tasks():
    """Bug #2: modified scoped values must be task-local, not globally cached."""
    call_count = 0

    def scoped_int() -> int:
        nonlocal call_count
        call_count += 1
        return call_count * 100

    def double(value: int) -> int:
        return value * 2

    from engin import Modify

    modifier = Modify(double)
    assembler = Assembler.from_mapped_providers(
        providers={},
        multiproviders={},
        modifiers={modifier.modifies_type_id: modifier},
    )
    assembler.add(Provide(scoped_int, scope="request"))

    task_a_has_built = asyncio.Event()
    a_value: int | None = None
    b_value: int | None = None

    async def task_a() -> None:
        nonlocal a_value
        with assembler.scope("request"):
            a_value = await assembler.build(int)
            task_a_has_built.set()
            await asyncio.sleep(0)

    async def task_b() -> None:
        nonlocal b_value
        await task_a_has_built.wait()
        with assembler.scope("request"):
            b_value = await assembler.build(int)

    await asyncio.gather(task_a(), task_b())

    assert a_value == 200, f"expected 200, got {a_value}"
    assert b_value == 400, f"expected 400, got {b_value}"
    assert a_value != b_value, "modified scoped values leaked across tasks"


async def test_subtask_scope_does_not_corrupt_parent_scope():
    """Bug #1: spawned subtask entering inner scope must not corrupt parent's scope."""
    call_count = 0

    def outer_provider() -> int:
        nonlocal call_count
        call_count += 1
        return call_count

    assembler = Assembler([Provide(outer_provider, scope="outer")])

    async def subtask() -> None:
        with assembler.scope("inner"):
            await asyncio.sleep(0)

    with assembler.scope("outer"):
        val1 = await assembler.build(int)

        # Spawn a subtask that enters a different scope
        await asyncio.create_task(subtask())

        # Parent scope should still be intact — same cached value
        val2 = await assembler.build(int)

    assert val1 is val2, "parent scope was corrupted by subtask"
    assert call_count == 1, f"expected 1 provider call, got {call_count}"


async def test_scoped_modifier_reruns_per_scope_entry():
    """Sequential regression: modifier must re-run on each scope entry, not use stale cache."""
    provider_count = 0
    modifier_count = 0

    def scoped_int() -> int:
        nonlocal provider_count
        provider_count += 1
        return provider_count * 10

    def add_one(value: int) -> int:
        nonlocal modifier_count
        modifier_count += 1
        return value + 1

    from engin import Modify

    modifier = Modify(add_one)
    assembler = Assembler.from_mapped_providers(
        providers={},
        multiproviders={},
        modifiers={modifier.modifies_type_id: modifier},
    )
    assembler.add(Provide(scoped_int, scope="request"))

    with assembler.scope("request"):
        first = await assembler.build(int)

    with assembler.scope("request"):
        second = await assembler.build(int)

    assert first == 11, f"expected 11, got {first}"
    assert second == 21, f"expected 21, got {second}"
    assert provider_count == 2, f"provider should have run twice, ran {provider_count}"
    assert modifier_count == 2, f"modifier should have run twice, ran {modifier_count}"


def test_scoped_multiprovider_rejected():
    """Multiproviders cannot be scoped — rejected at construction time."""

    def scoped_ints() -> list[int]:
        return [1]

    with pytest.raises(ValueError, match="Multiproviders cannot be scoped"):
        Provide(scoped_ints, scope="request")
