from adventureworks_agent.json_shape import shape


def test_drops_null_values():
    assert shape({"a": 1, "b": None}) == {"a": 1}


def test_drops_false_booleans():
    assert shape({"a": True, "b": False}) == {"a": True}


def test_rounds_doubles_to_2dp():
    assert shape({"cost": 3.14159}) == {"cost": 3.14}


def test_strips_brackets_from_keys():
    assert shape({"warnings[]": [1, 2]}) == {"warnings": [1, 2]}


def test_recurses_into_nested_structures():
    obj = {"rows": [{"a": None, "b": 1.005}, {"a": False, "c": 2}]}
    assert shape(obj) == {"rows": [{"b": 1.0}, {"c": 2}]}


def test_leaves_non_dict_scalars_untouched():
    assert shape("hello") == "hello"
    assert shape(5) == 5
