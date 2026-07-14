# pymd: Expanding Input and Output Types

## Concept

pymd currently supports exactly one input kind (`input-slider`) and one output kind (`plot`, generic over Plotly trace types but only ever fed `(x, y)` data). This is the first real generalization of that MVP: two new input kinds (`input-checkbox`, `input-dropdown`) and support for four more Plotly trace types (`bar`, `histogram`, `pie`, `box`/`violin`) on the existing `plot` directive. It replaces the single `if node_type == "pymd-input-slider"` branch in `transform.py` and the hardcoded `x: data[0], y: data[1]` in `runtime.js` with kind-dispatched equivalents.

**Explicitly out of scope for this round** (considered and rejected):
- Radio buttons — would need Tweakpane's `plugin-essentials` add-on (a second CDN dependency) to render as a real radio grid; without it, "radio" would just be a dropdown alias with no visual difference. Not worth the dependency for this batch.
- Free-text input — breaks the precompute-everything model (infinite possible values, can't grid it).
- Color-swatch input, readout/text output, table output, Plotly `indicator` — floated during brainstorming but deferred; not part of this batch.
- Heatmaps, radar/polar charts, true continuous color pickers — need genuinely new (2D, r/θ) data shapes, a different tier of effort than this batch.

## New input directives

### `input-checkbox`

```
:::{input-checkbox} enabled
:value: true
:::
```

- `arg`: the input's name (same convention as `input-slider`).
- `options.value` (boolean): initial state.
- No body.
- Grid dimension is always `[True, False]`, regardless of the initial value — same principle as `input-slider` always gridding its full `min..max` range regardless of its initial `value`.

### `input-dropdown`

```
:::{input-dropdown} color
:value: green
red
green
blue
:::
```

- `arg`: the input's name.
- `options.value` (string, optional): initial selection. Defaults to the first body line if omitted.
- `body`: choices, one per line (plain strings — reuses the existing `body`-as-string mechanism already used by `calc-python`, rather than relying on mystmd's unverified `"parsed"` option type for a YAML/JSON list).
- Grid dimension is the literal list of choice strings, in body order.

Both flow into the same `inputs`/`input_nodes` collection in `transform.py`'s `_collect_nodes` that `input-slider` currently populates alone. This becomes a per-kind dispatch (e.g. a small `INPUT_KIND_HANDLERS` dict keyed by node type) instead of a single `if` branch.

`precompute.py` generalizes similarly: `matched_inputs`/`input_values` currently assume every input is a `(min, max, step)` tuple. This becomes a kind-tagged value (e.g. `{"kind": "slider", "min":.., "max":.., "step":..}`, `{"kind": "checkbox"}`, `{"kind": "dropdown", "choices": [...]}`), with a small per-kind function computing that input's value list:
- slider → `input_values(min, max, step)` (existing range logic, unchanged)
- checkbox → `[True, False]`
- dropdown → `choices` verbatim

## Output: generalizing `plot`

No new directive — `plot`'s `arg` already passes straight through as the Plotly trace `type`. What's missing is a data-shape convention, since `bar`/`box`/`violin` want `(x, y)` like `scatter` does today, `histogram` wants only `x`, and `pie` wants `(labels, values)`.

**Two accepted return shapes from a calc function**, mirroring Python's own args/kwargs duality:

1. **Dict → kwargs.** `{"x": [...], "y": [...]}`, `{"labels": [...], "values": [...]}`, etc. Spread directly into the Plotly trace object. Keys map straight to Plotly's own field names, so this already covers every current and future trace type with zero pymd-side mapping code.
2. **Tuple/list → positional args.** `(x, y)`, `(x,)`, `(labels, values)`. Zipped against a small per-trace-type ordered field list:

   ```python
   TRACE_FIELDS = {
       "scatter": ("x", "y"),
       "bar": ("x", "y"),
       "box": ("x", "y"),
       "violin": ("x", "y"),
       "histogram": ("x",),
       "pie": ("labels", "values"),
   }
   ```

   to build the same kwargs dict as (1).

`runtime.js`'s `draw()` changes from the hardcoded `x: data[0], y: data[1]` to: if `currentData()` is an array, zip against a JS-side mirror of `TRACE_FIELDS`; if it's a plain object, spread it directly into the trace.

**Breaking change, accepted deliberately**: the existing demo's calc functions return `(x, y)` tuples today, which still works unchanged for `scatter` (same shape, same `TRACE_FIELDS` entry) — but the demo gets extended with new blocks exercising the other four trace types, not dual-supported via some other legacy path.

## Testing

- Unit tests: `TRACE_FIELDS` zip logic (dict vs. tuple/list input, all six trace types), and the generalized `precompute` kind dispatch (checkbox's fixed `[True, False]`, dropdown's choice-list passthrough).
- Playwright end-to-end: extend the existing slider→plot flow test to cover at least one new input (`input-dropdown` driving a plot) and one new output (`pie`, since it's the one whose data shape most differs from the current `x`/`y` default).
- Docs: `content/inputs.md` and `content/outputs.md` get a worked example for each of the six additions.
