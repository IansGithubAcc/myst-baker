# pymd MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the MVP of pymd — a MyST executable plugin that precomputes a Python function over a grid of slider values at build time and renders a static, fully-interactive Plotly chart with no server or live Python kernel.

**Architecture:** A Python package (`pymd`) provides an executable entrypoint script that MyST spawns as a subprocess, communicating via JSON over stdin/stdout. At parse time it turns `input-slider`/`calc-python`/`plot` fenced blocks into placeholder AST nodes; at document-transform time it resolves them (match plot's target function to sliders by signature, compute the full grid, replace the placeholder with a raw-HTML node containing the Tweakpane widget, a Plotly container, the precomputed JSON, and a small runtime script).

**Tech Stack:** Python ≥3.13, `mystmd` (installed via PyPI, which manages its own Node.js runtime), Tweakpane (CDN) for widgets, Plotly.js (CDN) for the chart, `pytest` for unit/integration tests, `pytest-playwright` for the real-browser test.

## Global Constraints

- Python ≥3.13 (per existing `pyproject.toml`)
- `mystmd` installed via PyPI (`pip`/`uv`), not npm — keeps the whole toolchain inside one dependency manager (`uv`)
- No custom dev server or JS bundling step for the MVP — `myst start` used unmodified; CDN `<script>` tags for Tweakpane/Plotly; runtime JS inlined
- No bespoke error handling beyond the combinatorial budget guard — exceptions propagate and crash the build
- Combinatorial budget: default 10,000 grid combinations, overridable via the `PYMD_MAX_GRID_SIZE` environment variable
- The exact PLUGIN_SPEC option/argument schema for MyST executable plugins is not fully documented publicly — tasks that touch it include an explicit "run against the real `myst` CLI and correct field names from its error output" step. This is expected engineering work, not a sign anything is wrong.
- **pymd must work identically on Windows, Linux, and Mac.** MyST (Node.js) spawns our plugin as a subprocess without a shell, which only ever works if the spawned file is a real platform-native executable — a `.py` file relies on shebang interpretation (POSIX-only, absent on Windows entirely) and MyST's own docs assume this. The fix is to expose the plugin as a proper Python packaging `console_scripts` entry point (`[project.scripts]` in `pyproject.toml`) rather than a raw script MyST spawns by path — `uv sync`/`pip install` then generate the correct real executable per platform automatically (a real shebang'd script on POSIX, a real compiled `.exe` launcher on Windows), with zero platform-specific code of our own. mystmd's plugin loader resolves `path` via a literal file-existence check, not a `PATH` search, so a small setup helper (`scripts/link_plugin_launcher.py`, Task 2) copies whichever platform's generated launcher to one fixed name that `myst.yml` references identically everywhere. Project setup is therefore two commands: `uv sync` then `uv run python scripts/link_plugin_launcher.py` — see Task 2 for the concrete mechanism and its verification steps.
- `calc-python`'s function-based model (one Python function per plot, whose signature declares its input dependencies) is the design this plan implements — see spec section "Open design question" for why this was chosen: the signature-as-dependency-declaration mechanism was never actually challenged during brainstorming, only the exact directive name/fencing was flagged as illustrative. If, during implementation, a clearly better shape emerges, prefer it — but don't leave this as unresolved; this plan commits to a concrete design.

---

## File Structure

```
pyproject.toml                        # modified: add deps, src-layout package config, console_scripts entry point
myst.yml                              # new: MyST project config, registers the plugin
scripts/link_plugin_launcher.py       # new: one-time setup step, fixed-name launcher copy (see Global Constraints)
src/pymd/
    __init__.py                       # new
    plugin.py                         # new: PLUGIN_SPEC + --directive/--transform CLI dispatch
    precompute.py                     # new: pure grid-computation engine (no MyST dependency)
    directives.py                     # new: placeholder-node builders for input-slider/calc-python/plot
    transform.py                      # new: document-transform glue (precompute.py + directives.py -> rendered HTML node)
    render.py                         # new: raw-HTML fragment builder (widget + plot container + JSON + scripts)
    static/runtime.js                 # new: client runtime (Tweakpane init, lookup-on-change, Plotly.react)
content/
    index.md                          # new: fixture/demo page (one input-slider, one calc-python, one plot)
tests/
    test_precompute.py                 # new
    test_directives.py                 # new
    test_transform.py                  # new
    test_e2e_browser.py                # new: Playwright
```

- `precompute.py` has zero MyST/AST knowledge — pure functions over plain Python values. This is deliberate: it's the part with the most logic and no external-tool uncertainty, so it should be fully unit-testable in isolation.
- `directives.py` and `transform.py` are split because directive *parsing* (turning one block into one placeholder node) and *document transform* (walking the whole page, matching nodes to each other, calling precompute, rendering) are different responsibilities with different inputs (one node vs. the whole AST).
- `render.py` is separate from `transform.py` so the "how do we build the actual HTML fragment" concern (which will change a lot as the client runtime is tuned) doesn't churn the AST-walking logic.
- There is deliberately no standalone `pymd_plugin.py` entrypoint script at the repo root. MyST needs a real, platform-native executable to spawn (see the cross-platform Global Constraint above) — that executable is generated by `uv sync` from a `console_scripts` entry point (`pymd-plugin = "pymd.plugin:main"`) declared in `pyproject.toml`, not hand-written by us.

---

### Task 1: Project bootstrap and MyST baseline

**Files:**
- Modify: `pyproject.toml`
- Create: `myst.yml`
- Create: `content/index.md` (trivial placeholder page, no pymd blocks yet)

**Interfaces:**
- Consumes: nothing (first task)
- Produces: a working `uv`-managed environment with `myst` on PATH inside the venv, and a `myst.yml` project that builds successfully with zero pymd involvement. Later tasks assume `uv run myst build` and `uv run myst start` work.

- [ ] **Step 1: Add `mystmd` as a dependency**

Edit `pyproject.toml` to add the dependency:

```toml
[project]
name = "pymd"
version = "0.1.0"
description = "Precomputed interactive docs via a MyST executable plugin"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "mystmd",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-playwright>=0.5",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pymd"]
```

- [ ] **Step 2: Sync the environment and verify `myst` is available**

Run: `uv sync`
Then run: `uv run myst --version`
Expected: prints a version string (e.g. `v1.9.0` or newer) with no error. If this fails, `mystmd`'s PyPI package auto-installs a Node.js runtime on first use — re-run `uv run myst --version` once more before troubleshooting further, since the first invocation may need to finish that setup.

- [ ] **Step 3: Scaffold the MyST project**

Run: `uv run myst init` (accept prompts with defaults; this creates `myst.yml`)

Confirm `myst.yml` now exists at the repo root with a `project:` key.

- [ ] **Step 4: Create a trivial fixture page and verify baseline build**

Create `content/index.md`:

```markdown
# pymd

This is the pymd MVP fixture page.
```

Edit `myst.yml` so its `project.toc` (or default content discovery) includes `content/index.md` — if `myst init` already scaffolded a different default page, replace its reference to point at `content/index.md` instead.

Run: `uv run myst build`
Expected: build succeeds, producing output under `_build/` with no errors.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml myst.yml content/index.md uv.lock
git commit -m "chore: bootstrap mystmd toolchain and baseline project"
```

---

### Task 2: Executable plugin skeleton and spawn verification

This task exists specifically to de-risk whether MyST can actually spawn our plugin as a subprocess, on every platform pymd needs to support — not just this dev machine. **A prior attempt at this task found that MyST cannot spawn a raw `.py` script (or a `.cmd` wrapper around one) on Windows at all**: a `.py` file relies on shebang-line interpretation, which is a POSIX kernel feature with no Windows equivalent (`spawn EFTYPE` — Windows' process creation only understands real compiled executables); a `.cmd` wrapper needs Node's `shell: true` spawn option to run at all (Node hardened this post-CVE-2024-27980), which mystmd's plugin loader never passes and gives no config knob to request (`spawn EINVAL`). Neither is a bug in our code — both are fundamental to how Windows process creation and Node's spawn security model work.

The fix: don't hand MyST a raw script at all. Declare the plugin as a Python packaging `console_scripts` entry point instead, and let `uv sync` generate the real, platform-native executable for us — exactly the mechanism every cross-platform Python CLI tool (`black`, `ruff`, `pytest`, ...) already relies on to get a working Windows `.exe` without anyone hand-writing one. On POSIX this generates an ordinary shebang'd script (works exactly as MyST's docs assume); on Windows it generates a real compiled launcher `.exe`. Same `pyproject.toml` entry, same `myst.yml` reference, no per-platform code of our own.

**Files:**
- Modify: `pyproject.toml` (add `[project.scripts]` entry point)
- Create: `src/pymd/__init__.py`
- Create: `src/pymd/plugin.py`
- Modify: `myst.yml`

**Interfaces:**
- Consumes: nothing new
- Produces: `pymd.plugin.main()` — the CLI entrypoint function, callable with `sys.argv`-style args, reads a JSON AST from stdin, writes a JSON AST to stdout. Later tasks (3, 5) extend `PLUGIN_SPEC` and the `--transform document` branch defined here; the dispatch shape (`--directive <name>`, `--transform <name>`, no-args-prints-spec) is what later tasks plug into.

- [ ] **Step 1: Write the plugin package skeleton**

Create `src/pymd/__init__.py` (empty).

Create `src/pymd/plugin.py`:

```python
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
```

- [ ] **Step 2: Declare the console_scripts entry point and regenerate the environment**

Edit `pyproject.toml`, adding:

```toml
[project.scripts]
pymd-plugin = "pymd.plugin:main"
```

Run: `uv sync`

Verify the launcher was generated:
- Windows: check `.venv/Scripts/pymd-plugin.exe` exists
- Linux/Mac: check `.venv/bin/pymd-plugin` exists and is executable

Run it directly to confirm it works before involving MyST at all: `uv run pymd-plugin` (no args) — expected output is the `PLUGIN_SPEC` JSON printed to stdout.

**Confirmed finding from a prior attempt at this step:** mystmd's plugin loader checks the `path` with a literal file-existence check (`fs.existsSync`), not a `PATH` search — a bare `pymd-plugin` name does NOT resolve. It also means the real launcher's location differs by OS (`.venv/Scripts/pymd-plugin.exe` on Windows vs. `.venv/bin/pymd-plugin` on Linux/Mac), so `myst.yml` cannot reference either path directly and still be identical across platforms. Step 3 below fixes this with one fixed-name file both platforms produce.

- [ ] **Step 3: Add a setup helper that copies the launcher to one fixed, OS-independent name**

Create `scripts/link_plugin_launcher.py`:

```python
"""One-time setup step: copies the platform-specific console_scripts
launcher generated by `uv sync` to a single fixed-name file, so myst.yml
can reference it identically on every OS. Re-run after any `uv sync`
that recreates the virtualenv.
"""
import shutil
import sys
from pathlib import Path

VENV_DIR = Path(__file__).resolve().parent.parent / ".venv"
FIXED_NAME = "pymd-plugin-bin.exe"  # .exe required even here: Node's Windows spawn
# path needs a recognized extension to invoke a real PE binary directly;
# the suffix is inert on POSIX (exec there is permission/content-based, not name-based)


def launcher_source():
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "pymd-plugin.exe"
    return VENV_DIR / "bin" / "pymd-plugin"


def main():
    source = launcher_source()
    if not source.exists():
        raise SystemExit(
            f"Expected console_scripts launcher not found at {source}. "
            f"Run 'uv sync' first."
        )
    dest = VENV_DIR / FIXED_NAME
    shutil.copy2(source, dest)
    if sys.platform != "win32":
        dest.chmod(0o755)
    print(f"Copied {source} -> {dest}")


if __name__ == "__main__":
    main()
```

Run: `uv run python scripts/link_plugin_launcher.py`
Expected: prints `Copied ... -> .../.venv/pymd-plugin-bin.exe`, and that file now exists.

- [ ] **Step 4: Register the plugin in `myst.yml` and verify MyST can spawn it — run against the real CLI**

Edit `myst.yml`, adding under the `project:` key:

```yaml
project:
  plugins:
    - type: executable
      path: .venv/pymd-plugin-bin.exe
```

Run: `uv run myst build --debug` (the `--debug` flag surfaces plugin stderr output per MyST's own debugging docs)

Expected: build succeeds with no spawn errors. This path is identical regardless of OS — only Step 3's helper script branches on platform, `myst.yml` itself does not.

- [ ] **Step 5: Prove the transform is actually being invoked (not just present)**

Temporarily add a line to `main()`'s `--transform` branch in `src/pymd/plugin.py`: `print("pymd transform ran", file=sys.stderr)` (the `import sys` already present covers this).

Run: `uv run myst build --debug` again and confirm `pymd transform ran` appears in the output.

Remove that debug print line once confirmed (it did its job; keep the file clean).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock src/pymd/__init__.py src/pymd/plugin.py myst.yml scripts/link_plugin_launcher.py
git commit -m "feat: add executable plugin skeleton via console_scripts entry point"
```

Note: `.venv/pymd-plugin-bin.exe` itself is inside the gitignored `.venv/` directory and is never committed — only the helper script that produces it is. Anyone setting up the project runs `uv sync` then `uv run python scripts/link_plugin_launcher.py` (this two-step setup should be documented in the README as part of finishing this task, since it's now a real, permanent part of the project's setup instructions, not a one-off).

---

### Task 3: Precompute engine (pure Python, no MyST involved)

**Files:**
- Create: `src/pymd/precompute.py`
- Test: `tests/test_precompute.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (deliberately standalone)
- Produces:
  - `input_values(min_value, max_value, step) -> list[float]`
  - `matched_inputs(func, inputs: dict[str, tuple[float, float, float]]) -> list[tuple[str, list]]`
  - `grid_size(matched: list[tuple[str, list]]) -> int`
  - `max_grid_size() -> int`
  - `compute_grid(func, inputs: dict[str, tuple[float, float, float]]) -> dict[str, Any]`
  - `GridTooLargeError` exception class
  - `MAX_GRID_SIZE_ENV_VAR` constant (`"PYMD_MAX_GRID_SIZE"`)

  Task 5 calls `compute_grid` directly with a real calc function and the inputs collected from the page's `input-slider` nodes.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_precompute.py`:

```python
import pytest

from pymd.precompute import (
    input_values,
    matched_inputs,
    grid_size,
    compute_grid,
    max_grid_size,
    GridTooLargeError,
    MAX_GRID_SIZE_ENV_VAR,
)


def test_input_values_inclusive_range():
    assert input_values(0, 10, 1) == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


def test_input_values_non_integer_step():
    assert input_values(0, 1, 0.5) == [0, 0.5, 1]


def test_matched_inputs_single_param():
    def f(a):
        return a

    matched = matched_inputs(f, {"a": (0, 10, 1)})
    assert matched == [("a", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])]


def test_matched_inputs_missing_input_raises():
    def f(a, b):
        return a + b

    with pytest.raises(ValueError, match="b"):
        matched_inputs(f, {"a": (0, 10, 1)})


def test_grid_size_multiplies_across_inputs():
    def f(a, b):
        return a + b

    matched = matched_inputs(f, {"a": (0, 2, 1), "b": (0, 1, 1)})
    assert grid_size(matched) == 3 * 2


def test_compute_grid_calls_function_per_combination():
    def f(a):
        return a * 2

    result = compute_grid(f, {"a": (0, 2, 1)})
    assert result == {"0": 0, "1": 2, "2": 4}


def test_compute_grid_two_inputs_keys_joined_with_pipe():
    def f(a, b):
        return a + b

    result = compute_grid(f, {"a": (0, 1, 1), "b": (0, 1, 1)})
    assert result == {"0|0": 0, "0|1": 1, "1|0": 1, "1|1": 2}


def test_compute_grid_raises_when_over_budget(monkeypatch):
    monkeypatch.setenv(MAX_GRID_SIZE_ENV_VAR, "2")

    def f(a):
        return a

    with pytest.raises(GridTooLargeError):
        compute_grid(f, {"a": (0, 10, 1)})


def test_max_grid_size_defaults_to_10000(monkeypatch):
    monkeypatch.delenv(MAX_GRID_SIZE_ENV_VAR, raising=False)
    assert max_grid_size() == 10_000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_precompute.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pymd.precompute'`

- [ ] **Step 3: Write the implementation**

Create `src/pymd/precompute.py`:

```python
import inspect
import itertools
import os

DEFAULT_MAX_GRID_SIZE = 10_000
MAX_GRID_SIZE_ENV_VAR = "PYMD_MAX_GRID_SIZE"


class GridTooLargeError(Exception):
    def __init__(self, function_name, size, limit):
        self.function_name = function_name
        self.size = size
        self.limit = limit
        super().__init__(
            f"Grid for '{function_name}' has {size} combinations, "
            f"exceeding the limit of {limit}. "
            f"Set {MAX_GRID_SIZE_ENV_VAR} to override."
        )


def input_values(min_value, max_value, step):
    steps = int(round((max_value - min_value) / step))
    return [round(min_value + i * step, 10) for i in range(steps + 1)]


def matched_inputs(func, inputs):
    signature = inspect.signature(func)
    matched = []
    for name in signature.parameters:
        if name not in inputs:
            raise ValueError(
                f"Function '{func.__name__}' has parameter '{name}' with no "
                f"matching input-slider block on this page."
            )
        matched.append((name, input_values(*inputs[name])))
    return matched


def grid_size(matched):
    size = 1
    for _, values in matched:
        size *= len(values)
    return size


def max_grid_size():
    return int(os.environ.get(MAX_GRID_SIZE_ENV_VAR, DEFAULT_MAX_GRID_SIZE))


def compute_grid(func, inputs):
    matched = matched_inputs(func, inputs)
    names = [name for name, _ in matched]
    value_lists = [values for _, values in matched]

    size = grid_size(matched)
    limit = max_grid_size()
    if size > limit:
        raise GridTooLargeError(func.__name__, size, limit)

    results = {}
    for combo in itertools.product(*value_lists):
        key = "|".join(str(v) for v in combo)
        results[key] = func(**dict(zip(names, combo)))
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_precompute.py -v`
Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/pymd/precompute.py tests/test_precompute.py
git commit -m "feat: add precompute grid engine with budget guard"
```

---

### Task 4: Directive placeholder-node registration

**Files:**
- Create: `src/pymd/directives.py`
- Modify: `src/pymd/plugin.py`
- Test: `tests/test_directives.py`

**Interfaces:**
- Consumes: nothing from precompute.py (directives.py only shapes placeholder nodes, doesn't compute anything)
- Produces:
  - `INPUT_SLIDER_DIRECTIVE`, `CALC_PYTHON_DIRECTIVE`, `PLOT_DIRECTIVE` — dicts appended to `PLUGIN_SPEC["directives"]` in `plugin.py`
  - `build_placeholder_node(directive_name: str, arg: str | None, options: dict, body: str) -> dict` — used by `plugin.py`'s `--directive` branch. Task 5's `transform.py` consumes the placeholder node shape this produces: `{"type": "pymd-input-slider" | "pymd-calc-python" | "pymd-plot", "arg": ..., "options": {...}, "body": "..."}`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_directives.py`:

```python
from pymd.directives import build_placeholder_node


def test_build_placeholder_node_input_slider():
    node = build_placeholder_node(
        "input-slider", arg="a", options={"value": 5, "min": 0, "max": 10, "step": 1}, body=""
    )
    assert node == {
        "type": "pymd-input-slider",
        "arg": "a",
        "options": {"value": 5, "min": 0, "max": 10, "step": 1},
        "body": "",
    }


def test_build_placeholder_node_calc_python():
    source = "def f(a):\n    return a\n"
    node = build_placeholder_node("calc-python", arg=None, options={}, body=source)
    assert node == {
        "type": "pymd-calc-python",
        "arg": None,
        "options": {},
        "body": source,
    }


def test_build_placeholder_node_plot():
    node = build_placeholder_node(
        "plot", arg="scatter", options={"data": "get_plot_data", "mode": "lines"}, body=""
    )
    assert node == {
        "type": "pymd-plot",
        "arg": "scatter",
        "options": {"data": "get_plot_data", "mode": "lines"},
        "body": "",
    }


def test_build_placeholder_node_rejects_unknown_directive():
    import pytest

    with pytest.raises(ValueError, match="unknown-thing"):
        build_placeholder_node("unknown-thing", arg=None, options={}, body="")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_directives.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pymd.directives'`

- [ ] **Step 3: Write the implementation**

Create `src/pymd/directives.py`:

```python
KNOWN_DIRECTIVES = {"input-slider", "calc-python", "plot"}

INPUT_SLIDER_DIRECTIVE = {
    "name": "input-slider",
    "doc": "A numeric slider input, bound to a name referenced by calc function parameters.",
    "arg": {"type": "String", "doc": "The input's name"},
    "options": {
        "value": {"type": "Number", "doc": "Initial value"},
        "min": {"type": "Number", "doc": "Minimum value"},
        "max": {"type": "Number", "doc": "Maximum value"},
        "step": {"type": "Number", "doc": "Step size"},
    },
}

CALC_PYTHON_DIRECTIVE = {
    "name": "calc-python",
    "doc": "A raw Python function definition, executed once per grid combination.",
    "body": {"type": "string", "doc": "Python source defining one function"},
}

PLOT_DIRECTIVE = {
    "name": "plot",
    "doc": "A Plotly output block. The argument is a Plotly trace type (e.g. scatter).",
    "arg": {"type": "String", "doc": "Plotly trace type"},
    "options": {
        "data": {"type": "String", "doc": "Name of the calc function providing this plot's data"},
    },
}


def build_placeholder_node(directive_name, arg, options, body):
    if directive_name not in KNOWN_DIRECTIVES:
        raise ValueError(f"unknown directive: {directive_name}")
    return {
        "type": f"pymd-{directive_name}",
        "arg": arg,
        "options": options,
        "body": body,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_directives.py -v`
Expected: all 4 tests PASS

- [ ] **Step 5: Wire the directives into `PLUGIN_SPEC` and the `--directive` dispatch branch**

Modify `src/pymd/plugin.py`:

```python
import json
import sys

from pymd.directives import (
    INPUT_SLIDER_DIRECTIVE,
    CALC_PYTHON_DIRECTIVE,
    PLOT_DIRECTIVE,
    build_placeholder_node,
)

PLUGIN_SPEC = {
    "name": "pymd",
    "directives": [INPUT_SLIDER_DIRECTIVE, CALC_PYTHON_DIRECTIVE, PLOT_DIRECTIVE],
    "transforms": [{"stage": "document"}],
}
```

In the `--directive` branch of `main()`, replace the no-op passthrough with:

```python
    if argv[0] == "--directive":
        directive_name = argv[1]
        payload = _read_ast_from_stdin()
        node = build_placeholder_node(
            directive_name,
            arg=payload.get("arg"),
            options=payload.get("options", {}),
            body=payload.get("body", ""),
        )
        _write_ast_to_stdout(node)
        return
```

(The exact shape of what MyST sends on stdin for a `--directive` invocation — e.g. whether `arg`/`options`/`body` are top-level keys or nested — is one of the schema details flagged in Global Constraints as unverified against public docs. Step 6 below verifies and corrects this against the real tool.)

- [ ] **Step 6: Verify against the real `myst` CLI and correct any schema mismatches**

Add a fixture block to `content/index.md`:

````markdown
```{input-slider} a
:value: 5
:min: 0
:max: 10
:step: 1
```
````

Run: `uv run myst build --debug`

If MyST reports a schema error (rejected option type names, unexpected `arg`/`options`/`body` field names on stdin, etc.), read the error message and adjust `directives.py`'s directive specs and/or `plugin.py`'s stdin-reading code to match what MyST actually sends/expects. Repeat until the build succeeds. Document any corrections made as a comment in `directives.py` next to the field that needed adjusting.

- [ ] **Step 7: Commit**

```bash
git add src/pymd/directives.py src/pymd/plugin.py tests/test_directives.py content/index.md
git commit -m "feat: register input-slider/calc-python/plot directives as placeholder nodes"
```

---

### Task 5: Document-transform wiring

**Files:**
- Create: `src/pymd/transform.py`
- Modify: `src/pymd/plugin.py`
- Test: `tests/test_transform.py`

**Interfaces:**
- Consumes: `pymd.precompute.compute_grid(func, inputs)` from Task 3; the placeholder node shape `{"type": "pymd-input-slider"|"pymd-calc-python"|"pymd-plot", "arg", "options", "body"}` from Task 4
- Produces: `transform_document(ast: dict) -> dict` — takes a full MyST page AST (a tree whose nodes may include `pymd-input-slider`/`pymd-calc-python`/`pymd-plot` nodes anywhere in `children`), returns a new AST with every `pymd-plot` node replaced by `{"type": "html", "value": "<...>"}`. Task 6's `render.py` is called from here to build that HTML string — this task defines the call site: `render.render_plot(plot_node, grid_result, plotly_trace_type)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_transform.py`:

```python
from pymd.transform import transform_document


def _page_ast(input_node, calc_node, plot_node):
    return {
        "type": "root",
        "children": [input_node, calc_node, plot_node],
    }


def test_transform_document_replaces_plot_node_with_html():
    input_node = {
        "type": "pymd-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 2, "step": 1},
        "body": "",
    }
    calc_node = {
        "type": "pymd-calc-python",
        "arg": None,
        "options": {},
        "body": "def get_plot_data(a):\n    return a * 2\n",
    }
    plot_node = {
        "type": "pymd-plot",
        "arg": "scatter",
        "options": {"data": "get_plot_data"},
        "body": "",
    }

    result = transform_document(_page_ast(input_node, calc_node, plot_node))

    children_types = [child["type"] for child in result["children"]]
    assert children_types == ["pymd-input-slider", "pymd-calc-python", "html"]

    html_node = result["children"][2]
    assert '"0": 0' in html_node["value"]
    assert '"1": 2' in html_node["value"]
    assert '"2": 4' in html_node["value"]


def test_transform_document_raises_when_plot_references_unknown_function():
    input_node = {
        "type": "pymd-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 1, "step": 1},
        "body": "",
    }
    calc_node = {
        "type": "pymd-calc-python",
        "arg": None,
        "options": {},
        "body": "def get_plot_data(a):\n    return a\n",
    }
    plot_node = {
        "type": "pymd-plot",
        "arg": "scatter",
        "options": {"data": "does_not_exist"},
        "body": "",
    }

    import pytest

    with pytest.raises(NameError, match="does_not_exist"):
        transform_document(_page_ast(input_node, calc_node, plot_node))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_transform.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pymd.transform'`

- [ ] **Step 3: Write the implementation**

Create `src/pymd/transform.py`:

```python
from pymd import precompute, render


def _collect_nodes(ast):
    inputs = {}
    calc_namespace = {}
    plot_nodes = []

    for child in ast["children"]:
        node_type = child["type"]
        if node_type == "pymd-input-slider":
            name = child["arg"]
            options = child["options"]
            inputs[name] = (options["min"], options["max"], options["step"])
        elif node_type == "pymd-calc-python":
            exec(child["body"], calc_namespace)
        elif node_type == "pymd-plot":
            plot_nodes.append(child)

    return inputs, calc_namespace, plot_nodes


def transform_document(ast):
    inputs, calc_namespace, plot_nodes = _collect_nodes(ast)

    new_children = []
    for child in ast["children"]:
        if child["type"] != "pymd-plot":
            new_children.append(child)
            continue

        function_name = child["options"]["data"]
        if function_name not in calc_namespace:
            raise NameError(
                f"plot block references '{function_name}', which is not "
                f"defined by any calc-python block on this page."
            )
        func = calc_namespace[function_name]
        grid_result = precompute.compute_grid(func, inputs)
        html = render.render_plot(child, grid_result)
        new_children.append({"type": "html", "value": html})

    return {**ast, "children": new_children}
```

- [ ] **Step 4: Run test to verify it passes**

This will still fail until `render.py` exists (Task 6). For now, create a minimal stub so this task's tests can pass on their own: create `src/pymd/render.py` with just enough to satisfy the test's assertions (checking that the JSON grid values appear in the output):

```python
import json


def render_plot(plot_node, grid_result):
    return f'<script type="application/json">{json.dumps(grid_result)}</script>'
```

Run: `uv run pytest tests/test_transform.py -v`
Expected: both tests PASS

- [ ] **Step 5: Wire `transform_document` into the plugin's `--transform` dispatch**

Modify `src/pymd/plugin.py`'s `--transform` branch:

```python
    if argv[0] == "--transform":
        ast = _read_ast_from_stdin()
        ast = transform.transform_document(ast)
        _write_ast_to_stdout(ast)
        return
```

Add `from pymd import transform` to the top of `plugin.py`.

- [ ] **Step 6: Commit**

```bash
git add src/pymd/transform.py src/pymd/render.py src/pymd/plugin.py tests/test_transform.py
git commit -m "feat: wire document transform (input+calc+plot nodes -> precomputed HTML)"
```

---

### Task 6: Client runtime and full HTML rendering

**Files:**
- Create: `src/pymd/static/runtime.js`
- Modify: `src/pymd/render.py`
- Test: `tests/test_transform.py` (extend)

**Interfaces:**
- Consumes: the `render_plot(plot_node, grid_result)` call site from Task 5 (signature unchanged — this task fills in its real implementation)
- Produces: the final `<div>`/`<script>` HTML string embedded in the page, containing: a Tweakpane mount point + init call, a Plotly container `<div>`, the grid JSON, and the runtime script tag. Task 7/8 depend on this actually working in a browser.

- [ ] **Step 1: Write the client runtime**

Create `src/pymd/static/runtime.js`:

```javascript
function pymdInitPlot(containerId, inputSpecs, grid, traceType, traceOptions) {
  const container = document.getElementById(containerId);
  const controlsEl = document.createElement('div');
  const plotEl = document.createElement('div');
  container.appendChild(controlsEl);
  container.appendChild(plotEl);

  const pane = new Tweakpane.Pane({ container: controlsEl });
  const params = {};
  inputSpecs.forEach((spec) => {
    params[spec.name] = spec.value;
  });

  function currentKey() {
    return inputSpecs.map((spec) => String(params[spec.name])).join('|');
  }

  function currentData() {
    return grid[currentKey()];
  }

  function draw() {
    const data = currentData();
    const trace = Object.assign({ type: traceType, x: data[0], y: data[1] }, traceOptions);
    Plotly.react(plotEl, [trace], {});
  }

  inputSpecs.forEach((spec) => {
    pane
      .addBinding(params, spec.name, {
        min: spec.min,
        max: spec.max,
        step: spec.step,
      })
      .on('change', draw);
  });

  draw();
}
```

- [ ] **Step 2: Write the full `render_plot` implementation**

Modify `src/pymd/render.py`:

```python
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
```

- [ ] **Step 3: Update `transform.py` to pass `input_specs` through**

Modify `src/pymd/transform.py`'s `transform_document` — it needs each plot's matched input specs (name/value/min/max/step), not just the grid result. Update the loop body:

```python
        function_name = child["options"]["data"]
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
                "value": options["value"],
                "min": options["min"],
                "max": options["max"],
                "step": options["step"],
            }
            for name, options in (
                (n["arg"], n["options"])
                for n in ast["children"]
                if n["type"] == "pymd-input-slider" and n["arg"] in inspect_params(func)
            )
        ]
        html = render.render_plot(child, grid_result, input_specs)
```

Add a small helper above `_collect_nodes` in `transform.py`:

```python
import inspect


def inspect_params(func):
    return set(inspect.signature(func).parameters)
```

- [ ] **Step 4: Update the existing transform test for the new `render_plot` signature**

Modify `tests/test_transform.py` — since `render_plot` now takes a third argument, and the stub written in Task 5 no longer matches, update the test assertions to check for the container div and the `pymdInitPlot(` call instead of raw JSON (the JSON is now nested inside the script call):

```python
def test_transform_document_replaces_plot_node_with_html():
    input_node = {
        "type": "pymd-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 2, "step": 1},
        "body": "",
    }
    calc_node = {
        "type": "pymd-calc-python",
        "arg": None,
        "options": {},
        "body": "def get_plot_data(a):\n    return a * 2\n",
    }
    plot_node = {
        "type": "pymd-plot",
        "arg": "scatter",
        "options": {"data": "get_plot_data"},
        "body": "",
    }

    result = transform_document(_page_ast(input_node, calc_node, plot_node))

    children_types = [child["type"] for child in result["children"]]
    assert children_types == ["pymd-input-slider", "pymd-calc-python", "html"]

    html_node = result["children"][2]
    assert "pymdInitPlot(" in html_node["value"]
    assert '"0": 0' in html_node["value"]
    assert '"1": 2' in html_node["value"]
    assert '"2": 4' in html_node["value"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_transform.py -v`
Expected: both tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/pymd/static/runtime.js src/pymd/render.py src/pymd/transform.py tests/test_transform.py
git commit -m "feat: render Tweakpane+Plotly client runtime into precomputed plot HTML"
```

---

### Task 7: Full fixture page and real end-to-end build

**Files:**
- Modify: `content/index.md`

**Interfaces:**
- Consumes: everything from Tasks 1–6
- Produces: a real, complete demo page proving the whole pipeline works via the actual `myst` CLI. Task 8's Playwright test loads this page's built output.

- [ ] **Step 1: Write the full fixture page**

Replace the contents of `content/index.md` with:

````markdown
# pymd MVP demo

```{input-slider} a
:value: 3
:min: 0
:max: 10
:step: 1
```

```{calc-python}
def get_plot_data(a):
    x = list(range(10))
    y = [a * xi for xi in x]
    return x, y
```

```{plot} scatter
:data: get_plot_data
:mode: lines
```
````

- [ ] **Step 2: Build for real**

Run: `uv run myst build --debug`
Expected: build succeeds with no errors.

- [ ] **Step 3: Manually verify in a browser**

Run: `uv run myst start`
Open the printed local URL, confirm: the slider renders, dragging it updates the line plot, and the browser console shows no errors.

This step has no automated assertion — it's a manual sanity check before writing the automated version in Task 8. If anything looks wrong here, fix it before moving on; Task 8 will otherwise just automate a broken experience.

- [ ] **Step 4: Commit**

```bash
git add content/index.md
git commit -m "feat: add full pymd MVP demo page"
```

---

### Task 8: Playwright browser test

**Files:**
- Create: `tests/test_e2e_browser.py`

**Interfaces:**
- Consumes: the built output of `content/index.md` from Task 7 (via `uv run myst build`, invoked as a subprocess fixture in this test)
- Produces: nothing consumed by later tasks — this is the final verification layer

- [ ] **Step 1: Install Playwright's browser binaries**

Run: `uv run playwright install chromium`
Expected: downloads and installs a Chromium binary with no errors.

- [ ] **Step 2: Write the failing test**

Create `tests/test_e2e_browser.py`:

```python
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def built_site():
    subprocess.run(
        ["uv", "run", "myst", "build"], cwd=REPO_ROOT, check=True
    )
    return REPO_ROOT / "_build" / "html" / "index.html"


def test_slider_updates_plot_with_no_console_errors(built_site, page):
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    page.goto(built_site.as_uri())

    plot_locator = page.locator(".js-plotly-plot").first
    plot_locator.wait_for(state="visible")

    before = page.evaluate(
        "() => document.querySelector('.js-plotly-plot').data[0].y.slice(0, 3)"
    )

    slider_input = page.locator("input[type='range']").first
    slider_input.fill("8")
    slider_input.dispatch_event("change")

    page.wait_for_timeout(300)

    after = page.evaluate(
        "() => document.querySelector('.js-plotly-plot').data[0].y.slice(0, 3)"
    )

    assert before != after
    assert console_errors == []
```

- [ ] **Step 3: Run test to verify it fails (or reveals a real bug)**

Run: `uv run pytest tests/test_e2e_browser.py -v`
Expected: either PASS immediately (if Tasks 1–7 are solid), or a specific failure pointing at a real integration bug — e.g. Tweakpane's control might not literally render as `input[type='range']` (some Tweakpane bindings render a custom slider element, not a native `<input type="range">`). If the locator doesn't find the expected element, inspect the built HTML/DOM directly (`page.content()` or a non-headless run via `PWDEBUG=1`) and adjust the locator to match Tweakpane's actual rendered markup.

- [ ] **Step 4: Fix any real issues found, until the test passes**

Iterate on `runtime.js` / `render.py` / the test's locators as needed based on what Step 3 reveals. This step intentionally has no fixed code — what needs fixing depends on what Step 3 finds.

- [ ] **Step 5: Run the full test suite one more time**

Run: `uv run pytest -v`
Expected: all tests across `tests/test_precompute.py`, `tests/test_directives.py`, `tests/test_transform.py`, and `tests/test_e2e_browser.py` PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_e2e_browser.py
git commit -m "test: add Playwright browser test proving slider->plot flow works end to end"
```

---

## Self-Review Notes

**Spec coverage:** Architecture (Task 2), directive syntax (Task 4), precompute engine incl. budget guard (Task 3), client runtime incl. Tweakpane+Plotly (Task 6), testing incl. Playwright (Task 8), MVP scope (single slider/calc/scatter demo, Task 7) — all covered. The spec's "falls out automatically" claims (other Tweakpane kinds, other Plotly trace types) aren't separately tasked, since the plan's `directives.py`/`render.py` design already makes them free — `PLOT_DIRECTIVE`'s `arg` is forwarded as Plotly's own trace type string with no hardcoded list, and adding another `input-*` directive is a few lines in `directives.py` following the same pattern as `input-slider`, not a new mechanism.

**Placeholder scan:** No TBD/TODO markers. The one place flagged as "verify against the real tool" (Task 4 Step 6, Task 2 Step 3) is genuine unavoidable uncertainty about an undocumented wire format, not a deferred design decision — each such step names exactly what to run and what "success" looks like.

**Type consistency:** Placeholder node shape (`type`/`arg`/`options`/`body`) is identical across `directives.py` (Task 4), `transform.py` (Task 5), and the tests. `compute_grid`'s return type (`dict[str, Any]` keyed by pipe-joined stringified values) is used identically in `transform.py` and `render.py`. `render_plot`'s signature changes once (Task 5's 2-arg stub → Task 6's 3-arg real version) — Task 6 Step 4 explicitly updates the Task 5 test to match, so no stale signature is left behind.
