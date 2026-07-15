import base64
import inspect
import re

from pymd import precompute, render

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


_CALC_FENCE_RE = re.compile(r"^(?P<lang>\w+)\{calc\}$")


def _calc_fence_lang(node):
    """Return the declared language of a `<lang>{calc}` code fence, or
    `None` if this code node isn't a calc fence at all.

    mdast splits a fence's info string on the first whitespace: `lang`
    gets everything before it, `meta` everything after. With no space in
    `python{calc}`, the whole string lands in `lang` and `meta` is empty;
    with a space (`python {calc}`), `lang` is `python` and `meta` is
    `{calc}`. Concatenating them back reconstructs the original info
    string either way.
    """
    info = (node.get("lang") or "") + (node.get("meta") or "")
    match = _CALC_FENCE_RE.match(info)
    return match.group("lang") if match else None


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
        elif node_type == "code":
            calc_lang = _calc_fence_lang(node)
            if calc_lang is not None:
                if calc_lang != "python":
                    raise ValueError(
                        f"calc block declares language {calc_lang!r}, but "
                        f"only 'python' calc blocks are supported"
                    )
                exec(node["value"], calc_namespace)

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

    CORRECTED (found by reading the book-theme's bundled iframe renderer,
    `chunk-RUUCG5OS.js`): that renderer ignores any `style` we put on the
    iframe mdast node entirely -- it hardcodes the iframe's own style
    (`width/height:100%; position:absolute`) and wraps it in a `div` sized by
    `padding-bottom:60%` of the div's *width* (a fixed 5:3 aspect-ratio box),
    capped at the page's content width. So there is no way to request a
    taller box through this node; only `width` (parsed by the renderer's
    `WE()`) affects sizing, and it's already maxed at "100%". The content
    rendered inside the iframe must instead fit whatever height that
    aspect-ratio box works out to -- see the flex layout in render.py/
    runtime.js, which makes the Plotly chart resize to fill it exactly
    instead of assuming a fixed pixel height.
    """
    data_uri = "data:text/html;base64," + base64.b64encode(html.encode("utf-8")).decode("ascii")
    return {
        "type": "iframe",
        "src": data_uri,
        "width": "100%",
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
            _INPUT_CLIENT_SPECS[input_nodes[name]["type"]](name, input_nodes[name])
            for name in inspect_params(func)
            if name in input_nodes
        ]
        html = render.render_plot(plot_node, grid_result, input_specs)
        return _iframe_node(html)

    return _replace_plots(ast, replace_plot)
