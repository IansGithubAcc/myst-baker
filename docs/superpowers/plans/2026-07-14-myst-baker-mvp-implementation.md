# myst-baker MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the MVP of myst-baker — a MyST executable plugin that precomputes a Python function over a grid of slider values at build time and renders a static, fully-interactive Plotly chart with no server or live Python kernel.

**Architecture:** A Python package (`myst-baker`) provides an executable entrypoint script that MyST spawns as a subprocess, communicating via JSON over stdin/stdout. At parse time it turns `input-slider`/`calc-python`/`plot` fenced blocks into placeholder AST nodes; at document-transform time it resolves them (match plot's target function to sliders by signature, compute the full grid, replace the placeholder with a raw-HTML node containing the Tweakpane widget, a Plotly container, the precomputed JSON, and a small runtime script).

**Tech Stack:** Python ≥3.13, `mystmd` (installed via PyPI, which manages its own Node.js runtime), Tweakpane (CDN) for widgets, Plotly.js (CDN) for the chart, `pytest` for unit/integration tests, `pytest-playwright` for the real-browser test.

## Global Constraints

- Python ≥3.13 (per existing `pyproject.toml`)
- `mystmd` installed via PyPI (`pip`/`uv`), not npm — keeps the whole toolchain inside one dependency manager (`uv`)
- No custom dev server or JS bundling step for the MVP — `myst start` used unmodified; CDN `<script>` tags for Tweakpane/Plotly; runtime JS inlined
- No bespoke error handling beyond the combinatorial budget guard — exceptions propagate and crash the build
- Combinatorial budget: default 10,000 grid combinations, overridable via the `MYST_BAKER_MAX_GRID_SIZE` environment variable
- The exact PLUGIN_SPEC option/argument schema for MyST executable plugins is not fully documented publicly — tasks that touch it include an explicit "run against the real `myst` CLI and correct field names from its error output" step. This is expected engineering work, not a sign anything is wrong.
- **myst-baker must work identically on Windows, Linux, and Mac.** MyST (Node.js) spawns our plugin as a subprocess without a shell, which only ever works if the spawned file is a real platform-native executable — a `.py` file relies on shebang interpretation (POSIX-only, absent on Windows entirely) and MyST's own docs assume this. The fix is to expose the plugin as a proper Python packaging `console_scripts` entry point (`[project.scripts]` in `pyproject.toml`) rather than a raw script MyST spawns by path — `uv sync`/`pip install` then generate the correct real executable per platform automatically (a real shebang'd script on POSIX, a real compiled `.exe` launcher on Windows), with zero platform-specific code of our own. mystmd's plugin loader resolves `path` via a literal file-existence check, not a `PATH` search, so a small setup helper (`scripts/link_plugin_launcher.py`, Task 2) copies whichever platform's generated launcher to one fixed name that `myst.yml` references identically everywhere. Project setup is therefore two commands: `uv sync` then `uv run python scripts/link_plugin_launcher.py` — see Task 2 for the concrete mechanism and its verification steps.
- `calc-python`'s function-based model (one Python function per plot, whose signature declares its input dependencies) is the design this plan implements — see spec section "Open design question" for why this was chosen: the signature-as-dependency-declaration mechanism was never actually challenged during brainstorming, only the exact directive name/fencing was flagged as illustrative. If, during implementation, a clearly better shape emerges, prefer it — but don't leave this as unresolved; this plan commits to a concrete design.

---

## File Structure

```
pyproject.toml                        # modified: add deps, src-layout package config, console_scripts entry point
myst.yml                              # new: MyST project config, registers the plugin
scripts/link_plugin_launcher.py       # new: one-time setup step, fixed-name launcher copy (see Global Constraints)
src/myst_baker/
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
    test_plugin.py                     # new: added in fix round, --directive JSON-array regression test
    test_e2e_browser.py                # new: Playwright
```

- `precompute.py` has zero MyST/AST knowledge — pure functions over plain Python values. This is deliberate: it's the part with the most logic and no external-tool uncertainty, so it should be fully unit-testable in isolation.
- `directives.py` and `transform.py` are split because directive *parsing* (turning one block into one placeholder node) and *document transform* (walking the whole page, matching nodes to each other, calling precompute, rendering) are different responsibilities with different inputs (one node vs. the whole AST).
- `render.py` is separate from `transform.py` so the "how do we build the actual HTML fragment" concern (which will change a lot as the client runtime is tuned) doesn't churn the AST-walking logic.
- There is deliberately no standalone `myst_baker_plugin.py` entrypoint script at the repo root. MyST needs a real, platform-native executable to spawn (see the cross-platform Global Constraint above) — that executable is generated by `uv sync` from a `console_scripts` entry point (`myst-baker-plugin = "myst_baker.plugin:main"`) declared in `pyproject.toml`, not hand-written by us.

---

### Task 1: Project bootstrap and MyST baseline — ✅ complete (commits 5dd497e..2602654)

**Files:**
- Modify: `pyproject.toml`
- Create: `myst.yml`
- Create: `content/index.md` (trivial placeholder page, no myst-baker blocks yet)

**Interfaces:**
- Consumes: nothing (first task)
- Produces: a working `uv`-managed environment with `myst` on PATH inside the venv, and a `myst.yml` project that builds successfully with zero myst-baker involvement. Later tasks assume `uv run myst build` and `uv run myst start` work.

- [x] **Step 1: Add `mystmd` as a dependency**

Edit `pyproject.toml` to add the dependency:

```toml
[project]
name = "myst-baker"
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
packages = ["src/myst_baker"]
```

- [x] **Step 2: Sync the environment and verify `myst` is available**

Run: `uv sync`
Then run: `uv run myst --version`
Expected: prints a version string (e.g. `v1.9.0` or newer) with no error. If this fails, `mystmd`'s PyPI package auto-installs a Node.js runtime on first use — re-run `uv run myst --version` once more before troubleshooting further, since the first invocation may need to finish that setup.

- [x] **Step 3: Scaffold the MyST project**

Run: `uv run myst init` (accept prompts with defaults; this creates `myst.yml`)

Confirm `myst.yml` now exists at the repo root with a `project:` key.

- [x] **Step 4: Create a trivial fixture page and verify baseline build**

Create `content/index.md`:

```markdown
# myst-baker

This is the myst-baker MVP fixture page.
```

Edit `myst.yml` so its `project.toc` (or default content discovery) includes `content/index.md` — if `myst init` already scaffolded a different default page, replace its reference to point at `content/index.md` instead.

Run: `uv run myst build`
Expected: build succeeds, producing output under `_build/` with no errors.

- [x] **Step 5: Commit**

```bash
git add pyproject.toml myst.yml content/index.md uv.lock
git commit -m "chore: bootstrap mystmd toolchain and baseline project"
```

**As actually built:** `README.md` was also added (hatchling hard-requires the `readme` file declared in `pyproject.toml` to exist), and `.gitignore` picked up a `_build` entry `myst init` appended automatically. Both were correct, necessary consequences of the steps above, not scope creep.

---

### Task 2: Executable plugin skeleton and spawn verification — ✅ complete (commits 2602654..5b57b1c)

This task exists specifically to de-risk whether MyST can actually spawn our plugin as a subprocess, on every platform myst-baker needs to support — not just this dev machine. **A first attempt at this task (commit `1edb97d`, superseded) tried a raw `.py` script and a `.cmd` wrapper, and found MyST cannot spawn either on Windows at all**: a `.py` file relies on shebang-line interpretation, which is a POSIX kernel feature with no Windows equivalent (`spawn EFTYPE` — Windows' process creation only understands real compiled executables); a `.cmd` wrapper needs Node's `shell: true` spawn option to run at all (Node hardened this post-CVE-2024-27980), which mystmd's plugin loader never passes and gives no config knob to request (`spawn EINVAL`). Neither is a bug in our code — both are fundamental to how Windows process creation and Node's spawn security model work.

The fix actually shipped: don't hand MyST a raw script at all. Declare the plugin as a Python packaging `console_scripts` entry point instead, and let `uv sync` generate the real, platform-native executable for us — exactly the mechanism every cross-platform Python CLI tool (`black`, `ruff`, `pytest`, ...) already relies on to get a working Windows `.exe` without anyone hand-writing one. On POSIX this generates an ordinary shebang'd script (works exactly as MyST's docs assume); on Windows it generates a real compiled launcher `.exe`. Same `pyproject.toml` entry, same `myst.yml` reference, no per-platform code of our own.

**Files:**
- Modify: `pyproject.toml` (add `[project.scripts]` entry point)
- Create: `src/myst_baker/__init__.py`
- Create: `src/myst_baker/plugin.py`
- Modify: `myst.yml`
- Create: `scripts/link_plugin_launcher.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `myst_baker.plugin.main()` — the CLI entrypoint function, callable with `sys.argv`-style args, reads a JSON AST from stdin, writes a JSON AST to stdout. Later tasks (3, 5) extend `PLUGIN_SPEC` and the `--transform document` branch defined here; the dispatch shape (`--directive <name>`, `--transform <name>`, no-args-prints-spec) is what later tasks plug into.

- [x] **Step 1: Write the plugin package skeleton**

Create `src/myst_baker/__init__.py` (empty).

Create `src/myst_baker/plugin.py`:

```python
import json
import sys

PLUGIN_SPEC = {
    "name": "myst-baker",
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

    raise SystemExit(f"myst-baker plugin: unrecognized arguments: {argv}")


if __name__ == "__main__":
    main()
```

- [x] **Step 2: Declare the console_scripts entry point and regenerate the environment**

Edit `pyproject.toml`, adding:

```toml
[project.scripts]
myst-baker-plugin = "myst_baker.plugin:main"
```

Run: `uv sync`

Verify the launcher was generated:
- Windows: check `.venv/Scripts/myst-baker-plugin.exe` exists
- Linux/Mac: check `.venv/bin/myst-baker-plugin` exists and is executable

Run it directly to confirm it works before involving MyST at all: `uv run myst-baker-plugin` (no args) — expected output is the `PLUGIN_SPEC` JSON printed to stdout.

**Confirmed finding:** mystmd's plugin loader checks the `path` with a literal file-existence check (`fs.existsSync`), not a `PATH` search — a bare `myst-baker-plugin` name does NOT resolve. It also means the real launcher's location differs by OS (`.venv/Scripts/myst-baker-plugin.exe` on Windows vs. `.venv/bin/myst-baker-plugin` on Linux/Mac), so `myst.yml` cannot reference either path directly and still be identical across platforms. Step 3 below fixes this with one fixed-name file both platforms produce.

- [x] **Step 3: Add a setup helper that copies the launcher to one fixed, OS-independent name**

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
FIXED_NAME = "myst-baker-plugin-bin.exe"  # .exe required even here: Node's Windows spawn
# path needs a recognized extension to invoke a real PE binary directly;
# the suffix is inert on POSIX (exec there is permission/content-based, not name-based)


def launcher_source():
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "myst-baker-plugin.exe"
    return VENV_DIR / "bin" / "myst-baker-plugin"


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
Expected: prints `Copied ... -> .../.venv/myst-baker-plugin-bin.exe`, and that file now exists.

**As actually shipped, `_find_real_launcher`/`launcher_source` checks the Windows candidate path before the POSIX one unconditionally** (not gated on `sys.platform` at the point of choosing which candidate to look for first, only in the final `dest.chmod` branch). Harmless given a real `.venv` only ever produces one candidate; flagged as known, accepted debt in the final whole-branch review (see note at the end of this document).

- [x] **Step 4: Register the plugin in `myst.yml` and verify MyST can spawn it — run against the real CLI**

Edit `myst.yml`, adding under the `project:` key:

```yaml
project:
  plugins:
    - type: executable
      path: .venv/myst-baker-plugin-bin.exe
```

Run: `uv run myst build --debug` (the `--debug` flag surfaces plugin stderr output per MyST's own debugging docs)

Expected: build succeeds with no spawn errors. This path is identical regardless of OS — only Step 3's helper script branches on platform, `myst.yml` itself does not.

- [x] **Step 5: Prove the transform is actually being invoked (not just present)**

Temporarily add a line to `main()`'s `--transform` branch in `src/myst_baker/plugin.py`: `print("myst-baker transform ran", file=sys.stderr)` (the `import sys` already present covers this).

Run: `uv run myst build --debug` again and confirm `myst-baker transform ran` appears in the output.

Remove that debug print line once confirmed (it did its job; keep the file clean).

- [x] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock src/myst_baker/__init__.py src/myst_baker/plugin.py myst.yml scripts/link_plugin_launcher.py
git commit -m "feat: add executable plugin skeleton via console_scripts entry point"
```

Note: `.venv/myst-baker-plugin-bin.exe` itself is inside the gitignored `.venv/` directory and is never committed — only the helper script that produces it is. Setup is documented in README.md's "Setup" section: `uv sync`, then `uv run python scripts/link_plugin_launcher.py`.

**Known accepted gap:** the POSIX side of this mechanism (launcher path, `.exe`-suffix-on-every-platform behavior) is reasoned from documented POSIX semantics, not empirically verified — all development and testing happened on a Windows machine. Worth a first-run sanity check on Linux/Mac CI.

---

### Task 3: Precompute engine (pure Python, no MyST involved) — ✅ complete (commits 5b57b1c..a20b8bf)

**Files:**
- Create: `src/myst_baker/precompute.py`
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
  - `MAX_GRID_SIZE_ENV_VAR` constant (`"MYST_BAKER_MAX_GRID_SIZE"`)

  Task 5 calls `compute_grid` directly with a real calc function and the inputs collected from the page's `input-slider` nodes.

- [x] **Step 1: Write the failing tests**

Create `tests/test_precompute.py`:

```python
import pytest

from myst_baker.precompute import (
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

(This is 9 test functions — an earlier note in this plan said "8 tests," a miscount; 9 is correct and expected.)

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_precompute.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myst_baker.precompute'`

- [x] **Step 3: Write the implementation**

Create `src/myst_baker/precompute.py`:

```python
import inspect
import itertools
import os

DEFAULT_MAX_GRID_SIZE = 10_000
MAX_GRID_SIZE_ENV_VAR = "MYST_BAKER_MAX_GRID_SIZE"


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

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_precompute.py -v`
Expected: all 9 tests PASS

- [x] **Step 5: Commit**

```bash
git add src/myst_baker/precompute.py tests/test_precompute.py
git commit -m "feat: add precompute grid engine with budget guard"
```

**Gap surfaced in final review, fixed in the fix round (see "Final Whole-Branch Review — Fix Round" at the end of this document):** `compute_grid`'s key building (`"|".join(str(v) for v in combo)`) used Python's `str()`, while `runtime.js`'s `currentKey()` uses JS's `String()` on the same values. These diverge for whole-number floats: Python's `str(1.0) == "1.0"`, JS's `String(1) == "1"`. Since `input_values` produces floats whenever `min`/`max`/`step` aren't all integers, any fractional `:step:` whose grid includes a whole-number point silently mismatched between the precomputed key and the client's lookup key, breaking the plot in the browser. Not exercised by the MVP's own fixture at the time (`step: 1`, all-integer grid) or the Playwright test. Fixed via `precompute._stringify`.

---

### Task 4: Directive placeholder-node registration — ✅ complete (commits a20b8bf..885bc29)

**Files:**
- Create: `src/myst_baker/directives.py`
- Modify: `src/myst_baker/plugin.py`
- Test: `tests/test_directives.py`
- Modify: `content/index.md` (fixture block for real-tool verification)

**Interfaces:**
- Consumes: nothing from precompute.py (directives.py only shapes placeholder nodes, doesn't compute anything)
- Produces:
  - `INPUT_SLIDER_DIRECTIVE`, `CALC_PYTHON_DIRECTIVE`, `PLOT_DIRECTIVE` — dicts appended to `PLUGIN_SPEC["directives"]` in `plugin.py`
  - `build_placeholder_node(directive_name: str, arg: str | None, options: dict, body: str) -> dict` — used by `plugin.py`'s `--directive` branch. Task 5's `transform.py` consumes the placeholder node shape this produces: `{"type": "myst-baker-input-slider" | "myst-baker-calc-python" | "myst-baker-plot", "arg": ..., "options": {...}, "body": "..."}`.

- [x] **Step 1: Write the failing test**

Create `tests/test_directives.py`:

```python
from myst_baker.directives import build_placeholder_node


def test_build_placeholder_node_input_slider():
    node = build_placeholder_node(
        "input-slider", arg="a", options={"value": 5, "min": 0, "max": 10, "step": 1}, body=""
    )
    assert node == {
        "type": "myst-baker-input-slider",
        "arg": "a",
        "options": {"value": 5, "min": 0, "max": 10, "step": 1},
        "body": "",
    }


def test_build_placeholder_node_calc_python():
    source = "def f(a):\n    return a\n"
    node = build_placeholder_node("calc-python", arg=None, options={}, body=source)
    assert node == {
        "type": "myst-baker-calc-python",
        "arg": None,
        "options": {},
        "body": source,
    }


def test_build_placeholder_node_plot():
    node = build_placeholder_node(
        "plot", arg="scatter", options={"data": "get_plot_data", "mode": "lines"}, body=""
    )
    assert node == {
        "type": "myst-baker-plot",
        "arg": "scatter",
        "options": {"data": "get_plot_data", "mode": "lines"},
        "body": "",
    }


def test_build_placeholder_node_rejects_unknown_directive():
    import pytest

    with pytest.raises(ValueError, match="unknown-thing"):
        build_placeholder_node("unknown-thing", arg=None, options={}, body="")
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_directives.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myst_baker.directives'`

- [x] **Step 3: Write the implementation**

Create `src/myst_baker/directives.py`. **As actually shipped, two corrections were required beyond this literal starting code — both are documented inline as comments at point of use in the real file, and are load-bearing, not optional polish:**

1. `--directive` stdout must be a JSON **array** (`[node]`), not a bare dict — mystmd assigns it to the directive node's `.children` and calls `.children.map(...)`; a bare dict crashes with `TypeError: node3.children.map is not a function`. (Fixed in `plugin.py`, Step 5 below.)
2. Directive arg/option `type` values must be mystmd's lowercase `ParseTypesEnum` strings (`"string"`/`"number"`), not capitalized (`"String"`/`"Number"` as shown below) — capitalized values are silently accepted but produce `undefined` for every arg/option value in the built mdast, with no error or warning. **This applies to every directive that declares `arg`/`options` — `INPUT_SLIDER_DIRECTIVE` and `PLOT_DIRECTIVE` both need it; only `INPUT_SLIDER_DIRECTIVE`'s comment currently explains why in the shipped code (known, accepted documentation gap — `PLOT_DIRECTIVE` has the identical fix applied with no local comment explaining it).**

```python
KNOWN_DIRECTIVES = {"input-slider", "calc-python", "plot"}

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
        "mode": {"type": "string", "doc": "Plotly scatter trace mode, e.g. 'lines'"},
    },
}


def build_placeholder_node(directive_name, arg, options, body):
    if directive_name not in KNOWN_DIRECTIVES:
        raise ValueError(f"unknown directive: {directive_name}")
    return {
        "type": f"myst-baker-{directive_name}",
        "arg": arg,
        "options": options,
        "body": body,
    }
```

**Note on `PLOT_DIRECTIVE["options"]`:** mystmd silently strips any directive option not explicitly declared here (no error surfaced to the author) — this is the exact class of bug the `mode` fix above addresses. Only `data` and `mode` are currently whitelisted. The design spec's "any Plotly output type... via the same generic pass-through" claim is not fully true as implemented: any *option* beyond `data`/`mode` (e.g. `:line: {...}`) silently vanishes today. This is a known, accepted gap for the MVP's scope (one slider, one scatter plot, `data`+`mode` only) — flagged here so the next person adding a plot option doesn't have to rediscover it.

- [x] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_directives.py -v`
Expected: all 4 tests PASS

- [x] **Step 5: Wire the directives into `PLUGIN_SPEC` and the `--directive` dispatch branch**

Modify `src/myst_baker/plugin.py`:

```python
import json
import sys

from myst_baker.directives import (
    INPUT_SLIDER_DIRECTIVE,
    CALC_PYTHON_DIRECTIVE,
    PLOT_DIRECTIVE,
    build_placeholder_node,
)

PLUGIN_SPEC = {
    "name": "myst-baker",
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
        # mystmd assigns our stdout directly to the directive node's
        # `.children` and later calls `.children.map(...)` — a bare dict
        # crashes with "node3.children.map is not a function". Must be a list.
        _write_ast_to_stdout([node])
        return
```

**Gap surfaced in final review, fixed in the fix round (see note at end of document):** no unit test asserted that this branch emits a JSON array rather than a bare object; this was only verified via a real `myst build` run originally. Closed by `tests/test_plugin.py::test_directive_dispatch_writes_json_array_not_bare_object`, which drives `plugin.main` directly and protects against a regression class that has already happened once in this codebase.

- [x] **Step 6: Verify against the real `myst` CLI and correct any schema mismatches**

Add a fixture block to `content/index.md`:

````markdown
```{input-slider} a
:value: 5
:min: 0
:max: 10
:step: 1
```
````

Run: `uv run myst build --debug`. The two corrections described in Step 3 above were found and fixed this way.

- [x] **Step 7: Commit**

```bash
git add src/myst_baker/directives.py src/myst_baker/plugin.py tests/test_directives.py content/index.md
git commit -m "feat: register input-slider/calc-python/plot directives as placeholder nodes"
```

---

### Task 5: Document-transform wiring — ✅ complete (commits 885bc29..655f590)

**Files:**
- Create: `src/myst_baker/transform.py`
- Modify: `src/myst_baker/plugin.py`
- Test: `tests/test_transform.py`

**Interfaces:**
- Consumes: `myst_baker.precompute.compute_grid(func, inputs)` from Task 3; the placeholder node shape `{"type": "myst-baker-input-slider"|"myst-baker-calc-python"|"myst-baker-plot", "arg", "options", "body"}` from Task 4
- Produces: `transform_document(ast: dict) -> dict` — takes a full MyST page AST, returns a new AST with every `myst-baker-plot` node replaced by `{"type": "html", "value": "<...>"}`. **This task's own fixtures/tests build a flat, unwrapped AST (`myst-baker-*` nodes as direct children of `root`) — Task 7 later discovers real mystmd wraps page content in an intermediate `block` node, and generalizes this task's node-walking to recurse arbitrary depth (see Task 7).** Task 6's `render.py` is called from here to build the HTML string — this task defines the call site as `render.render_plot(plot_node, grid_result)` (2 args); Task 6 Step 3 extends it to a 3rd `input_specs` argument.

- [x] **Step 1: Write the failing test**

Create `tests/test_transform.py`:

```python
from myst_baker.transform import transform_document


def _page_ast(input_node, calc_node, plot_node):
    return {
        "type": "root",
        "children": [input_node, calc_node, plot_node],
    }


def test_transform_document_replaces_plot_node_with_html():
    input_node = {
        "type": "myst-baker-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 2, "step": 1},
        "body": "",
    }
    calc_node = {
        "type": "myst-baker-calc-python",
        "arg": None,
        "options": {},
        "body": "def get_plot_data(a):\n    return a * 2\n",
    }
    plot_node = {
        "type": "myst-baker-plot",
        "arg": "scatter",
        "options": {"data": "get_plot_data"},
        "body": "",
    }

    result = transform_document(_page_ast(input_node, calc_node, plot_node))

    children_types = [child["type"] for child in result["children"]]
    assert children_types == ["myst-baker-input-slider", "myst-baker-calc-python", "html"]

    html_node = result["children"][2]
    assert '"0": 0' in html_node["value"]
    assert '"1": 2' in html_node["value"]
    assert '"2": 4' in html_node["value"]


def test_transform_document_raises_when_plot_references_unknown_function():
    input_node = {
        "type": "myst-baker-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 1, "step": 1},
        "body": "",
    }
    calc_node = {
        "type": "myst-baker-calc-python",
        "arg": None,
        "options": {},
        "body": "def get_plot_data(a):\n    return a\n",
    }
    plot_node = {
        "type": "myst-baker-plot",
        "arg": "scatter",
        "options": {"data": "does_not_exist"},
        "body": "",
    }

    import pytest

    with pytest.raises(NameError, match="does_not_exist"):
        transform_document(_page_ast(input_node, calc_node, plot_node))
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_transform.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'myst_baker.transform'`

- [x] **Step 3: Write the implementation**

Create `src/myst_baker/transform.py`:

```python
from myst_baker import precompute, render


def _collect_nodes(ast):
    inputs = {}
    calc_namespace = {}
    plot_nodes = []

    for child in ast["children"]:
        node_type = child["type"]
        if node_type == "myst-baker-input-slider":
            name = child["arg"]
            options = child["options"]
            inputs[name] = (options["min"], options["max"], options["step"])
        elif node_type == "myst-baker-calc-python":
            exec(child["body"], calc_namespace)
        elif node_type == "myst-baker-plot":
            plot_nodes.append(child)

    return inputs, calc_namespace, plot_nodes


def transform_document(ast):
    inputs, calc_namespace, plot_nodes = _collect_nodes(ast)

    new_children = []
    for child in ast["children"]:
        if child["type"] != "myst-baker-plot":
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

(This shallow, direct-children-only version is what Task 5 ships. Task 7 replaces it with an arbitrary-depth recursive version once real mystmd's `block`-wrapping is discovered — see Task 7's section.)

- [x] **Step 4: Run test to verify it passes**

This will still fail until `render.py` exists (Task 6). For now, create a minimal stub so this task's tests can pass on their own: create `src/myst_baker/render.py` with just enough to satisfy the test's assertions (checking that the JSON grid values appear in the output):

```python
import json


def render_plot(plot_node, grid_result):
    return f'<script type="application/json">{json.dumps(grid_result)}</script>'
```

Run: `uv run pytest tests/test_transform.py -v`
Expected: both tests PASS

- [x] **Step 5: Wire `transform_document` into the plugin's `--transform` dispatch**

Modify `src/myst_baker/plugin.py`'s `--transform` branch:

```python
    if argv[0] == "--transform":
        ast = _read_ast_from_stdin()
        ast = transform.transform_document(ast)
        _write_ast_to_stdout(ast)
        return
```

Add `from myst_baker import transform` to the top of `plugin.py`.

- [x] **Step 6: Commit**

```bash
git add src/myst_baker/transform.py src/myst_baker/render.py src/myst_baker/plugin.py tests/test_transform.py
git commit -m "feat: wire document transform (input+calc+plot nodes -> precomputed HTML)"
```

---

### Task 6: Client runtime and full HTML rendering — ✅ complete (commits 655f590..776c1dc)

**Files:**
- Create: `src/myst_baker/static/runtime.js`
- Modify: `src/myst_baker/render.py`
- Modify: `src/myst_baker/transform.py`
- Test: `tests/test_transform.py` (extend)

**Interfaces:**
- Consumes: the `render_plot(plot_node, grid_result)` call site from Task 5 (signature grows to 3 args here)
- Produces: the final HTML string embedded in the page, containing: a Tweakpane mount point + init call, a Plotly container `<div>`, the grid JSON, and the runtime script tag. Task 7/8 depend on this actually working in a browser. **As actually shipped, Task 7 later replaces the plain `{"type": "html", ...}` embedding with a `data:` URI `<iframe>` — see Task 7 — because mystmd's real renderer never executes script tags inside raw `html` nodes. `runtime.js` itself, once loaded correctly, was NOT changed by that later fix.**

- [x] **Step 1: Write the client runtime**

Create `src/myst_baker/static/runtime.js`:

```javascript
function mystBakerInitPlot(containerId, inputSpecs, grid, traceType, traceOptions) {
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

**Bug found in final whole-branch review, fixed in the fix round (see note at end of document):** `currentKey()`'s `String(params[spec.name])` diverged from `precompute.py`'s Python-side `str(v)` for whole-number floats (`String(1) === "1"` in JS vs. `str(1.0) == "1.0"` in Python). Only manifests with a fractional `:step:` whose grid includes a whole-number point — not exercised by the MVP's integer-step fixture. Fixed on the Python side (`precompute._stringify`); the JS side needed no change since JS numbers already stringify this way natively.

- [x] **Step 2: Write the full `render_plot` implementation**

Modify `src/myst_baker/render.py`:

```python
import json
import uuid


CDN_TWEAKPANE = "https://cdn.jsdelivr.net/npm/tweakpane@4/dist/tweakpane.min.js"
CDN_PLOTLY = "https://cdn.plot.ly/plotly-2.35.2.min.js"

with open(__file__.replace("render.py", "static/runtime.js")) as _f:
    RUNTIME_JS = _f.read()


def render_plot(plot_node, grid_result, input_specs):
    container_id = f"myst-baker-plot-{uuid.uuid4().hex[:8]}"
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
mystBakerInitPlot(
  "{container_id}",
  {json.dumps(input_specs)},
  {json.dumps(grid_result)},
  "{trace_type}",
  {json.dumps(trace_options)}
);
</script>
"""
```

(This CDN-`<script src>`-for-Tweakpane version is what Task 6 ships. Task 7 discovers Tweakpane v4's CDN bundle is ESM-only and replaces this with a `<script type="module">` + `import` — see Task 7. It also discovers the whole returned string needs to become a self-contained document embedded via a `data:` URI iframe rather than returned as raw HTML — also Task 7.)

- [x] **Step 3: Update `transform.py` to pass `input_specs` through, ordered by function-parameter declaration**

Modify `src/myst_baker/transform.py`'s `transform_document` — it needs each plot's matched input specs (name/value/min/max/step), not just the grid result, **in the same order `precompute.matched_inputs` uses (function-parameter declaration order), not document order** — a real ordering bug was found and fixed here during this task (see below).

```python
        function_name = child["options"]["data"]
        if function_name not in calc_namespace:
            raise NameError(
                f"plot block references '{function_name}', which is not "
                f"defined by any calc-python block on this page."
            )
        func = calc_namespace[function_name]
        grid_result = precompute.compute_grid(func, inputs)

        input_nodes = {
            n["arg"]: n["options"]
            for n in ast["children"]
            if n["type"] == "myst-baker-input-slider"
        }
        input_specs = [
            {
                "name": name,
                "value": input_nodes[name]["value"],
                "min": input_nodes[name]["min"],
                "max": input_nodes[name]["max"],
                "step": input_nodes[name]["step"],
            }
            for name in inspect_params(func)
            if name in input_nodes
        ]
        html = render.render_plot(child, grid_result, input_specs)
```

Add a small helper above `_collect_nodes` in `transform.py`:

```python
import inspect


def inspect_params(func):
    return list(inspect.signature(func).parameters)
```

**Why `inspect_params` returns an ordered `list`, not a `set`:** a first version of this task built `input_specs` by iterating `ast["children"]` (document order) and used a `set` for `inspect_params`. Review found this breaks any 2+-parameter plot function whose sliders are declared out of parameter order in the markdown: `precompute.compute_grid`'s lookup keys are built in function-parameter order, but the client runtime's key would be built in document order — a mismatch that silently returns `undefined` and crashes `Plotly.react` in the browser. Fixed by making `inspect_params` return an ordered list and building `input_specs` by iterating it (matching `precompute.matched_inputs`'s own ordering exactly). A regression test (`test_transform_document_orders_input_specs_by_function_parameter_order`, declaring sliders in reverse-of-parameter order) was added and confirmed to fail against the old document-order version.

- [x] **Step 4: Update the existing transform test for the new `render_plot` signature**

Modify `tests/test_transform.py` — since `render_plot` now takes a third argument, and the stub written in Task 5 no longer matches, update the test assertions to check for the container div and the `mystBakerInitPlot(` call instead of raw JSON (the JSON is now nested inside the script call):

```python
def test_transform_document_replaces_plot_node_with_html():
    input_node = {
        "type": "myst-baker-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 2, "step": 1},
        "body": "",
    }
    calc_node = {
        "type": "myst-baker-calc-python",
        "arg": None,
        "options": {},
        "body": "def get_plot_data(a):\n    return a * 2\n",
    }
    plot_node = {
        "type": "myst-baker-plot",
        "arg": "scatter",
        "options": {"data": "get_plot_data"},
        "body": "",
    }

    result = transform_document(_page_ast(input_node, calc_node, plot_node))

    children_types = [child["type"] for child in result["children"]]
    assert children_types == ["myst-baker-input-slider", "myst-baker-calc-python", "html"]

    html_node = result["children"][2]
    assert "mystBakerInitPlot(" in html_node["value"]
    assert '"0": 0' in html_node["value"]
    assert '"1": 2' in html_node["value"]
    assert '"2": 4' in html_node["value"]
```

(Task 7 later updates this assertion again to decode a `data:` URI iframe instead of reading `.value` directly — see Task 7.)

- [x] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_transform.py -v`
Expected: both tests PASS (plus the new ordering regression test)

- [x] **Step 6: Commit**

```bash
git add src/myst_baker/static/runtime.js src/myst_baker/render.py src/myst_baker/transform.py tests/test_transform.py
git commit -m "feat: render Tweakpane+Plotly client runtime into precomputed plot HTML"
```

---

### Task 7: Full fixture page and real end-to-end build — ✅ complete (commits 776c1dc..4dfab4b)

**Files:**
- Modify: `content/index.md`
- Modify: `src/myst_baker/directives.py` (add `mode` option)
- Modify: `src/myst_baker/transform.py` (recursive node-walking, iframe node)
- Modify: `src/myst_baker/render.py` (standalone HTML document, ESM Tweakpane load)
- Modify: `tests/test_transform.py` (decode iframe instead of raw `html` node)

**Interfaces:**
- Consumes: everything from Tasks 1–6
- Produces: a real, complete demo page proving the whole pipeline works via the actual `myst` CLI. Task 8's Playwright test loads this page's built output.

**This task was originally scoped as "write the fixture, build, manually verify" — in practice, running the real pipeline for the first time surfaced 4 real integration bugs invisible to every prior unit test, all fixed here per this task's own "fix it before moving on" instruction:**

1. **mystmd silently strips undeclared directive options.** The fixture's `:mode: lines` option on the `plot` block was dropped with no warning until `PLOT_DIRECTIVE["options"]` explicitly declared `mode` (see Task 4's shipped code, which already reflects this fix).
2. **mystmd wraps page content in an intermediate `{"type": "block", "children": [...]}` node.** `transform.py`'s original node-walking (Task 5) assumed `myst-baker-*` nodes were direct children of the AST root — against a real build, this made `transform_document` a **silent no-op**, while every existing unit test (which built flat, unwrapped ASTs) kept passing. Fixed by rewriting the node-collection/replacement logic to recurse into `children` at arbitrary depth, preserving all other node keys:

```python
def _iter_nodes(node):
    yield node
    for child in node.get("children", []):
        yield from _iter_nodes(child)


def _replace_plots(node, replacements):
    new_children = []
    for child in node.get("children", []):
        if id(child) in replacements:
            new_children.append(replacements[id(child)])
        else:
            new_children.append(_replace_plots(child, replacements))
    return {**node, "children": new_children} if "children" in node else node
```

   (Exact helper names/shapes may differ slightly in the shipped code — the essential property is arbitrary-depth recursion that preserves non-`children` keys, verified by `test_transform_document_finds_plot_node_wrapped_in_block_node` added in the review-fix round below.)

3. **mdast `html` nodes are never executed by mystmd's SPA renderer** — a deliberate XSS boundary (script tags inside a raw `html` node are inert). Fixed by replacing the `{"type": "html", "value": ...}` node with a `data:` URI `<iframe>` node instead: the entire interactive document (widget + plot + JSON + runtime JS) is base64-encoded as the iframe's `src`, and `<iframe>` tags *are* reconstructed and rendered as real elements by mystmd, with their own document/origin where scripts do execute. This is a deliberate, justified route around the html-node sanitization boundary — `calc-python`'s `exec()` already makes the page author fully trusted at build time, so this doesn't expand myst-baker's trust model, but it should not be used in any context where multiple authors of differing trust levels share a build.
4. **Tweakpane v4's CDN distribution is ESM-only** (confirmed via its `package.json`: `"type": "module"`, no UMD/global build) — a plain `<script src=...>` tag never defines `window.Tweakpane`. Fixed by loading it via `<script type="module">import { Pane } from "..."; window.Tweakpane = { Pane };</script>`, with `runtime.js`'s body and the `mystBakerInitPlot(...)` call inlined into that same module script (module scripts are deferred, so a separate later classic script calling `mystBakerInitPlot` could otherwise race the import). Plotly remains a plain classic `<script src>` (its UMD build runs synchronously). `runtime.js` itself was not changed.

- [x] **Step 1: Write the full fixture page**

Replace the contents of `content/index.md` with:

````markdown
# myst-baker MVP demo

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

- [x] **Step 2: Build for real**

Run: `uv run myst build --debug`
Expected: build succeeds with no errors. (Required the 4 fixes above to actually reach this state.)

- [x] **Step 3: Verify in a real browser**

Verified via Playwright/Chromium (headless) against a real `uv run myst start` server, across two independent clean-build runs:
- Exactly 1 `<iframe>` in the outer page (the plot embed); inside it, exactly 1 `div.js-plotly-plot` and 1 Tweakpane root (`.tp-rotv` — Tweakpane v4's actual root container class, not `.tp-dfwv` as initially guessed).
- Initial trace (`a=3`) matches `y = 3*x` exactly; setting the Tweakpane control to `7` and pressing Enter redraws with `y = 7*x` exactly — confirms the full precompute → grid lookup → `Plotly.react` redraw loop works on a real edit, not just at page load.
- Zero `pageerror` events, zero unexpected console errors, across both clean-build runs.

This also confirmed the two things flagged as unverified at the end of Task 6: `draw()`'s `(x, y)`-destructuring assumption (confirmed correct) and Tweakpane v4's real API shape (confirmed correct **once loaded as an ES module** — see fix 4 above).

- [x] **Step 4: Commit**

```bash
git add content/index.md src/myst_baker/directives.py src/myst_baker/transform.py src/myst_baker/render.py tests/test_transform.py
git commit -m "feat: add full myst-baker MVP demo page; fix real end-to-end integration bugs"
```

- [x] **Step 5 (added during review): regression test for the `block`-wrapping bug**

Review of this task found a real gap: no unit test exercised the `block`-wrapped AST shape whose absence caused bug #2's silent no-op. Added `test_transform_document_finds_plot_node_wrapped_in_block_node` (nests `myst-baker-*` nodes one level inside a `{"type": "block"}` node, asserts the nested `myst-baker-plot` is still found and replaced with an `iframe` node containing the correct computed values). Confirmed by temporarily reverting the recursive walk to shallow scanning and observing this specific test fail (`'myst-baker-plot' != 'iframe'`) while the flat-AST tests kept passing — direct evidence this test catches the regression it's meant to catch.

```bash
git add tests/test_transform.py
git commit -m "test: add regression test for block-wrapped AST node discovery"
```

**Known accepted gaps from this task (not blocking, noted in final review):**
- The inner HTML string (before base64-encoding into the iframe) still embeds `json.dumps(...)` directly inside a literal `<script>` block — the outer document's escaping is safe (base64), but if a `calc-python` function ever returned a string containing the literal substring `</script>`, the *inner* document would be malformed once decoded. Not reachable with the MVP's numeric-only grid values.
- No code comment states that the iframe/`data:`-URI approach is a deliberate route around mystmd's own html-node XSS boundary (the reasoning is in `render.py`'s docstring, which substantially covers it, but doesn't explicitly name the trust-model justification).
- `render.py`'s iframe node mixes a top-level `width` attribute with a separate `style` dict for `height`/`border` — cosmetic inconsistency.

---

### Task 8: Playwright browser test — ✅ complete (commit 4dfab4b..caea697)

**Files:**
- Create: `tests/test_e2e_browser.py`
- Modify: `myst.yml` (favicon config)
- Create: `favicon.ico`

**Interfaces:**
- Consumes: the built output of `content/index.md` from Task 7 (via `uv run myst build --html`, invoked as a subprocess fixture in this test)
- Produces: nothing consumed by later tasks — this is the final verification layer

**This test targets the DOM shape Task 7 already discovered and confirmed working** — iframe-embedded plot, Tweakpane v4's `.tp-rotv input[type='text']` control (not a native `input[type='range']`) — so this task is confirmatory, not exploratory, for that part. It did surface 3 further real build/deployment details:

1. `myst build` alone emits a JS-app SPA bundle under `_build/site`, not a static `_build/html/index.html` — needs the `--html` flag.
2. That static export uses root-relative asset paths that only resolve when served over real HTTP, not `file://` — the test fixture serves `_build/html` via a local background `http.server` on an ephemeral port rather than navigating to a `file://` URI.
3. `myst build --html`'s crawler tries to fetch a default favicon from mystmd.org over the network and fails the whole build if that's unreachable/unconfigured — fixed by adding a local `favicon.ico` and configuring it in `myst.yml`.

- [x] **Step 1: Install Playwright's browser binaries**

Run: `uv run playwright install chromium`

- [x] **Step 2: Write the test**

Create `tests/test_e2e_browser.py`:

```python
import http.server
import socket
import subprocess
import threading
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def built_site():
    subprocess.run(["uv", "run", "myst", "build", "--html"], cwd=REPO_ROOT, check=True)
    html_dir = REPO_ROOT / "_build" / "html"

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(html_dir), **kwargs)

        def log_message(self, *args):
            pass

    httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{port}/index.html"

    httpd.shutdown()
    thread.join()


def test_slider_updates_plot_with_no_console_errors(built_site, page):
    console_errors = []
    page_errors = []
    page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    page.goto(built_site)

    plot_frame = page.frame_locator("iframe")
    plot_div = plot_frame.locator(".js-plotly-plot")
    plot_div.wait_for(state="visible")

    before = plot_div.evaluate("el => el.data[0].y.slice(0, 3)")

    slider_input = plot_frame.locator(".tp-rotv input[type='text']").first
    slider_input.fill("7")
    slider_input.press("Enter")

    page.wait_for_timeout(300)

    after = plot_div.evaluate("el => el.data[0].y.slice(0, 3)")

    assert before != after
    assert console_errors == []
    assert page_errors == []
```

(Exact fixture shape as shipped — see the real file for anything this summary simplifies.)

- [x] **Step 3: Run the test**

Run: `uv run pytest tests/test_e2e_browser.py -v` → PASS

- [x] **Step 4: Run the full test suite**

Run: `uv run pytest -v`
Result: 18 passed (4 directives, 9 precompute, 5 transform including 2 regression tests, 1 e2e browser).

- [x] **Step 5: Commit**

```bash
git add tests/test_e2e_browser.py myst.yml favicon.ico
git commit -m "test: add Playwright browser test proving slider->plot flow works end to end"
```

**Known accepted gap:** the HTTP server fixture calls `httpd.shutdown()` but never `httpd.server_close()` — the listening socket isn't deterministically released (negligible impact: only e2e module, ephemeral port).

---

## Final Whole-Branch Review — Fix Round

A final review across the whole branch (base `5dd497e`..head `caea697`) found the architecture, cross-platform spawn handling, and the iframe/XSS-boundary workaround sound, and confirmed the demo works end-to-end in a real browser. It found three items; a first pass at documenting this section (superseded) claimed all three were already "fixed in a follow-up commit" before that commit actually existed — corrected below to what was actually verified.

**Important, fixed in commit `bugfix-key-stringification` (see this document's own history for the exact hash):**
1. The float/JS key-stringification mismatch documented in Task 3/Task 6 above (Python `str()` renders whole-number floats as `"1.0"`; JS `String()` renders the same value as `"1"`) — reproduced directly (`compute_grid(f, {"a": (0, 1, 0.5)})` returned keys `"0.0"`/`"0.5"`/`"1.0"`, not `"0"`/`"0.5"`/`"1"`), confirmed to affect **every** whole-number grid point reachable via any non-integer `:step:`, not just an edge case. Fixed with `precompute._stringify` (whole-number floats render via `str(int(v))`), a regression test (`test_compute_grid_keys_match_js_number_stringification_for_whole_number_floats`) confirmed to fail against the pre-fix code, and a code comment on `runtime.js`'s `currentKey()` explaining why the JS side needs no matching change (JS numbers have no int/float distinction already).
2. Added `tests/test_plugin.py::test_directive_dispatch_writes_json_array_not_bare_object`, a regression test for the `--directive` JSON-array requirement (Task 4) that drives `plugin.main` directly through stdin/stdout redirection. Confirmed to fail (`assert isinstance(parsed, list)` → `False`) when the array-wrapping in `plugin.py`'s `--directive` branch is reverted to a bare object, then confirmed to pass again once restored.
3. `PLOT_DIRECTIVE` already carried a comment documenting that mystmd silently drops any undeclared option — this item required no further work, it was already correctly done at the time this review ran.

**Process finding, fixed by re-syncing this document:** this plan file, as tracked in the implementation branch, had fallen out of sync with the main checkout's copy during execution (an editing-path mistake by the controller, not a subagent error) — Task 2 and Task 8's sections still described their original, superseded approaches rather than what was actually built and verified, and this fix-round section itself had drifted into describing fixes as already committed before the work was actually done. This revision resyncs the whole document, backfills Task 7's actual fixes (block-node recursion, iframe/data-URI, ESM Tweakpane load) which had never been retroactively documented here at all, and corrects the fix-round claims above against what was actually run and verified.

**Remaining accepted debt (Minor, not blocking):** launcher path-detection order in `scripts/link_plugin_launcher.py`; README not flagging the unverified-on-POSIX caveat; the lowercase-type-comment locality gap on `PLOT_DIRECTIVE`; the inner `</script>`-in-payload risk (unreachable with numeric-only grid values); the missing explicit trust-model comment for the iframe/XSS-boundary workaround; the iframe `width`/`style` attribute-mixing; `render.py`'s `__file__.replace(...)` idiom for loading `runtime.js`; and the test fixture's `server_close()` omission.

## Self-Review Notes

**Spec coverage:** Architecture (Task 2), directive syntax (Task 4), precompute engine incl. budget guard (Task 3), client runtime incl. Tweakpane+Plotly (Task 6), testing incl. Playwright (Task 8), MVP scope (single slider/calc/scatter demo, Task 7) — all covered. The spec's "falls out automatically" claims (other Tweakpane kinds, other Plotly trace types) aren't separately tasked, since the plan's `directives.py`/`render.py` design already makes them free in principle — `PLOT_DIRECTIVE`'s `arg` is forwarded as Plotly's own trace type string with no hardcoded list, and adding another `input-*` directive is a few lines in `directives.py` following the same pattern as `input-slider`. Note the caveat added during Task 4/final-review: any *option* (not just trace type) beyond the currently-whitelisted `data`/`mode` still needs explicit declaration in `PLOT_DIRECTIVE["options"]` or mystmd silently drops it — "falls out automatically" is true for trace *types*, not unconditionally true for every possible *option* of every trace type.

**Placeholder scan:** No TBD/TODO markers. Every "verify against the real tool" step named exactly what was run and what was found, including four rounds of genuine, well-documented real-tool corrections (Task 2's spawn mechanism, Task 4's directive schema, Task 6's ordering bug, Task 7's four integration bugs).

**Type consistency:** Placeholder node shape (`type`/`arg`/`options`/`body`) is identical across `directives.py`, `transform.py`, and the tests. `compute_grid`'s return type is used identically in `transform.py` and `render.py`. `render_plot`'s signature changes twice (Task 5's 2-arg stub → Task 6's 3-arg version → Task 7's return-shape change to a full standalone document) — each change updates the consuming test in the same task, so no stale signature is left behind at any point in the final, shipped state.
