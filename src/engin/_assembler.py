from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from inspect import BoundArguments, Signature
from typing import Any, Generic, TypeVar

from engin._dependency import Dependency, Provide
from engin._type_utils import TypeId, is_multi_type, type_id_of

T = TypeVar("T")


@dataclass(slots=True, kw_only=True, frozen=True)
class AssembledDependency(Generic[T]):
    dependency: Dependency[Any, T]
    bound_args: BoundArguments

    async def __call__(self) -> T:
        return await self.dependency(*self.bound_args.args, **self.bound_args.kwargs)


class Assembler:
    def __init__(self, providers: Iterable[Provide]) -> None:
        self._providers: dict[TypeId, Provide[Any]] = {}
        self._multiproviders: dict[TypeId, list[Provide[list[Any]]]] = defaultdict(list)
        self._dependencies: dict[TypeId, Any] = {}

        for provider in providers:
            type_id = provider.return_type_id
            if not provider.is_multiprovider:
                if type_id in self._providers:
                    raise RuntimeError(f"A Provider already exists for '{type_id}'")
                self._providers[type_id] = provider
            else:
                self._multiproviders[type_id].append(provider)

    def _resolve_providers(self, type_id: TypeId) -> list[Provide]:
        if type_id.multi:
            providers = self._multiproviders.get(type_id)
        else:
            providers = [provider] if (provider := self._providers.get(type_id)) else None
        if not providers:
            raise LookupError(f"No Provider registered for dependency '{type_id}'")

        required_providers: list[Provide[Any]] = []
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
            value = await provider(*bound_args.args, **bound_args.kwargs)
            if provider.is_multiprovider:
                if target in self._dependencies:
                    self._dependencies[target].extend(value)
                else:
                    self._dependencies[target] = value
            else:
                self._dependencies[target] = value

    async def _bind_arguments(self, signature: Signature) -> BoundArguments:
        args = []
        kwargs = {}
        for param_name, param in signature.parameters.items():
            if param_name == "self":
                args.append(object())
                continue
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

    async def get(self, type_: type[T]) -> T:
        type_id = type_id_of(type_)
        if type_id.multi:
            out = []
            for provider in self._multiproviders[type_id]:
                assembled_dependency = await self.assemble(provider)
                out.extend(await assembled_dependency())
            return out
        else:
            assembled_dependency = await self.assemble(self._providers[type_id])
            return await assembled_dependency()

    def has(self, type_: type[T]) -> bool:
        return type_id_of(type_) in self._providers