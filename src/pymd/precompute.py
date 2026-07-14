import inspect
import itertools
import os

DEFAULT_MAX_GRID_SIZE = 10_000
MAX_GRID_SIZE_ENV_VAR = "PYMD_MAX_GRID_SIZE"


class GridTooLargeError(Exception):
    def __init__(self, function_name, size, limit):
        self.function_name = function_name
        self.size = size
        self.limit = limit
        super().__init__(
            f"Grid for '{function_name}' has {size} combinations, "
            f"exceeding the limit of {limit}. "
            f"Set {MAX_GRID_SIZE_ENV_VAR} to override."
        )


def input_values(min_value, max_value, step):
    steps = int(round((max_value - min_value) / step))
    return [round(min_value + i * step, 10) for i in range(steps + 1)]


def matched_inputs(func, inputs):
    signature = inspect.signature(func)
    matched = []
    for name in signature.parameters:
        if name not in inputs:
            raise ValueError(
                f"Function '{func.__name__}' has parameter '{name}' with no "
                f"matching input-slider block on this page."
            )
        matched.append((name, input_values(*inputs[name])))
    return matched


def grid_size(matched):
    size = 1
    for _, values in matched:
        size *= len(values)
    return size


def max_grid_size():
    return int(os.environ.get(MAX_GRID_SIZE_ENV_VAR, DEFAULT_MAX_GRID_SIZE))


def _stringify(value):
    # Must match runtime.js's `String(v)` exactly. JS has no int/float
    # distinction, so String(1) === "1" for a whole-number value however it
    # arrived; Python's str() renders the same whole-number float as "1.0".
    # Without this, any fractional :step: whose grid includes a whole-number
    # point produces a key here that the client's lookup can never match.
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def compute_grid(func, inputs):
    matched = matched_inputs(func, inputs)
    names = [name for name, _ in matched]
    value_lists = [values for _, values in matched]

    size = grid_size(matched)
    limit = max_grid_size()
    if size > limit:
        raise GridTooLargeError(func.__name__, size, limit)

    results = {}
    for combo in itertools.product(*value_lists):
        key = "|".join(_stringify(v) for v in combo)
        results[key] = func(**dict(zip(names, combo)))
    return results
