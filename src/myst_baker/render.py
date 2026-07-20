import json
import uuid


CDN_TWEAKPANE = "https://cdn.jsdelivr.net/npm/tweakpane@4/dist/tweakpane.min.js"
CDN_PLOTLY = "https://cdn.plot.ly/plotly-2.35.2.min.js"

with open(__file__.replace("render.py", "static/runtime.js")) as _f:
    RUNTIME_JS = _f.read()


TRACE_FIELDS = {
    "scatter": ("x", "y"),
    "bar": ("x", "y"),
    "box": ("x", "y"),
    "violin": ("x", "y"),
    "histogram": ("x",),
    "pie": ("labels", "values"),
}


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


def _prettify_trace_name(function_name):
    return function_name.replace("_", " ").capitalize()


def render_plot(plot_node, grids, input_specs):
    """Build a standalone HTML document for one plot block.

    CORRECTED (verified against real `myst build`/`myst start` + a headless
    browser, see transform.py for the full story): this used to return a bare
    `<div>`/`<script>` fragment meant to be embedded directly into the page via
    an mdast `{"type": "html", "value": ...}` node. That never executes in
    mystmd's book-theme site (SPA) renderer -- `<script>` tags are never run
    from mdast "html" nodes, by design (they're an XSS-sanitization boundary).
    This function now returns a *complete* HTML document, because the caller
    (transform.py) embeds it as the `srcdoc`/`src` of a real `<iframe>` node
    instead, which *does* execute scripts (in its own document/origin).

    `grids` is a list of `(function_name, grid_result)` pairs, one per
    `calc` function named in `:data:` (comma-separated for more than one).
    A single-function plot keeps today's flat `{key: {plotly fields}}` grid
    shape, byte-for-byte, so every pre-existing plot's rendered output is
    unaffected. Combining more than one function into one plot switches to
    `{key: [{plotly fields}, ...]}` -- one trace dict per function, in
    `:data:` order -- each defaulted with a `name` (derived from its
    function name) so Plotly's legend/hover can tell the traces apart;
    runtime.js normalizes both shapes into a trace list before drawing.
    """
    container_id = f"myst-baker-plot-{uuid.uuid4().hex[:8]}"
    trace_type = plot_node["arg"]
    trace_options = {
        k: v for k, v in plot_node["options"].items() if k not in ("data",)
    }
    if len(grids) == 1:
        _, single_grid = grids[0]
        grid_result = {
            key: _trace_data(value, trace_type) for key, value in single_grid.items()
        }
    else:
        grid_result = {}
        for key in grids[0][1]:
            traces = []
            for function_name, grid in grids:
                data = dict(_trace_data(grid[key], trace_type))
                data.setdefault("name", _prettify_trace_name(function_name))
                traces.append(data)
            grid_result[key] = traces

    # CORRECTED (verified against a real headless-browser run: `page.on("pageerror")`
    # reported "Unexpected token 'export'" followed by "Tweakpane is not defined"):
    # Tweakpane v4's CDN bundle (dist/tweakpane.min.js) is ESM-only -- it ends in
    # `export{...,kr as Pane,...}` -- there is no UMD/global build for v4 (v3 had
    # one; v4 dropped it, per Tweakpane's own docs, which show `<script
    # type="module">` + `import`). Loading it via a classic `<script src=...>` tag
    # (as this originally did) fails to parse, so `window.Tweakpane` is never
    # defined and `new Tweakpane.Pane(...)` throws. Fixed by loading it as an ES
    # module and assigning the imported `Pane` to `window.Tweakpane.Pane` so
    # runtime.js (which references the `Tweakpane.Pane` global, unchanged) still
    # works. This must all be one `<script type="module">` block: module scripts
    # are deferred (like `defer`), so a later *classic* script calling
    # `mystBakerInitPlot` could otherwise run before the import finishes; Plotly's CDN
    # build, by contrast, *is* a real UMD bundle (verified: it's wrapped in
    # `!function(t,e){"object"==typeof exports...}`, attaching `window.Plotly`
    # synchronously), so it's safe to keep as a plain classic `<script src>`
    # loaded before the module script.
    # The book-theme's iframe renderer forces this document's own iframe
    # element to a fixed height (a padding-bottom aspect-ratio box on the
    # embedding side; see transform.py's `_iframe_node` docstring), so there
    # is no fixed pixel height to aim for here. Instead the container fills
    # the iframe's viewport (100vh, which inside an iframe refers to the
    # iframe's own height) with a column flexbox: the Tweakpane controls take
    # their natural height and the Plotly div gets whatever is left, so
    # runtime.js can resize the chart to fit exactly instead of overflowing
    # into a scrollbar.
    return f"""<!doctype html>
<html>
<head><meta charset="utf-8">
<style>
/* Tweakpane's default theme is dark; retheme it to match mystmd's book-theme
   (verified against a real build: white page background, warm-gray/stone
   heading text #1c1917, gray-200 #e5e7eb borders, gray-600 #4b5563 secondary
   text, sans-serif UI font -- see kbd/border/heading computed styles) rather
   than clashing with it. Tweakpane v4 themes entirely through --tp-* custom
   properties (no JS theme option), so overriding them on :root reaches both
   the controls panel and any popup elements it appends straight to <body>.
   The default --tp-container-unit-size (20px) also reads visually small next
   to the page's normal text size, so it's bumped up along with the padding/
   spacing/value-width variables that scale alongside it, plus the .tp-rotv
   font-size, which Tweakpane hardcodes to 11px rather than exposing as a
   variable. */
:root {{
  --tp-base-background-color: #ffffff;
  --tp-base-shadow-color: rgba(0, 0, 0, 0.1);
  --tp-base-font-family: ui-sans-serif, system-ui, sans-serif;
  --tp-button-background-color: #f3f4f6;
  --tp-button-background-color-hover: #e5e7eb;
  --tp-button-background-color-focus: #e5e7eb;
  --tp-button-background-color-active: #d1d5db;
  --tp-button-foreground-color: #374151;
  --tp-container-background-color: #f9fafb;
  --tp-container-background-color-hover: #f3f4f6;
  --tp-container-background-color-focus: #f3f4f6;
  --tp-container-background-color-active: #e5e7eb;
  --tp-container-foreground-color: #374151;
  --tp-container-horizontal-padding: 8px;
  --tp-container-vertical-padding: 6px;
  --tp-container-unit-spacing: 6px;
  --tp-container-unit-size: 28px;
  --tp-groove-foreground-color: #e5e7eb;
  --tp-input-background-color: #f3f4f6;
  --tp-input-background-color-hover: #e5e7eb;
  --tp-input-background-color-focus: #e5e7eb;
  --tp-input-background-color-active: #d1d5db;
  --tp-input-foreground-color: #1c1917;
  --tp-label-foreground-color: #4b5563;
  --tp-monitor-background-color: #f3f4f6;
  --tp-monitor-foreground-color: #374151;
  --tp-blade-value-width: 200px;
}}
.tp-rotv {{
  font-size: 13px;
}}
</style>
</head>
<body style="margin:0">
<div id="{container_id}" style="display:flex;flex-direction:column;height:100vh;box-sizing:border-box"></div>
<script src="{CDN_PLOTLY}"></script>
<script type="module">
import {{ Pane }} from "{CDN_TWEAKPANE}";
window.Tweakpane = {{ Pane }};
{RUNTIME_JS}
mystBakerInitPlot(
  "{container_id}",
  {json.dumps(input_specs)},
  {json.dumps(grid_result)},
  "{trace_type}",
  {json.dumps(trace_options)}
);
</script>
</body>
</html>
"""
