KNOWN_DIRECTIVES = {"input-slider", "input-checkbox", "input-dropdown", "calc-python", "plot"}

# CORRECTED (verified against real `myst build --debug`): mystmd's directive-option
# type-check (myst-parser's contentFromNode, see ParseTypesEnum) only recognizes the
# lowercase string literals "string" | "number" | "boolean" | "parsed" (these travel
# over JSON, so the JS-constructor identity checks it also does, `spec.type === String`
# etc., never match — a plugin's spec is always plain JSON). The brief's original spec
# used capitalized "String"/"Number" here for `arg`/`options`, which matched none of
# mystmd's branches and silently produced `undefined` (no warning) for every arg/option
# value; input-slider's `arg`/`options` all came back empty in the built mdast until
# this was lowercased. CALC_PYTHON_DIRECTIVE's `body` type was already lowercase
# "string" in the brief and needed no change.
INPUT_SLIDER_DIRECTIVE = {
    "name": "input-slider",
    "doc": "A numeric slider input, bound to a name referenced by calc function parameters.",
    "arg": {"type": "string", "doc": "The input's name"},
    "options": {
        "value": {"type": "number", "doc": "Initial value"},
        "min": {"type": "number", "doc": "Minimum value"},
        "max": {"type": "number", "doc": "Maximum value"},
        "step": {"type": "number", "doc": "Step size"},
    },
}

INPUT_CHECKBOX_DIRECTIVE = {
    "name": "input-checkbox",
    "doc": "A boolean checkbox input, bound to a name referenced by calc function parameters.",
    "arg": {"type": "string", "doc": "The input's name"},
    "options": {
        "value": {"type": "boolean", "doc": "Initial state"},
    },
}

INPUT_DROPDOWN_DIRECTIVE = {
    "name": "input-dropdown",
    "doc": (
        "A dropdown input selecting among a fixed list of choices (one per "
        "body line), bound to a name referenced by calc function parameters."
    ),
    "arg": {"type": "string", "doc": "The input's name"},
    "options": {
        "value": {
            "type": "string",
            "doc": "Initial selection (defaults to the first choice if omitted)",
        },
    },
    "body": {"type": "string", "doc": "Choices, one per line"},
}

CALC_PYTHON_DIRECTIVE = {
    "name": "calc-python",
    "doc": "A raw Python function definition, executed once per grid combination.",
    "body": {"type": "string", "doc": "Python source defining one function"},
}

PLOT_DIRECTIVE = {
    "name": "plot",
    "doc": "A Plotly output block. The argument is a Plotly trace type (e.g. scatter).",
    "arg": {"type": "string", "doc": "Plotly trace type"},
    "options": {
        "data": {"type": "string", "doc": "Name of the calc function providing this plot's data"},
        # CORRECTED (verified against real `myst build --debug`): mystmd's directive-option
        # validation (directive-options-correct) silently strips any option not declared here
        # (only a warning, no error, no data) before the placeholder node is ever built --
        # the plot directive's `:mode:` option was being dropped this way, so trace_options
        # in transform.py/render.py never actually received it. Declared explicitly so it
        # survives into the mdast node's `options` dict.
        "mode": {"type": "string", "doc": "Plotly trace mode (e.g. lines, markers, lines+markers)"},
    },
}


def build_placeholder_node(directive_name, arg, options, body):
    """Build the single placeholder mdast node for a pymd directive.

    Verified against the real `myst` CLI (`uv run myst build --debug`): MyST's
    stdin payload for a `--directive` invocation does have `arg`/`options`/`body`
    as top-level keys alongside `name` and the original `node`, matching what
    plugin.py already assumed — no correction needed here.

    The one correction required was on the *output* side, in plugin.py: MyST
    assigns whatever this function returns directly to the original directive
    node's `.children`, so plugin.py must send a JSON array (`[node]`), not this
    bare dict, over stdout. See the comment in plugin.py's `--directive` branch.
    """
    if directive_name not in KNOWN_DIRECTIVES:
        raise ValueError(f"unknown directive: {directive_name}")
    return {
        "type": f"pymd-{directive_name}",
        "arg": arg,
        "options": options,
        "body": body,
    }
