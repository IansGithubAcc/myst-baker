# Calc Fence Syntax (`python{calc}`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `{calc-python}` MyST directive with a plain-code-fence convention, `python{calc}`, so calc blocks get real IDE Python syntax highlighting while behaving identically at build time.

**Architecture:** `calc-python` currently is a real MyST directive (`{calc-python}`), which mystmd's parser only recognizes when the fence's info string starts with `{`, which blocks editors from ever recognizing it as Python. Since calc blocks declare no `:key: value` options and their source is never rendered to the reader, MyST's directive machinery isn't actually needed for them — mystmd will already produce a plain mdast `code` node for a fence like `` ```python{calc} `` (real `python` language token, so editors highlight it), and myst-baker's own document-transform (which already walks the whole page AST for every `myst-baker-*` node) can recognize that `code` node itself, purely as a Python-side convention, instead of relying on mystmd's directive dispatch.

**Tech Stack:** Python 3, mystmd (JS, invoked as a subprocess via `myst build`), pytest.

## Global Constraints

- No back-compat shim for the old `` ```{calc-python} `` fence form — every existing occurrence in code and docs is rewritten, not dual-supported.
- Only `python` is a supported calc-block language; any other language prefix (e.g. `r{calc}`) must fail the build loudly with a clear error, not silently mis-execute.
- `input-slider`, `input-checkbox`, `input-dropdown`, and `plot` are unaffected — they remain real MyST directives and are out of scope for every task below.
- mdast's `code` node uses `value` for its body text (not `body` — that field name is specific to myst-baker's own directive placeholder nodes, which `code` nodes are not).

---

### Task 1: Remove `calc-python` as a MyST directive

**Files:**
- Modify: `src/myst_baker/directives.py`
- Modify: `src/myst_baker/plugin.py`
- Test: `tests/test_directives.py`
- Test: `tests/test_plugin.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `KNOWN_DIRECTIVES` (in `src/myst_baker/directives.py`) no longer contains `"calc-python"`; `build_placeholder_node("calc-python", ...)` now raises `ValueError` like any other unrecognized directive name. `PLUGIN_SPEC["directives"]` (in `src/myst_baker/plugin.py`) no longer lists a calc directive. Task 2 does not depend on anything produced here beyond these two facts.

- [ ] **Step 1: Update the two tests to expect `calc-python` is no longer a known directive**

  In `tests/test_directives.py`, replace this test:

  ```python
  def test_build_placeholder_node_calc_python():
      source = "def f(a):\n    return a\n"
      node = build_placeholder_node("calc-python", arg=None, options={}, body=source)
      assert node == {
          "type": "myst-baker-calc-python",
          "arg": None,
          "options": {},
          "body": source,
      }
  ```

  with:

  ```python
  def test_build_placeholder_node_rejects_calc_python_as_directive():
      import pytest

      with pytest.raises(ValueError, match="calc-python"):
          build_placeholder_node("calc-python", arg=None, options={}, body="")
  ```

  In `tests/test_plugin.py`, replace:

  ```python
  def test_plugin_spec_lists_all_directives(monkeypatch):
      out = io.StringIO()
      monkeypatch.setattr("sys.stdout", out)
      plugin.main([])
      spec = json.loads(out.getvalue())
      directive_names = {d["name"] for d in spec["directives"]}
      assert directive_names == {
          "input-slider",
          "input-checkbox",
          "input-dropdown",
          "calc-python",
          "plot",
      }
  ```

  with:

  ```python
  def test_plugin_spec_lists_all_directives(monkeypatch):
      out = io.StringIO()
      monkeypatch.setattr("sys.stdout", out)
      plugin.main([])
      spec = json.loads(out.getvalue())
      directive_names = {d["name"] for d in spec["directives"]}
      assert directive_names == {
          "input-slider",
          "input-checkbox",
          "input-dropdown",
          "plot",
      }
  ```

- [ ] **Step 2: Run tests to verify these two fail**

  Run: `uv run pytest tests/test_directives.py tests/test_plugin.py -v`
  Expected: `test_build_placeholder_node_rejects_calc_python_as_directive` FAILS (current code still builds a `myst-baker-calc-python` node instead of raising), and `test_plugin_spec_lists_all_directives` FAILS (current spec still includes `"calc-python"`).

- [ ] **Step 3: Remove `CALC_PYTHON_DIRECTIVE` from `src/myst_baker/directives.py`**

  Change the `KNOWN_DIRECTIVES` line from:

  ```python
  KNOWN_DIRECTIVES = {"input-slider", "input-checkbox", "input-dropdown", "calc-python", "plot"}
  ```

  to:

  ```python
  KNOWN_DIRECTIVES = {"input-slider", "input-checkbox", "input-dropdown", "plot"}
  ```

  Delete the entire `CALC_PYTHON_DIRECTIVE` block:

  ```python
  CALC_PYTHON_DIRECTIVE = {
      "name": "calc-python",
      "doc": "A raw Python function definition, executed once per grid combination.",
      "body": {"type": "string", "doc": "Python source defining one function"},
  }
  ```

- [ ] **Step 4: Remove `CALC_PYTHON_DIRECTIVE` from `src/myst_baker/plugin.py`**

  Change the import block from:

  ```python
  from myst_baker.directives import (
      INPUT_SLIDER_DIRECTIVE,
      INPUT_CHECKBOX_DIRECTIVE,
      INPUT_DROPDOWN_DIRECTIVE,
      CALC_PYTHON_DIRECTIVE,
      PLOT_DIRECTIVE,
      build_placeholder_node,
  )
  ```

  to:

  ```python
  from myst_baker.directives import (
      INPUT_SLIDER_DIRECTIVE,
      INPUT_CHECKBOX_DIRECTIVE,
      INPUT_DROPDOWN_DIRECTIVE,
      PLOT_DIRECTIVE,
      build_placeholder_node,
  )
  ```

  Change the `PLUGIN_SPEC["directives"]` list from:

  ```python
  PLUGIN_SPEC = {
      "name": "myst-baker",
      "directives": [
          INPUT_SLIDER_DIRECTIVE,
          INPUT_CHECKBOX_DIRECTIVE,
          INPUT_DROPDOWN_DIRECTIVE,
          CALC_PYTHON_DIRECTIVE,
          PLOT_DIRECTIVE,
      ],
      "transforms": [{"stage": "document"}],
  }
  ```

  to:

  ```python
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
  ```

- [ ] **Step 5: Run the full test suite to verify everything (still) passes**

  Run: `uv run pytest tests/test_directives.py tests/test_plugin.py tests/test_transform.py -v`
  Expected: all PASS. (`tests/test_transform.py` still builds `myst-baker-calc-python` nodes by hand and doesn't go through `build_placeholder_node`/`PLUGIN_SPEC`, so it's unaffected by this task — Task 2 changes it.)

- [ ] **Step 6: Commit**

  ```bash
  git add src/myst_baker/directives.py src/myst_baker/plugin.py tests/test_directives.py tests/test_plugin.py
  git commit -m "refactor: remove calc-python as a MyST directive"
  ```

---

### Task 2: Recognize `python{calc}` plain code fences in the document transform

**Files:**
- Modify: `src/myst_baker/transform.py`
- Test: `tests/test_transform.py`

**Interfaces:**
- Consumes: nothing from Task 1 beyond it being merged first (no shared code).
- Produces: `transform_document(ast)` (unchanged signature) now recognizes any mdast `code` node whose `lang`+`meta` reconstruct to `<word>{calc}` as a calc block, executing its `value` into the shared calc namespace when `<word> == "python"`, and raising `ValueError` otherwise. Plain `code` nodes that don't end in `{calc}` (e.g. an ordinary `` ```python `` prose example) are left untouched — not executed, not erroring.

- [ ] **Step 1: Rewrite `tests/test_transform.py` to use the new fence convention and cover the new behavior**

  Replace the entire file with:

  ```python
  import base64
  import json

  import pytest

  from myst_baker.transform import transform_document


  def _decode_iframe_html(iframe_node):
      assert iframe_node["type"] == "iframe"
      prefix = "data:text/html;base64,"
      assert iframe_node["src"].startswith(prefix)
      encoded = iframe_node["src"][len(prefix) :]
      return base64.b64decode(encoded).decode("utf-8")


  def _page_ast(input_node, calc_node, plot_node):
      return {
          "type": "root",
          "children": [input_node, calc_node, plot_node],
      }


  def _calc_node(source):
      return {"type": "code", "lang": "python{calc}", "value": source}


  def test_transform_document_replaces_plot_node_with_html():
      input_node = {
          "type": "myst-baker-input-slider",
          "arg": "a",
          "options": {"value": 1, "min": 0, "max": 2, "step": 1},
          "body": "",
      }
      calc_node = _calc_node("def get_plot_data(a):\n    return a, a * 2\n")
      plot_node = {
          "type": "myst-baker-plot",
          "arg": "scatter",
          "options": {"data": "get_plot_data"},
          "body": "",
      }

      result = transform_document(_page_ast(input_node, calc_node, plot_node))

      children_types = [child["type"] for child in result["children"]]
      assert children_types == ["myst-baker-input-slider", "code", "iframe"]

      iframe_node = result["children"][2]
      html = _decode_iframe_html(iframe_node)
      assert "mystBakerInitPlot(" in html
      assert '"0": {"x": 0, "y": 0}' in html
      assert '"1": {"x": 1, "y": 2}' in html
      assert '"2": {"x": 2, "y": 4}' in html


  def test_transform_document_raises_when_plot_references_unknown_function():
      input_node = {
          "type": "myst-baker-input-slider",
          "arg": "a",
          "options": {"value": 1, "min": 0, "max": 1, "step": 1},
          "body": "",
      }
      calc_node = _calc_node("def get_plot_data(a):\n    return a\n")
      plot_node = {
          "type": "myst-baker-plot",
          "arg": "scatter",
          "options": {"data": "does_not_exist"},
          "body": "",
      }

      with pytest.raises(NameError, match="does_not_exist"):
          transform_document(_page_ast(input_node, calc_node, plot_node))


  def test_transform_document_finds_plot_node_wrapped_in_block_node():
      # Regression test for a real end-to-end build bug: mystmd does not put
      # top-level page content directly under the document root's `children`.
      # Instead it wraps it in an intermediate `{"type": "block", "children":
      # [...]}` node (verified against a real `myst build --debug`), so the
      # actual shape is root -> block -> [myst-baker-* nodes], not root -> [myst-baker-*
      # nodes] directly as every other test in this file constructs it. A
      # scanner that only looks at `ast["children"]` (or otherwise fails to
      # recurse into nested `children`) finds nothing here and silently leaves
      # the myst-baker-plot node untransformed -- exactly the bug fixed in
      # transform.py's `_iter_nodes`/`_replace_plots`. This test must fail if
      # that recursion is ever reverted to shallow/immediate-children scanning.
      input_node = {
          "type": "myst-baker-input-slider",
          "arg": "a",
          "options": {"value": 1, "min": 0, "max": 2, "step": 1},
          "body": "",
      }
      calc_node = _calc_node("def get_plot_data(a):\n    return a, a * 2\n")
      plot_node = {
          "type": "myst-baker-plot",
          "arg": "scatter",
          "options": {"data": "get_plot_data"},
          "body": "",
      }

      block_node = {
          "type": "block",
          "children": [input_node, calc_node, plot_node],
      }
      ast = {
          "type": "root",
          "children": [block_node],
      }

      result = transform_document(ast)

      # The plot node nested inside the "block" wrapper must have been found
      # and replaced with an iframe node, in place.
      assert result["children"][0]["type"] == "block"
      inner_children_types = [child["type"] for child in result["children"][0]["children"]]
      assert inner_children_types == ["myst-baker-input-slider", "code", "iframe"]

      iframe_node = result["children"][0]["children"][2]
      html = _decode_iframe_html(iframe_node)
      assert "mystBakerInitPlot(" in html
      assert '"0": {"x": 0, "y": 0}' in html
      assert '"1": {"x": 1, "y": 2}' in html
      assert '"2": {"x": 2, "y": 4}' in html


  def test_transform_document_orders_input_specs_by_function_parameter_order():
      # The function declares parameters in the order (a, b), but the
      # input-slider blocks appear in the AST in the opposite order (b, then
      # a). input_specs must follow the function's declared parameter order
      # (matching precompute.matched_inputs / compute_grid's key order), not
      # the document order the slider blocks appear in -- otherwise the
      # client's lookup key built from input_specs won't match the
      # precomputed grid's keys.
      input_node_b = {
          "type": "myst-baker-input-slider",
          "arg": "b",
          "options": {"value": 1, "min": 0, "max": 1, "step": 1},
          "body": "",
      }
      input_node_a = {
          "type": "myst-baker-input-slider",
          "arg": "a",
          "options": {"value": 1, "min": 0, "max": 1, "step": 1},
          "body": "",
      }
      calc_node = _calc_node("def f(a, b):\n    return a, b\n")
      plot_node = {
          "type": "myst-baker-plot",
          "arg": "scatter",
          "options": {"data": "f"},
          "body": "",
      }

      ast = {
          "type": "root",
          "children": [input_node_b, input_node_a, calc_node, plot_node],
      }

      result = transform_document(ast)

      html = _decode_iframe_html(result["children"][-1])

      # runtime.js (embedded above) *defines* mystBakerInitPlot, so find the last
      # occurrence -- the actual invocation with the real arguments.
      call_index = html.rindex("mystBakerInitPlot(")
      array_start = html.index("[", call_index)
      input_specs, _ = json.JSONDecoder().raw_decode(html, array_start)

      assert [spec["name"] for spec in input_specs] == ["a", "b"]


  def test_transform_document_supports_checkbox_input():
      input_node = {
          "type": "myst-baker-input-checkbox",
          "arg": "enabled",
          "options": {"value": True},
          "body": "",
      }
      calc_node = _calc_node("def get_plot_data(enabled):\n    return enabled, int(enabled) * 2\n")
      plot_node = {
          "type": "myst-baker-plot",
          "arg": "scatter",
          "options": {"data": "get_plot_data"},
          "body": "",
      }

      result = transform_document(_page_ast(input_node, calc_node, plot_node))

      iframe_node = result["children"][2]
      html = _decode_iframe_html(iframe_node)
      assert '"true": {"x": true, "y": 2}' in html
      assert '"false": {"x": false, "y": 0}' in html


  def test_transform_document_supports_dropdown_input():
      input_node = {
          "type": "myst-baker-input-dropdown",
          "arg": "color",
          "options": {},
          "body": "red\ngreen\nblue",
      }
      calc_node = _calc_node("def get_plot_data(color):\n    return color, len(color)\n")
      plot_node = {
          "type": "myst-baker-plot",
          "arg": "scatter",
          "options": {"data": "get_plot_data"},
          "body": "",
      }

      result = transform_document(_page_ast(input_node, calc_node, plot_node))

      iframe_node = result["children"][2]
      html = _decode_iframe_html(iframe_node)
      assert '"red": {"x": "red", "y": 3}' in html
      assert '"green": {"x": "green", "y": 5}' in html
      assert '"blue": {"x": "blue", "y": 4}' in html


  def test_transform_document_raises_for_non_python_calc_language():
      input_node = {
          "type": "myst-baker-input-slider",
          "arg": "a",
          "options": {"value": 1, "min": 0, "max": 1, "step": 1},
          "body": "",
      }
      calc_node = {"type": "code", "lang": "r{calc}", "value": "f <- function(a) a\n"}
      plot_node = {
          "type": "myst-baker-plot",
          "arg": "scatter",
          "options": {"data": "f"},
          "body": "",
      }

      with pytest.raises(ValueError, match="declares language 'r'"):
          transform_document(_page_ast(input_node, calc_node, plot_node))


  def test_transform_document_ignores_plain_python_code_fence():
      # A fence that merely happens to be lang="python" (no `{calc}` suffix,
      # e.g. an ordinary prose/example snippet) is not a live calc block --
      # it must not be exec'd or otherwise treated as a calc source. The
      # body below would raise if it were ever exec'd, so this test fails
      # loudly if that ever regresses.
      input_node = {
          "type": "myst-baker-input-slider",
          "arg": "a",
          "options": {"value": 1, "min": 0, "max": 1, "step": 1},
          "body": "",
      }
      plain_code_node = {
          "type": "code",
          "lang": "python",
          "value": "raise RuntimeError('should never run')\n",
      }
      calc_node = _calc_node("def f(a):\n    return a, a\n")
      plot_node = {
          "type": "myst-baker-plot",
          "arg": "scatter",
          "options": {"data": "f"},
          "body": "",
      }

      ast = {
          "type": "root",
          "children": [input_node, plain_code_node, calc_node, plot_node],
      }

      result = transform_document(ast)

      assert result["children"][-1]["type"] == "iframe"
  ```

- [ ] **Step 2: Run tests to verify the expected failures**

  Run: `uv run pytest tests/test_transform.py -v`
  Expected: every test FAILS. The renamed calc fixtures (`type: "code", lang: "python{calc}"`) aren't recognized by the current `_collect_nodes` (which only checks for `node_type == "myst-baker-calc-python"`), so no function ever gets defined and every plot lookup raises `NameError` for the target function name — including in tests that expect a *different* error or no error at all. The two brand-new tests also fail (`test_transform_document_raises_for_non_python_calc_language` gets no `ValueError` at all; `test_transform_document_ignores_plain_python_code_fence` fails with a `NameError` for `f`, not because the plain fence ran, but because the real calc fence isn't recognized either yet).

- [ ] **Step 3: Implement recognition in `src/myst_baker/transform.py`**

  Add near the top of the file (after the existing imports):

  ```python
  import re
  ```

  So the import block becomes:

  ```python
  import base64
  import inspect
  import re

  from myst_baker import precompute, render
  ```

  Add this helper right before `_collect_nodes`:

  ```python
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
  ```

  Change `_collect_nodes` from:

  ```python
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
          elif node_type == "myst-baker-calc-python":
              exec(node["body"], calc_namespace)

      return inputs, input_nodes, calc_namespace
  ```

  to:

  ```python
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
  ```

- [ ] **Step 4: Run tests to verify they pass**

  Run: `uv run pytest tests/test_transform.py -v`
  Expected: all PASS.

- [ ] **Step 5: Run the full test suite**

  Run: `uv run pytest tests/test_directives.py tests/test_plugin.py tests/test_transform.py -v`
  Expected: all PASS.

- [ ] **Step 6: Commit**

  ```bash
  git add src/myst_baker/transform.py tests/test_transform.py
  git commit -m "feat: recognize python{calc} plain code fences as calc blocks"
  ```

---

### Task 3: Migrate content docs to `python{calc}` and verify the real build

**Files:**
- Modify: `content/index.md`
- Modify: `content/calculations.md`
- Modify: `content/inputs.md`
- Modify: `content/outputs.md`
- Modify: `content/gallery.md`

**Interfaces:**
- Consumes: Task 1 and Task 2's `transform_document`/`PLUGIN_SPEC` behavior — this task only changes markdown content, not code.
- Produces: nothing consumed by a later task (this is the last task).

- [ ] **Step 1: Rewrite every calc fence and prose mention across the five content files**

  Every occurrence in these files is either a fence header `` ```{calc-python} `` or a backtick-quoted prose mention `` `calc-python` `` (confirmed by inspection — no other variant exists). Run:

  ```bash
  sed -i \
    -e 's/```{calc-python}/```python{calc}/g' \
    -e 's/`calc-python`/`calc`/g' \
    content/index.md content/calculations.md content/inputs.md content/outputs.md content/gallery.md
  ```

- [ ] **Step 2: Verify no old-syntax occurrences remain**

  Run: `grep -rn "calc-python" content/`
  Expected: no output (no matches).

- [ ] **Step 3: Build the real site with mystmd**

  Run: `uv run myst build --html`
  Expected: build succeeds with no errors. This is the real proof that mystmd still parses `` ```python{calc} `` fences as plain code blocks and that myst-baker's document-transform (Task 2) still finds and executes them — every page under `content/` (`index.md`, `calculations.md`, `inputs.md`, `outputs.md`, `gallery.md`) exercises at least one calc block feeding a `plot` block, so a build failure here means a fence was missed or malformed by Step 1's substitution.

- [ ] **Step 4: Run the full test suite**

  Run: `uv run pytest -v`
  Expected: all PASS. (This includes `tests/test_e2e_browser.py`, which builds the real site and drives it with Playwright — it requires Playwright's browser binaries to be installed; if they aren't available in this environment, it's acceptable for those specific tests to be skipped/erroring for that pre-existing environment reason, but every other test, and the Step 3 build, must succeed.)

- [ ] **Step 5: Commit**

  ```bash
  git add content/index.md content/calculations.md content/inputs.md content/outputs.md content/gallery.md
  git commit -m "docs: migrate calc blocks from {calc-python} to python{calc}"
  ```
