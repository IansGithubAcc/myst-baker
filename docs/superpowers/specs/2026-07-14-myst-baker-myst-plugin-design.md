# myst-baker: Precomputed Interactive Docs via a MyST Executable Plugin

## Concept

A documentation authoring layer, built as a MyST executable plugin, where markdown fences declare input widgets, Python calculation functions, and output blocks (plots, tables, etc.). At build time, myst-baker runs the calc functions over the full cartesian grid of possible input values and bakes the results into the page as JSON. The published site is fully static: moving a slider is a JSON key lookup plus a plot update in JS. No server, no live Python kernel, hostable anywhere static files are served.

## Why MyST (Route decision)

Three implementation routes were considered: a standalone tool (own parser/renderer, full control, most work), a MyST executable plugin (inherits MyST's theming, cross-refs, PDF export, and its existing Jupyter Book audience), and an Observable Framework preprocessor (best-in-class reactive client, but JS-centric and fights the "author never leaves Python" goal). **MyST was chosen** — we are adding tools to an existing, solid ecosystem rather than building one from scratch.

## Architecture

myst-baker is a Python script registered in `myst.yml` as a MyST **executable plugin**:

```yaml
project:
  plugins:
    - type: executable
      path: myst_baker_plugin.py
```

MyST invokes this script three ways, all AST-in/AST-out as JSON over stdin/stdout:
- no args → prints `PLUGIN_SPEC` (declares myst-baker's directives and a document-stage transform)
- `--directive <name>` → called once per block instance at parse time, turning a fenced block into a lightweight placeholder AST node carrying its options/body verbatim (no computation yet)
- `--transform document` → called once per page with the whole page AST. This is where the real work happens:
  1. Walk the AST, collect all `input-*` nodes (name → widget config), all calc-definition nodes (function name → source), all `plot` nodes (which function they reference, which Plotly trace type)
  2. Execute the calc source into a shared namespace
  3. For each `plot` node, introspect its target function's signature to find which input(s) it depends on — the signature is the single source of truth, no separate declaration of which inputs a plot uses
  4. Build the cartesian product of the matched inputs' values, call the function once per combination, collect results
  5. Serialize results to JSON keyed by joined stringified input values (e.g. `"3"` for one input, `"3|7"` for two)
  6. Replace each `plot` placeholder node with a raw-HTML node containing: the widget elements, a plot container `<div>`, the JSON inlined in a `<script type="application/json">` tag, and a `<script>` wiring Plotly + our runtime JS

Because this transform runs as a normal step inside MyST's own build, `myst start`'s existing file-watcher and live-reload pick it up automatically — no custom dev server is needed.

## Chosen libraries

- **Widget library: Tweakpane** — small, actively maintained (241k weekly downloads), good plugin ecosystem, purpose-built for parameter panels.
- **Plotting library: Plotly.js** — chosen for MVP for its breadth of chart types (relevant for likely future engineering-style outputs: contours, heatmaps, 3D surfaces) and its purpose-built update-in-place API (`Plotly.react`). Heaviest of the candidates considered (~3.6MB), but CDN-cached. **This choice is explicitly revisitable** if it doesn't work well in practice.
- These two libraries are **decoupled** from each other (Option B from the brainstorm): the widget layer and the plotting layer are independent, glued together by myst-baker's own small runtime. This was chosen over a unified single-library approach (e.g. Vega-Lite's own param-binding) specifically because myst-baker's roadmap includes non-chart output kinds; a unified approach would only cover chart-shaped outputs and require a second mechanism for anything else anyway.

## Directive syntax (illustrative, not settled)

MyST directives take a name, an optional argument, options (`:key: value` lines or a `---`-delimited YAML block), and a body. Two distinct patterns are used, chosen per side based on the shape of the underlying library's own vocabulary:

- **Inputs use explicit per-kind directive names** (`input-slider`, `input-dropdown`, `input-checkbox`, ...), because Tweakpane's control vocabulary is small, stable, and *inferred* from a combination of the bound value's type and the options given — not from an explicit type keyword. Naming the kind directly in the directive keeps the control kind visible in the source rather than requiring a reader to infer it from which options happen to be present.
- **Plots use a single generic `plot` directive whose argument is Plotly's own trace-type string** (`scatter`, `bar`, `heatmap`, `surface`, ...), because Plotly already has a large, stable, self-documenting vocabulary of trace types. Options forward near-verbatim into that trace's own config fields. This means every Plotly trace type is available without myst-baker maintaining a directive per chart type.

Illustrative example (**not a locked design** — see the open question below):

````markdown
```{input-slider} a
:value: 5
:min: 0
:max: 10
:step: 1
```

```{calc-python}
def get_plot_data(a: int):
    x = list(range(10))
    y = [a * xi for xi in x]
    return x, y
```

```{plot} scatter
:data: get_plot_data
:mode: lines
```
````

## Precompute engine

- Walks the page AST for any `input-*` node and any `plot` node (any trace-type argument) — the matching-by-function-signature logic is the same regardless of which input kind or which Plotly trace type is involved.
- For each `plot` node: match its function's parameters to `input-*` nodes by name, build the cartesian grid, call the function once per combination, serialize to JSON keyed by joined stringified input values.
- **Combinatorial budget guard**: before running anything, compute the total grid size (product of each input's value count). If it exceeds a threshold, fail the build with a clear error naming the offending block and the combo count. The threshold has a default but is configurable via an argument — no silent truncation.
- No bespoke error handling beyond the budget guard: Python exceptions during grid execution propagate naturally and crash the build; unresolved references (missing function, unmatched parameter) error out via normal Python error paths. This is a deliberate simplicity choice — the build-time-only nature of the pipeline means there's no runtime failure mode to protect against, so there's no need to catch and reformat errors that already fail loudly.

## Client runtime

Per page, the document-transform emits one `<script type="application/json">` block per `plot` node containing its precomputed grid, plus a shared inline `<script>` runtime (~50 lines) that:

1. On load, initializes a Tweakpane `Pane` and registers one binding per `input-*` node, using that node's forwarded options.
2. On any binding's `change` event, re-derives the lookup key from the current values of that plot's dependent inputs and looks up the matching precomputed entry.
3. Calls `Plotly.react(plotDiv, [trace], layout)` with the looked-up data.

Tweakpane and Plotly are pulled from CDN `<script>` tags; the runtime itself is inlined rather than shipped as a separate asset file for now — no build-time JS bundling step. Revisit bundling if page weight becomes a problem.

## Testing

Two layers:
1. **Build-time (Python)**: feed a small fixture page through the plugin's document-transform, assert on the resulting AST/HTML (grid computed correctly, budget check fires when expected, signature-matching resolves correctly).
2. **Browser-level (Playwright)**: build the fixture page for real via `myst build`, load the output HTML in a real browser, move the slider, and assert no console errors/exceptions are logged and the plot's data visibly updates. This is the actual end-to-end proof that precompute → lookup → `Plotly.react` works in practice, not just that the Python logic produces plausible JSON.

## Scope

**Architecture supports, automatically, with no dedicated build-out required:**
- Any Tweakpane input kind (slider, dropdown, checkbox, color, text, ...) — each is just another directive name pointed at the same generic Tweakpane-forwarding handler
- Any Plotly output type — whatever Plotly itself supports (charts, tables, images, annotations, ...) — via the same generic `{plot} <type>` pass-through

**MVP demo/test target** (what gets built and exercised first — not a hard boundary the architecture enforces):
- One page, one `input-slider`, one calc block, one `{plot} scatter`

**Excluded by decision, not "later":**
- Inline prose calc values (e.g. `` {calc}`f(a)` ``) — never part of the plan

**Decided at implementation time, based on actual difficulty:**
- Continuous/non-grid inputs — include if a simple interpolation-based approach turns out easy, drop if it proves hard
- Inline JSON vs. sidecar JSON files — a storage choice made once real payload sizes are seen, not decided up front

**Open design question — not deferred, must be actively resolved during implementation planning:**
- The `calc-python` block, and the whole "author writes a Python function, a plot block names it by string" model, is a rough illustrative draft only. Implementation should determine the actual best design, which may look nothing like what's shown in this doc.
