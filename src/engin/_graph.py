from collections.abc import Iterable
from typing import TypedDict

from engin._dependency import Dependency, Provide
from engin._type_utils import TypeId


class Node(TypedDict):
    node: Dependency
    parent: Dependency | None


class DependencyGrapher:
    def __init__(self, providers: dict[TypeId, Provide | list[Provide]]) -> None:
        self._providers: dict[TypeId, Provide | list[Provide]] = providers

    def resolve(self, roots: Iterable[Dependency]) -> list[Node]:
        seen: set[TypeId] = set()
        nodes: list[Node] = []

        for root in roots:
            for parameter in root.parameter_types:
                if parameter in seen:
                    continue

                seen.add(parameter)
                provider = self._providers[parameter]

                # multiprovider
                if isinstance(provider, list):
                    for p in provider:
                        nodes.append({"node": p, "parent": root})
                        nodes.extend(self.resolve([p]))
                # single provider
                else:
                    nodes.append({"node": provider, "parent": root})
                    nodes.extend(self.resolve([provider]))

        return nodes
