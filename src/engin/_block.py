import inspect
from collections.abc import Callable, Iterable, Sequence
from itertools import chain
from typing import TYPE_CHECKING, ClassVar

from engin._dependency import Dependency, Func, Invoke, Provide
from engin._option import Option
from engin.exceptions import InvalidBlockError

if TYPE_CHECKING:
    from engin._engin import Engin


def provide(
    func_: Func | None = None, *, scope: str | None = None, override: bool = False
) -> Func | Callable[[Func], Func]:
    """
    A decorator for defining a Provider in a Block.
    """

    def _inner(func: Func) -> Func:
        func._opt = Provide(func, override=override, scope=scope)  # type: ignore[attr-defined]
        return func

    if func_ is None:
        return _inner
    else:
        return _inner(func_)


def invoke(func_: Func | None = None) -> Func | Callable[[Func], Func]:
    """
    A decorator for defining an Invocation in a Block.
    """

    def _inner(func: Func) -> Func:
        func._opt = Invoke(func)  # type: ignore[attr-defined]
        return func

    if func_ is None:
        return _inner
    else:
        return _inner(func_)


class Block:
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

    name: ClassVar[str | None] = None
    options: ClassVar[Sequence[Option]] = []

    @classmethod
    def apply(cls, engin: "Engin") -> None:
        block_name = cls.name or cls.__name__
        for option in chain(cls.options, cls._method_options()):
            if isinstance(option, Dependency):
                option._block_name = block_name
            option.apply(engin)

    @classmethod
    def _method_options(cls) -> Iterable[Provide | Invoke]:
        for name, method in inspect.getmembers(cls, inspect.isfunction):
            if option := getattr(method, "_opt", None):
                if not isinstance(option, Provide | Invoke):
                    raise InvalidBlockError(
                        block=cls,
                        reason="Block option is not an instance of Provide or Invoke",
                    )
                yield option
            else:
                raise InvalidBlockError(
                    block=cls,
                    reason=(
                        f"Method '{name}' is not a Provider or Invocation, did you "
                        "forget to decorate it?"
                    ),
                )
