from pymd.directives import build_placeholder_node


def test_build_placeholder_node_input_slider():
    node = build_placeholder_node(
        "input-slider", arg="a", options={"value": 5, "min": 0, "max": 10, "step": 1}, body=""
    )
    assert node == {
        "type": "pymd-input-slider",
        "arg": "a",
        "options": {"value": 5, "min": 0, "max": 10, "step": 1},
        "body": "",
    }


def test_build_placeholder_node_calc_python():
    source = "def f(a):\n    return a\n"
    node = build_placeholder_node("calc-python", arg=None, options={}, body=source)
    assert node == {
        "type": "pymd-calc-python",
        "arg": None,
        "options": {},
        "body": source,
    }


def test_build_placeholder_node_plot():
    node = build_placeholder_node(
        "plot", arg="scatter", options={"data": "get_plot_data", "mode": "lines"}, body=""
    )
    assert node == {
        "type": "pymd-plot",
        "arg": "scatter",
        "options": {"data": "get_plot_data", "mode": "lines"},
        "body": "",
    }


def test_build_placeholder_node_rejects_unknown_directive():
    import pytest

    with pytest.raises(ValueError, match="unknown-thing"):
        build_placeholder_node("unknown-thing", arg=None, options={}, body="")
