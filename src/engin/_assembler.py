import asyncio
import logging
from collections import defaultdict
from collections.abc import Iterable, Sequence
from contextvars import ContextVar
from dataclasses import dataclass, field
from inspect import BoundArguments, Signature
from types import TracebackType
from typing import Any, Generic, TypeVar, cast

from typing_extensions import Self

from engin._dependency import Dependency, Modify, Provide, Supply
from engin._type_utils import TypeId
from engin.exceptions import NotInScopeError, ProviderError, TypeNotProvidedError

LOG = logging.getLogger("engin")

T = TypeVar("T")


@dataclass(slots=True, kw_only=True, frozen=True)
class _ScopeNode:
    """
    A node in a linked list of scopes.

    Each Assembler has a root node whose cache holds globally-scoped values.
    Entering a named scope pushes a new child node; exiting pops it. Lookups
    walk the chain from the current node up to the root, so child scopes
    inherit values cached in parent scopes.
    """

    name: str
    cache: dict[TypeId, Any] = field(default_factory=dict)
    modified_cache: dict[TypeId, Any] = field(default_factory=dict)
    parent: "_ScopeNode | None" = None

    def find(self, type_id: TypeId) -> tuple[bool, Any]:
        """
        Search for a cached value by walking up the scope chain.

        Args:
            type_id: the type to look up.

        Returns:
            A (found, value) tuple.
        """
        node: _ScopeNode | None = self
        while node is not None:
            if type_id in node.cache:
                return True, node.cache[type_id]
            node = node.parent
        return False, None

    def find_modified(self, type_id: TypeId) -> tuple[bool, Any]:
        """
        Search for a modified cached value by walking up the scope chain.

        Args:
            type_id: the type to look up.

        Returns:
            A (found, value) tuple.
        """
        node: _ScopeNode | None = self
        while node is not None:
            if type_id in node.modified_cache:
                return True, node.modified_cache[type_id]
            node = node.parent
        return False, None

    def has_scope(self, name: str) -> bool:
        """
        Check whether a named scope exists in the chain.

        Args:
            name: the scope name to search for.

        Returns:
            True if the scope is present in the chain, else False.
        """
        node: _ScopeNode | None = self
        while node is not None:
            if node.name == name:
                return True
            node = node.parent
        return False

    @property
    def scope_names(self) -> list[str]:
        """
        Return the names of all scopes in the chain, from innermost to root.
        """
        names: list[str] = []
        node: _ScopeNode | None = self
        while node is not None:
            names.append(node.name)
            node = node.parent
        return names


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
        self._lock = asyncio.Lock()
        self._graph_cache: dict[TypeId, list[Provide]] = defaultdict(list)
        self._root_node = _ScopeNode(name="__root__")
        self._scope_var: ContextVar[_ScopeNode] = ContextVar("_scope", default=self._root_node)

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
        scope = self._scope_var.get()

        # Check modified cache (walks scope chain up to root)
        found, val = scope.find_modified(type_id)
        if found:
            return cast("T", val)

        if type_id.multi:
            # Multiproviders are never scoped, so they always live in the root cache.

            # Cache hit (skip when modifier exists — need to fall through to apply it)
            if type_id not in self._modifiers:
                found, val = scope.find(type_id)
                if found:
                    return cast("T", val)

            if type_id not in self._root_node.cache:
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
                self._root_node.cache[type_id] = out

            # Apply modifier if exists
            if type_id in self._modifiers:
                assembled = await self.assemble(self._modifiers[type_id])
                modified_value = await assembled()
                self._root_node.modified_cache[type_id] = modified_value
                return cast("T", modified_value)

            return cast("T", self._root_node.cache[type_id])

        # --- single providers ---

        # Check scope chain cache (skip when modifier exists — we need to fall through
        # to apply it)
        if type_id not in self._modifiers:
            found, val = scope.find(type_id)
            if found:
                return cast("T", val)

        # Build if not yet cached. When a modifier exists we skip the early return above,
        # so we still need to guard against rebuilding a scoped type already in the chain.
        if not scope.find(type_id)[0]:
            if type_id not in self._providers:
                raise TypeNotProvidedError(type_id)

            provider = self._providers[type_id]
            if provider.scope and not scope.has_scope(provider.scope):
                raise NotInScopeError(
                    provider=provider,
                    scope_stack=scope.scope_names,
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
                scope.cache[type_id] = value
            else:
                self._root_node.cache[type_id] = value

        # Apply modifier if exists
        if type_id in self._modifiers:
            assembled = await self.assemble(self._modifiers[type_id])
            modified_value = await assembled()
            if self._is_scoped_type(type_id):
                scope.modified_cache[type_id] = modified_value
            else:
                self._root_node.modified_cache[type_id] = modified_value
            return cast("T", modified_value)

        found, val = scope.find(type_id)
        if found:
            return cast("T", val)
        raise TypeNotProvidedError(type_id)

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

        self._root_node.cache.clear()
        self._root_node.modified_cache.clear()
        self._graph_cache.clear()

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
        scope = self._scope_var.get()
        for provider in self._resolve_providers(target, set()):
            type_id = provider.return_type_id
            if not provider.is_multiprovider and scope.find(type_id)[0]:
                continue

            bound_args = await self._bind_arguments(provider.signature)
            try:
                value = await provider(*bound_args.args, **bound_args.kwargs)
            except Exception as err:
                raise ProviderError(
                    provider=provider, error_type=type(err), error_message=str(err)
                ) from err

            if provider.is_multiprovider:
                if type_id in self._root_node.cache:
                    self._root_node.cache[type_id].extend(value)
                else:
                    self._root_node.cache[type_id] = value
            elif provider.scope:
                scope.cache[type_id] = value
            else:
                self._root_node.cache[type_id] = value

    async def _bind_arguments(self, signature: Signature) -> BoundArguments:
        args = []
        kwargs = {}
        scope = self._scope_var.get()
        for param_name, param in signature.parameters.items():
            if param_name == "self":
                args.append(object())
                continue
            param_key = TypeId.from_type(param.annotation)
            found, val = scope.find(param_key)
            if not found:
                await self._satisfy(param_key)
                found, val = scope.find(param_key)
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
        scope_var = self._assembler._scope_var
        scope_var.set(_ScopeNode(name=self._scope, parent=scope_var.get()))
        return self._assembler

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
        /,
    ) -> None:
        scope_var = self._assembler._scope_var
        node = scope_var.get()
        if node.name != self._scope:
            raise RuntimeError(
                f"Exited scope '{node.name}' is not the expected scope '{self._scope}'"
            )
        if node.parent is None:
            raise RuntimeError("cannot exit the root scope")
        scope_var.set(node.parent)
