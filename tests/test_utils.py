from engin._utils import type_id_of


def test_type_id_of_int():
    assert type_id_of(int) == "builtins.int"


def test_type_id_of_list_of_int():
    assert type_id_of(list[int]) == "builtins.int[]"
