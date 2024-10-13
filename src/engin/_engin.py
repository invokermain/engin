import logging
from asyncio import Event
from collections.abc import Iterable
from inspect import BoundArguments, Signature
from typing import Any, TypeAlias, Union

from typing_extensions import TypeVar

from engin._dependency import Dependency, Invoke, Provide
from engin._types import TypeKey
from engin._utils import type_to_key

LOG = logging.getLogger(__name__)

Option: TypeAlias = Union[Invoke, Provide, "Module"]


class Module:
    def __init__(self, name: str, *options: Option) -> None:
        self._name = name
        self._options = options

    @property
    def name(self) -> str:
        return self._name

    @property
    def options(self) -> list[Option]:
        return list(self._options)


T = TypeVar("T")


class DependencyManager:
    def __init__(self, providers: dict[TypeKey, Provide]) -> None:
        self._providers = providers
        self._dependencies: dict[TypeKey, Any] = {}

    def _resolve_providers(self, target: TypeKey) -> list[Provide]:
        provider = self._providers.get(target)
        if provider is None:
            raise LookupError(f"No Provider registered for dependency '{target}'")
        required_providers = [
            provider
            for provider_param in provider.parameter_types
            for provider in self._resolve_providers(provider_param)
        ]
        return [*required_providers, provider]

    async def _satisfy(self, target: TypeKey) -> None:
        providers = self._resolve_providers(target)
        for provider in providers:
            bound_args = await self.bind_arguments(provider.signature)
            self._dependencies[provider.return_type] = await provider(
                *bound_args.args, **bound_args.kwargs
            )

    async def bind_arguments(self, signature: Signature) -> BoundArguments:
        args = []
        kwargs = {}
        for param_name, param in signature.parameters.items():
            param_key = type_to_key(param.annotation)
            if param_key not in self._dependencies:
                await self._satisfy(param_key)
            val = self._dependencies[param_key]
            if param.kind == param.POSITIONAL_ONLY:
                args.append(val)
            else:
                kwargs[param.name] = val

        return signature.bind(*args, **kwargs)

    def get_provider(self, return_type: type) -> Provide:
        return self._providers[type_to_key(return_type)]


class Engin:
    def __init__(self, *options: Option) -> None:
        self._providers: dict[TypeKey, Provide] = {}
        self._invokables: list[Invoke] = []
        self._stop_event = Event()

        self._destruct_options(options)
        self._dependency_manager = DependencyManager(self._providers)

    def _destruct_options(self, options: Iterable[Option]):
        for opt in options:
            if isinstance(opt, Module):
                self._destruct_options(opt.options)
            if isinstance(opt, Provide):
                LOG.debug(f"PROVIDE\t{opt}")
                self._providers[opt.return_type] = opt
            elif isinstance(opt, Invoke):
                LOG.debug(f"INVOKE\t{opt}")
                self._invokables.append(opt)

    async def run(self):
        await self.start()

        # lifecycle startup

        # wait till stop signal recieved
        await self._stop_event.wait()

        # lifecycle shutdown

    async def start(self) -> None:
        for invocation in self._invokables:
            bound_args = await self._dependency_manager.bind_arguments(invocation.signature)
            await invocation(*bound_args.args, **bound_args.kwargs)

        self._stop_event = Event()

    async def stop(self) -> None:
        self._stop_event.set()
