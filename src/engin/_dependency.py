import inspect
import typing
from abc import ABC
from inspect import BoundArguments, Signature, isclass, iscoroutinefunction
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    ParamSpec,
    Type,
    TypeAlias,
    TypeVar,
    cast,
    get_type_hints,
)

from engin._types import TypeId
from engin._utils import type_id_of

P = ParamSpec("P")
T = TypeVar("T")
Func: TypeAlias = Callable[P, T] | Callable[P, Awaitable[T]]


class Dependency(ABC, Generic[P, T]):
    def __init__(self, func: Func[P, T], module_name: str | None = None) -> None:
        self._func = func
        self._is_async = iscoroutinefunction(func)
        self._bound_arguments: BoundArguments | None = None
        self._signature = inspect.signature(self._func)
        self._module_name = module_name

    @property
    def module_name(self) -> str | None:
        return self._module_name

    @property
    def name(self) -> str:
        return f"{self._func.__module__}.{self._func.__name__}"

    @property
    def parameter_types(self) -> list[TypeId]:
        return [type_id_of(param.annotation) for param in self._signature.parameters.values()]

    @property
    def signature(self) -> Signature:
        return self._signature

    def set_module_name(self, name: str) -> None:
        self._module_name = name

    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        if self._is_async:
            return await cast(Awaitable[T], self._func(*args, **kwargs))
        else:
            return cast(T, self._func(*args, **kwargs))


class Invoke(Dependency):
    def __init__(self, invocation: Func[P, T], module_name: str | None = None):
        super().__init__(func=invocation, module_name=module_name)

    def __str__(self) -> str:
        return f"Invoke({self.name})"


class Provide(Dependency[Any, T]):
    def __init__(self, builder: Func[P, T], module_name: str | None = None):
        super().__init__(func=builder, module_name=module_name)
        self._is_multi = typing.get_origin(self.return_type) is list

        if self._is_multi:
            args = typing.get_args(self.return_type)
            if len(args) != 1:
                raise ValueError(
                    f"A multiprovider must be of the form list[X], not '{self.return_type}'"
                )

    @property
    def return_type(self) -> Type[T]:
        if isclass(self._func):
            return_type = self._func  # __init__ returns self
        else:
            try:
                return_type = get_type_hints(self._func)["return"]
            except KeyError:
                raise RuntimeError(f"Dependency '{self.name}' requires a return typehint")

        return return_type

    @property
    def return_type_id(self) -> str:
        return type_id_of(self.return_type)

    @property
    def is_multiprovider(self) -> bool:
        return self._is_multi

    def __hash__(self) -> int:
        return hash(self.return_type_id)

    def __str__(self) -> str:
        return f"Provide({self.name}() -> {self.return_type_id})"


class Supply(Provide, Generic[T]):
    def __init__(self, value: T, module_name: str | None = None):
        self._value = value
        super().__init__(builder=self._get_val, module_name=module_name)

    @property
    def return_type(self) -> Type[T]:
        if isinstance(self._value, list):
            return list[type(self._value[0])]  # type: ignore[misc,return-value]
        return type(self._value)

    def _get_val(self) -> T:
        return self._value

    def __str__(self) -> str:
        return f"Supply({self.name} -> {self.return_type_id})"
