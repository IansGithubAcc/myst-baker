# `python{calc:hide}` Flag Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let authors write `` ```python{calc:hide} `` to keep a calc block's
source out of the rendered page, while it still executes into the page's
calc namespace exactly as an unflagged `` ```python{calc} `` block does.

**Architecture:** Extend the existing calc-fence regex in
`src/myst_baker/transform.py` to recognize an optional `:flag` suffix inside
the `{calc}` tag, validate any flags against a known set (fail loudly on
typos), and generalize the tree-rewrite pass that already replaces `plot`
placeholders so it also drops any `code` node carrying the `hide` flag
before the tree reaches mystmd's renderer.

**Tech Stack:** Python 3, pytest. No new dependencies.

## Global Constraints

- Only `python` calc blocks are supported — this plan does not change that
  check, only adds a flag alongside it.
- Unrecognized flags must raise `ValueError` at build time — no silent
  no-ops (matches the existing language-mismatch check's philosophy; see
  `docs/superpowers/specs/2026-07-17-calc-hide-flag-design.md`).
- No changes to `directives.py`, `plugin.py`, `precompute.py`, or the client
  runtime (`src/myst_baker/static/runtime.js`).
- A non-hidden (`` ```python{calc} `` with no flags) block's behavior must
  be byte-for-byte unchanged — every existing test in
  `tests/test_transform.py` must keep passing without modification.

---

### Task 1: Recognize, validate, and act on the `:hide` calc-fence flag

**Files:**
- Modify: `src/myst_baker/transform.py:82-140` (regex, fence-match helper,
  `_collect_nodes`, `_replace_plots`), `src/myst_baker/transform.py:189-210`
  (`transform_document`)
- Test: `tests/test_transform.py`

**Interfaces:**
- Consumes: nothing new from outside this file — `_iter_nodes` (unchanged,
  `transform.py:11-26`) still yields every mdast node depth-first.
- Produces: `transform_document(ast) -> ast` (signature unchanged). Callers
  outside this file (`plugin.py`'s `--transform` branch) need no changes —
  hiding is purely internal tree-rewrite behavior.

- [ ] **Step 1: Write the failing tests**

Add these three tests to the end of `tests/test_transform.py` (it already
imports `pytest`, `json`, `base64`, `transform_document`, and defines
`_page_ast`/`_calc_node`/`_decode_iframe_html` — reuse them as-is):

```python
def test_transform_document_hides_calc_block_source_when_flagged():
    input_node = {
        "type": "myst-baker-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 2, "step": 1},
        "body": "",
    }
    calc_node = {
        "type": "code",
        "lang": "python{calc:hide}",
        "value": "def get_plot_data(a):\n    return a, a * 2\n",
    }
    plot_node = {
        "type": "myst-baker-plot",
        "arg": "scatter",
        "options": {"data": "get_plot_data"},
        "body": "",
    }

    result = transform_document(_page_ast(input_node, calc_node, plot_node))

    # The hidden calc block's `code` node must be gone -- only the slider
    # and the rendered plot remain -- but the function it defined must
    # still have run: the iframe HTML below still reflects its output.
    children_types = [child["type"] for child in result["children"]]
    assert children_types == ["myst-baker-input-slider", "iframe"]

    iframe_node = result["children"][1]
    html = _decode_iframe_html(iframe_node)
    assert '"0": {"x": 0, "y": 0}' in html
    assert '"1": {"x": 1, "y": 2}' in html
    assert '"2": {"x": 2, "y": 4}' in html


def test_transform_document_keeps_unflagged_calc_block_alongside_hidden_one():
    input_node = {
        "type": "myst-baker-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 1, "step": 1},
        "body": "",
    }
    visible_calc_node = _calc_node("def visible_fn(a):\n    return a, a\n")
    hidden_calc_node = {
        "type": "code",
        "lang": "python{calc:hide}",
        "value": "def hidden_fn(a):\n    return a, a * 2\n",
    }
    plot_node = {
        "type": "myst-baker-plot",
        "arg": "scatter",
        "options": {"data": "hidden_fn"},
        "body": "",
    }

    ast = {
        "type": "root",
        "children": [input_node, visible_calc_node, hidden_calc_node, plot_node],
    }

    result = transform_document(ast)

    # The visible block's `code` node survives; the hidden one is dropped.
    children_types = [child["type"] for child in result["children"]]
    assert children_types == ["myst-baker-input-slider", "code", "iframe"]


def test_transform_document_raises_for_unknown_calc_flag():
    input_node = {
        "type": "myst-baker-input-slider",
        "arg": "a",
        "options": {"value": 1, "min": 0, "max": 1, "step": 1},
        "body": "",
    }
    calc_node = {
        "type": "code",
        "lang": "python{calc:bogus}",
        "value": "def f(a):\n    return a, a\n",
    }
    plot_node = {
        "type": "myst-baker-plot",
        "arg": "scatter",
        "options": {"data": "f"},
        "body": "",
    }

    with pytest.raises(ValueError, match="unknown flag 'bogus'"):
        transform_document(_page_ast(input_node, calc_node, plot_node))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_transform.py -k "hide or unknown_calc_flag or keeps_unflagged" -v`

Expected: all three new tests FAIL. The `hide`/`keeps_unflagged` tests fail
because the `code` node for `python{calc:hide}` is still present in
`result["children"]` (nothing drops it yet). The `unknown_calc_flag` test
fails because `python{calc:bogus}` doesn't match today's
`_CALC_FENCE_RE` at all (no flag syntax exists yet), so `_collect_nodes`
silently skips it as "not a calc fence" instead of raising — no
`ValueError` is raised, so `pytest.raises` fails with `DID NOT RAISE`.

- [ ] **Step 3: Extend the regex and add flag parsing**

In `src/myst_baker/transform.py`, replace lines 82-98 (the `_CALC_FENCE_RE`
definition and `_calc_fence_lang` function) with:

```python
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
```

- [ ] **Step 4: Validate flags and update `_collect_nodes`**

Replace the body of `_collect_nodes` (`transform.py:101-122`) — specifically
the `elif node_type == "code":` branch — so it reads:

```python
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
```

(The function's signature, its `inputs`/`input_nodes` handling, and its
`return inputs, input_nodes, calc_namespace` line are unchanged.)

- [ ] **Step 5: Generalize the tree-rewrite pass to drop hidden nodes**

Rename `_replace_plots` (`transform.py:125-140`) to `_rewrite_tree` and add
the hidden-node branch:

```python
def _rewrite_tree(node, replace_plot):
    """Return a copy of `node` with every descendant `myst-baker-plot` node (at any
    depth) replaced by `replace_plot(plot_node)`, and every hidden calc `code`
    node (see `_is_hidden_calc_node`) dropped entirely. See `_iter_nodes` for
    why this needs to recurse rather than only look at the immediate children.
    """
    children = node.get("children")
    if children is None:
        return node

    new_children = []
    for child in children:
        if child.get("type") == "myst-baker-plot":
            new_children.append(replace_plot(child))
        elif _is_hidden_calc_node(child):
            continue
        else:
            new_children.append(_rewrite_tree(child, replace_plot))
    return {**node, "children": new_children}
```

Then update `transform_document`'s final line (`transform.py:210`) from
`return _replace_plots(ast, replace_plot)` to
`return _rewrite_tree(ast, replace_plot)`.

- [ ] **Step 6: Run the full test suite to verify everything passes**

Run: `uv run pytest tests/test_transform.py -v`

Expected: PASS for all tests in the file, including the three new ones and
every pre-existing one (language validation, plain-`python`-fence
ignoring, block-wrapper recursion, input ordering, checkbox/dropdown
support, plot replacement).

- [ ] **Step 7: Commit**

```bash
git add src/myst_baker/transform.py tests/test_transform.py
git commit -m "$(cat <<'EOF'
feat: support python{calc:hide} to hide calc block source

A calc block tagged :hide still executes into the page's calc
namespace but its source is dropped from the rendered tree, so
plot-only calc functions don't need to be shown as reading material.
EOF
)"
```

---

### Task 2: Document the `:hide` flag

**Files:**
- Modify: `docs/guide/calculations.md:1-16`

**Interfaces:**
- Consumes: nothing (docs-only change).
- Produces: nothing consumed by other tasks.

- [ ] **Step 1: Add a tip block introducing the flag**

In `docs/guide/calculations.md`, insert a new `{tip}` directive block
immediately after the existing `{note}` block (i.e. right after line 15,
before the blank line and `## A single calculation` heading), so the file
reads:

`````markdown
```{note}
Because this all happens at *build* time, there's no runtime Python on the
published page — by the time a reader's browser loads it, every result is
already sitting in a JSON table. A `calc` function can do anything
ordinary Python can (import from the standard library, loop, branch); it
just needs to return an `(x, y)` pair of equal-length sequences for the
`plot` block that consumes it.
```

```{tip}
Add `:hide` inside the tag — `` ```python{calc:hide} `` — to keep a
block's source out of the rendered page while it still executes into the
page's calc namespace. Handy when a `calc` function exists purely to feed
a `plot` block and isn't meant to be read as an example.
```

## A single calculation
`````

- [ ] **Step 2: Commit**

```bash
git add docs/guide/calculations.md
git commit -m "docs: document python{calc:hide}"
```
