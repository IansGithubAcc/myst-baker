import base64
import json

from pymd.transform import transform_document


def _decode_iframe_html(iframe_node):
    assert iframe_node["type"] == "iframe"
    prefix = "data:text/html;base64,"
    assert iframe_node["src"].startswith(prefix)
    encoded = iframe_node["src"][len(prefix) :]
    return base64.b64decode(encoded).decode("utf-8")


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
    assert children_types == ["pymd-input-slider", "pymd-calc-python", "iframe"]

    iframe_node = result["children"][2]
    html = _decode_iframe_html(iframe_node)
    assert "pymdInitPlot(" in html
    assert '"0": 0' in html
    assert '"1": 2' in html
    assert '"2": 4' in html


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


def test_transform_document_orders_input_specs_by_function_parameter_order():
    # The function declares parameters in the order (a, b), but the
    # input-slider blocks appear in the AST in the opposite order (b, then
    # a). input_specs must follow the function's declared parameter order
    # (matching precompute.matched_inputs / compute_grid's key order), not
    # the document order the slider blocks appear in -- otherwise the
    # client's lookup key built from input_specs won't match the
    # precomputed grid's keys.
    input_node_b = {
        "type": "pymd-input-slider",
        "arg": "b",
        "options": {"value": 1, "min": 0, "max": 1, "step": 1},
        "body": "",
    }
    input_node_a = {
        "type": "pymd-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 1, "step": 1},
        "body": "",
    }
    calc_node = {
        "type": "pymd-calc-python",
        "arg": None,
        "options": {},
        "body": "def f(a, b):\n    return a + b\n",
    }
    plot_node = {
        "type": "pymd-plot",
        "arg": "scatter",
        "options": {"data": "f"},
        "body": "",
    }

    ast = {
        "type": "root",
        "children": [input_node_b, input_node_a, calc_node, plot_node],
    }

    result = transform_document(ast)

    html = _decode_iframe_html(result["children"][-1])

    # runtime.js (embedded above) *defines* pymdInitPlot, so find the last
    # occurrence -- the actual invocation with the real arguments.
    call_index = html.rindex("pymdInitPlot(")
    array_start = html.index("[", call_index)
    input_specs, _ = json.JSONDecoder().raw_decode(html, array_start)

    assert [spec["name"] for spec in input_specs] == ["a", "b"]
