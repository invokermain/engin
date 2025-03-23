import inspect
import typing
from abc import ABC
from collections.abc import Awaitable, Callable
from inspect import Parameter, Signature, isclass, iscoroutinefunction
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    ParamSpec,
    TypeAlias,
    TypeVar,
    cast,
    get_type_hints,
)

from engin._introspect import get_first_external_frame
from engin._option import Option
from engin._type_utils import TypeId

if TYPE_CHECKING:
    from engin._engin import Engin

P = ParamSpec("P")
T = TypeVar("T")
Func: TypeAlias = Callable[P, T]


def _noop(*args: Any, **kwargs: Any) -> None: ...


class Dependency(ABC, Option, Generic[P, T]):
    def __init__(self, func: Func[P, T], block_name: str | None = None) -> None:
        self._func = func
        self._is_async = iscoroutinefunction(func)
        self._signature = inspect.signature(self._func)
        self._block_name = block_name

        source_frame = get_first_external_frame()
        self._source_package = cast("str", source_frame.frame.f_globals["__package__"])
        self._source_frame = cast("str", source_frame.frame.f_globals["__name__"])

    @property
    def source_module(self) -> str:
        """
        The module that this Dependency originated from.

        Returns:
            A string, e.g. "examples.fastapi.app"
        """
        return self._source_frame

    @property
    def source_package(self) -> str:
        """
        The package that this Dependency originated from.

        Returns:
            A string, e.g. "engin"
        """
        return self._source_package

    @property
    def block_name(self) -> str | None:
        return self._block_name

    @property
    def func_name(self) -> str:
        return self._func.__name__

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
        return [TypeId.from_type(param.annotation) for param in parameters]

    @property
    def signature(self) -> Signature:
        return self._signature

    def set_block_name(self, name: str) -> None:
        self._block_name = name

    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        if self._is_async:
            return await cast("Awaitable[T]", self._func(*args, **kwargs))
        else:
            return self._func(*args, **kwargs)


class Invoke(Dependency):
    """
    Marks a function as an Invocation.

    Invocations are functions that are called prior to lifecycle startup. Invocations
    should not be long running as the application startup will be blocked until all
    Invocation are completed.

    Invocations can be provided as an Option to the Engin or a Block.

    Examples:
        ```python3
        def print_string(a_string: str) -> None:
            print(f"invoking with value: '{a_string}'")

        invocation = Invoke(print_string)
        ```
    """

    def __init__(self, invocation: Func[P, T], block_name: str | None = None) -> None:
        super().__init__(func=invocation, block_name=block_name)

    def apply(self, engin: "Engin") -> None:
        engin._invocations.append(self)

    def __str__(self) -> str:
        return f"Invoke({self.name})"


class Entrypoint(Invoke):
    """
    Marks a type as an Entrypoint.

    Entrypoints are a short hand for no-op Invocations that can be used to
    """

    def __init__(self, type_: type[Any], *, block_name: str | None = None) -> None:
        self._type = type_
        super().__init__(invocation=_noop, block_name=block_name)

    @property
    def parameter_types(self) -> list[TypeId]:
        return [TypeId.from_type(self._type)]

    @property
    def signature(self) -> Signature:
        return Signature(
            parameters=[
                Parameter(name="x", kind=Parameter.POSITIONAL_ONLY, annotation=self._type)
            ]
        )

    def __str__(self) -> str:
        return f"Entrypoint({TypeId.from_type(self._type)})"


class Provide(Dependency[Any, T]):
    def __init__(self, builder: Func[P, T], block_name: str | None = None) -> None:
        super().__init__(func=builder, block_name=block_name)
        self._is_multi = typing.get_origin(self.return_type) is list

        # Validate that the provider does to depend on its own output value, as this will
        # cause a recursion error and is undefined behaviour wise.
        if any(
            self.return_type == param.annotation
            for param in self.signature.parameters.values()
        ):
            raise ValueError("A provider cannot depend on its own return type")

        # Validate that multiproviders only return a list of one type.
        if self._is_multi:
            args = typing.get_args(self.return_type)
            if len(args) != 1:
                raise ValueError(
                    f"A multiprovider must be of the form list[X], not '{self.return_type}'"
                )

    @property
    def return_type(self) -> type[T]:
        if isclass(self._func):
            return_type = self._func  # __init__ returns self
        else:
            try:
                return_type = get_type_hints(self._func, include_extras=True)["return"]
            except KeyError as err:
                raise RuntimeError(
                    f"Dependency '{self.name}' requires a return typehint"
                ) from err

        return return_type

    @property
    def return_type_id(self) -> TypeId:
        return TypeId.from_type(self.return_type)

    @property
    def is_multiprovider(self) -> bool:
        return self._is_multi

    def apply(self, engin: "Engin") -> None:
        if self.is_multiprovider:
            if self.return_type_id in engin._multiproviders:
                engin._multiproviders[self.return_type_id].append(self)
            else:
                engin._multiproviders[self.return_type_id] = [self]
        else:
            engin._providers[self.return_type_id] = self

    def __hash__(self) -> int:
        return hash(self.return_type_id)

    def __str__(self) -> str:
        return f"Provide({self.return_type_id})"


class Supply(Provide, Generic[T]):
    def __init__(
        self, value: T, *, type_hint: type | None = None, block_name: str | None = None
    ) -> None:
        self._value = value
        self._type_hint = type_hint
        if self._type_hint is not None:
            self._get_val.__annotations__["return"] = type_hint
        super().__init__(builder=self._get_val, block_name=block_name)

    @property
    def return_type(self) -> type[T]:
        if self._type_hint is not None:
            return self._type_hint
        if isinstance(self._value, list):
            return list[type(self._value[0])]  # type: ignore[misc,return-value]
        return type(self._value)

    def _get_val(self) -> T:
        return self._value

    def __str__(self) -> str:
        return f"Supply({self.return_type_id})"
