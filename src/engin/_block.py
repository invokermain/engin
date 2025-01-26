import inspect
from collections.abc import Iterable, Iterator
from typing import ClassVar

from engin._dependency import Func, Invoke, Provide


def provide(func: Func) -> Func:
    func._opt = Provide(func)  # type: ignore[attr-defined]
    return func


def invoke(func: Func) -> Func:
    func._opt = Invoke(func)  # type: ignore[attr-defined]
    return func


class Block(Iterable[Provide | Invoke]):
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
