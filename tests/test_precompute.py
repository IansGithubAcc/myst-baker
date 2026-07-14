import pytest

from pymd.precompute import (
    input_values,
    matched_inputs,
    grid_size,
    compute_grid,
    max_grid_size,
    GridTooLargeError,
    MAX_GRID_SIZE_ENV_VAR,
)


def test_input_values_inclusive_range():
    assert input_values(0, 10, 1) == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


def test_input_values_non_integer_step():
    assert input_values(0, 1, 0.5) == [0, 0.5, 1]


def test_matched_inputs_single_param():
    def f(a):
        return a

    matched = matched_inputs(f, {"a": (0, 10, 1)})
    assert matched == [("a", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])]


def test_matched_inputs_missing_input_raises():
    def f(a, b):
        return a + b

    with pytest.raises(ValueError, match="b"):
        matched_inputs(f, {"a": (0, 10, 1)})


def test_grid_size_multiplies_across_inputs():
    def f(a, b):
        return a + b

    matched = matched_inputs(f, {"a": (0, 2, 1), "b": (0, 1, 1)})
    assert grid_size(matched) == 3 * 2


def test_compute_grid_calls_function_per_combination():
    def f(a):
        return a * 2

    result = compute_grid(f, {"a": (0, 2, 1)})
    assert result == {"0": 0, "1": 2, "2": 4}


def test_compute_grid_two_inputs_keys_joined_with_pipe():
    def f(a, b):
        return a + b

    result = compute_grid(f, {"a": (0, 1, 1), "b": (0, 1, 1)})
    assert result == {"0|0": 0, "0|1": 1, "1|0": 1, "1|1": 2}


def test_compute_grid_raises_when_over_budget(monkeypatch):
    monkeypatch.setenv(MAX_GRID_SIZE_ENV_VAR, "2")

    def f(a):
        return a

    with pytest.raises(GridTooLargeError):
        compute_grid(f, {"a": (0, 10, 1)})


def test_max_grid_size_defaults_to_10000(monkeypatch):
    monkeypatch.delenv(MAX_GRID_SIZE_ENV_VAR, raising=False)
    assert max_grid_size() == 10_000
