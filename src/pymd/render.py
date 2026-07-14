import json
import uuid


CDN_TWEAKPANE = "https://cdn.jsdelivr.net/npm/tweakpane@4/dist/tweakpane.min.js"
CDN_PLOTLY = "https://cdn.plot.ly/plotly-2.35.2.min.js"

with open(__file__.replace("render.py", "static/runtime.js")) as _f:
    RUNTIME_JS = _f.read()


def render_plot(plot_node, grid_result, input_specs):
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
    """
    container_id = f"pymd-plot-{uuid.uuid4().hex[:8]}"
    trace_type = plot_node["arg"]
    trace_options = {
        k: v for k, v in plot_node["options"].items() if k not in ("data",)
    }

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
    # `pymdInitPlot` could otherwise run before the import finishes; Plotly's CDN
    # build, by contrast, *is* a real UMD bundle (verified: it's wrapped in
    # `!function(t,e){"object"==typeof exports...}`, attaching `window.Plotly`
    # synchronously), so it's safe to keep as a plain classic `<script src>`
    # loaded before the module script.
    return f"""<!doctype html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0">
<div id="{container_id}"></div>
<script src="{CDN_PLOTLY}"></script>
<script type="module">
import {{ Pane }} from "{CDN_TWEAKPANE}";
window.Tweakpane = {{ Pane }};
{RUNTIME_JS}
pymdInitPlot(
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
