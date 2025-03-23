from collections.abc import Callable
from typing import Annotated, TypeAlias

from engin._type_utils import TypeId


def test_type_id_of_int():
    type_id = TypeId.from_type(int)
    assert type_id == TypeId(type=int, multi=False)
    assert str(type_id) == "int"


def test_type_id_of_list_of_int():
    type_id = TypeId.from_type(list[int])
    assert type_id == TypeId(type=int, multi=True)
    assert str(type_id) == "int[]"


def test_type_id_of_alias():
    MyAlias: TypeAlias = int

    assert (
        TypeId.from_type(MyAlias)
        == TypeId(type=MyAlias, multi=False)
        == TypeId(type=int, multi=False)
    )


def test_type_id_of_type_of_class():
    class Foo: ...

    type_id = TypeId.from_type(type[Foo])
    assert type_id == TypeId(type=type[Foo], multi=False)
    assert str(type_id) == "type[Foo]"


def test_type_id_of_callable():
    func = Callable[[int], str]
    type_id = TypeId.from_type(func)
    assert type_id == TypeId(type=Callable[[int], str], multi=False)
    assert str(type_id) == "Callable[[int], str]"


def test_type_id_of_multi_callable():
    many_func = list[Callable[[int], str]]
    type_id = TypeId.from_type(many_func)
    assert type_id == TypeId(type=Callable[[int], str], multi=True)
    assert str(type_id) == "Callable[[int], str][]"


def test_type_id_of_annotation():
    annotated = Annotated[int, "Activity"]
    type_id = TypeId.from_type(annotated)
    assert type_id == TypeId(type=Annotated[int, "Activity"], multi=False)
    assert str(type_id) == "Annotated[int, Activity]"


def test_type_id_of_complex_annotation():
    annotated = Annotated[Callable[[int], str], "Activity"]
    type_id = TypeId.from_type(annotated)
    assert type_id == TypeId(type=Annotated[Callable[[int], str], "Activity"], multi=False)
    assert str(type_id) == "Annotated[Callable[[int], str], Activity]"


def test_type_id_of_union():
    union = int | str
    type_id = TypeId.from_type(union)
    assert type_id == TypeId(type=int | str, multi=False)
    assert str(type_id) == "Union[int, str]"
