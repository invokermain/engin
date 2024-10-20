from engin import Provide
from engin._dependency import Supply


def test_provide_discriminates_singluar():
    def i_provide() -> int:
        return 3

    provider = Provide(i_provide)
    assert not provider.is_multiprovider
    assert provider.return_type_id == "builtins.int"


def test_provide_discriminates_multir():
    def i_provide_multi() -> list[int]:
        return [3]

    provider = Provide(i_provide_multi)
    assert provider.is_multiprovider
    assert provider.return_type_id == "builtins.int[]"


def test_supply_singular():
    class Foo: ...

    supply = Supply(Foo())
    assert supply.return_type_id == "tests.test_dependencies.Foo"


def test_supply_multi():
    class Foo: ...

    supply = Supply([Foo()])
    assert supply.return_type_id == "tests.test_dependencies.Foo[]"
    assert supply.is_multiprovider
