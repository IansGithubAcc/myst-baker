# Optional Plotly Figure-Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a `plot` block's calc function return a full Plotly figure
(a real `plotly.graph_objects`/`plotly.express` figure, or a hand-written
`{"data": [...], "layout": {...}}` dict) instead of a single trace's
fields, via a new reserved `` ```{plot} figure `` argument — giving full
control over titles, axis labels, tick formatting, annotations, and
multi-trace layouts. plotly becomes an optional extra,
`myst-baker[plotly]`.

**Architecture:** `figure` is a reserved value for the `plot` directive's
existing `arg` (today always a Plotly trace type). `render.py`'s
`_trace_data` gets a new branch for `trace_type == "figure"` that calls a
new `_figure_json` helper: it serializes a real figure object via
`plotly.io.to_json` (imported lazily, only when one is actually
encountered — myst-baker never hard-imports plotly), or passes a plain
dict through unchanged. No changes to `precompute.py` or
`transform.py` — the existing single-function grid path already assigns
whatever `_trace_data` returns per grid key. `runtime.js`'s `draw()`
gets one new branch: when `traceType === 'figure'`, use the grid entry's
`data` array as traces as-is and its `layout` merged over the default
`{autosize: true}`, instead of the existing per-trace
`Object.assign({type: traceType}, d, traceOptions)` merge.

**Tech Stack:** Python 3, pytest, plotly (optional). No client-side test
runner exists — `runtime.js` is only verified through the existing
Playwright browser tests against a real `myst build` output.

## Global Constraints

- myst-baker itself must never hard-import plotly at module load time —
  only lazily, inside `_figure_json`, when a figure-like object is
  actually encountered. plotly must stay a true optional dependency (see
  `docs/superpowers/specs/2026-07-20-plotly-figure-mode-design.md`).
- `_figure_json` **must** strip `layout.template` from a real figure's
  serialized JSON, unconditionally. Verified empirically: `pio.to_json`
  on a two-point scatter figure with just a title serializes to 6724
  bytes; the same figure with `fig.layout.template = None` set first
  serializes to 91 bytes — `pio.to_json` always resolves and inlines the
  full default theme (colorscales for every trace kind, not just the
  ones used) into every figure's layout. Since this gets baked once per
  precomputed grid combination, leaving it in would multiply that
  redundant weight by every input value on the page. Every myst-baker
  page already loads real Plotly.js from a pinned CDN version, whose own
  built-in defaults render identically without an explicit template, so
  dropping the key costs nothing visually. See the design spec's
  "CORRECTED" note for the full reasoning and its documented
  consequence (named non-default themes, e.g. `template="plotly_dark"`,
  are not preserved — authors wanting a specific look should set
  colors/fonts directly in `layout`).
- `:data:` in figure mode names exactly one calc function; `:mode:` (and
  any other non-`data` directive option) is ignored entirely in figure
  mode. Combining multiple figure-returning functions in one `:data:`
  list is not a supported combination — no special guard/error is added
  for it (per the design decision), it's simply undocumented.
- No changes to `precompute.py` or `transform.py`.
- Every existing test must keep passing unmodified except the one
  Playwright iframe-count assertion that's expected to change (Task 2).

---

### Task 1: Figure-mode JSON conversion (`render.py`) + optional dependency

**Files:**
- Modify: `pyproject.toml` (add `[project.optional-dependencies]` and a
  dev-group addition)
- Modify: `src/myst_baker/render.py:22-31` (`_trace_data`)
- Modify: `src/myst_baker/directives.py:52` (`PLOT_DIRECTIVE`'s `arg` doc)
- Test: `tests/test_render.py`, `tests/test_transform.py`

**Interfaces:**
- Produces: `_figure_json(value) -> dict` (new). `_trace_data(value,
  trace_type) -> dict` keeps its existing signature; for
  `trace_type == "figure"` it now returns `_figure_json(value)` instead
  of raising.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_render.py` (it already imports `pytest` and
`_trace_data`, `TRACE_FIELDS` from `myst_baker.render`):

```python
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
```

Append to `tests/test_transform.py` (it already defines `_page_ast`,
`_calc_node`, `_decode_iframe_html`, `_decode_plot_call_args` — reuse
them as-is):

```python
def test_transform_document_supports_figure_mode_with_plain_dict_return():
    input_node = {
        "type": "myst-baker-input-slider",
        "arg": "offset",
        "options": {"value": 0, "min": 0, "max": 1, "step": 1},
        "body": "",
    }
    calc_node = _calc_node(
        "def make_figure(offset):\n"
        "    return {'data': [{'type': 'scatter', 'x': [0, 1], 'y': [offset, offset + 1]}], "
        "'layout': {'title': {'text': 'Example'}}}\n"
    )
    plot_node = {
        "type": "myst-baker-plot",
        "arg": "figure",
        "options": {"data": "make_figure"},
        "body": "",
    }

    result = transform_document(_page_ast(input_node, calc_node, plot_node))

    html = _decode_iframe_html(result["children"][-1])
    _, _, grid, trace_type, _ = _decode_plot_call_args(html)

    assert trace_type == "figure"
    assert grid["0"] == {
        "data": [{"type": "scatter", "x": [0, 1], "y": [0, 1]}],
        "layout": {"title": {"text": "Example"}},
    }
    assert grid["1"] == {
        "data": [{"type": "scatter", "x": [0, 1], "y": [1, 2]}],
        "layout": {"title": {"text": "Example"}},
    }
```

- [ ] **Step 2: Run the tests to verify the expected failures**

Run: `uv run pytest tests/test_render.py tests/test_transform.py -k "figure" -v`

Expected:
- `test_trace_data_passes_figure_dict_through_unchanged` **PASSES**
  already (no code change needed for a plain dict — noted above).
- `test_trace_data_raises_type_error_for_invalid_figure_return` **FAILS**
  — today's code raises `ValueError` (`"plot type 'figure' has no known
  positional field order..."`) instead of `TypeError`.
- `test_trace_data_serializes_real_plotly_figure_and_strips_default_template`
  **FAILS** — a `go.Figure` isn't a `dict`, and `"figure"` isn't in
  `TRACE_FIELDS`, so today's code raises `ValueError`.
- `test_transform_document_supports_figure_mode_with_plain_dict_return`
  **FAILS** — same `ValueError`, surfacing through the full
  `transform_document` pipeline instead of directly through
  `_trace_data`.

- [ ] **Step 3: Implement `_figure_json` and the `_trace_data` branch**

In `src/myst_baker/render.py`, replace the existing `_trace_data`
function (`render.py:22-31`) with:

```python
def _figure_json(value):
    if hasattr(value, "to_plotly_json"):
        import plotly.io as pio

        result = json.loads(pio.to_json(value))
        result.get("layout", {}).pop("template", None)
        return result
    if isinstance(value, dict):
        return value
    raise TypeError(
        f"calc function for a `{{plot}} figure` block must return a plotly "
        f"figure or a {{'data': [...], 'layout': {{...}}}} dict, got {type(value)!r}"
    )


def _trace_data(value, trace_type):
    if trace_type == "figure":
        return _figure_json(value)
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

(`render.py` already has `import json` at the top — no new top-level
import needed; `plotly.io` is imported lazily inside `_figure_json`.)

- [ ] **Step 4: Run the tests again to verify the render.py/transform.py cases pass**

Run: `uv run pytest tests/test_render.py tests/test_transform.py -k "figure" -v`

Expected:
- `test_trace_data_passes_figure_dict_through_unchanged` PASSES (still).
- `test_trace_data_raises_type_error_for_invalid_figure_return` PASSES.
- `test_transform_document_supports_figure_mode_with_plain_dict_return`
  PASSES.
- `test_trace_data_serializes_real_plotly_figure_and_strips_default_template`
  **SKIPPED** (plotly isn't installed in the dev environment yet — fixed
  in the next step).

- [ ] **Step 5: Add the `plotly` optional extra and dev dependency**

In `pyproject.toml`, insert a new table right after the `dependencies`
list (before `[project.urls]`):

```toml
[project.optional-dependencies]
plotly = ["plotly>=5"]
```

Then update the `[dependency-groups]` `dev` list to include plotly (so
the gated test above actually runs, rather than skips, for contributors
and CI):

```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-playwright>=0.5",
    "plotly>=5",
]
```

Run: `uv sync`

Expected: `uv.lock` updates and plotly installs into `.venv`.

- [ ] **Step 6: Run the full render/transform test files to verify the previously-skipped test now passes**

Run: `uv run pytest tests/test_render.py tests/test_transform.py -v`

Expected: PASS for every test in both files, including
`test_trace_data_serializes_real_plotly_figure_and_strips_default_template`
(no longer skipped) and every pre-existing test (trace-type field
mapping, all `transform_document` behaviors from prior features).

- [ ] **Step 7: Update the `plot` directive's argument doc**

In `src/myst_baker/directives.py`, change the `PLOT_DIRECTIVE`'s `arg`
entry (currently `"arg": {"type": "string", "doc": "Plotly trace
type"},`, `directives.py:52`) to:

```python
    "arg": {
        "type": "string",
        "doc": (
            "Plotly trace type (e.g. scatter), or 'figure' for a full "
            "custom Plotly figure returned by the calc function"
        ),
    },
```

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock src/myst_baker/render.py src/myst_baker/directives.py tests/test_render.py tests/test_transform.py
git commit -m "$(cat <<'EOF'
feat: support {plot} figure for full custom Plotly figures

A calc function can now return a complete plotly figure (or a plain
{data, layout} dict) instead of a single trace's fields, giving full
control over titles, axis labels, tick formatting, and annotations.
plotly becomes an optional extra, myst-baker[plotly]. The resolved
default theme is stripped from serialized figures -- verified it
otherwise multiplies ~75x per baked grid combination for no visual
benefit, since every page already loads real Plotly.js.
EOF
)"
```

---

### Task 2: Client-side figure rendering + worked example + browser verification

**Files:**
- Modify: `src/myst_baker/static/runtime.js:50-64` (`draw`)
- Modify: `docs/guide/outputs.md` (new "Full Plotly figures" section)
- Modify: `tests/test_e2e_browser.py`

**Interfaces:**
- Consumes: the `"figure"` trace-type grid shape produced by Task 1's
  `_trace_data`/`_figure_json` (`{"data": [...], "layout": {...}}` per
  grid key).
- Produces: nothing consumed by other tasks — this is the final
  user-visible half of the feature.

- [ ] **Step 1: Add the figure-mode branch to `runtime.js`'s `draw()`**

In `src/myst_baker/static/runtime.js`, replace the `draw()` function
(currently `runtime.js:50-64`) with:

```javascript
  function draw() {
    const data = currentData();
    if (traceType === 'figure') {
      // A full figure already carries its own per-trace `type` and a
      // complete `layout` (see render.py's _figure_json) -- no
      // type/traceOptions merge here, unlike the trace-building path
      // below; the whole point of figure mode is that the calc function
      // has full control.
      const layout = Object.assign({ autosize: true }, data.layout);
      Plotly.react(plotEl, data.data, layout, { responsive: true });
      return;
    }
    // A single combined `calc` function's grid entry is a bare object (see
    // render.py); combining several into one plot makes it an array, one
    // trace object per function. Normalizing here keeps a single draw path
    // for both shapes instead of branching the whole function in two.
    const traces = (Array.isArray(data) ? data : [data]).map((d) =>
      Object.assign({ type: traceType }, d, traceOptions)
    );
    const layout = { autosize: true };
    if (traceType === 'bar' && traces.length > 1) {
      layout.barmode = 'group';
    }
    Plotly.react(plotEl, traces, layout, { responsive: true });
  }
```

- [ ] **Step 2: Add the worked example to `docs/guide/outputs.md`**

Append this new section to the end of `docs/guide/outputs.md` (after
the existing "Box and violin plots" section). Note the fencing here
matches the file's existing convention exactly (compare to the "One
dataset, three scatter modes" section near the top of the file): prose
and the `{warning}` directive sit unwrapped as real markdown; only the
raw-source demonstration is wrapped once in a 4-backtick fence (using
literal triple-backtick lines as plain text inside it), immediately
followed by the same trio unwrapped so MyST parses it for real and
renders a live plot.

The content inside the fence below tops out at 4 backticks (the nested
raw-source demo), so it's wrapped here in 5 backticks purely so this
plan step itself renders unambiguously — the 5-backtick fence is not
part of what gets pasted into `outputs.md`; everything *between* it is.

`````markdown

## Full Plotly figures

Every trace type above hands `plot` a single calc function whose return
value is spread into one trace, with `plot`'s argument naming that
trace's Plotly type. For full control over the chart — axis titles,
tick formatting, annotations, or several differently-typed traces on
one plot — give `plot` the reserved argument `figure` instead of a
trace type, and have its calc function return a complete figure rather
than a single trace's fields.

```{warning}
Figure mode only needs the optional `plotly` extra
(`pip install myst-baker[plotly]` / `uv add "myst-baker[plotly]"`) if
the calc function builds a real `plotly.graph_objects`/`plotly.express`
figure. A calc function can also return a plain
`{"data": [...], "layout": {...}}` dict by hand instead, with no extra
install required.
```

A `figure` block's calc function isn't combinable with others —
`:data:` names exactly one function — and `:mode:` (or any other
directive option) is ignored, since the figure already fully specifies
its own styling.

````md
```{input-slider} phase
:value: 0
:min: -3
:max: 3
:step: 0.25
```

```python{calc}
import math
import plotly.graph_objects as go

def phase_shifted_wave(phase):
    x = list(range(-10, 11))
    y = [math.sin(xi / 3 + phase) for xi in x]
    fig = go.Figure(data=[go.Scatter(x=x, y=y, mode="lines")])
    fig.update_layout(
        title="Phase-shifted wave",
        xaxis_title="x",
        yaxis_title="sin(x/3 + phase)",
        annotations=[
            dict(x=0, y=y[10], text=f"phase = {phase:.2f}", showarrow=True, arrowhead=2)
        ],
    )
    return fig
```

```{plot} figure
:data: phase_shifted_wave
```
````

```{input-slider} phase
:value: 0
:min: -3
:max: 3
:step: 0.25
```

```python{calc}
import math
import plotly.graph_objects as go

def phase_shifted_wave(phase):
    x = list(range(-10, 11))
    y = [math.sin(xi / 3 + phase) for xi in x]
    fig = go.Figure(data=[go.Scatter(x=x, y=y, mode="lines")])
    fig.update_layout(
        title="Phase-shifted wave",
        xaxis_title="x",
        yaxis_title="sin(x/3 + phase)",
        annotations=[
            dict(x=0, y=y[10], text=f"phase = {phase:.2f}", showarrow=True, arrowhead=2)
        ],
    )
    return fig
```

```{plot} figure
:data: phase_shifted_wave
```
`````

Everything from `## Full Plotly figures` through the final closing
` ```` ` above is what gets appended to `outputs.md`, exactly as shown.

- [ ] **Step 3: Build the docs and confirm the new example renders**

Run: `uv run myst build --html`

Expected: build succeeds with no errors. If it fails, read the error —
a common cause would be a typo in the fenced example above; fix it and
rebuild before continuing.

- [ ] **Step 4: Update the existing iframe-count assertion**

In `tests/test_e2e_browser.py`, `test_new_output_types_render_with_no_console_errors`
currently has this comment and assertion:

```python
    # docs/guide/outputs.md's live plots, in document order: 3 scatter-mode
    # plots, 1 bar, 1 combined-trace bar (revenue + expenses), 1 histogram,
    # 1 pie, 1 box, 1 violin = 9 total. Confirmed empirically against the
    # built page (including each trace's `.type`) rather than assumed from
    # document structure alone.
    iframe_count = page.locator("iframe").count()
    assert iframe_count == 9
```

Replace it with:

```python
    # docs/guide/outputs.md's live plots, in document order: 3 scatter-mode
    # plots, 1 bar, 1 combined-trace bar (revenue + expenses), 1 histogram,
    # 1 pie, 1 box, 1 violin, 1 figure-mode (phase-shifted wave) = 10 total.
    # Confirmed empirically against the built page (including each trace's
    # `.type`) rather than assumed from document structure alone.
    iframe_count = page.locator("iframe").count()
    assert iframe_count == 10
```

- [ ] **Step 5: Add a browser test for the figure-mode plot**

Append to `tests/test_e2e_browser.py`:

```python
def test_figure_mode_plot_renders_layout_and_updates(outputs_page_url, page):
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page_errors = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    page.goto(outputs_page_url)

    # The "Full Plotly figures" example is the 10th (last) iframe on the
    # page -- see the updated count/order comment on
    # test_new_output_types_render_with_no_console_errors above.
    plot_frame = page.frame_locator("iframe").nth(9)
    plot_locator = plot_frame.locator(".js-plotly-plot").first
    plot_locator.wait_for(state="visible")

    # The calc function's own layout (title, axis titles, annotation) must
    # have made it all the way through _figure_json/runtime.js's figure
    # branch -- not just a bare, unstyled trace.
    title_text = plot_locator.evaluate("el => el.layout.title.text")
    assert title_text == "Phase-shifted wave"
    assert plot_locator.evaluate("el => el.layout.annotations.length") == 1

    before = plot_locator.evaluate("el => el.data[0].y.slice(0, 3)")

    slider_input = plot_frame.locator(".tp-rotv input[type='text']").first
    slider_input.fill("1")
    slider_input.press("Enter")

    page.wait_for_timeout(300)

    after = plot_locator.evaluate("el => el.data[0].y.slice(0, 3)")

    assert before != after
    assert console_errors == []
    assert page_errors == []
```

- [ ] **Step 6: Run the browser test suite to verify everything passes**

Run: `uv run pytest tests/test_e2e_browser.py -v`

Expected: PASS for all tests, including the updated iframe-count
assertion (now 10) and the new `test_figure_mode_plot_renders_layout_and_updates`.
If the iframe count or the frame index (`nth(9)`) doesn't match reality,
run with `-v` and adjust both the assertion and the docstring/comment to
match the actual built page rather than guessing again.

- [ ] **Step 7: Commit**

```bash
git add src/myst_baker/static/runtime.js docs/guide/outputs.md tests/test_e2e_browser.py
git commit -m "$(cat <<'EOF'
feat: render {plot} figure blocks in the browser runtime

runtime.js's draw() now recognizes the figure grid shape (a full
{data, layout} object per key) and passes it straight to Plotly.react
instead of merging trace type/options into it. Adds a worked example
(phase-shifted wave with a title, axis labels, and an annotation) to
the outputs guide, verified end-to-end with Playwright.
EOF
)"
```

---

### Task 3: Document the optional `plotly` extra and changelog entry

**Files:**
- Modify: `docs/installation.md`
- Modify: `docs/changelog.md`

**Interfaces:**
- Consumes: nothing (docs-only change).
- Produces: nothing consumed by other tasks.

- [ ] **Step 1: Document the extra in `docs/installation.md`**

Insert a new section right before the existing `## Developing this
repo` heading (currently the file's last section):

The inner shell-command blocks below are 3-backtick fences, so (as in
Task 2's Step 2) this is wrapped in 4 backticks purely so this plan
step itself renders unambiguously — that outer fence is not part of
what gets pasted into `installation.md`.

````markdown
## Optional: full Plotly figures

`{plot} figure` blocks (see the [outputs guide](guide/outputs.md)) let
a calc function build a complete Plotly figure instead of a single
trace. If it does so using `plotly.graph_objects` or `plotly.express`
directly, install the optional `plotly` extra alongside myst-baker:

```
uv add "myst-baker[plotly]"
```

or with `pip`:

```
pip install "myst-baker[plotly]"
```

This isn't required if a calc function instead returns a plain
`{"data": [...], "layout": {...}}` dict by hand.

## Developing this repo
````

(Only the `## Optional: full Plotly figures` section through its blank
line before `## Developing this repo` is new — the `## Developing this
repo` heading itself already exists and is shown only to anchor the
insertion point.)

- [ ] **Step 2: Add a changelog entry**

In `docs/changelog.md`, insert a new section above `## 0.1.0`:

```markdown
## Unreleased

### Added

- A `` `{plot} figure` `` mode for full custom Plotly figures: a calc
  function can return a complete `plotly.graph_objects`/`plotly.express`
  figure (via the optional `myst-baker[plotly]` extra) or a hand-written
  `{"data": [...], "layout": {...}}` dict, giving full control over
  titles, axis labels, tick formatting, annotations, and multi-trace
  layouts that trace-type-only `plot` blocks don't expose.

## 0.1.0
```

- [ ] **Step 3: Commit**

```bash
git add docs/installation.md docs/changelog.md
git commit -m "docs: document the optional plotly extra and figure mode"
```
