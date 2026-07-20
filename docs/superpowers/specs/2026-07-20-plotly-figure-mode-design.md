# Optional plotly support: `{plot} figure`

## Problem

`plot` blocks today only ever produce one Plotly *trace* per calc function:
a dict of trace fields (`{"x": [...], "y": [...]}`) or a positional
tuple matched against a hardcoded field order (`TRACE_FIELDS` in
`render.py`). The directive's argument is always a trace type
(`scatter`, `bar`, ...), and the client runtime (`runtime.js`) always
builds each trace as `Object.assign({type: traceType}, d, traceOptions)`
and a fixed layout (`{autosize: true}`, plus a `barmode` tweak for
grouped bars).

There is no way to control axis titles, tick formatting, annotations,
subplots, multiple differently-typed traces on one plot, or any other
Plotly `layout` concept — the framework has no concept of `layout` at
all today. Authors who have `plotly` installed should be able to build a
full `go.Figure` (or any `plotly.express` figure) inside a calc block and
have myst-baker bake its complete JSON (data + layout) into the page,
getting the full flexibility of the Plotly API instead of myst-baker's
trace-field mapping.

plotly is not a dependency of myst-baker today. This should stay true —
the feature is opt-in via a new `myst-baker[plotly]` extra.

## Decision

Add a reserved `figure` value for the `plot` directive's argument, used
in place of a real trace type:

````
```{plot} figure
:data: my_figure_func
```
````

`:data:` in figure mode names exactly one calc function (the existing
comma-separated multi-function combining feature is for combining
several *traces* onto one plot; a full figure already carries its own
list of traces internally, so there's no defined meaning for combining
two figure-returning functions — this is simply not a supported
combination, and no special validation/error is added for it).

The named calc function returns one of:
- a real plotly figure object — anything exposing `.to_plotly_json()`
  (covers `go.Figure` and every `plotly.express` chart), or
- a plain `{"data": [...], "layout": {...}}` dict, hand-written, with no
  plotly install required at all.

`:mode:` (and any other non-`data` directive option) is ignored entirely
in figure mode — the whole point is that the calc function has full
control over styling, so myst-baker doesn't try to merge anything in on
top of it.

Rejected alternative: auto-detecting figure mode from the calc
function's return shape regardless of the directive's `arg`. Rejected
because it's implicit — a reader can't tell a plot block computes a full
figure just by looking at it, and it would make an ordinary `plot`
block's meaning depend on what its calc function happens to return
rather than on what's written in the directive.

## Mechanism

### `pyproject.toml`

```toml
[project.optional-dependencies]
plotly = ["plotly>=5"]
```

### `directives.py`

`PLOT_DIRECTIVE`'s `arg` doc string is updated to mention `figure` as a
reserved value alongside real Plotly trace types. No schema change — the
directive's `arg` is already a free-form string field.

### `render.py`

New helper:

```python
def _figure_json(value):
    if hasattr(value, "to_plotly_json"):
        import plotly.io as pio
        return json.loads(pio.to_json(value))
    if isinstance(value, dict):
        return value
    raise TypeError(
        f"calc function for a `{{plot}} figure` block must return a plotly "
        f"figure or a {{'data': [...], 'layout': {{...}}}} dict, got {type(value)!r}"
    )
```

`plotly.io` is imported lazily, only when a figure-like object is
actually encountered — myst-baker never hard-imports plotly at module
load time, so it stays a true optional dependency. Using
`plotly.io.to_json` (not the bare `.to_plotly_json()` dict) matters: it
runs plotly's own JSON encoder, which cleans up numpy arrays,
pandas Series, and datetime values that a raw `go.Figure` may hold
internally; `.to_plotly_json()` alone can still contain values
`json.dumps` chokes on.

CORRECTED (verified empirically: `pio.to_json` on a two-point scatter
figure with nothing but a title serializes to 6724 bytes; the same
figure with `fig.layout.template = None` set first serializes to 91
bytes): `pio.to_json`/`.to_plotly_json()` always resolves and inlines
`pio.templates.default` (the "plotly" theme's full color/font/colorbar
style dict for every trace kind, not just the ones used) into
`layout.template`, whether or not the calc function ever touched
templating. This is fine for a one-off standalone export, but
myst-baker bakes one such JSON blob *per grid combination* — for a
figure varying over even a modest slider (dozens of steps), that's the
6.6 KB of pure redundant styling metadata multiplied by every step,
added to the page for no visual benefit: every myst-baker page already
loads real Plotly.js from a pinned CDN version, whose own built-in
defaults are exactly what `pio.templates["plotly"]` codifies, so the
resolved template renders identically whether it's present in the JSON
or simply absent. `_figure_json` therefore deletes
`result["layout"]["template"]` (if present) unconditionally after
parsing, for every figure-mode grid entry. This does mean a calc
function that assigns a *named* non-default template (e.g.
`fig.update_layout(template="plotly_dark")`) loses that specific theme
— there is no cheap way to keep "which named theme" without either
re-embedding its full resolved style dict (the bloat this avoids) or
having myst-baker separately ship Plotly.js's own template registry
(out of scope). Authors wanting a specific look should set colors/fonts
directly in `layout` rather than via a named template. This constraint
is called out in the documentation.

`_trace_data(value, trace_type)` gets a new first branch:

```python
def _trace_data(value, trace_type):
    if trace_type == "figure":
        return _figure_json(value)
    ...  # existing dict / positional-tuple logic, unchanged
```

This is the only change needed in `render_plot` — the existing
single-function path (`len(grids) == 1`) already assigns
`_trace_data(...)`'s return value per grid key, so a figure's
`{"data": [...], "layout": {...}}` dict flows through unchanged from
there.

### `transform.py`

No changes. The single-function code path already does the right thing
once `_trace_data` handles `trace_type == "figure"`. The multi-function
combining path is simply never given a defined meaning for figure mode
— no guard is added for `:data: f1,f2` + `figure`.

### `runtime.js`

`draw()` gets one new branch, checked before the existing trace-building
logic:

```javascript
function draw() {
  const data = currentData();
  if (traceType === 'figure') {
    const layout = Object.assign({ autosize: true }, data.layout);
    Plotly.react(plotEl, data.data, layout, { responsive: true });
    return;
  }
  // ... existing behavior, unchanged
}
```

`data.data` is used as the traces array as-is (each trace already
carries its own Plotly `type`); layout defaults to `autosize: true` but
the figure's own layout wins on any key it sets (including its own
`width`/`height`/`autosize`, if the calc function wants to opt out of
autosizing). No `barmode` special-casing — that logic is bar-specific
and untouched.

## Testing

- `tests/test_render.py` (or wherever `_trace_data`/`render_plot` are
  currently tested): a calc function returning a plain
  `{"data": [...], "layout": {...}}` dict flows through
  `render_plot`/`transform_document` end-to-end with no plotly installed.
- A test gated on plotly actually being importable
  (`pytest.importorskip`) that builds a real `go.Figure` and confirms
  `_figure_json`'s result has no `layout.template` key and contains the
  expected clean trace/layout data.
- `_trace_data` raising `TypeError` for an unrecognized return value in
  figure mode (e.g. a plain tuple, which has no defined meaning here).
- Existing trace-type tests (`scatter`, `bar`, `pie`, etc.) continue to
  pass unmodified — `trace_type != "figure"` behavior is untouched.

## Documentation

- `docs/guide/outputs.md`: new "Full Plotly figures" section (after the
  existing trace-type sections) covering the `{plot} figure` syntax, a
  worked example building a `go.Figure` with a title, axis labels, and
  an annotation, and a short note that a plain
  `{"data": [...], "layout": {...}}` dict works too, without plotly
  installed.
- `docs/installation.md`: one line noting
  `pip install myst-baker[plotly]` / `uv add "myst-baker[plotly]"` for
  figure-mode support.
- `docs/changelog.md`: entry for the new feature, matching the existing
  pattern in that file.

## Open questions

None — this is a self-contained addition. It doesn't change precompute
semantics, the existing trace-type/positional-tuple path, or any
non-figure directive behavior.
