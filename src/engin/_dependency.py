import inspect
import typing
from abc import ABC
from inspect import Parameter, Signature, isclass, iscoroutinefunction
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

from engin._type_utils import TypeId, type_id_of

P = ParamSpec("P")
T = TypeVar("T")
Func: TypeAlias = (
    Callable[P, T] | Callable[P, Awaitable[T]] | Callable[[], T] | Callable[[], Awaitable[T]]
)
_SELF = object()


def _noop(*args: Any, **kwargs: Any) -> None: ...


class Dependency(ABC, Generic[P, T]):
    def __init__(self, func: Func[P, T], block_name: str | None = None) -> None:
        self._func = func
        self._is_async = iscoroutinefunction(func)
        self._signature = inspect.signature(self._func)
        self._block_name = block_name

    @property
    def block_name(self) -> str | None:
        return self._block_name

    @property
    def name(self) -> str:
        if self._block_name:
            return f"{self._block_name}.{self._func.__name__}"
        else:
            return f"{self._func.__module__}.{self._func.__name__}"

    @property
    def parameter_types(self) -> list[TypeId]:
        parameters = list(self._signature.parameters.values())
        if not parameters:
            return []
        if parameters[0].name == "self":
            parameters.pop(0)
        return [type_id_of(param.annotation) for param in parameters]

    @property
    def signature(self) -> Signature:
        return self._signature

    def set_block_name(self, name: str) -> None:
        self._block_name = name

    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        if self._is_async:
            return await cast(Awaitable[T], self._func(*args, **kwargs))
        else:
            return cast(T, self._func(*args, **kwargs))


class Invoke(Dependency):
    def __init__(self, invocation: Func[P, T], block_name: str | None = None):
        super().__init__(func=invocation, block_name=block_name)

    def __str__(self) -> str:
        return f"Invoke({self.name})"


class Entrypoint(Invoke):
    def __init__(self, type_: Type[Any], *, block_name: str | None = None) -> None:
        self._type = type_
        super().__init__(invocation=_noop, block_name=block_name)

    @property
    def parameter_types(self) -> list[TypeId]:
        return [type_id_of(self._type)]

    @property
    def signature(self) -> Signature:
        return Signature(
            parameters=[
                Parameter(name="x", kind=Parameter.POSITIONAL_ONLY, annotation=self._type)
            ]
        )

    def __str__(self) -> str:
        return f"Entrypoint({type_id_of(self._type)})"


class Provide(Dependency[Any, T]):
    def __init__(self, builder: Func[P, T], block_name: str | None = None):
        super().__init__(func=builder, block_name=block_name)
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
    def return_type_id(self) -> TypeId:
        return type_id_of(self.return_type)

    @property
    def is_multiprovider(self) -> bool:
        return self._is_multi

    def __hash__(self) -> int:
        return hash(self.return_type_id)

    def __str__(self) -> str:
        return f"Provide({self.return_type_id})"


class Supply(Provide, Generic[T]):
    def __init__(
        self, value: T, *, type_hint: type | None = None, block_name: str | None = None
    ):
        self._value = value
        self._type_hint = type_hint
        if self._type_hint is not None:
            self._get_val.__annotations__["return"] = type_hint
        super().__init__(builder=self._get_val, block_name=block_name)

    @property
    def return_type(self) -> Type[T]:
        if self._type_hint is not None:
            return self._type_hint
        if isinstance(self._value, list):
            return list[type(self._value[0])]  # type: ignore[misc,return-value]
        return type(self._value)

    def _get_val(self) -> T:
        return self._value

    def __str__(self) -> str:
        return f"Supply({self.return_type_id})"
