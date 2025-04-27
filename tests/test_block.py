from unittest.mock import Mock

import pytest

from engin import Block, Engin, invoke, provide
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
