import base64
import json

import pytest

from myst_baker.transform import transform_document


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


def _calc_node(source):
    return {"type": "code", "lang": "python{calc}", "value": source}


def test_transform_document_replaces_plot_node_with_html():
    input_node = {
        "type": "myst-baker-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 2, "step": 1},
        "body": "",
    }
    calc_node = _calc_node("def get_plot_data(a):\n    return a, a * 2\n")
    plot_node = {
        "type": "myst-baker-plot",
        "arg": "scatter",
        "options": {"data": "get_plot_data"},
        "body": "",
    }

    result = transform_document(_page_ast(input_node, calc_node, plot_node))

    children_types = [child["type"] for child in result["children"]]
    assert children_types == ["myst-baker-input-slider", "code", "iframe"]

    iframe_node = result["children"][2]
    html = _decode_iframe_html(iframe_node)
    assert "mystBakerInitPlot(" in html
    assert '"0": {"x": 0, "y": 0}' in html
    assert '"1": {"x": 1, "y": 2}' in html
    assert '"2": {"x": 2, "y": 4}' in html


def test_transform_document_raises_when_plot_references_unknown_function():
    input_node = {
        "type": "myst-baker-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 1, "step": 1},
        "body": "",
    }
    calc_node = _calc_node("def get_plot_data(a):\n    return a\n")
    plot_node = {
        "type": "myst-baker-plot",
        "arg": "scatter",
        "options": {"data": "does_not_exist"},
        "body": "",
    }

    with pytest.raises(NameError, match="does_not_exist"):
        transform_document(_page_ast(input_node, calc_node, plot_node))


def test_transform_document_finds_plot_node_wrapped_in_block_node():
    # Regression test for a real end-to-end build bug: mystmd does not put
    # top-level page content directly under the document root's `children`.
    # Instead it wraps it in an intermediate `{"type": "block", "children":
    # [...]}` node (verified against a real `myst build --debug`), so the
    # actual shape is root -> block -> [myst-baker-* nodes], not root ->
    # [myst-baker-* nodes] directly as every other test in this file constructs it. A
    # scanner that only looks at `ast["children"]` (or otherwise fails to
    # recurse into nested `children`) finds nothing here and silently leaves
    # the myst-baker-plot node untransformed -- exactly the bug fixed in
    # transform.py's `_iter_nodes`/`_replace_plots`. This test must fail if
    # that recursion is ever reverted to shallow/immediate-children scanning.
    input_node = {
        "type": "myst-baker-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 2, "step": 1},
        "body": "",
    }
    calc_node = _calc_node("def get_plot_data(a):\n    return a, a * 2\n")
    plot_node = {
        "type": "myst-baker-plot",
        "arg": "scatter",
        "options": {"data": "get_plot_data"},
        "body": "",
    }

    block_node = {
        "type": "block",
        "children": [input_node, calc_node, plot_node],
    }
    ast = {
        "type": "root",
        "children": [block_node],
    }

    result = transform_document(ast)

    # The plot node nested inside the "block" wrapper must have been found
    # and replaced with an iframe node, in place.
    assert result["children"][0]["type"] == "block"
    inner_children_types = [child["type"] for child in result["children"][0]["children"]]
    assert inner_children_types == ["myst-baker-input-slider", "code", "iframe"]

    iframe_node = result["children"][0]["children"][2]
    html = _decode_iframe_html(iframe_node)
    assert "mystBakerInitPlot(" in html
    assert '"0": {"x": 0, "y": 0}' in html
    assert '"1": {"x": 1, "y": 2}' in html
    assert '"2": {"x": 2, "y": 4}' in html


def test_transform_document_orders_input_specs_by_function_parameter_order():
    # The function declares parameters in the order (a, b), but the
    # input-slider blocks appear in the AST in the opposite order (b, then
    # a). input_specs must follow the function's declared parameter order
    # (matching precompute.matched_inputs / compute_grid's key order), not
    # the document order the slider blocks appear in -- otherwise the
    # client's lookup key built from input_specs won't match the
    # precomputed grid's keys.
    input_node_b = {
        "type": "myst-baker-input-slider",
        "arg": "b",
        "options": {"value": 1, "min": 0, "max": 1, "step": 1},
        "body": "",
    }
    input_node_a = {
        "type": "myst-baker-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 1, "step": 1},
        "body": "",
    }
    calc_node = _calc_node("def f(a, b):\n    return a, b\n")
    plot_node = {
        "type": "myst-baker-plot",
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

    # runtime.js (embedded above) *defines* mystBakerInitPlot, so find the last
    # occurrence -- the actual invocation with the real arguments.
    call_index = html.rindex("mystBakerInitPlot(")
    array_start = html.index("[", call_index)
    input_specs, _ = json.JSONDecoder().raw_decode(html, array_start)

    assert [spec["name"] for spec in input_specs] == ["a", "b"]


def test_transform_document_supports_checkbox_input():
    input_node = {
        "type": "myst-baker-input-checkbox",
        "arg": "enabled",
        "options": {"value": True},
        "body": "",
    }
    calc_node = _calc_node("def get_plot_data(enabled):\n    return enabled, int(enabled) * 2\n")
    plot_node = {
        "type": "myst-baker-plot",
        "arg": "scatter",
        "options": {"data": "get_plot_data"},
        "body": "",
    }

    result = transform_document(_page_ast(input_node, calc_node, plot_node))

    iframe_node = result["children"][2]
    html = _decode_iframe_html(iframe_node)
    assert '"true": {"x": true, "y": 2}' in html
    assert '"false": {"x": false, "y": 0}' in html


def test_transform_document_supports_dropdown_input():
    input_node = {
        "type": "myst-baker-input-dropdown",
        "arg": "color",
        "options": {},
        "body": "red\ngreen\nblue",
    }
    calc_node = _calc_node("def get_plot_data(color):\n    return color, len(color)\n")
    plot_node = {
        "type": "myst-baker-plot",
        "arg": "scatter",
        "options": {"data": "get_plot_data"},
        "body": "",
    }

    result = transform_document(_page_ast(input_node, calc_node, plot_node))

    iframe_node = result["children"][2]
    html = _decode_iframe_html(iframe_node)
    assert '"red": {"x": "red", "y": 3}' in html
    assert '"green": {"x": "green", "y": 5}' in html
    assert '"blue": {"x": "blue", "y": 4}' in html


def test_transform_document_raises_for_non_python_calc_language():
    input_node = {
        "type": "myst-baker-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 1, "step": 1},
        "body": "",
    }
    calc_node = {"type": "code", "lang": "r{calc}", "value": "f <- function(a) a\n"}
    plot_node = {
        "type": "myst-baker-plot",
        "arg": "scatter",
        "options": {"data": "f"},
        "body": "",
    }

    with pytest.raises(ValueError, match="declares language 'r'"):
        transform_document(_page_ast(input_node, calc_node, plot_node))


def test_transform_document_ignores_plain_python_code_fence():
    # A fence that merely happens to be lang="python" (no `{calc}` suffix,
    # e.g. an ordinary prose/example snippet) is not a live calc block --
    # it must not be exec'd or otherwise treated as a calc source. The
    # body below would raise if it were ever exec'd, so this test fails
    # loudly if that ever regresses.
    input_node = {
        "type": "myst-baker-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 1, "step": 1},
        "body": "",
    }
    plain_code_node = {
        "type": "code",
        "lang": "python",
        "value": "raise RuntimeError('should never run')\n",
    }
    calc_node = _calc_node("def f(a):\n    return a, a\n")
    plot_node = {
        "type": "myst-baker-plot",
        "arg": "scatter",
        "options": {"data": "f"},
        "body": "",
    }

    ast = {
        "type": "root",
        "children": [input_node, plain_code_node, calc_node, plot_node],
    }

    result = transform_document(ast)

    assert result["children"][-1]["type"] == "iframe"
