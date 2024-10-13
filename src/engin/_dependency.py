import inspect
from abc import ABC
from enum import Enum
from inspect import BoundArguments, Signature, isclass, iscoroutinefunction
from typing import (
    Awaitable,
    Callable,
    ParamSpec,
    TypeAlias,
    TypeVar,
    cast,
    get_type_hints,
)

from engin._types import TypeKey
from engin._utils import type_to_key

P = ParamSpec("P")
T = TypeVar("T")
Func: TypeAlias = Callable[P, T] | Callable[P, Awaitable[T]]


class DependencyType(Enum):
    PROVIDE = "PROVIDE"
    INVOKE = "INVOKE"


class Dependency(ABC):
    def __init__(self, func: Func[P, T], dependency_type: DependencyType):
        self._func = func
        self._is_async = iscoroutinefunction(func)
        self._bound_arguments: BoundArguments | None = None
        self._signature = inspect.signature(self._func)
        self._type = dependency_type

    @property
    def type(self) -> DependencyType:
        return self._type

    @property
    def signature(self) -> Signature:
        return self._signature

    @property
    def parameter_types(self) -> list[TypeKey]:
        return [type_to_key(param.annotation) for param in self._signature.parameters.values()]

    @property
    def return_type(self) -> str:
        if isclass(self._func):
            return_type = self._func  # __init__ returns self
        else:
            try:
                return_type = get_type_hints(self._func)["return"]
            except KeyError:
                raise RuntimeError(f"Dependency '{self.name}' requires a return typehint")
        return type_to_key(return_type)

    @property
    def name(self) -> str:
        return f"{self._func.__module__}.{self._func.__name__}"

    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        if self._is_async:
            return await cast(Awaitable[T], self._func(*args, **kwargs))
        else:
            return cast(T, self._func(*args, **kwargs))


class Invoke(Dependency):
    def __init__(self, invocation: Func[P, T], module_name: str | None = None):
        super().__init__(func=invocation, dependency_type=DependencyType.INVOKE)
        self._module_name = module_name

    def __str__(self) -> str:
        module_string = f" from module {self._module_name}" if self._module_name else ""
        return f"{self.name}()" + module_string


class Provide(Dependency):
    def __init__(self, builder: Func[P, T], module_name: str | None = None):
        super().__init__(func=builder, dependency_type=DependencyType.PROVIDE)
        self._module_name = module_name

    def __str__(self) -> str:
        module_string = f" from module {self._module_name}" if self._module_name else ""
        return f"{self.return_type} < - {self.name}()" + module_string
