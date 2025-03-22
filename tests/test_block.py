from engin import Block, Engin, invoke, provide


def test_block():
    class MyBlock(Block):
        @provide
        def provide_int(self) -> int:
            return 3

        @invoke
        def invoke_square(self, some: int) -> None:
            return some**2

    my_block = MyBlock()

    options = list(my_block._method_options())
    assert len(options) == 2

    assert Engin(my_block)
