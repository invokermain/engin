from collections.abc import Iterable
from dataclasses import dataclass
from inspect import BoundArguments, Signature
from typing import Any, Generic, TypeVar

from engin._dependency import Dependency, DependencyType, Provide
from engin._types import TypeId
from engin._utils import type_id_of

T = TypeVar("T")


@dataclass(slots=True, kw_only=True, frozen=True)
class AssembledDependency(Generic[T]):
    dependency: Dependency[Any, T]
    bound_args: BoundArguments

    async def __call__(self) -> T:
        return await self.dependency(*self.bound_args.args, **self.bound_args.kwargs)


class _ProviderCollection(Dependency[Any, T]):
    def __init__(self, provider: Provide[Any, T]) -> None:
        self._providers = [provider]
        self._return_type = provider.return_type
        super().__init__(self.resolve)

    def add(self, provider: Provide[Any, T]) -> None:
        self._providers.append(provider)

    @property
    def return_type(self) -> type[T]:
        return self._return_type

    async def resolve(self) -> list[T]:
        out = []
        for provider in self._providers:
            out.extend(await provider())


class Assembler:
    def __init__(self, providers: Iterable[Provide]) -> None:
        self._providers: dict[TypeId, list[Provide]] = {}
        self._dependencies: dict[TypeId, Any] = {}

        for provider in providers:
            if provider.return_type_id in self._providers:
                self._providers[provider.return_type_id].append(provider)
            else:
                self._providers[provider.return_type_id] = [provider]

    def _resolve_providers(self, target: TypeId) -> list[Provide]:
        providers = self._providers.get(target)
        if not providers:
            raise LookupError(f"No Provider registered for dependency '{target}'")

        required_providers = []
        for provider in providers:
            required_providers.extend(
                provider
                for provider_param in provider.parameter_types
                for provider in self._resolve_providers(provider_param)
            )

        return [*required_providers, *providers]

    async def _satisfy(self, target: TypeId) -> None:
        providers = self._resolve_providers(target)
        for provider in providers:
            bound_args = await self._bind_arguments(provider.signature)
            self._dependencies[provider.return_type_id] = await provider(
                *bound_args.args, **bound_args.kwargs
            )

    async def _bind_arguments(self, signature: Signature) -> BoundArguments:
        args = []
        kwargs = {}
        for param_name, param in signature.parameters.items():
            param_key = type_id_of(param.annotation)
            if param_key not in self._dependencies:
                await self._satisfy(param_key)
            val = self._dependencies[param_key]
            if param.kind == param.POSITIONAL_ONLY:
                args.append(val)
            else:
                kwargs[param.name] = val

        return signature.bind(*args, **kwargs)

    async def assemble(self, dependency: Dependency[Any, T]) -> AssembledDependency[T]:
        return AssembledDependency(
            dependency=dependency,
            bound_args=await self._bind_arguments(dependency.signature),
        )

    async def get(self, return_type: type[T]) -> T:
        return await self.assemble(self._providers[type_id_of(return_type)])

    def has(self, return_type: type[T]) -> bool:
        return type_id_of(return_type) in self._providers
