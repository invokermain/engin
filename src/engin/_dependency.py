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
    def __init__(self, func: Func[P, T]) -> None:
        self._func = func
        self._is_async = iscoroutinefunction(func)
        self._signature = inspect.signature(self._func, eval_str=True)
        self._block_name: str | None = None

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
    def parameter_type_ids(self) -> list[TypeId]:
        parameters = list(self._signature.parameters.values())
        if not parameters:
            return []
        if parameters[0].name == "self":
            parameters.pop(0)
        return [TypeId.from_type(param.annotation) for param in parameters]

    @property
    def signature(self) -> Signature:
        return self._signature

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

    def __init__(self, invocation: Func[P, T]) -> None:
        super().__init__(func=invocation)

    def apply(self, engin: "Engin") -> None:
        engin._invocations.append(self)

    def __str__(self) -> str:
        return f"Invoke({self.name})"


class Entrypoint(Invoke):
    """
    Marks a type as an Entrypoint.

    Entrypoints are a short hand for no-op Invocations that can be used to
    """

    def __init__(self, type_: type[Any]) -> None:
        self._type = type_
        super().__init__(invocation=_noop)

    @property
    def parameter_type_ids(self) -> list[TypeId]:
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
    def __init__(
        self,
        factory: Func[P, T],
        *,
        scope: str | None = None,
        as_type: type | None = None,
        override: bool = False,
    ) -> None:
        """
        Provide a type via a factory function.

        Args:
            factory: the factory function that returns the type.
            scope: (optional) associate this provider with a specific scope.
            as_type: (optional) allows you to explicitly specify the provided type, e.g.
                to type erase a concrete type, or to provide a mock implementation.
            override: (optional) allow this provider to override other providers for the
                same type from the same package.
        """
        super().__init__(func=factory)
        self._scope = scope
        self._override = override
        self._explicit_type = as_type
        self._return_type = self._resolve_return_type()
        self._return_type_id = TypeId.from_type(self._return_type)

        if self._explicit_type is not None:
            self._signature = self._signature.replace(return_annotation=self._explicit_type)

        self._is_multi = typing.get_origin(self._return_type) is list

        # Validate that the provider does to depend on its own output value, as this will
        # cause a recursion error and is undefined behaviour wise.
        if any(
            self._return_type == param.annotation
            for param in self._signature.parameters.values()
        ):
            raise ValueError("A provider cannot depend on its own return type")

        # Validate that multiproviders only return a list of one type.
        if self._is_multi:
            args = typing.get_args(self._return_type)
            if len(args) != 1:
                raise ValueError(
                    f"A multiprovider must be of the form list[X], not '{self._return_type}'"
                )

    @property
    def return_type(self) -> type[T]:
        return self._return_type

    @property
    def return_type_id(self) -> TypeId:
        return self._return_type_id

    @property
    def is_multiprovider(self) -> bool:
        return self._is_multi

    @property
    def scope(self) -> str | None:
        return self._scope

    def apply(self, engin: "Engin") -> None:
        type_id = self.return_type_id
        if self.is_multiprovider:
            engin._multiproviders[type_id].append(self)
            return

        if type_id not in engin._providers:
            engin._providers[type_id] = self
            return

        existing_provider = engin._providers[type_id]
        is_same_package = existing_provider.source_package == self.source_package

        # overwriting a dependency from the same package must be explicit
        if is_same_package and not self._override:
            msg = (
                f"{self} from '{self._source_frame}' is implicitly overriding "
                f"{existing_provider} from '{existing_provider.source_module}', if this "
                "is intentional specify `override=True` for the overriding Provider"
            )
            raise RuntimeError(msg)

        engin._providers[type_id] = self

    def __hash__(self) -> int:
        return hash(self.return_type_id)

    def __str__(self) -> str:
        return f"Provide(factory={self.func_name}, type={self._return_type_id})"

    def _resolve_return_type(self) -> type[T]:
        if self._explicit_type is not None:
            return self._explicit_type
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


class Supply(Provide, Generic[T]):
    def __init__(
        self, value: T, *, as_type: type | None = None, override: bool = False
    ) -> None:
        """
        Supply a value.

        This is a shorthand which under the hood creates a Provider with a noop factory
        function.

        Args:
            value: the value to Supply.
            as_type: (optional) allows you to explicitly specify the provided type, e.g.
              to type erase a concrete type, or to provide a mock implementation.
            override: (optional) allow this provider to override other providers for the
              same type from the same package.
        """
        self._value = value
        super().__init__(factory=self._get_val, as_type=as_type, override=override)

    @property
    def name(self) -> str:
        if self._block_name:
            return f"{self._block_name}.supply"
        else:
            return f"{self._source_frame}.supply"

    def _resolve_return_type(self) -> type[T]:
        if self._explicit_type is not None:
            return self._explicit_type
        if isinstance(self._value, list):
            return list[type(self._value[0])]  # type: ignore[misc,return-value]
        return type(self._value)

    def _get_val(self) -> T:
        return self._value

    def __str__(self) -> str:
        return f"Supply(value={self._value}, type={self.return_type_id})"
