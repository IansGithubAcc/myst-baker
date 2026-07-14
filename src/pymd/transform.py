import base64
import inspect

from pymd import precompute, render

# Height of the iframe embedding each plot. mystmd's reconstructed "iframe"
# mdast node honors an inline `style` dict (verified against a real `myst
# build`: typing `<iframe ... style="height:450px">` directly in markdown
# round-trips to `{"type": "iframe", ..., "style": {"height": "450px"}}`), so
# we can size the iframe to comfortably fit the Tweakpane controls above the
# Plotly chart.
IFRAME_HEIGHT = "600px"


def inspect_params(func):
    return list(inspect.signature(func).parameters)


def _iter_nodes(node):
    """Depth-first walk over every mdast node in the tree, including `node` itself.

    CORRECTED (verified against real `myst build --debug`): real mystmd wraps
    top-level content in an intermediate "block" node -- the document root's
    `children` is `[{"type": "block", "children": [<our pymd-* nodes>]}]`, not
    a flat list of the pymd-* nodes directly. Scanning only `ast["children"]`
    (as this function originally did) never found any pymd nodes at all in a
    real build, so the transform silently no-op'd (no error, but the plot
    directive was never replaced with rendered HTML). Recursing into
    `children` at any depth fixes this while remaining correct for the flat
    ASTs used in the unit tests.
    """
    yield node
    for child in node.get("children") or []:
        yield from _iter_nodes(child)


def _collect_nodes(ast):
    inputs = {}
    input_nodes = {}
    calc_namespace = {}

    for node in _iter_nodes(ast):
        node_type = node.get("type")
        if node_type == "pymd-input-slider":
            name = node["arg"]
            options = node["options"]
            inputs[name] = (options["min"], options["max"], options["step"])
            input_nodes[name] = node
        elif node_type == "pymd-calc-python":
            exec(node["body"], calc_namespace)

    return inputs, input_nodes, calc_namespace


def _replace_plots(node, replace_plot):
    """Return a copy of `node` with every descendant `pymd-plot` node (at any
    depth) replaced by `replace_plot(plot_node)`. See `_iter_nodes` for why
    this needs to recurse rather than only look at the immediate children.
    """
    children = node.get("children")
    if children is None:
        return node

    new_children = []
    for child in children:
        if child.get("type") == "pymd-plot":
            new_children.append(replace_plot(child))
        else:
            new_children.append(_replace_plots(child, replace_plot))
    return {**node, "children": new_children}


def _iframe_node(html):
    """Wrap a standalone HTML document as a `data:` URI iframe mdast node.

    CORRECTED (verified against real `myst build`/`myst start` + a headless
    browser): the original design embedded the rendered widget/plot HTML
    (including `<script>` tags loading Tweakpane/Plotly from CDN and wiring
    up the runtime) as `{"type": "html", "value": html}`. That never actually
    ran: mystmd's book-theme site renderer only executes raw HTML that its
    parser could reconstruct into typed mdast nodes (things like `<div>`,
    `<b>`, `<iframe>`); anything it can't reconstruct -- notably `<script>`,
    confirmed by typing a literal `<script>` tag directly in a markdown
    fixture and observing it round-trip to the same `{"type": "html", ...}`
    node type -- is kept as a raw "html" node and rendered as inert, HTML
    escaped *text* client-side (this is a deliberate XSS boundary: arbitrary
    scripts from page content must never execute in the parent document).
    There is no config flag to disable this; it is not a bug in mystmd.

    `<iframe>` tags, by contrast, *are* reconstructed into a real mdast
    `iframe` node and rendered as an actual `<iframe>` element, and a `data:`
    URI `src` executes the embedded document's own `<script>` tags normally
    (in the iframe's own document/origin, verified with Playwright: a
    `data:text/html;base64,...` iframe's `body.innerText` reflects content
    that only exists after script execution). So the plot's rendered HTML is
    now embedded this way instead.
    """
    data_uri = "data:text/html;base64," + base64.b64encode(html.encode("utf-8")).decode("ascii")
    return {
        "type": "iframe",
        "src": data_uri,
        "width": "100%",
        "style": {"height": IFRAME_HEIGHT, "border": "none"},
    }


def transform_document(ast):
    inputs, input_nodes, calc_namespace = _collect_nodes(ast)

    def replace_plot(plot_node):
        function_name = plot_node["options"]["data"]
        if function_name not in calc_namespace:
            raise NameError(
                f"plot block references '{function_name}', which is not "
                f"defined by any calc-python block on this page."
            )
        func = calc_namespace[function_name]
        grid_result = precompute.compute_grid(func, inputs)

        input_specs = [
            {
                "name": name,
                "value": input_nodes[name]["options"]["value"],
                "min": input_nodes[name]["options"]["min"],
                "max": input_nodes[name]["options"]["max"],
                "step": input_nodes[name]["options"]["step"],
            }
            for name in inspect_params(func)
            if name in input_nodes
        ]
        html = render.render_plot(plot_node, grid_result, input_specs)
        return _iframe_node(html)

    return _replace_plots(ast, replace_plot)
