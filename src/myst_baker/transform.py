import base64
import inspect
import re

from myst_baker import precompute, render

def inspect_params(func):
    return list(inspect.signature(func).parameters)


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
    "myst-baker-input-slider": _slider_precompute_spec,
    "myst-baker-input-checkbox": _checkbox_precompute_spec,
    "myst-baker-input-dropdown": _dropdown_precompute_spec,
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
    "myst-baker-input-slider": _slider_client_spec,
    "myst-baker-input-checkbox": _checkbox_client_spec,
    "myst-baker-input-dropdown": _dropdown_client_spec,
}


_CALC_FENCE_RE = re.compile(r"^(?P<lang>\w+)\{calc(?P<flags>(?::\w+)*)\}$")

_KNOWN_CALC_FLAGS = {"hide"}


def _calc_fence_match(node):
    """Return the regex match for a `<lang>{calc[:flag...]}` code fence's
    info string, or `None` if this code node isn't a calc fence at all.

    mdast splits a fence's info string on the first whitespace: `lang`
    gets everything before it, `meta` everything after. With no space in
    `python{calc}` or `python{calc:hide}`, the whole string lands in
    `lang` and `meta` is empty; with a space (`python {calc}`), `lang` is
    `python` and `meta` is `{calc}`. Concatenating them back reconstructs
    the original info string either way.
    """
    info = (node.get("lang") or "") + (node.get("meta") or "")
    return _CALC_FENCE_RE.match(info)


def _calc_fence_flags(match):
    return [flag for flag in match.group("flags").split(":") if flag]


def _is_hidden_calc_node(node):
    if node.get("type") != "code":
        return False
    match = _calc_fence_match(node)
    return match is not None and "hide" in _calc_fence_flags(match)


def _process_state_node(node, inputs, input_nodes, calc_namespace):
    """If `node` is an input or calc block, fold it into the mutable `inputs`/
    `input_nodes`/`calc_namespace` state (exec'ing calc source as needed).
    Every other node type is left untouched.
    """
    node_type = node.get("type")
    if node_type in _INPUT_PRECOMPUTE_SPECS:
        name = node["arg"]
        inputs[name] = _INPUT_PRECOMPUTE_SPECS[node_type](node)
        input_nodes[name] = node
    elif node_type == "code":
        match = _calc_fence_match(node)
        if match is not None:
            calc_lang = match.group("lang")
            if calc_lang != "python":
                raise ValueError(
                    f"calc block declares language {calc_lang!r}, but "
                    f"only 'python' calc blocks are supported"
                )
            for flag in _calc_fence_flags(match):
                if flag not in _KNOWN_CALC_FLAGS:
                    raise ValueError(
                        f"calc block declares unknown flag {flag!r}; "
                        f"recognized flags are {sorted(_KNOWN_CALC_FLAGS)}"
                    )
            exec(node["value"], calc_namespace)


def _rewrite_tree(node, replace_plot, inputs, input_nodes, calc_namespace):
    """Return a copy of `node` with every descendant `myst-baker-plot` node (at any
    depth) replaced by `replace_plot(plot_node)`, and every hidden calc `code`
    node (see `_is_hidden_calc_node`) dropped entirely.

    Recurses into `children` at any depth (verified against a real `myst
    build --debug`: mystmd wraps top-level content in an intermediate
    "block" node, so the document root's `children` is `[{"type": "block",
    "children": [<our myst-baker-* nodes>]}]`, not a flat list of the
    myst-baker-* nodes directly -- scanning only immediate children misses
    them entirely and silently no-ops).

    This also folds each input/calc node into `inputs`/`input_nodes`/
    `calc_namespace` (via `_process_state_node`) in the same depth-first,
    document order, *before* resolving any plot node that follows it. This
    makes a plot bind to whichever calc function/input block was most
    recently defined before it in the document, rather than to whatever a
    same-named later definition anywhere on the page happens to leave
    behind.
    """
    children = node.get("children")
    if children is None:
        return node

    new_children = []
    for child in children:
        if child.get("type") == "myst-baker-plot":
            new_children.append(replace_plot(child))
        elif _is_hidden_calc_node(child):
            _process_state_node(child, inputs, input_nodes, calc_namespace)
        else:
            _process_state_node(child, inputs, input_nodes, calc_namespace)
            new_children.append(
                _rewrite_tree(child, replace_plot, inputs, input_nodes, calc_namespace)
            )
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
    inputs = {}
    input_nodes = {}
    calc_namespace = {}

    def replace_plot(plot_node):
        function_names = [name.strip() for name in plot_node["options"]["data"].split(",")]
        funcs = []
        for function_name in function_names:
            if function_name not in calc_namespace:
                raise NameError(
                    f"plot block references '{function_name}', which is not "
                    f"defined by any calc block on this page."
                )
            funcs.append(calc_namespace[function_name])

        param_names = inspect_params(funcs[0])
        for function_name, func in zip(function_names, funcs):
            these_params = inspect_params(func)
            if these_params != param_names:
                raise ValueError(
                    f"plot block combines '{function_names[0]}' ({param_names}) "
                    f"and '{function_name}' ({these_params}) as traces on one "
                    f"plot, but they take different parameters; functions "
                    f"combined into one plot must share the same inputs."
                )

        grids = [
            (function_name, precompute.compute_grid(func, inputs))
            for function_name, func in zip(function_names, funcs)
        ]

        input_specs = [
            _INPUT_CLIENT_SPECS[input_nodes[name]["type"]](name, input_nodes[name])
            for name in param_names
            if name in input_nodes
        ]
        html = render.render_plot(plot_node, grids, input_specs)
        return _iframe_node(html)

    return _rewrite_tree(ast, replace_plot, inputs, input_nodes, calc_namespace)
