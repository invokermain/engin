from typing import Annotated
from unittest.mock import Mock

import pytest

from engin import Decorate, Entrypoint, Invoke, Provide, Supply
from tests.deps import int_provider, make_aliased_int, make_int


def test_provide_discriminates_singular():
    provider = int_provider()
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


def test_provide_with_non_callable_type_shows_helpful_error():
    with pytest.raises(ValueError, match="Supply"):
        Provide([3])


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

    invoke = Invoke(make_int)
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


def test_provider_with_invalid_list_type():
    def invalid(a: int) -> list:
        return []

    with pytest.raises(ValueError, match=r"list\[X\]"):
        Provide(invalid)


def test_provides_implicit_overrides_providers():
    provide_a = int_provider()
    provide_b = int_provider()

    engin = Mock()
    engin._providers = {}

    provide_a.apply(engin)

    with pytest.raises(RuntimeError, match="implicit"):
        provide_b.apply(engin)


def test_provides_implicit_overrides_supply():
    provide_a = Supply(3)
    provide_b = Supply(4)

    engin = Mock()
    engin._providers = {}

    provide_a.apply(engin)

    with pytest.raises(RuntimeError, match="implicit"):
        provide_b.apply(engin)


def test_provides_explicit_overrides_allowed():
    provide_a = int_provider()
    provide_b = int_provider(override=True)

    engin = Mock()
    engin._providers = {}

    provide_a.apply(engin)
    provide_b.apply(engin)


def test_provides_implicit_overrides_allowed_when_3rd_party():
    provide_a = int_provider()
    provide_b = int_provider()

    provide_a._source_package = "foo"

    engin = Mock()
    engin._providers = {}

    provide_a.apply(engin)
    provide_b.apply(engin)


def test_provide_as_type():
    provide = int_provider(as_type=float)
    assert provide.return_type is float
    assert provide.signature.return_annotation is float


def test_supply_as_type():
    supply = Supply(3, as_type=float)
    assert supply.return_type is float
    assert supply.signature.return_annotation is float


def test_decorate_validates_input_output_type_match():
    def invalid_decorator(value: int) -> str:
        return str(value)

    with pytest.raises(ValueError, match="must match"):
        Decorate(invalid_decorator)


def test_decorate_requires_return_type():
    def no_return_type(value: int):
        return value

    with pytest.raises(RuntimeError, match="return type hint"):
        Decorate(no_return_type)


def test_decorate_requires_at_least_one_parameter():
    def no_params() -> int:
        return 1

    with pytest.raises(ValueError, match="at least one parameter"):
        Decorate(no_params)


def test_decorate_with_non_callable_type_raises():
    with pytest.raises(ValueError, match="not callable"):
        Decorate([3])


def test_decorate_str_format():
    def add_prefix(value: str) -> str:
        return f"prefix_{value}"

    decorator = Decorate(add_prefix)
    assert "add_prefix" in str(decorator)
    assert "str" in str(decorator)


def test_decorate_decorates_type_id():
    def add_prefix(value: str) -> str:
        return f"prefix_{value}"

    decorator = Decorate(add_prefix)
    assert decorator.decorates_type_id.type is str
    assert not decorator.decorates_type_id.multi


def test_decorate_apply_adds_to_engin():
    def add_prefix(value: str) -> str:
        return f"prefix_{value}"

    decorator = Decorate(add_prefix)

    engin = Mock()
    engin._decorators = {}

    decorator.apply(engin)

    assert decorator.decorates_type_id in engin._decorators
    assert engin._decorators[decorator.decorates_type_id] is decorator


def test_decorate_override_conflict():
    def add_prefix_a(value: str) -> str:
        return f"a_{value}"

    def add_prefix_b(value: str) -> str:
        return f"b_{value}"

    decorator_a = Decorate(add_prefix_a)
    decorator_b = Decorate(add_prefix_b)

    engin = Mock()
    engin._decorators = {}

    decorator_a.apply(engin)

    with pytest.raises(RuntimeError, match="conflicts"):
        decorator_b.apply(engin)


def test_decorate_explicit_override_allowed():
    def add_prefix_a(value: str) -> str:
        return f"a_{value}"

    def add_prefix_b(value: str) -> str:
        return f"b_{value}"

    decorator_a = Decorate(add_prefix_a)
    decorator_b = Decorate(add_prefix_b, override=True)

    engin = Mock()
    engin._decorators = {}

    decorator_a.apply(engin)
    decorator_b.apply(engin)

    assert engin._decorators[decorator_a.decorates_type_id] is decorator_b
