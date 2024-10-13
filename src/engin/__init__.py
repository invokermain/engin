import inspect
import logging
from collections.abc import Callable
from inspect import BoundArguments, Signature, iscoroutinefunction
from typing import Any, Awaitable, ParamSpec, TypeAlias, TypeVar, get_type_hints

from engin._utils import type_to_key

LOG = logging.getLogger(__name__)
P = ParamSpec("P")
T = TypeVar("T")
Builder: TypeAlias = Callable[P, T | Awaitable[T]]
Invocation: TypeAlias = Callable[P, T | Awaitable[T]]


class Provide:
    def __init__(self, builder: Builder) -> None:
        self._builder = builder
        self._is_async = iscoroutinefunction(builder)
        self._output = None

    async def build(self) -> T:
        if self._is_async:
            self._output = await self._builder()
        else:
            self._output = self._builder()
        return self._output

    @property
    def name(self) -> str:
        return type_to_key(self._builder)

    @property
    def provided_type(self) -> str:
        return_type = get_type_hints(self._builder)["return"]
        return type_to_key(return_type)


class Invoke:
    def __init__(self, invocation: Invocation):
        self._invocation = invocation
        self._is_async = iscoroutinefunction(invocation)
        self._bound_arguments: BoundArguments | None = None
        self._signature = inspect.signature(self._invocation)

    @property
    def signature(self) -> Signature:
        return self._signature

    @property
    def name(self) -> str:
        return self._invocation.__name__

    def bind(self, dependencies: dict[str, Any]) -> None:
        args = []
        kwargs = {}
        for param_name, param in self._signature.parameters.items():
            param_key = type_to_key(param.annotation)
            if param_key not in dependencies:
                raise LookupError(f"Missing dependency '{param_key}' for '{self.name}'")
            val = dependencies[param_key]
            if param.kind == param.POSITIONAL_ONLY:
                args.append(val)
            else:
                kwargs[param.name] = val

        self._bound_arguments = self._signature.bind(*args, **kwargs)

    async def __call__(self) -> None:
        if self._bound_arguments is None:
            raise RuntimeError("Cannot call invocation as arguments have not been bound")
        if self._is_async:
            self._output = await self._invocation(
                *self._bound_arguments.args, **self._bound_arguments.kwargs
            )
        else:
            self._output = self._invocation(
                *self._bound_arguments.args, **self._bound_arguments.kwargs
            )


Options: TypeAlias = Provide | Invoke


class Engin:
    def __init__(self, *options: Options) -> None:
        self._providers = []
        self._invocations = []

        for opt in options:
            if isinstance(opt, Provide):
                LOG.debug(f"PROVIDE\t{opt.provided_type} <- {opt.name}")
                self._providers.append(opt)
            elif isinstance(opt, Invoke):
                LOG.debug(f"INVOKE\t{opt.name}")
                self._invocations.append(opt)

        self._dependencies = {}

    async def run(self):
        # resolve dependency graph
        for provider in self._providers:
            self._dependencies[provider.provided_type] = await provider.build()

        # invoke invocations
        for invocation in self._invocations:
            invocation.bind(self._dependencies)
            await invocation()


__all__ = ["Engin", "Invoke", "Provide", "Options"]
