import asyncio
import logging
from collections import defaultdict
from collections.abc import Iterable, Sequence
from contextvars import ContextVar
from dataclasses import dataclass
from inspect import BoundArguments, Signature
from types import TracebackType
from typing import Any, Generic, TypeVar, cast

from typing_extensions import Self

from engin._dependency import Dependency, Modify, Provide, Supply
from engin._type_utils import TypeId
from engin.exceptions import NotInScopeError, ProviderError, TypeNotProvidedError

LOG = logging.getLogger("engin")

T = TypeVar("T")


@dataclass
class _ScopeNode:
    name: str
    cache: dict[TypeId, Any]
    modified_cache: dict[TypeId, Any]
    parent: "_ScopeNode | None"

    def find(self, type_id: TypeId) -> tuple[bool, Any]:
        node: _ScopeNode | None = self
        while node is not None:
            if type_id in node.cache:
                return True, node.cache[type_id]
            node = node.parent
        return False, None

    def find_modified(self, type_id: TypeId) -> tuple[bool, Any]:
        node: _ScopeNode | None = self
        while node is not None:
            if type_id in node.modified_cache:
                return True, node.modified_cache[type_id]
            node = node.parent
        return False, None

    def has_scope(self, name: str) -> bool:
        node: _ScopeNode | None = self
        while node is not None:
            if node.name == name:
                return True
            node = node.parent
        return False

    @property
    def scope_names(self) -> list[str]:
        names: list[str] = []
        node: _ScopeNode | None = self
        while node is not None:
            names.append(node.name)
            node = node.parent
        return names


_SCOPE: ContextVar[_ScopeNode | None] = ContextVar("_SCOPE", default=None)


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
    to `build` will produce the same value.

    Examples:
        ```python
        def build_str() -> str:
            return "foo"

        a = Assembler([Provide(build_str)])
        await a.build(str)
        ```
    """

    def __init__(self, providers: Iterable[Provide]) -> None:
        self._providers: dict[TypeId, Provide[Any]] = {}
        self._multiproviders: dict[TypeId, list[Provide[list[Any]]]] = defaultdict(list)
        self._modifiers: dict[TypeId, Modify[Any]] = {}
        self._assembled_outputs: dict[TypeId, Any] = {}
        self._modified_outputs: dict[TypeId, Any] = {}
        self._lock = asyncio.Lock()
        self._graph_cache: dict[TypeId, list[Provide]] = defaultdict(list)

        for provider in providers:
            type_id = provider.return_type_id
            if not provider.is_multiprovider:
                if type_id in self._providers:
                    raise RuntimeError(f"A Provider already exists for '{type_id}'")
                self._providers[type_id] = provider
            else:
                self._multiproviders[type_id].append(provider)

    @classmethod
    def from_mapped_providers(
        cls,
        providers: dict[TypeId, Provide[Any]],
        multiproviders: dict[TypeId, list[Provide[list[Any]]]],
        modifiers: dict[TypeId, Modify[Any]] | None = None,
    ) -> Self:
        """
        Create an Assembler from pre-mapped providers.

        This method is only exposed for performance reasons in the case that Providers
        have already been mapped, it is recommended to use the `__init__` method if this
        is not the case.

        Args:
            providers: a dictionary of Providers with the Provider's `return_type_id` as
              the key.
            multiproviders: a dictionary of list of Providers with the Provider's
              `return_type_id` as key. All Providers in the given list must be for the
              related `return_type_id`.
            modifiers: (optional) a dictionary of Modifiers with the Modifier's
              `modifies_type_id` as the key.

        Returns:
            An Assembler instance.
        """
        assembler = cls(tuple())  # noqa: C408
        assembler._providers = providers
        assembler._multiproviders = multiproviders
        assembler._modifiers = modifiers or {}
        return assembler

    @property
    def providers(self) -> Sequence[Provide[Any]]:
        multi_providers = [p for multi in self._multiproviders.values() for p in multi]
        return [*self._providers.values(), *multi_providers]

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

    async def build(self, type_: type[T]) -> T:
        """
        Build the type from Assembler's factories.

        If the type has been built previously the value will be cached and will return the
        same instance. If a modifier exists for the type, it will be applied after the
        provider is called.

        Args:
            type_: the type of the desired value to build.

        Raises:
            TypeNotProvidedError: When no provider is found for the given type.
            ProviderError: When a provider errors when trying to construct the type or
                any of its dependent types.

        Returns:
            The constructed value.
        """
        type_id = TypeId.from_type(type_)
        scope = _SCOPE.get()

        # Check modified cache (scope-local first, then global)
        if scope is not None:
            found, val = scope.find_modified(type_id)
            if found:
                return cast("T", val)
        if type_id in self._modified_outputs:
            return cast("T", self._modified_outputs[type_id])

        if type_id.multi:
            return await self._build_multi(type_id, scope)

        # --- single providers ---

        # Check scope node cache then global cache (skip when modifier exists —
        # we need to fall through to apply it)
        if type_id not in self._modifiers:
            if scope is not None:
                found, val = scope.find(type_id)
                if found:
                    return cast("T", val)
            if type_id in self._assembled_outputs:
                return cast("T", self._assembled_outputs[type_id])

        # Build if not yet cached. When a modifier exists we skip the early return above,
        # so we still need to guard against rebuilding a scoped type already in the node.
        already_in_scope = scope is not None and scope.find(type_id)[0]
        if not already_in_scope and type_id not in self._assembled_outputs:
            if type_id not in self._providers:
                raise TypeNotProvidedError(type_id)

            provider = self._providers[type_id]
            if provider.scope and (scope is None or not scope.has_scope(provider.scope)):
                raise NotInScopeError(
                    provider=provider,
                    scope_stack=scope.scope_names if scope else [],
                )

            assembled_dependency = await self.assemble(provider)
            try:
                value = await assembled_dependency()
            except Exception as err:
                raise ProviderError(
                    provider=provider,
                    error_type=type(err),
                    error_message=str(err),
                ) from err

            if provider.scope:
                assert scope is not None
                scope.cache[type_id] = value
            else:
                self._assembled_outputs[type_id] = value

        # Apply modifier if exists
        if type_id in self._modifiers:
            assembled = await self.assemble(self._modifiers[type_id])
            modified_value = await assembled()
            if scope is not None and self._is_scoped_type(type_id):
                scope.modified_cache[type_id] = modified_value
            else:
                self._modified_outputs[type_id] = modified_value
            return cast("T", modified_value)

        if scope is not None:
            found, val = scope.find(type_id)
            if found:
                return cast("T", val)
        return cast("T", self._assembled_outputs[type_id])

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

        If this replaces an existing provider, this will clear all previously assembled
        output. Note: multiproviders cannot be replaced, they are always appended.

        Args:
            provider: the Provide instance to add.

        Returns:
             None
        """
        type_id = provider.return_type_id
        if provider.is_multiprovider:
            self._multiproviders[type_id].append(provider)
        else:
            self._providers[type_id] = provider

        self._assembled_outputs.clear()
        self._modified_outputs.clear()
        self._graph_cache.clear()

    async def _build_multi(self, type_id: TypeId, scope: "_ScopeNode | None") -> Any:
        # Multiproviders are never scoped, so they always live in _assembled_outputs.

        # Cache hit (skip when modifier exists — need to fall through to apply it)
        if type_id not in self._modifiers and type_id in self._assembled_outputs:
            return self._assembled_outputs[type_id]

        if type_id not in self._assembled_outputs:
            providers = self._multiproviders.get(type_id)
            if not providers:
                raise TypeNotProvidedError(type_id)

            out: list[Any] = []
            for p in providers:
                assembled_dep = await self.assemble(p)
                try:
                    out.extend(await assembled_dep())
                except Exception as err:
                    raise ProviderError(
                        provider=p,
                        error_type=type(err),
                        error_message=str(err),
                    ) from err
            self._assembled_outputs[type_id] = out

        # Apply modifier if exists
        if type_id in self._modifiers:
            assembled = await self.assemble(self._modifiers[type_id])
            modified_value = await assembled()
            self._modified_outputs[type_id] = modified_value
            return modified_value

        return self._assembled_outputs[type_id]

    def _is_scoped_type(self, type_id: TypeId) -> bool:
        provider = self._providers.get(type_id)
        return provider is not None and provider.scope is not None

    def scope(self, scope: str) -> "_ScopeContextManager":
        return _ScopeContextManager(scope=scope, assembler=self)

    def _resolve_providers(self, type_id: TypeId, resolved: set[TypeId]) -> Iterable[Provide]:
        """
        Resolves the chain of providers required to satisfy the provider of a given type.
        Ordering of the return value is very important here!
        """
        if type_id in self._graph_cache:
            return self._graph_cache[type_id]

        if type_id.multi:
            root_providers = self._multiproviders.get(type_id)
        else:
            root_providers = [provider] if (provider := self._providers.get(type_id)) else None

        if not root_providers:
            if type_id.multi:
                LOG.warning(f"no provider for '{type_id}' defaulting to empty list")
                root_providers = [(Supply([], as_type=list[type_id.type]))]  # type: ignore[name-defined]
                # store default to prevent the warning appearing multiple times
                self._multiproviders[type_id] = root_providers
            else:
                raise TypeNotProvidedError(type_id)

        # providers that must be satisfied to satisfy the root level providers
        resolved_providers = [
            child_provider
            for root_provider in root_providers
            for root_provider_param in root_provider.parameter_type_ids
            for child_provider in self._resolve_providers(root_provider_param, resolved)
            if root_provider_param not in resolved
        ]

        resolved_providers.extend(root_providers)

        resolved.add(type_id)
        self._graph_cache[type_id] = resolved_providers

        return resolved_providers

    async def _satisfy(self, target: TypeId) -> None:
        scope = _SCOPE.get()
        for provider in self._resolve_providers(target, set()):
            type_id = provider.return_type_id
            if not provider.is_multiprovider:
                if scope is not None and scope.find(type_id)[0]:
                    continue
                if type_id in self._assembled_outputs:
                    continue

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
            elif provider.scope and scope is not None:
                scope.cache[type_id] = value
            else:
                self._assembled_outputs[type_id] = value

    async def _bind_arguments(self, signature: Signature) -> BoundArguments:
        args = []
        kwargs = {}
        scope = _SCOPE.get()
        for param_name, param in signature.parameters.items():
            if param_name == "self":
                args.append(object())
                continue
            param_key = TypeId.from_type(param.annotation)
            val = None
            found_in_scope = False
            if scope is not None:
                found_in_scope, val = scope.find(param_key)
            if not found_in_scope:
                if param_key not in self._assembled_outputs:
                    await self._satisfy(param_key)
                # After _satisfy, scoped types land in scope node
                if scope is not None:
                    found_in_scope, val = scope.find(param_key)
                if not found_in_scope:
                    val = self._assembled_outputs[param_key]
            if param.kind == param.POSITIONAL_ONLY:
                args.append(val)
            else:
                kwargs[param.name] = val

        return signature.bind(*args, **kwargs)


class _ScopeContextManager:
    def __init__(self, scope: str, assembler: Assembler) -> None:
        self._scope = scope
        self._assembler = assembler

    def __enter__(self) -> Assembler:
        _SCOPE.set(
            _ScopeNode(
                name=self._scope,
                cache={},
                modified_cache={},
                parent=_SCOPE.get(),
            )
        )
        return self._assembler

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        node = _SCOPE.get()
        if node is None or node.name != self._scope:
            actual = node.name if node else "<no scope>"
            raise RuntimeError(
                f"Exited scope '{actual}' is not the expected scope '{self._scope}'"
            )
        _SCOPE.set(node.parent)
