from pymd.transform import transform_document


def _page_ast(input_node, calc_node, plot_node):
    return {
        "type": "root",
        "children": [input_node, calc_node, plot_node],
    }


def test_transform_document_replaces_plot_node_with_html():
    input_node = {
        "type": "pymd-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 2, "step": 1},
        "body": "",
    }
    calc_node = {
        "type": "pymd-calc-python",
        "arg": None,
        "options": {},
        "body": "def get_plot_data(a):\n    return a * 2\n",
    }
    plot_node = {
        "type": "pymd-plot",
        "arg": "scatter",
        "options": {"data": "get_plot_data"},
        "body": "",
    }

    result = transform_document(_page_ast(input_node, calc_node, plot_node))

    children_types = [child["type"] for child in result["children"]]
    assert children_types == ["pymd-input-slider", "pymd-calc-python", "html"]

    html_node = result["children"][2]
    assert '"0": 0' in html_node["value"]
    assert '"1": 2' in html_node["value"]
    assert '"2": 4' in html_node["value"]


def test_transform_document_raises_when_plot_references_unknown_function():
    input_node = {
        "type": "pymd-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 1, "step": 1},
        "body": "",
    }
    calc_node = {
        "type": "pymd-calc-python",
        "arg": None,
        "options": {},
        "body": "def get_plot_data(a):\n    return a\n",
    }
    plot_node = {
        "type": "pymd-plot",
        "arg": "scatter",
        "options": {"data": "does_not_exist"},
        "body": "",
    }

    import pytest

    with pytest.raises(NameError, match="does_not_exist"):
        transform_document(_page_ast(input_node, calc_node, plot_node))
