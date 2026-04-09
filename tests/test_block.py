from unittest.mock import Mock

import pytest

from engin import Block, Engin, Invoke, Modify, Provide, invoke, modify, provide
from engin.exceptions import InvalidBlockError


def test_block():
    class MyBlock(Block):
        @provide
        def provide_int(self) -> int:
            return 3

        @invoke
        def invoke_square(self, some: int) -> None: ...

        @provide()
        def provide_str(self) -> str:
            return "3"

        @invoke()
        def invoke_str(self, some: str) -> None: ...

    my_block = MyBlock()

    options = list(my_block._method_options())

    assert len(options) == 4
    assert Engin(my_block)


def test_block_validation_undecorated_method():
    class MyBlock(Block):
        def provide_str(self) -> str:
            return "3"

    with pytest.raises(InvalidBlockError) as exc_info:
        MyBlock.apply(Mock())

    assert "forget" in str(exc_info.value)


def test_block_validation_illegal_decorator():
    class MyBlock(Block):
        def provide_str(self) -> str:
            return "3"

        provide_str._opt = int

    with pytest.raises(InvalidBlockError) as exc_info:
        MyBlock.apply(Mock())

    assert "Invoke" in str(exc_info.value)


def test_block_with_modify():
    class MyBlock(Block):
        @provide
        def provide_str(self) -> str:
            return "foo"

        @modify
        def add_prefix(self, value: str) -> str:
            return f"prefix_{value}"

    my_block = MyBlock()

    options = list(my_block._method_options())

    assert len(options) == 2


def test_block_modify_with_override():
    class MyBlock(Block):
        @provide
        def provide_str(self) -> str:
            return "foo"

        @modify(override=True)
        def add_prefix(self, value: str) -> str:
            return f"prefix_{value}"

    my_block = MyBlock()

    options = list(my_block._method_options())

    assert len(options) == 2


async def test_block_scoped_modifier_only_affects_block_invocations():
    """Modifier in a block only affects that block's invocations, not outside ones."""
    received_in_block: str | None = None
    received_outside: str | None = None

    class MyBlock(Block):
        @modify
        def upper(self, value: str) -> str:
            return value.upper()

        @invoke
        def check(self, value: str) -> None:
            nonlocal received_in_block
            received_in_block = value

    def check_raw(value: str) -> None:
        nonlocal received_outside
        received_outside = value

    def make_str() -> str:
        return "foo"

    engin = Engin(Provide(make_str), MyBlock(), Invoke(check_raw))
    await engin.start()
    await engin.stop()

    assert received_in_block == "FOO", (
        f"block invocation should see modified value, got {received_in_block}"
    )
    assert received_outside == "foo", (
        f"outside invocation should see raw value, got {received_outside}"
    )


async def test_block_scoped_modifier_does_not_affect_other_block():
    """Modifier in BlockA does not affect BlockB's invocations."""
    received_a: str | None = None
    received_b: str | None = None

    class BlockA(Block):
        @modify
        def upper(self, value: str) -> str:
            return value.upper()

        @invoke
        def check_a(self, value: str) -> None:
            nonlocal received_a
            received_a = value

    class BlockB(Block):
        @invoke
        def check_b(self, value: str) -> None:
            nonlocal received_b
            received_b = value

    def make_str() -> str:
        return "foo"

    engin = Engin(Provide(make_str), BlockA(), BlockB())
    await engin.start()
    await engin.stop()

    assert received_a == "FOO", f"BlockA should see modified value, got {received_a}"
    assert received_b == "foo", f"BlockB should see raw value, got {received_b}"


async def test_block_modifier_composes_with_global_modifier():
    """Block modifier receives the globally-modified value."""
    received: str | None = None

    def make_str() -> str:
        return "foo"

    def global_prefix(value: str) -> str:
        return f"global_{value}"

    class MyBlock(Block):
        @modify
        def upper(self, value: str) -> str:
            return value.upper()

        @invoke
        def check(self, value: str) -> None:
            nonlocal received
            received = value

    engin = Engin(Provide(make_str), Modify(global_prefix), MyBlock())
    await engin.start()
    await engin.stop()

    assert received == "GLOBAL_FOO", (
        f"block should see global then block modifier, got {received}"
    )


async def test_global_modifier_applied_via_engin():
    """Global modifier works through the Engin invocation path (not just Assembler.build)."""
    received: str | None = None

    def make_str() -> str:
        return "foo"

    def add_prefix(value: str) -> str:
        return f"prefix_{value}"

    def check(value: str) -> None:
        nonlocal received
        received = value

    engin = Engin(Provide(make_str), Modify(add_prefix), Invoke(check))
    await engin.start()
    await engin.stop()

    assert received == "prefix_foo", f"invocation should see modified value, got {received}"
