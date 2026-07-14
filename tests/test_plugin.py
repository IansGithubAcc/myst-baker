import io
import json

from pymd import plugin


def _run_directive(directive_name, payload, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    plugin.main(["--directive", directive_name])
    return out.getvalue()


def test_directive_dispatch_writes_json_array_not_bare_object(monkeypatch):
    # mystmd assigns our stdout directly to the directive node's `.children`
    # and calls `.children.map(...)` on it -- a bare object crashes with
    # "node3.children.map is not a function". Regression test for that.
    stdout = _run_directive(
        "input-slider",
        {"arg": "a", "options": {"value": 5, "min": 0, "max": 10, "step": 1}, "body": ""},
        monkeypatch,
    )

    parsed = json.loads(stdout)
    assert isinstance(parsed, list)
    assert parsed == [
        {
            "type": "pymd-input-slider",
            "arg": "a",
            "options": {"value": 5, "min": 0, "max": 10, "step": 1},
            "body": "",
        }
    ]
