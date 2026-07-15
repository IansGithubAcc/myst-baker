# Input/Output Types Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two new input directives (`input-checkbox`, `input-dropdown`) and four new supported Plotly trace types (`bar` — already works, verified as a smoke test only — `histogram`, `pie`, `box`/`violin`) to pymd's existing MyST plugin.

**Architecture:** Generalizes the single `if node_type == "pymd-input-slider"` branch in `transform.py` and the hardcoded `x: data[0], y: data[1]` in `runtime.js` into kind-dispatched equivalents. Calc-python functions gain a second accepted return shape (a dict of Plotly trace field names, spread in verbatim) alongside the existing tuple/list shape (now zipped against a small per-trace-type ordered field list, `TRACE_FIELDS`, computed once at build time in `render.py` — not in the browser).

**Tech Stack:** Python 3.13, MyST executable plugin (`pymd-plugin`), Tweakpane v4 (client widgets, CDN), Plotly.js (client charts, CDN), pytest + pytest-playwright.

## Global Constraints

- No new CDN dependencies (radio buttons were explicitly dropped from scope because they'd require Tweakpane's `plugin-essentials` add-on — see `docs/superpowers/specs/2026-07-14-input-output-types-expansion-design.md`).
- Existing `input-slider` and `plot` directive markdown syntax must keep working unchanged — this is an additive change at the directive/authoring level.
- Internal Python data shapes (the `inputs` dict passed to `precompute.matched_inputs`, and calc-python return values for non-scatter trace types) are allowed to change — there are no external consumers of these internals, only `transform.py` itself.
- Directive option types in `directives.py` must stay lowercase `"string"|"number"|"boolean"` (mystmd's directive-option type-check only recognizes these lowercase literals — see the existing comment at the top of `directives.py`).

---

## Task 1: `input-checkbox` and `input-dropdown` directive schemas

**Files:**
- Modify: `src/pymd/directives.py`
- Modify: `src/pymd/plugin.py`
- Test: `tests/test_directives.py`
- Test: `tests/test_plugin.py`

**Interfaces:**
- Produces: `INPUT_CHECKBOX_DIRECTIVE`, `INPUT_DROPDOWN_DIRECTIVE` dicts (same shape as the existing `INPUT_SLIDER_DIRECTIVE`), importable from `pymd.directives`. `KNOWN_DIRECTIVES` includes `"input-checkbox"` and `"input-dropdown"`. `build_placeholder_node("input-checkbox", ...)` produces a `{"type": "pymd-input-checkbox", ...}` node; `build_placeholder_node("input-dropdown", ...)` produces `{"type": "pymd-input-dropdown", ...}`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_directives.py` (after `test_build_placeholder_node_input_slider`):

```python
def test_build_placeholder_node_input_checkbox():
    node = build_placeholder_node(
        "input-checkbox", arg="enabled", options={"value": True}, body=""
    )
    assert node == {
        "type": "pymd-input-checkbox",
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
        "type": "pymd-input-dropdown",
        "arg": "color",
        "options": {"value": "green"},
        "body": "red\ngreen\nblue",
    }
```

Add to `tests/test_plugin.py` (new import `plugin` is already imported; this test only needs `json`/`io`, already imported):

```python
def test_plugin_spec_lists_all_directives(monkeypatch):
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    plugin.main([])
    spec = json.loads(out.getvalue())
    directive_names = {d["name"] for d in spec["directives"]}
    assert directive_names == {
        "input-slider",
        "input-checkbox",
        "input-dropdown",
        "calc-python",
        "plot",
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_directives.py tests/test_plugin.py -v`
Expected: the four new tests FAIL — `build_placeholder_node` raises `ValueError: unknown directive: input-checkbox` for the first two, and `test_plugin_spec_lists_all_directives` fails the set-equality assertion (missing `"input-checkbox"`/`"input-dropdown"`).

- [ ] **Step 3: Add the directive schemas**

In `src/pymd/directives.py`, change the top line:

```python
KNOWN_DIRECTIVES = {"input-slider", "input-checkbox", "input-dropdown", "calc-python", "plot"}
```

Add these two dicts directly after `INPUT_SLIDER_DIRECTIVE` (before `CALC_PYTHON_DIRECTIVE`):

```python
INPUT_CHECKBOX_DIRECTIVE = {
    "name": "input-checkbox",
    "doc": "A boolean checkbox input, bound to a name referenced by calc function parameters.",
    "arg": {"type": "string", "doc": "The input's name"},
    "options": {
        "value": {"type": "boolean", "doc": "Initial state"},
    },
}

INPUT_DROPDOWN_DIRECTIVE = {
    "name": "input-dropdown",
    "doc": (
        "A dropdown input selecting among a fixed list of choices (one per "
        "body line), bound to a name referenced by calc function parameters."
    ),
    "arg": {"type": "string", "doc": "The input's name"},
    "options": {
        "value": {
            "type": "string",
            "doc": "Initial selection (defaults to the first choice if omitted)",
        },
    },
    "body": {"type": "string", "doc": "Choices, one per line"},
}
```

- [ ] **Step 4: Register the new directives in the plugin spec**

In `src/pymd/plugin.py`, change the import and `PLUGIN_SPEC`:

```python
from pymd import transform
from pymd.directives import (
    INPUT_SLIDER_DIRECTIVE,
    INPUT_CHECKBOX_DIRECTIVE,
    INPUT_DROPDOWN_DIRECTIVE,
    CALC_PYTHON_DIRECTIVE,
    PLOT_DIRECTIVE,
    build_placeholder_node,
)

PLUGIN_SPEC = {
    "name": "pymd",
    "directives": [
        INPUT_SLIDER_DIRECTIVE,
        INPUT_CHECKBOX_DIRECTIVE,
        INPUT_DROPDOWN_DIRECTIVE,
        CALC_PYTHON_DIRECTIVE,
        PLOT_DIRECTIVE,
    ],
    "transforms": [{"stage": "document"}],
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_directives.py tests/test_plugin.py -v`
Expected: all tests PASS (6 in `test_directives.py`, 2 in `test_plugin.py`).

- [ ] **Step 6: Commit**

```bash
git add src/pymd/directives.py src/pymd/plugin.py tests/test_directives.py tests/test_plugin.py
git commit -m "feat: add input-checkbox and input-dropdown directive schemas"
```

---

## Task 2: Generalize the input pipeline (precompute.py + transform.py)

This is one task because the two files share a contract (the shape of the `inputs` dict) that must change atomically for the test suite to stay green between commits.

**Files:**
- Modify: `src/pymd/precompute.py`
- Modify: `src/pymd/transform.py`
- Test: `tests/test_precompute.py` (full rewrite of input-shape fixtures)
- Test: `tests/test_transform.py` (two new tests appended)

**Interfaces:**
- Consumes: `INPUT_CHECKBOX_DIRECTIVE`/`INPUT_DROPDOWN_DIRECTIVE` node types (`pymd-input-checkbox`, `pymd-input-dropdown`) from Task 1.
- Produces: `precompute.values_for_input(spec)` — `spec` is `{"kind": "slider", "min", "max", "step"}` | `{"kind": "checkbox"}` | `{"kind": "dropdown", "choices": [...]}`, returns the list of values for that input. `precompute.matched_inputs(func, inputs)` now takes `inputs` as `{name: spec}` (kind-tagged dicts) instead of bare `(min, max, step)` tuples — same return shape as before (`[(name, values), ...]`). `transform.py`'s per-plot `input_specs` list now includes a `"kind"` key per entry, consumed by `runtime.js` in Task 3.

- [ ] **Step 1: Write the failing precompute tests (full file rewrite)**

Replace `tests/test_precompute.py` entirely with:

```python
import pytest

from pymd.precompute import (
    input_values,
    values_for_input,
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


def test_values_for_input_slider():
    spec = {"kind": "slider", "min": 0, "max": 2, "step": 1}
    assert values_for_input(spec) == [0, 1, 2]


def test_values_for_input_checkbox():
    assert values_for_input({"kind": "checkbox"}) == [True, False]


def test_values_for_input_dropdown():
    spec = {"kind": "dropdown", "choices": ["red", "green", "blue"]}
    assert values_for_input(spec) == ["red", "green", "blue"]


def test_values_for_input_rejects_unknown_kind():
    with pytest.raises(ValueError, match="unknown-kind"):
        values_for_input({"kind": "unknown-kind"})


def test_matched_inputs_single_param():
    def f(a):
        return a

    matched = matched_inputs(f, {"a": {"kind": "slider", "min": 0, "max": 10, "step": 1}})
    assert matched == [("a", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])]


def test_matched_inputs_missing_input_raises():
    def f(a, b):
        return a + b

    with pytest.raises(ValueError, match="b"):
        matched_inputs(f, {"a": {"kind": "slider", "min": 0, "max": 10, "step": 1}})


def test_grid_size_multiplies_across_inputs():
    def f(a, b):
        return a + b

    matched = matched_inputs(
        f,
        {
            "a": {"kind": "slider", "min": 0, "max": 2, "step": 1},
            "b": {"kind": "slider", "min": 0, "max": 1, "step": 1},
        },
    )
    assert grid_size(matched) == 3 * 2


def test_compute_grid_calls_function_per_combination():
    def f(a):
        return a * 2

    result = compute_grid(f, {"a": {"kind": "slider", "min": 0, "max": 2, "step": 1}})
    assert result == {"0": 0, "1": 2, "2": 4}


def test_compute_grid_two_inputs_keys_joined_with_pipe():
    def f(a, b):
        return a + b

    result = compute_grid(
        f,
        {
            "a": {"kind": "slider", "min": 0, "max": 1, "step": 1},
            "b": {"kind": "slider", "min": 0, "max": 1, "step": 1},
        },
    )
    assert result == {"0|0": 0, "0|1": 1, "1|0": 1, "1|1": 2}


def test_compute_grid_raises_when_over_budget(monkeypatch):
    monkeypatch.setenv(MAX_GRID_SIZE_ENV_VAR, "2")

    def f(a):
        return a

    with pytest.raises(GridTooLargeError):
        compute_grid(f, {"a": {"kind": "slider", "min": 0, "max": 10, "step": 1}})


def test_max_grid_size_defaults_to_10000(monkeypatch):
    monkeypatch.delenv(MAX_GRID_SIZE_ENV_VAR, raising=False)
    assert max_grid_size() == 10_000


def test_compute_grid_keys_match_js_number_stringification_for_whole_number_floats():
    def f(a):
        return a

    result = compute_grid(f, {"a": {"kind": "slider", "min": 0, "max": 1, "step": 0.5}})
    assert result == {"0": 0.0, "0.5": 0.5, "1": 1.0}


def test_compute_grid_keys_match_js_boolean_stringification():
    def f(a):
        return a

    result = compute_grid(f, {"a": {"kind": "checkbox"}})
    assert result == {"true": True, "false": False}


def test_compute_grid_dropdown_keys_are_choice_strings():
    def f(a):
        return a

    result = compute_grid(f, {"a": {"kind": "dropdown", "choices": ["red", "green"]}})
    assert result == {"red": "red", "green": "green"}
```

- [ ] **Step 2: Run precompute tests to verify they fail**

Run: `uv run pytest tests/test_precompute.py -v`
Expected: FAIL — `ImportError: cannot import name 'values_for_input'`, plus every test passing a kind-tagged dict fails against the current `input_values(*inputs[name])` unpacking.

- [ ] **Step 3: Rewrite `precompute.py`'s input-value logic**

In `src/pymd/precompute.py`, keep `input_values` unchanged. Replace `_stringify` and `matched_inputs` with:

```python
def values_for_input(spec):
    kind = spec["kind"]
    if kind == "slider":
        return input_values(spec["min"], spec["max"], spec["step"])
    if kind == "checkbox":
        return [True, False]
    if kind == "dropdown":
        return list(spec["choices"])
    raise ValueError(f"unknown input kind: {kind!r}")


def matched_inputs(func, inputs):
    signature = inspect.signature(func)
    matched = []
    for name in signature.parameters:
        if name not in inputs:
            raise ValueError(
                f"Function '{func.__name__}' has parameter '{name}' with no "
                f"matching input block on this page."
            )
        matched.append((name, values_for_input(inputs[name])))
    return matched
```

Then update `_stringify` (bool must be checked before the float branch — `bool` is a subclass of `int` in Python):

```python
def _stringify(value):
    # Must match runtime.js's `String(v)` exactly. JS's String(true)/String(false)
    # is lowercase, but Python's str(True)/str(False) is capitalized -- checkbox
    # inputs need this special-cased or the browser's grid lookup never matches.
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
```

- [ ] **Step 4: Run precompute tests to verify they pass**

Run: `uv run pytest tests/test_precompute.py -v`
Expected: all 15 tests PASS.

- [ ] **Step 5: Write the failing transform tests**

Add to `tests/test_transform.py` (after the existing tests, same file):

```python
def test_transform_document_supports_checkbox_input():
    input_node = {
        "type": "pymd-input-checkbox",
        "arg": "enabled",
        "options": {"value": True},
        "body": "",
    }
    calc_node = {
        "type": "pymd-calc-python",
        "arg": None,
        "options": {},
        "body": "def get_plot_data(enabled):\n    return int(enabled) * 2\n",
    }
    plot_node = {
        "type": "pymd-plot",
        "arg": "scatter",
        "options": {"data": "get_plot_data"},
        "body": "",
    }

    result = transform_document(_page_ast(input_node, calc_node, plot_node))

    iframe_node = result["children"][2]
    html = _decode_iframe_html(iframe_node)
    assert '"true": 2' in html
    assert '"false": 0' in html


def test_transform_document_supports_dropdown_input():
    input_node = {
        "type": "pymd-input-dropdown",
        "arg": "color",
        "options": {},
        "body": "red\ngreen\nblue",
    }
    calc_node = {
        "type": "pymd-calc-python",
        "arg": None,
        "options": {},
        "body": "def get_plot_data(color):\n    return len(color)\n",
    }
    plot_node = {
        "type": "pymd-plot",
        "arg": "scatter",
        "options": {"data": "get_plot_data"},
        "body": "",
    }

    result = transform_document(_page_ast(input_node, calc_node, plot_node))

    iframe_node = result["children"][2]
    html = _decode_iframe_html(iframe_node)
    assert '"red": 3' in html
    assert '"green": 5' in html
    assert '"blue": 4' in html
```

- [ ] **Step 6: Run transform tests to verify the new ones fail**

Run: `uv run pytest tests/test_transform.py -v`
Expected: the two new tests FAIL with a `KeyError` (`_collect_nodes` doesn't yet recognize `pymd-input-checkbox`/`pymd-input-dropdown`, so `inputs` never gets an entry for `enabled`/`color`, and `precompute.matched_inputs` raises `ValueError: ... has parameter 'enabled' with no matching input block`). The 4 pre-existing tests in this file still PASS (Task 2 hasn't touched their behavior yet).

- [ ] **Step 7: Generalize `transform.py`'s node collection and client input-specs**

In `src/pymd/transform.py`, add these helpers directly after the `_iter_nodes` function (before `_collect_nodes`):

```python
def _dropdown_choices(body):
    return [line.strip() for line in body.splitlines() if line.strip()]


def _slider_precompute_spec(node):
    options = node["options"]
    return {"kind": "slider", "min": options["min"], "max": options["max"], "step": options["step"]}


def _checkbox_precompute_spec(node):
    return {"kind": "checkbox"}


def _dropdown_precompute_spec(node):
    return {"kind": "dropdown", "choices": _dropdown_choices(node["body"])}


_INPUT_PRECOMPUTE_SPECS = {
    "pymd-input-slider": _slider_precompute_spec,
    "pymd-input-checkbox": _checkbox_precompute_spec,
    "pymd-input-dropdown": _dropdown_precompute_spec,
}


def _slider_client_spec(name, node):
    options = node["options"]
    return {
        "kind": "slider",
        "name": name,
        "value": options["value"],
        "min": options["min"],
        "max": options["max"],
        "step": options["step"],
    }


def _checkbox_client_spec(name, node):
    return {"kind": "checkbox", "name": name, "value": node["options"]["value"]}


def _dropdown_client_spec(name, node):
    choices = _dropdown_choices(node["body"])
    value = node["options"].get("value", choices[0] if choices else None)
    return {"kind": "dropdown", "name": name, "value": value, "choices": choices}


_INPUT_CLIENT_SPECS = {
    "pymd-input-slider": _slider_client_spec,
    "pymd-input-checkbox": _checkbox_client_spec,
    "pymd-input-dropdown": _dropdown_client_spec,
}
```

Replace `_collect_nodes` with:

```python
def _collect_nodes(ast):
    inputs = {}
    input_nodes = {}
    calc_namespace = {}

    for node in _iter_nodes(ast):
        node_type = node.get("type")
        if node_type in _INPUT_PRECOMPUTE_SPECS:
            name = node["arg"]
            inputs[name] = _INPUT_PRECOMPUTE_SPECS[node_type](node)
            input_nodes[name] = node
        elif node_type == "pymd-calc-python":
            exec(node["body"], calc_namespace)

    return inputs, input_nodes, calc_namespace
```

In `transform_document`'s `replace_plot`, replace the `input_specs` comprehension with:

```python
        input_specs = [
            _INPUT_CLIENT_SPECS[input_nodes[name]["type"]](name, input_nodes[name])
            for name in inspect_params(func)
            if name in input_nodes
        ]
```

- [ ] **Step 8: Run transform tests to verify they pass**

Run: `uv run pytest tests/test_transform.py -v`
Expected: all 6 tests PASS.

- [ ] **Step 9: Run the full Python test suite**

Run: `uv run pytest tests/ --ignore=tests/test_e2e_browser.py -v`
Expected: all tests PASS (Playwright e2e tests are excluded here since they require a full `myst build` and are covered in Task 7).

- [ ] **Step 10: Commit**

```bash
git add src/pymd/precompute.py src/pymd/transform.py tests/test_precompute.py tests/test_transform.py
git commit -m "feat: generalize input pipeline for checkbox and dropdown kinds"
```

---

## Task 3: Kind-aware Tweakpane bindings in `runtime.js`

**Files:**
- Modify: `src/pymd/static/runtime.js`

**Interfaces:**
- Consumes: `inputSpecs` entries now carry `spec.kind` (`"slider" | "checkbox" | "dropdown"`) and, for dropdown, `spec.choices` — produced by Task 2's `_INPUT_CLIENT_SPECS`.
- Produces: no change to `pymdInitPlot`'s exported call signature; `draw()` is untouched in this task (still the old hardcoded `x: data[0], y: data[1]` — that becomes generic in Task 5).

This is a pure client-side JS change with no Python test harness; it can't be unit-tested via pytest. Its correctness is verified in Task 7's Playwright e2e test, once Task 4 gives it real content to render against. Do not claim this task works until Task 7 passes.

- [ ] **Step 1: Update the Tweakpane binding loop**

In `src/pymd/static/runtime.js`, replace the `inputSpecs.forEach((spec) => { pane.addBinding(...) })` block with:

```javascript
  inputSpecs.forEach((spec) => {
    // Each input kind needs different Tweakpane binding options: a slider
    // needs min/max/step, a checkbox needs none (Tweakpane infers a checkbox
    // from the bound value already being a boolean), and a dropdown needs an
    // `options` map of {label: value} pairs to render as a <select>.
    let bindingOptions = {};
    if (spec.kind === 'slider') {
      bindingOptions = { min: spec.min, max: spec.max, step: spec.step };
    } else if (spec.kind === 'dropdown') {
      const options = {};
      spec.choices.forEach((choice) => {
        options[choice] = choice;
      });
      bindingOptions = { options };
    }
    pane.addBinding(params, spec.name, bindingOptions).on('change', draw);
  });
```

- [ ] **Step 2: Sanity-check the file parses**

Run: `node --check src/pymd/static/runtime.js`
Expected: no output, exit code 0 (syntax is valid; this does not execute the code, only parses it).

- [ ] **Step 3: Commit**

```bash
git add src/pymd/static/runtime.js
git commit -m "feat: bind checkbox and dropdown inputs to their own Tweakpane widgets"
```

---

## Task 4: Checkbox and dropdown worked examples in `content/inputs.md`

**Files:**
- Modify: `content/inputs.md`

**Interfaces:**
- Consumes: `input-checkbox`/`input-dropdown` directives (Task 1), the generalized pipeline (Task 2), and the kind-aware bindings (Task 3).

- [ ] **Step 1: Append a Checkbox section**

Add to the end of `content/inputs.md`:

```markdown
## Checkbox

An `input-checkbox`'s argument is the name other blocks refer to it by, same
as `input-slider`. Its `:value:` option sets the initial state; pymd always
precomputes both `true` and `false`, regardless of which one a page starts
on.

````md
```{input-checkbox} inverted
:value: false
```

```{calc-python}
import math

def maybe_inverted_sine(inverted):
    x = [i / 10 for i in range(-31, 32)]
    sign = -1 if inverted else 1
    y = [sign * math.sin(xi) for xi in x]
    return x, y
```

```{plot} scatter
:data: maybe_inverted_sine
:mode: lines
```
````

```{input-checkbox} inverted
:value: false
```

```{calc-python}
import math

def maybe_inverted_sine(inverted):
    x = [i / 10 for i in range(-31, 32)]
    sign = -1 if inverted else 1
    y = [sign * math.sin(xi) for xi in x]
    return x, y
```

```{plot} scatter
:data: maybe_inverted_sine
:mode: lines
```
```

- [ ] **Step 2: Append a Dropdown section**

Add directly after the Checkbox section:

```markdown
## Dropdown

An `input-dropdown`'s choices come from its body, one per line. Its
`:value:` option picks which one is initially selected — omit it and pymd
uses the first line. Every choice becomes one column of the precomputed
grid, so a three-choice dropdown is exactly as cheap as a three-step
slider.

````md
```{input-dropdown} waveform
:value: sine
sine
square
sawtooth
```

```{calc-python}
import math

def waveform_curve(waveform):
    x = [i / 10 for i in range(-31, 32)]
    if waveform == "sine":
        y = [math.sin(xi) for xi in x]
    elif waveform == "square":
        y = [1.0 if math.sin(xi) >= 0 else -1.0 for xi in x]
    else:
        period = 2 * math.pi
        y = [2 * ((xi / period) % 1) - 1 for xi in x]
    return x, y
```

```{plot} scatter
:data: waveform_curve
:mode: lines
```
````

```{input-dropdown} waveform
:value: sine
sine
square
sawtooth
```

```{calc-python}
import math

def waveform_curve(waveform):
    x = [i / 10 for i in range(-31, 32)]
    if waveform == "sine":
        y = [math.sin(xi) for xi in x]
    elif waveform == "square":
        y = [1.0 if math.sin(xi) >= 0 else -1.0 for xi in x]
    else:
        period = 2 * math.pi
        y = [2 * ((xi / period) % 1) - 1 for xi in x]
    return x, y
```

```{plot} scatter
:data: waveform_curve
:mode: lines
```
```

- [ ] **Step 3: Build the site and confirm no build errors**

Run: `uv run myst build --html`
Expected: `📚 Built 5 pages for project` with no errors or warnings about `input-checkbox`/`input-dropdown` (a warning here usually means an option/body type mismatch — see the `directives.py` gotcha comment about lowercase option types if one appears).

- [ ] **Step 4: Commit**

```bash
git add content/inputs.md
git commit -m "docs: add checkbox and dropdown worked examples"
```

---

## Task 5: `TRACE_FIELDS` normalization in `render.py`, simplified `draw()`

**Files:**
- Modify: `src/pymd/render.py`
- Modify: `src/pymd/static/runtime.js`
- Test: `tests/test_render.py` (new file)
- Modify: `tests/test_transform.py` (fix scatter-plot fixtures broken by the shape change)

**Interfaces:**
- Produces: `render.TRACE_FIELDS` (dict, trace type → ordered field-name tuple) and `render._trace_data(value, trace_type)` (dict passthrough, or positional zip against `TRACE_FIELDS`). `render_plot`'s `grid_result` argument may now contain either dicts or tuples/lists as values — both accepted transparently.
- Consumes: nothing new; existing `render_plot(plot_node, grid_result, input_specs)` signature is unchanged.

**Why existing demo content needs no changes:** every calc function in `content/*.md` already returns `(x, y)` tuples, and `TRACE_FIELDS["scatter"] = TRACE_FIELDS["bar"] = ("x", "y")`, so the normalized shape (`{"x": ..., "y": ...}`) is identical to what `runtime.js` already produced by hand. Only the synthetic single-value calc bodies in `tests/test_transform.py` (written before real chart shapes mattered) need updating.

- [ ] **Step 1: Write the failing render tests**

Create `tests/test_render.py`:

```python
import pytest

from pymd.render import _trace_data, TRACE_FIELDS


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
```

- [ ] **Step 2: Run render tests to verify they fail**

Run: `uv run pytest tests/test_render.py -v`
Expected: FAIL — `ImportError: cannot import name '_trace_data' from 'pymd.render'`.

- [ ] **Step 3: Add `TRACE_FIELDS`/`_trace_data` and apply them in `render_plot`**

In `src/pymd/render.py`, add this directly after the `RUNTIME_JS = _f.read()` line and before `def render_plot`:

```python
TRACE_FIELDS = {
    "scatter": ("x", "y"),
    "bar": ("x", "y"),
    "box": ("x", "y"),
    "violin": ("x", "y"),
    "histogram": ("x",),
    "pie": ("labels", "values"),
}


def _trace_data(value, trace_type):
    if isinstance(value, dict):
        return value
    if trace_type not in TRACE_FIELDS:
        raise ValueError(
            f"plot type {trace_type!r} has no known positional field order; "
            "either add it to TRACE_FIELDS or have its calc function return "
            "a dict of Plotly trace fields instead of a tuple/list."
        )
    return dict(zip(TRACE_FIELDS[trace_type], value))
```

In `render_plot`, directly after the line `trace_options = {...}` (which computes `trace_options` from `plot_node["options"]`), add:

```python
    grid_result = {
        key: _trace_data(value, trace_type) for key, value in grid_result.items()
    }
```

- [ ] **Step 4: Run render tests to verify they pass**

Run: `uv run pytest tests/test_render.py -v`
Expected: all 7 tests PASS.

- [ ] **Step 5: Simplify `runtime.js`'s `draw()`**

In `src/pymd/static/runtime.js`, replace the `draw()` function body:

```javascript
  function draw() {
    const data = currentData();
    const trace = Object.assign({ type: traceType }, data, traceOptions);
    Plotly.react(plotEl, [trace], { autosize: true }, { responsive: true });
  }
```

Run: `node --check src/pymd/static/runtime.js`
Expected: no output, exit code 0.

- [ ] **Step 6: Fix the now-broken scatter fixtures in `tests/test_transform.py`**

Run: `uv run pytest tests/test_transform.py -v`
Expected at this point: `test_transform_document_replaces_plot_node_with_html`, `test_transform_document_finds_plot_node_wrapped_in_block_node`, `test_transform_document_orders_input_specs_by_function_parameter_order`, `test_transform_document_supports_checkbox_input`, and `test_transform_document_supports_dropdown_input` all FAIL — their calc bodies return a bare number, and `_trace_data(number, "scatter")` raises `TypeError: zip argument #2 must support iteration`.

In `test_transform_document_replaces_plot_node_with_html`, change the calc body and assertions:

```python
    calc_node = {
        "type": "pymd-calc-python",
        "arg": None,
        "options": {},
        "body": "def get_plot_data(a):\n    return a, a * 2\n",
    }
```

```python
    assert '"0": {"x": 0, "y": 0}' in html
    assert '"1": {"x": 1, "y": 2}' in html
    assert '"2": {"x": 2, "y": 4}' in html
```

Apply the identical calc-body and assertion change to `test_transform_document_finds_plot_node_wrapped_in_block_node` (it uses the same fixture values).

In `test_transform_document_orders_input_specs_by_function_parameter_order`, change the calc body only (its assertions check `input_specs` ordering, not grid values):

```python
    calc_node = {
        "type": "pymd-calc-python",
        "arg": None,
        "options": {},
        "body": "def f(a, b):\n    return a, b\n",
    }
```

In `test_transform_document_supports_checkbox_input`, change the calc body and assertions:

```python
    calc_node = {
        "type": "pymd-calc-python",
        "arg": None,
        "options": {},
        "body": "def get_plot_data(enabled):\n    return enabled, int(enabled) * 2\n",
    }
```

```python
    assert '"true": {"x": true, "y": 2}' in html
    assert '"false": {"x": false, "y": 0}' in html
```

In `test_transform_document_supports_dropdown_input`, change the calc body and assertions:

```python
    calc_node = {
        "type": "pymd-calc-python",
        "arg": None,
        "options": {},
        "body": "def get_plot_data(color):\n    return color, len(color)\n",
    }
```

```python
    assert '"red": {"x": "red", "y": 3}' in html
    assert '"green": {"x": "green", "y": 5}' in html
    assert '"blue": {"x": "blue", "y": 4}' in html
```

- [ ] **Step 7: Run the full Python test suite**

Run: `uv run pytest tests/ --ignore=tests/test_e2e_browser.py -v`
Expected: all tests PASS.

- [ ] **Step 8: Build the site and confirm existing demo pages still work**

Run: `uv run myst build --html`
Expected: `📚 Built 5 pages for project` with no errors (this proves the existing content pages, whose calc functions already return `(x, y)` tuples, need no edits for this change).

- [ ] **Step 9: Commit**

```bash
git add src/pymd/render.py src/pymd/static/runtime.js tests/test_render.py tests/test_transform.py
git commit -m "feat: normalize plot trace data via TRACE_FIELDS, supporting non-x/y trace types"
```

---

## Task 6: Histogram, pie, and box/violin worked examples in `content/outputs.md`

**Files:**
- Modify: `content/outputs.md`

**Interfaces:**
- Consumes: Task 5's `TRACE_FIELDS`-based normalization (`histogram`/`pie`/`box`/`violin` all need it; `bar`, already in this file, does not).

- [ ] **Step 1: Append a Histogram section**

Add to the end of `content/outputs.md`:

```markdown
## Histogram

A `histogram` trace only needs one array — samples on `x`. A calc function
feeding a histogram should return a single-element tuple, `(x,)`, not a
bare list, so pymd can tell "one array" apart from "one array meant to be
unpacked positionally."

````md
```{input-slider} spread
:value: 1
:min: 0.5
:max: 3
:step: 0.5
```

```{calc-python}
def scaled_samples(spread):
    base = [-2, -1.5, -1, -0.5, -0.5, 0, 0, 0, 0.5, 0.5, 1, 1.5, 2]
    samples = [spread * b for b in base]
    return (samples,)
```

```{plot} histogram
:data: scaled_samples
```
````

```{input-slider} spread
:value: 1
:min: 0.5
:max: 3
:step: 0.5
```

```{calc-python}
def scaled_samples(spread):
    base = [-2, -1.5, -1, -0.5, -0.5, 0, 0, 0, 0.5, 0.5, 1, 1.5, 2]
    samples = [spread * b for b in base]
    return (samples,)
```

```{plot} histogram
:data: scaled_samples
```
```

- [ ] **Step 2: Append a Pie chart section**

```markdown
## Pie chart

A `pie` trace needs `labels` and `values` rather than `x`/`y`. Its
`calc-python` function returns them in that order as a 2-tuple, the same
shape as a scatter's `(x, y)` — just a different pair of names.

````md
```{input-slider} marketing_share
:value: 20
:min: 5
:max: 40
:step: 5
```

```{calc-python}
def budget_allocation(marketing_share):
    remaining = 100 - marketing_share
    labels = ["Marketing", "Engineering", "Operations"]
    values = [marketing_share, remaining * 0.6, remaining * 0.4]
    return labels, values
```

```{plot} pie
:data: budget_allocation
```
````

```{input-slider} marketing_share
:value: 20
:min: 5
:max: 40
:step: 5
```

```{calc-python}
def budget_allocation(marketing_share):
    remaining = 100 - marketing_share
    labels = ["Marketing", "Engineering", "Operations"]
    values = [marketing_share, remaining * 0.6, remaining * 0.4]
    return labels, values
```

```{plot} pie
:data: budget_allocation
```
```

- [ ] **Step 3: Append a Box and violin plots section**

```markdown
## Box and violin plots

`box` and `violin` traces take the same `(x, y)` shape as `bar` — repeated
`x` category labels group their matching `y` values into one distribution
per category. The same data feeds both trace types below.

````md
```{input-slider} shift
:value: 0
:min: -2
:max: 2
:step: 0.5
```

```{calc-python}
def quarterly_measurements(shift):
    categories = []
    measurements = []
    base = {
        "Q1": [10, 11, 9, 10.5, 12],
        "Q2": [11, 12, 10, 13, 11.5],
        "Q3": [13, 14, 12.5, 15, 13],
        "Q4": [12, 13, 11, 12.5, 14],
    }
    for quarter, values in base.items():
        for v in values:
            categories.append(quarter)
            measurements.append(v + shift)
    return categories, measurements
```

```{plot} box
:data: quarterly_measurements
```

```{plot} violin
:data: quarterly_measurements
```
````

```{input-slider} shift
:value: 0
:min: -2
:max: 2
:step: 0.5
```

```{calc-python}
def quarterly_measurements(shift):
    categories = []
    measurements = []
    base = {
        "Q1": [10, 11, 9, 10.5, 12],
        "Q2": [11, 12, 10, 13, 11.5],
        "Q3": [13, 14, 12.5, 15, 13],
        "Q4": [12, 13, 11, 12.5, 14],
    }
    for quarter, values in base.items():
        for v in values:
            categories.append(quarter)
            measurements.append(v + shift)
    return categories, measurements
```

```{plot} box
:data: quarterly_measurements
```

```{plot} violin
:data: quarterly_measurements
```
```

- [ ] **Step 4: Build the site and confirm no build errors**

Run: `uv run myst build --html`
Expected: `📚 Built 5 pages for project` with no errors.

- [ ] **Step 5: Commit**

```bash
git add content/outputs.md
git commit -m "docs: add histogram, pie, and box/violin worked examples"
```

---

## Task 7: End-to-end Playwright coverage for the new inputs and outputs

**Files:**
- Modify: `tests/test_e2e_browser.py`

**Interfaces:**
- Consumes: the built site (`content/inputs.md`'s new Dropdown section, `content/outputs.md`'s new Histogram/Pie/Box/Violin sections from Tasks 4 and 6).

mystmd serves each content page at its own path — confirmed by inspecting a real `uv run myst build --html` output: `content/inputs.md` → `_build/html/inputs/index.html`, `content/outputs.md` → `_build/html/outputs/index.html` (same pattern as the existing fixture's `_build/html/index.html` for `content/index.md`).

- [ ] **Step 1: Add a `built_site`-relative URL helper**

In `tests/test_e2e_browser.py`, the `built_site` fixture currently yields a hardcoded `.../index.html` string. Add two new fixtures right after it that derive sibling page URLs from the same server:

```python
@pytest.fixture(scope="module")
def inputs_page_url(built_site):
    return built_site.replace("/index.html", "/inputs/index.html")


@pytest.fixture(scope="module")
def outputs_page_url(built_site):
    return built_site.replace("/index.html", "/outputs/index.html")
```

- [ ] **Step 2: Discover the dropdown's real DOM shape**

Tweakpane's exact DOM for a list/dropdown binding hasn't been verified against a real build yet (the existing e2e test's own comments show this project always verifies Tweakpane's DOM empirically rather than assuming from docs — e.g. the `.tp-rotv`/`input[type='text']` comment for the slider). Before writing the assertion-based test, run this one-off exploration script to find the actual selector:

```bash
uv run python -c "
from playwright.sync_api import sync_playwright
import subprocess, functools, http.server, socketserver, threading
from pathlib import Path

subprocess.run(['uv', 'run', 'myst', 'build', '--html'], check=True)
html_dir = Path('_build/html')
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(html_dir))
httpd = socketserver.TCPServer(('127.0.0.1', 0), handler)
port = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f'http://127.0.0.1:{port}/inputs/index.html')
    # content/inputs.md's live iframes, in document order: One slider (0),
    # Two sliders (1), Three sliders (2), Fine steps (3), Checkbox (4),
    # Dropdown (5) -- the dropdown example is the 6th plot on the page.
    frame = page.frame_locator('iframe').nth(5)
    frame.locator('.tp-rotv').first.wait_for(state='visible')
    print(frame.locator('.tp-rotv').first.inner_html())
    browser.close()
httpd.shutdown()
"
```

Read the printed HTML to find the actual dropdown element (likely a `<select>` inside a `.tp-lstv`/`.tp-rotv` wrapper — Tweakpane v4's list binding). Use whatever selector this reveals in Step 3 below — if it differs from `.tp-rotv select`, use the real one and note the discovery in a code comment, matching this codebase's established style.

- [ ] **Step 3: Write the dropdown e2e test**

Add to `tests/test_e2e_browser.py`:

```python
def test_dropdown_updates_plot_with_no_console_errors(inputs_page_url, page):
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page_errors = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    page.goto(inputs_page_url)

    # content/inputs.md's live iframes, in document order: One slider (0),
    # Two sliders (1), Three sliders (2), Fine steps (3), Checkbox (4),
    # Dropdown (5) -- the dropdown example is the 6th plot on the page.
    plot_frame = page.frame_locator("iframe").nth(5)
    plot_locator = plot_frame.locator(".js-plotly-plot").first
    plot_locator.wait_for(state="visible")

    before = plot_locator.evaluate("el => el.data[0].y.slice(0, 3)")

    dropdown_select = plot_frame.locator(".tp-rotv select").first
    dropdown_select.select_option("square")

    page.wait_for_timeout(300)

    after = plot_locator.evaluate("el => el.data[0].y.slice(0, 3)")

    assert before != after
    assert console_errors == []
    assert page_errors == []
```

(If Step 2's discovery revealed a different selector than `.tp-rotv select`, use that selector here instead.)

- [ ] **Step 4: Write the new-output-types smoke test**

Add to `tests/test_e2e_browser.py`:

```python
def test_new_output_types_render_with_no_console_errors(outputs_page_url, page):
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page_errors = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    page.goto(outputs_page_url)

    # content/outputs.md's live plots, in document order: 3 scatter-mode
    # plots, 1 bar, 1 histogram, 1 pie, 1 box, 1 violin = 8 total.
    iframe_count = page.locator("iframe").count()
    assert iframe_count == 8

    for i in range(iframe_count):
        frame = page.frame_locator("iframe").nth(i)
        frame.locator(".js-plotly-plot").first.wait_for(state="visible")

    assert console_errors == []
    assert page_errors == []
```

- [ ] **Step 5: Run the new e2e tests**

Run: `uv run pytest tests/test_e2e_browser.py -v`
Expected: all tests PASS, including the pre-existing `test_slider_updates_plot_with_no_console_errors`. If `test_dropdown_updates_plot_with_no_console_errors` fails on the `dropdown_select.select_option(...)` line, re-run Step 2's discovery script and correct the selector — do not guess a second time.

- [ ] **Step 6: Run the entire test suite once more, end to end**

Run: `uv run pytest tests/ -v`
Expected: all tests PASS (directives, plugin, precompute, transform, render, e2e).

- [ ] **Step 7: Commit**

```bash
git add tests/test_e2e_browser.py
git commit -m "test: cover dropdown input and new plot trace types end-to-end"
```
