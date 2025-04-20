from collections.abc import Iterable
from dataclasses import dataclass

from engin import Provide
from engin._dependency import Dependency
from engin._type_utils import TypeId


@dataclass(slots=True, frozen=True, kw_only=True)
class Node:
    """
    A Node in the Dependency Graph.
    """

    node: Dependency
    parent: Dependency | None

    def __repr__(self) -> str:
        return f"Node(node={self.node!s},parent={self.parent!s})"


class DependencyGrapher:
    def __init__(self, providers: dict[TypeId, Provide | list[Provide]]) -> None:
        self._providers: dict[TypeId, Provide | list[Provide]] = providers

    def resolve(self, roots: Iterable[Dependency]) -> list[Node]:
        return self._resolve_recursive(roots, seen=set())

    def _resolve_recursive(
        self, roots: Iterable[Dependency], *, seen: set[TypeId]
    ) -> list[Node]:
        nodes: list[Node] = []
        for root in roots:
            for parameter in root.parameter_type_ids:
                provider = self._providers[parameter]

                # multiprovider
                if isinstance(provider, list):
                    nodes.extend(Node(node=p, parent=root) for p in provider)
                    if parameter not in seen:
                        nodes.extend(self._resolve_recursive(provider, seen=seen))
                # single provider
                else:
                    nodes.append(Node(node=provider, parent=root))
                    if parameter not in seen:
                        nodes.extend(self._resolve_recursive([provider], seen=seen))

                seen.add(parameter)

        return nodes
