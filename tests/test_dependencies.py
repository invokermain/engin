from typing import Annotated
from unittest.mock import Mock

import pytest

from engin import Provide
from engin._dependency import Entrypoint, Supply
from tests.deps import make_aliased_int, make_int


def test_provide_discriminates_singular():
    def i_provide() -> int:
        return 3

    provider = Provide(i_provide)
    assert not provider.is_multiprovider
    assert provider.return_type_id.type is int
    assert not provider.return_type_id.multi


def test_provide_discriminates_multi():
    def i_provide_multi() -> list[int]:
        return [3]

    provider = Provide(i_provide_multi)
    assert provider.is_multiprovider
    assert provider.return_type_id.type is int
    assert provider.return_type_id.multi


def test_supply_singular():
    class Foo: ...

    supply = Supply(Foo())
    assert not supply.is_multiprovider
    assert supply.return_type_id.type is Foo
    assert not supply.return_type_id.multi


def test_supply_multi():
    class Foo: ...

    supply = Supply([Foo()])
    assert supply.return_type_id.type is Foo
    assert supply.return_type_id.multi
    assert supply.is_multiprovider


def test_provide_with_alias():
    provider = Provide(make_aliased_int)

    assert provider.return_type_id.type


def test_provide_with_annotation():
    def make_str_1() -> Annotated[str, "1"]:
        return "bar"

    provider = Provide(make_str_1)

    assert provider.return_type_id.type
    assert str(provider.return_type_id) == "Annotated[str, 1]"


def test_dependency_sources():
    provide = Provide(make_int)
    assert provide.source_module == "tests.test_dependencies"
    assert provide.source_package == "tests"

    supply = Supply(3)
    assert supply.source_module == "tests.test_dependencies"
    assert supply.source_package == "tests"

    invoke = Provide(make_int)
    assert invoke.source_module == "tests.test_dependencies"
    assert invoke.source_package == "tests"

    entrypoint = Entrypoint(3)
    assert entrypoint.source_module == "tests.test_dependencies"
    assert entrypoint.source_package == "tests"


def test_provider_cannot_depend_on_self():
    def invalid_provider_1(a: int) -> int:
        return 1

    def invalid_provider_2(a: list[int]) -> list[int]:
        return [1]

    with pytest.raises(ValueError, match="return type"):
        Provide(invalid_provider_1)

    with pytest.raises(ValueError, match="return type"):
        Provide(invalid_provider_2)


def test_provides_implicit_overrides():
    provide_a = Provide(make_int)
    provide_b = Provide(make_int)

    engin = Mock()
    engin._providers = {}

    provide_a.apply(engin)

    with pytest.raises(RuntimeError, match="implicit"):
        provide_b.apply(engin)


def test_provides_explicit_overrides_allowed():
    provide_a = Provide(make_int)
    provide_b = Provide(make_int, override=True)

    engin = Mock()
    engin._providers = {}

    provide_a.apply(engin)
    provide_b.apply(engin)


def test_provides_implicit_overrides_allowed_when_3rd_party():
    provide_a = Provide(make_int)
    provide_b = Provide(make_int)

    provide_a._source_package = "foo"

    engin = Mock()
    engin._providers = {}

    provide_a.apply(engin)
    provide_b.apply(engin)
