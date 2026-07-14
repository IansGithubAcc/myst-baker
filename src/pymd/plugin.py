import json
import sys

PLUGIN_SPEC = {
    "name": "pymd",
    "directives": [],
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
        # no-op for now: proves the plumbing works before any real logic
        _write_ast_to_stdout(ast)
        return

    if argv[0] == "--directive":
        ast = _read_ast_from_stdin()
        _write_ast_to_stdout(ast)
        return

    raise SystemExit(f"pymd plugin: unrecognized arguments: {argv}")


if __name__ == "__main__":
    main()
