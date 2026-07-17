from myst_baker.directives import build_placeholder_node


def test_build_placeholder_node_input_slider():
    node = build_placeholder_node(
        "input-slider", arg="a", options={"value": 5, "min": 0, "max": 10, "step": 1}, body=""
    )
    assert node == {
        "type": "myst-baker-input-slider",
        "arg": "a",
        "options": {"value": 5, "min": 0, "max": 10, "step": 1},
        "body": "",
    }


def test_build_placeholder_node_rejects_calc_python_as_directive():
    import pytest

    with pytest.raises(ValueError, match="calc-python"):
        build_placeholder_node("calc-python", arg=None, options={}, body="")


def test_build_placeholder_node_plot():
    node = build_placeholder_node(
        "plot", arg="scatter", options={"data": "get_plot_data", "mode": "lines"}, body=""
    )
    assert node == {
        "type": "myst-baker-plot",
        "arg": "scatter",
        "options": {"data": "get_plot_data", "mode": "lines"},
        "body": "",
    }


def test_build_placeholder_node_input_checkbox():
    node = build_placeholder_node(
        "input-checkbox", arg="enabled", options={"value": True}, body=""
    )
    assert node == {
        "type": "myst-baker-input-checkbox",
        "arg": "enabled",
        "options": {"value": True},
        "body": "",
    }


def test_build_placeholder_node_input_dropdown():
    node = build_placeholder_node(
        "input-dropdown",
        arg="color",
        options={"value": "green"},
        body="red\ngreen\nblue",
    )
    assert node == {
        "type": "myst-baker-input-dropdown",
        "arg": "color",
        "options": {"value": "green"},
        "body": "red\ngreen\nblue",
    }


def test_build_placeholder_node_rejects_unknown_directive():
    import pytest

    with pytest.raises(ValueError, match="unknown-thing"):
        build_placeholder_node("unknown-thing", arg=None, options={}, body="")
