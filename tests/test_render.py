import pytest

from myst_baker.render import _trace_data, TRACE_FIELDS


def test_trace_data_passes_dict_through_unchanged():
    assert _trace_data({"x": [1, 2], "y": [3, 4]}, "scatter") == {"x": [1, 2], "y": [3, 4]}


def test_trace_data_zips_tuple_for_scatter():
    assert _trace_data(([1, 2], [3, 4]), "scatter") == {"x": [1, 2], "y": [3, 4]}


def test_trace_data_zips_tuple_for_bar():
    assert _trace_data((["Q1", "Q2"], [10, 20]), "bar") == {"x": ["Q1", "Q2"], "y": [10, 20]}


def test_trace_data_zips_single_element_tuple_for_histogram():
    assert _trace_data(([1, 2, 3],), "histogram") == {"x": [1, 2, 3]}


def test_trace_data_zips_tuple_for_pie():
    assert _trace_data((["a", "b"], [1, 2]), "pie") == {"labels": ["a", "b"], "values": [1, 2]}


def test_trace_data_zips_tuple_for_box_and_violin():
    assert _trace_data((["Q1", "Q1", "Q2"], [1, 2, 3]), "box") == {"x": ["Q1", "Q1", "Q2"], "y": [1, 2, 3]}
    assert _trace_data((["Q1", "Q1", "Q2"], [1, 2, 3]), "violin") == {"x": ["Q1", "Q1", "Q2"], "y": [1, 2, 3]}


def test_trace_data_raises_for_unknown_trace_type_without_dict():
    with pytest.raises(ValueError, match="unknown-type"):
        _trace_data([1, 2], "unknown-type")


def test_trace_data_passes_figure_dict_through_unchanged():
    # Already true today (the generic dict branch doesn't check trace_type
    # at all) -- this locks the behavior in rather than driving new code.
    figure = {
        "data": [{"type": "scatter", "x": [1, 2], "y": [3, 4]}],
        "layout": {"title": {"text": "t"}},
    }
    assert _trace_data(figure, "figure") == figure


def test_trace_data_raises_type_error_for_invalid_figure_return():
    with pytest.raises(TypeError, match="plotly figure"):
        _trace_data([1, 2], "figure")


def test_trace_data_serializes_real_plotly_figure_and_strips_default_template():
    go = pytest.importorskip("plotly.graph_objects")

    figure = go.Figure(data=[go.Scatter(x=[1, 2, 3], y=[4, 5, 6])])
    figure.update_layout(title="Example")

    result = _trace_data(figure, "figure")

    assert result["data"] == [{"x": [1, 2, 3], "y": [4, 5, 6], "type": "scatter"}]
    assert result["layout"] == {"title": {"text": "Example"}}
