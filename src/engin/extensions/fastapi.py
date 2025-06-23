import inspect
import typing
from collections.abc import Iterable
from inspect import Parameter
from typing import ClassVar, TypeVar

from fastapi.routing import APIRoute

from engin import Assembler, Engin, Entrypoint, Invoke, Option
from engin._dependency import Dependency, Supply, _noop
from engin._graph import DependencyGrapher, Node
from engin._type_utils import TypeId
from engin.extensions.asgi import ASGIEngin

try:
    from fastapi import APIRouter, FastAPI
    from fastapi.params import Depends
    from starlette.requests import HTTPConnection
except ImportError as err:
    raise ImportError(
        "fastapi package must be installed to use the fastapi extension"
    ) from err

__all__ = ["APIRouteDependency", "FastAPIEngin", "Inject"]


def _attach_assembler(app: FastAPI, assembler: Assembler) -> None:
    """
    An invocation that attaches the Engin's Assembler to the FastAPI application, enabling
    the Inject marker.
    """
    app.state.assembler = assembler


class FastAPIEngin(ASGIEngin):
    _LIB_OPTIONS: ClassVar[list[Option]] = [
        *ASGIEngin._LIB_OPTIONS,
        Invoke(_attach_assembler),
    ]
    _asgi_type = FastAPI

    def graph(self) -> list[Node]:
        grapher = _FastAPIDependencyGrapher({**self._providers, **self._multiproviders})
        return grapher.resolve(
            [
                Entrypoint(self._asgi_type),
                *[i for i in self._invocations if i.func_name != "_attach_assembler"],
            ]
        )


T = TypeVar("T")


def Inject(interface: type[T]) -> Depends:
    async def inner(conn: HTTPConnection) -> T:
        try:
            assembler: Assembler = conn.app.state.assembler
        except AttributeError:
            raise RuntimeError("Assembler is not attached to Application state") from None
        return await assembler.build(interface)

    dep = Depends(inner)
    dep.__engin__ = True  # type: ignore[attr-defined]
    return dep


class _FastAPIDependencyGrapher(DependencyGrapher):
    """
    This exists in order to bridge the gap between
    """

    def _resolve_recursive(
        self, roots: Iterable[Dependency], *, seen: set[TypeId]
    ) -> list[Node]:
        nodes: list[Node] = []
        for root in roots:
            for parameter in root.parameter_type_ids:
                provider = self._providers[parameter]

                # multiprovider
                if isinstance(provider, list):
                    for p in provider:
                        nodes.append(Node(node=p, parent=root))

                        if isinstance(p, Supply):
                            route_dependencies = _extract_routes_from_supply(p)
                            nodes.extend(
                                Node(node=route_dependency, parent=p)
                                for route_dependency in route_dependencies
                            )
                            nodes.extend(
                                self._resolve_recursive(route_dependencies, seen=seen)
                            )

                        if parameter not in seen:
                            nodes.extend(self._resolve_recursive(provider, seen=seen))
                # single provider
                else:
                    nodes.append(Node(node=provider, parent=root))
                    # not sure why anyone would ever supply a single APIRouter in an
                    # application, but just in case
                    if isinstance(provider, Supply):
                        route_dependencies = _extract_routes_from_supply(provider)
                        nodes.extend(
                            Node(node=route_dependency, parent=provider)
                            for route_dependency in route_dependencies
                        )
                        nodes.extend(self._resolve_recursive(route_dependencies, seen=seen))
                    if parameter not in seen:
                        nodes.extend(self._resolve_recursive([provider], seen=seen))

                seen.add(parameter)

        return nodes


def _extract_routes_from_supply(supply: Supply) -> list[Dependency]:
    if supply.is_multiprovider:
        inner = supply._value[0]
        if isinstance(inner, APIRouter):
            return [
                APIRouteDependency(supply, route)
                for route in inner.routes
                if isinstance(route, APIRoute)
            ]
    return []


class APIRouteDependency(Dependency):
    """
    This is a pseudo-dependency that is only used when calling FastAPIEngin.graph() in
    order to provide richer metadata to the Node.

    This class should never be constructed in application code.
    """

    def __init__(
        self,
        wraps: Dependency,
        route: APIRoute,
    ) -> None:
        """
        Warning: this should never be constructed in application code.
        """
        super().__init__(_noop)
        self._block_name = wraps.block_name
        self._wrapped = wraps
        self._route = route
        self._signature = inspect.signature(route.endpoint)

    @property
    def source_module(self) -> str:
        return self._wrapped.source_module

    @property
    def source_package(self) -> str:
        return self._wrapped.source_package

    @property
    def route(self) -> APIRoute:
        return self._route

    @property
    def parameter_type_ids(self) -> list[TypeId]:
        parameters = list(self._signature.parameters.values())
        if not parameters:
            return []
        if parameters[0].name == "self":
            parameters.pop(0)
        return [
            TypeId.from_type(typing.get_args(param.annotation)[0])
            for param in parameters
            if self._is_injected_param(param)
        ]

    @staticmethod
    def _is_injected_param(param: Parameter) -> bool:
        if typing.get_origin(param.annotation) != typing.Annotated:
            return False
        args = typing.get_args(param.annotation)
        if len(args) != 2:
            return False
        return isinstance(args[1], Depends) and hasattr(args[1], "__engin__")

    @property
    def name(self) -> str:
        methods = ",".join(self._route.methods)
        return f"{methods} {self._route.path}"

    def apply(self, engin: Engin) -> None:
        raise NotImplementedError("APIRouteDependency is not a real dependency")
