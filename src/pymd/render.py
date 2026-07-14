import json
import uuid


CDN_TWEAKPANE = "https://cdn.jsdelivr.net/npm/tweakpane@4/dist/tweakpane.min.js"
CDN_PLOTLY = "https://cdn.plot.ly/plotly-2.35.2.min.js"

with open(__file__.replace("render.py", "static/runtime.js")) as _f:
    RUNTIME_JS = _f.read()


def render_plot(plot_node, grid_result, input_specs):
    container_id = f"pymd-plot-{uuid.uuid4().hex[:8]}"
    trace_type = plot_node["arg"]
    trace_options = {
        k: v for k, v in plot_node["options"].items() if k not in ("data",)
    }

    return f"""
<div id="{container_id}"></div>
<script src="{CDN_TWEAKPANE}"></script>
<script src="{CDN_PLOTLY}"></script>
<script>{RUNTIME_JS}</script>
<script>
pymdInitPlot(
  "{container_id}",
  {json.dumps(input_specs)},
  {json.dumps(grid_result)},
  "{trace_type}",
  {json.dumps(trace_options)}
);
</script>
"""
