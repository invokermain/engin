from engin import Engin, Module, invoke, provide


def test_module():
    class MyModule(Module):
        @provide
        def provide_int(self) -> int:
            return 3

        @invoke
        def invoke_square(self, some: int) -> None:
            return some**2

    my_module = MyModule()

    options = list(iter(my_module))
    assert len(options) == 2

    assert Engin(my_module)
