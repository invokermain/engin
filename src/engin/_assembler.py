import asyncio
import logging
from collections import defaultdict
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from inspect import BoundArguments, Signature
from typing import Any, Generic, TypeVar, cast

from engin._dependency import Dependency, Provide, Supply
from engin._exceptions import ProviderError
from engin._type_utils import TypeId

LOG = logging.getLogger("engin")

T = TypeVar("T")


@dataclass(slots=True, kw_only=True, frozen=True)
class AssembledDependency(Generic[T]):
    """
    An AssembledDependency can be called to construct the result.
    """

    dependency: Dependency[Any, T]
    bound_args: BoundArguments

    async def __call__(self) -> T:
        """
        Construct the dependency.

        Returns:
            The constructed value.
        """
        return await self.dependency(*self.bound_args.args, **self.bound_args.kwargs)


class Assembler:
    """
    A container for Providers that is responsible for building provided types.

    The Assembler acts as a cache for previously built types, meaning repeat calls
    to `get` will produce the same value.

    Examples:
        ```python
        def build_str() -> str:
            return "foo"

        a = Assembler([Provide(build_str)])
        await a.get(str)
        ```
    """

    def __init__(self, providers: Iterable[Provide]) -> None:
        self._providers: dict[TypeId, Provide[Any]] = {}
        self._multiproviders: dict[TypeId, list[Provide[list[Any]]]] = defaultdict(list)
        self._assembled_outputs: dict[TypeId, Any] = {}
        self._consumed_providers: set[Provide[Any]] = set()
        self._lock = asyncio.Lock()

        for provider in providers:
            type_id = provider.return_type_id
            if not provider.is_multiprovider:
                if type_id in self._providers:
                    raise RuntimeError(f"A Provider already exists for '{type_id}'")
                self._providers[type_id] = provider
            else:
                self._multiproviders[type_id].append(provider)

    async def assemble(self, dependency: Dependency[Any, T]) -> AssembledDependency[T]:
        """
        Assemble a dependency.

        Given a Dependency type, such as Invoke, the Assembler constructs the types
        required by the Dependency's signature from its providers.

        Args:
            dependency: the Dependency to assemble.

        Returns:
            An AssembledDependency, which can be awaited to construct the final value.
        """
        async with self._lock:
            return AssembledDependency(
                dependency=dependency,
                bound_args=await self._bind_arguments(dependency.signature),
            )

    async def get(self, type_: type[T]) -> T:
        """
        Return the constructed value for the given type.

        This method assembles the required Providers and constructs their corresponding
        values.

        If the

        Args:
            type_: the type of the desired value.

        Raises:
            LookupError: When no provider is found for the given type.
            ProviderError: When a provider errors when trying to construct the type or
                any of its dependent types.

        Returns:
            The constructed value.
        """
        type_id = TypeId.from_type(type_)
        if type_id in self._assembled_outputs:
            return cast("T", self._assembled_outputs[type_id])
        if type_id.multi:
            if type_id not in self._multiproviders:
                raise LookupError(f"no provider found for target type id '{type_id}'")

            out = []
            for provider in self._multiproviders[type_id]:
                assembled_dependency = await self.assemble(provider)
                try:
                    out.extend(await assembled_dependency())
                except Exception as err:
                    raise ProviderError(
                        provider=provider,
                        error_type=type(err),
                        error_message=str(err),
                    ) from err
            self._assembled_outputs[type_id] = out
            return out  # type: ignore[return-value]
        else:
            if type_id not in self._providers:
                raise LookupError(f"no provider found for target type id '{type_id}'")

            assembled_dependency = await self.assemble(self._providers[type_id])
            try:
                value = await assembled_dependency()
            except Exception as err:
                raise ProviderError(
                    provider=self._providers[type_id],
                    error_type=type(err),
                    error_message=str(err),
                ) from err
            self._assembled_outputs[type_id] = value
            return value  # type: ignore[return-value]

    def has(self, type_: type[T]) -> bool:
        """
        Returns True if this Assembler has a provider for the given type.

        Args:
            type_: the type to check.

        Returns:
            True if the Assembler has a provider for type else False.
        """
        type_id = TypeId.from_type(type_)
        if type_id.multi:
            return type_id in self._multiproviders
        else:
            return type_id in self._providers

    def add(self, provider: Provide) -> None:
        """
        Add a provider to the Assembler post-initialisation.

        If this replaces an existing provider, this will clear any previously assembled
        output for the existing Provider.

        Args:
            provider: the Provide instance to add.

        Returns:
             None
        """
        type_id = provider.return_type_id
        if provider.is_multiprovider:
            if type_id in self._multiproviders:
                if type_id in self._assembled_outputs:
                    del self._assembled_outputs[type_id]
                self._multiproviders[type_id].append(provider)
            else:
                self._multiproviders[type_id] = [provider]
        else:
            if provider in self._consumed_providers:
                self._consumed_providers.remove(provider)
                del self._assembled_outputs[type_id]
            self._providers[type_id] = provider

    def _resolve_providers(self, type_id: TypeId) -> Collection[Provide]:
        if type_id.multi:
            providers = self._multiproviders.get(type_id)
        else:
            providers = [provider] if (provider := self._providers.get(type_id)) else None
        if not providers:
            if type_id.multi:
                LOG.warning(f"no provider for '{type_id}' defaulting to empty list")
                providers = [(Supply([], type_hint=list[type_id.type]))]  # type: ignore[name-defined]
                # store default to prevent the warning appearing multiple times
                self._multiproviders[type_id] = providers
            else:
                available = sorted(str(k) for k in self._providers)
                msg = f"Missing Provider for type '{type_id}', available: {available}"
                raise LookupError(msg)

        required_providers: list[Provide[Any]] = []
        for provider in providers:
            required_providers.extend(
                provider
                for provider_param in provider.parameter_types
                for provider in self._resolve_providers(provider_param)
            )

        return {*required_providers, *providers}

    async def _satisfy(self, target: TypeId) -> None:
        for provider in self._resolve_providers(target):
            if provider in self._consumed_providers:
                continue
            self._consumed_providers.add(provider)
            type_id = provider.return_type_id
            bound_args = await self._bind_arguments(provider.signature)
            try:
                value = await provider(*bound_args.args, **bound_args.kwargs)
            except Exception as err:
                raise ProviderError(
                    provider=provider, error_type=type(err), error_message=str(err)
                ) from err
            if provider.is_multiprovider:
                if type_id in self._assembled_outputs:
                    self._assembled_outputs[type_id].extend(value)
                else:
                    self._assembled_outputs[type_id] = value
            else:
                self._assembled_outputs[type_id] = value

    async def _bind_arguments(self, signature: Signature) -> BoundArguments:
        args = []
        kwargs = {}
        for param_name, param in signature.parameters.items():
            if param_name == "self":
                args.append(object())
                continue
            param_key = TypeId.from_type(param.annotation)
            has_dependency = param_key in self._assembled_outputs
            if not has_dependency:
                await self._satisfy(param_key)
            val = self._assembled_outputs[param_key]
            if param.kind == param.POSITIONAL_ONLY:
                args.append(val)
            else:
                kwargs[param.name] = val

        return signature.bind(*args, **kwargs)
