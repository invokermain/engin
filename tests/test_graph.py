from datetime import UTC, datetime

from engin import Provide, Supply
from engin._graph import DependencyGrapher


def test_dependency_grapher():
    def provide_int() -> int:
        return 3

    def provide_str(num: int) -> str:
        return f"num: {num}"

    def provide_many_str(some: str, dt: datetime) -> list[str]:
        return [some, dt.isoformat()]

    int_provider = Provide(provide_int)
    str_provider = Provide(provide_str)
    many_str_provider = Provide(provide_many_str)
    dt_supplier = Supply(datetime.now(UTC))

    grapher = DependencyGrapher(
        {
            int_provider.return_type_id: int_provider,
            str_provider.return_type_id: str_provider,
            many_str_provider.return_type_id: many_str_provider,
            dt_supplier.return_type_id: dt_supplier,
        }
    )

    nodes = grapher.resolve([many_str_provider])

    assert len(nodes) == 3
