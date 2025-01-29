import inspect
from collections.abc import Iterable, Iterator
from typing import ClassVar

from engin._dependency import Func, Invoke, Provide


def provide(func: Func) -> Func:
    """
    A decorator for defining a Provider in a Block.
    """
    func._opt = Provide(func)  # type: ignore[attr-defined]
    return func


def invoke(func: Func) -> Func:
    """
    A decorator for defining an Invocation in a Block.
    """
    func._opt = Invoke(func)  # type: ignore[attr-defined]
    return func


class Block(Iterable[Provide | Invoke]):
    """
    A Block is a collection of providers and invocations.

    Blocks are useful for grouping a collection of related providers and invocations, and
    are themselves a valid Option type that can be passed to the Engin.

    Providers are defined as methods decorated with the `provide` decorator, and similarly
    for Invocations and the `invoke` decorator.

    Examples:
        Define a simple block.

        ```python3
        from engin import Block, provide, invoke

        class MyBlock(Block):
            @provide
            def some_str(self) -> str:
                return "foo"

            @invoke
            def print_str(self, string: str) -> None:
                print(f"invoked on string '{string}')
        ```
    """

    options: ClassVar[list[Provide | Invoke]] = []

    def __init__(self, /, block_name: str | None = None) -> None:
        self._options: list[Provide | Invoke] = self.options[:]
        self._name = block_name or f"{type(self).__name__}"
        for _, method in inspect.getmembers(self):
            if opt := getattr(method, "_opt", None):
                if not isinstance(opt, Provide | Invoke):
                    raise RuntimeError("Block option is not an instance of Provide or Invoke")
                opt.set_block_name(self._name)
                self._options.append(opt)

    @property
    def name(self) -> str:
        return self._name

    def __iter__(self) -> Iterator[Provide | Invoke]:
        return iter(self._options)
