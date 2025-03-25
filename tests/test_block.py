from engin import Block, Engin, invoke, provide


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
