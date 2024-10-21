import inspect
from collections.abc import Iterable, Iterator

from engin._dependency import Func, Invoke, Provide


def provide(func: Func) -> Func:
    func._opt = Provide(func)  # type: ignore[union-attr]
    return func


def invoke(func: Func) -> Func:
    func._opt = Invoke(func)  # type: ignore[union-attr]
    return func


class Module(Iterable[Provide | Invoke]):
    _name: str
    _options: list[Provide | Invoke]

    def __init__(self, /, module_name: str | None = None) -> None:
        self._options: list[Provide | Invoke] = []
        self._name = module_name or f"{type(self).__module__}{type(self).__name__}"
        for _, method in inspect.getmembers(self):
            if opt := getattr(method, "_opt", None):
                if not isinstance(opt, (Provide, Invoke)):
                    raise RuntimeError("Module option is not an instance of Provide or Invoke")
                opt.set_module_name(self._name)
                self._options.append(opt)

    @property
    def name(self) -> str:
        return self._name

    def __iter__(self) -> Iterator[Provide | Invoke]:
        return iter(self._options)
