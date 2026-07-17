# Hiding calc block source: `python{calc:hide}`

## Problem

`calc` blocks always render their source to the reader — the fence is a
plain `code` mdast node (see `docs/superpowers/specs/2026-07-15-calc-fence-syntax-design.md`
for why it's plain rather than a directive), so mystmd's site renderer
shows it like any other Python code sample. Authors may want to compute a
plot's data without exposing the implementation, without giving up the
editor syntax highlighting that motivated the plain-fence form in the
first place.

## Decision

Add an optional `:hide` flag inside the existing `{calc}` tag:

````
```python{calc:hide}
def compound_growth(rate):
    ...
```
````

The block still executes into the page's calc namespace exactly as before
— `plot` blocks can still reference its function by name — but the code
node itself is dropped from the tree before mystmd renders the page, so
the reader never sees the source.

Rejected alternatives (see brainstorming discussion):
- **Directive-style `:hide: true` option** — would require reverting
  `calc` blocks to directive-fence syntax (`` ```{calc-python} ``),
  reintroducing the loss of editor syntax highlighting that the
  2026-07-15 change specifically fixed.
- **Project-wide `myst.yml` toggle** — simpler surface, but all-or-nothing
  across a page/project; doesn't let an author mix visible and hidden
  calc blocks on the same page (the compound-growth guide page already
  does this: some calc blocks are illustrative, others exist purely to
  drive a plot).

The flag syntax is deliberately generic (`(?::\w+)*`, not hardcoded to
just `hide`) so a future flag could be added the same way, but only
`hide` is implemented now — any other flag is a build-time error rather
than silently ignored, matching this project's existing "fail loudly"
philosophy (see the language-mismatch check this change sits next to).

## Mechanism

All changes are in `src/myst_baker/transform.py`.

1. **Recognition**: extend `_CALC_FENCE_RE` from
   `^(?P<lang>\w+)\{calc\}$` to
   `^(?P<lang>\w+)\{calc(?P<flags>(?::\w+)*)\}$`, capturing zero or more
   `:word` flag suffixes. `_calc_fence_lang`'s existing reconstruction of
   `lang + meta` into one info string is unaffected — flags live inside
   the braces, so they're part of the same no-space token that already
   lands entirely in `lang`.
2. **Flag parsing**: a small helper splits the `flags` group on `:` and
   drops empty segments (`""` for no flags, `"hide"` for one, extensible
   to more).
3. **Validation**: in `_collect_nodes`, after the existing language check,
   validate every parsed flag is in the known set (`{"hide"}`) and raise
   `ValueError` naming the bad flag otherwise. This runs before `exec`,
   consistent with the existing fail-before-executing order.
4. **Hiding**: the tree-rewrite pass that today only replaces
   `myst-baker-plot` placeholders (`_replace_plots`) is generalized to
   also drop, from a parent's `children`, any `code` node whose fence
   matches `{calc...}` and carries the `hide` flag. Renamed to reflect
   the broader responsibility (e.g. `_rewrite_tree`). Non-hidden calc
   blocks, and all other node types, pass through unchanged — only the
   node removal is new behavior.

No changes to `directives.py`, `plugin.py`, `precompute.py`, or the
client runtime — inputs, plots, and non-hidden calc blocks behave
identically to today.

## Testing

- `tests/test_transform.py`: a hidden calc block's function is still
  callable by a `plot` block (namespace unaffected), but the hidden
  block's `code` node is absent from the transformed tree; a
  non-hidden calc block on the same page is still present and unchanged.
- New case: `python{calc:bogus}` (or any unrecognized flag) raises a
  clear `ValueError` at build time.
- Existing calc-block tests (language validation, multi-block namespace
  sharing) continue to pass unmodified — `{calc}` with no flags behaves
  exactly as before.

## Documentation

`docs/guide/calculations.md` gains a short note introducing
`python{calc:hide}` alongside the existing calc-block explanation.

## Open questions

None — this is a self-contained addition with no effect on precompute
semantics, client runtime, or the other directive kinds.
