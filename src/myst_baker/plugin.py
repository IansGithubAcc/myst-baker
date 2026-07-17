#!/usr/bin/env python3
import json
import sys

from myst_baker import transform
from myst_baker.directives import (
    INPUT_SLIDER_DIRECTIVE,
    INPUT_CHECKBOX_DIRECTIVE,
    INPUT_DROPDOWN_DIRECTIVE,
    PLOT_DIRECTIVE,
    build_placeholder_node,
)

PLUGIN_SPEC = {
    "name": "myst-baker",
    "directives": [
        INPUT_SLIDER_DIRECTIVE,
        INPUT_CHECKBOX_DIRECTIVE,
        INPUT_DROPDOWN_DIRECTIVE,
        PLOT_DIRECTIVE,
    ],
    "transforms": [{"stage": "document"}],
}


def _read_ast_from_stdin():
    return json.load(sys.stdin)


def _write_ast_to_stdout(ast):
    json.dump(ast, sys.stdout)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv

    if not argv:
        print(json.dumps(PLUGIN_SPEC))
        return

    if argv[0] == "--transform":
        ast = _read_ast_from_stdin()
        ast = transform.transform_document(ast)
        _write_ast_to_stdout(ast)
        return

    if argv[0] == "--directive":
        directive_name = argv[1]
        payload = _read_ast_from_stdin()
        node = build_placeholder_node(
            directive_name,
            arg=payload.get("arg"),
            options=payload.get("options", {}),
            body=payload.get("body", ""),
        )
        # CORRECTED (verified against real `myst build --debug`, see directives.py):
        # MyST assigns our stdout JSON directly to the original directive node's
        # `.children` (`node.children = run(data, ...)` in myst-parser's
        # applyDirectives), then later does `node.children.map(...)` while lifting
        # directive children into the document tree. A bare object here made
        # `.children` a non-array and blew up with "node3.children.map is not a
        # function". We must return a JSON *array* of mdast nodes, so the single
        # placeholder node is wrapped as its sole element.
        _write_ast_to_stdout([node])
        return

    raise SystemExit(f"myst-baker plugin: unrecognized arguments: {argv}")


if __name__ == "__main__":
    main()
