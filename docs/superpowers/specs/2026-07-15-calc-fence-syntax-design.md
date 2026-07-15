# Calc block fence syntax: `python{calc}`

## Problem

Author-facing calc blocks are written as `` ```{calc-python} ``. mystmd's
directive-fence grammar (markdown-it-docutils, confirmed against mystmd's
source) requires the info string to start with `{name}` —
`^\{([^\s}]+)\}\s*(.*)$` — so nothing, including a real language tag, can
precede the brace. Because of that, no plain markdown editor (VS Code
included) syntax-highlights the block body: editor highlighting is driven
entirely by the editor's own markdown grammar recognizing a bare language
word immediately after the backticks, and `{calc-python}` isn't one. This is
unrelated to mystmd and no existing MyST VS Code extension bridges it either
(checked both `ExecutableBookProject.myst-highlight` and the newer
`jupyter-book/vscode-mystmd` — neither injects an embedded-language grammar
into directive bodies).

## Decision

Drop MyST's directive-fence mechanism for calc blocks entirely and recognize
them as a convention over plain fenced code blocks instead:

````
```python{calc}
def compound_growth(rate):
    ...
```
````

Because the info string no longer starts with `{`, mystmd's parser treats
this as an ordinary code fence — real `python` language token up front, so
editors highlight it like any other Python fence — and pymd recognizes it
itself during the document transform, which already walks the whole page
AST.

This is possible because `calc-python` has no MyST-directive-only
requirements: it declares no `:key: value` options (`CALC_PYTHON_DIRECTIVE`
in `src/pymd/directives.py` only has a `body`), and its source is never
rendered to the reader — `transform.py` only `exec`s it into a shared
namespace. The directives that *do* need MyST's directive machinery
(`input-slider`, `input-checkbox`, `input-dropdown`, `plot`) all rely on
`:key: value` option-line parsing, which only exists for real directive
fences, and none of them are source code needing highlighting — they're
unaffected by this change.

While touching this, generalize the tag from `calc-python` to `calc`: the
language is now carried by the leading token itself (`python{calc}`), so a
per-language directive name is redundant, and this matches the project's
existing convention for `plot` (one generic directive, type given by an
explicit token) rather than one directive name per kind. `calc` was chosen
over alternatives (`compute`, `fn`) because it matches the terminology
already used throughout `content/calculations.md` ("calc function", "calc
block") with no rewording needed.

## Mechanism

1. **Recognition**: for every plain `code` mdast node encountered during the
   existing whole-tree walk (`_collect_nodes` in `src/pymd/transform.py`),
   reconstruct the fence's info string from `lang` + `meta` (mdast splits on
   the first whitespace; with no space, the entire string lands in `lang`
   and `meta` is empty — reconstructing handles both `python{calc}` and
   `python {calc}` identically) and match it against:

   ```
   ^(?P<lang>\w+)\{calc\}$
   ```

2. **Validation**: if the pattern matches and `lang != "python"`, raise a
   clear build-time error (e.g. `f"calc block declares language {lang!r}, but
   only 'python' calc blocks are supported"`) — no other language is
   implemented, and this must fail loudly rather than silently mis-executing
   non-Python source as Python. This matches the project's existing
   philosophy (see the precompute engine's budget guard) of no silent
   failure modes.
3. **Execution**: if `lang == "python"`, behavior is identical to today —
   `exec(node["body"], calc_namespace)`.
4. **No collision with illustrative fences**: plain `` ```python `` or
   ` ````md ` fences used elsewhere in the docs purely to show example
   syntax don't end in `{calc}`, so they never match and are left alone.

## Removed

- `CALC_PYTHON_DIRECTIVE` and the `"calc-python"` entry in `KNOWN_DIRECTIVES`
  (`src/pymd/directives.py`).
- `CALC_PYTHON_DIRECTIVE`'s registration in `PLUGIN_SPEC["directives"]`
  (`src/pymd/plugin.py`) — mystmd no longer calls `--directive` for this
  block at all, since it's not a directive.

## Migration

No back-compat shim for the old `` ```{calc-python} `` form — every existing
occurrence is rewritten to `` ```python{calc} ``:

- `content/calculations.md`, `content/gallery.md` (and any other content
  page using calc blocks)
- `tests/test_transform.py`, `tests/test_plugin.py`, `tests/test_directives.py`

## Testing

- Existing tests that build/expect `pymd-calc-python` placeholder nodes are
  updated to build/expect plain `code` nodes with `lang: "python{calc}"`
  instead.
- New case: a `code` node with a non-Python language prefix (e.g.
  `r{calc}`) asserts the clear build-time error described above.

## Open questions

None — this is a self-contained syntax/recognition change with no effect on
precompute semantics, client runtime, or the other directive kinds.
