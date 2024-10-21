from engin._type_utils import TypeId, type_id_of


def test_type_id_of_int():
    assert type_id_of(int) == TypeId(type=int, multi=False)


def test_type_id_of_list_of_int():
    assert type_id_of(list[int]) == TypeId(type=int, multi=True)
