# Documentation overhaul — design

## Goal

Replace the ad-hoc `content/` example pages with a proper `docs/` tree that
covers what a Python package / MyST plugin's docs are expected to have:
install instructions, a usage guide, worked examples, a changelog, and an
authors/license page. The existing `content/*.md` pages are used only as
reference material while writing the new pages — `content/` is deleted once
`docs/` is complete and building successfully.

## Directory structure

```
docs/
  index.md              landing: what it is, mental model, minimal live example, nav
  installation.md        NEW: install into your own repo + this repo's dev setup
  guide/
    inputs.md            rewritten from content/inputs.md
    calculations.md      rewritten from content/calculations.md
    outputs.md           rewritten from content/outputs.md
  examples/
    gallery.md           rewritten from content/gallery.md
  changelog.md            NEW: single 0.1.0 entry, Keep a Changelog format
  authors.md              NEW: author, MIT license pointer, contributing pointer
```

`docs/superpowers/` (specs/plans from prior development) is untouched — it's
the coding agent's own history, not part of the published site, and is not
referenced from the new pages.

## `myst.yml`

- `project.toc` rewritten to point at the new paths:
  - `docs/index.md` (root)
  - `docs/installation.md` (its own top-level entry)
  - `Guide` section: `docs/guide/inputs.md`, `docs/guide/calculations.md`,
    `docs/guide/outputs.md`
  - `Examples` section: `docs/examples/gallery.md`
  - `docs/changelog.md` (its own top-level entry)
  - `docs/authors.md` (its own top-level entry)
- Frontmatter filled in: `title`, `description`, `authors: [Ian Mullens]`,
  `github: https://github.com/IansGithubAcc/myst-baker`.
- The `plugins.executable.path` entry is unchanged.

## Page content

**`docs/index.md`** — same role as today's `content/index.md`: what
myst-baker is, the three-piece mental model (input widget / `calc` / `plot`),
one minimal live example, and a "where to go next" nav updated to the new
paths (`guide/inputs.md`, `guide/calculations.md`, `guide/outputs.md`,
`examples/gallery.md`).

**`docs/installation.md`** (new content, not derived from `content/`) covers
two audiences:
1. **Using myst-baker in your own MyST project** — install the package (note
   it isn't published to PyPI yet, so install from source/git), add the
   `executable` plugin entry to your project's `myst.yml`, and the
   Windows-vs-Linux/Mac launcher-path caveat currently in the README (`uv
   sync` places the console-script at a platform-specific path that
   `myst.yml`'s `plugins.executable.path` must match literally).
2. **Developing this repo** — `uv sync`, `uv run myst build`.

**`docs/guide/inputs.md`**, **`docs/guide/calculations.md`**,
**`docs/guide/outputs.md`** — same technical content as the corresponding
`content/*.md` pages (input widget configurations, `calc` block semantics,
plot trace types), rewritten with cross-links updated to the new paths.

**`docs/examples/gallery.md`** — same worked examples as
`content/gallery.md`, rewritten with updated cross-links.

**`docs/changelog.md`** — Keep a Changelog format, one `## 0.1.0` entry
summarizing current capabilities: input widgets (slider/checkbox/dropdown),
`python{calc}` fence blocks, the `plot` output block with its six built-in
trace types (scatter, bar, histogram, pie, box, violin), and the
precomputed/static-build architecture (no runtime Python on the published
page).

**`docs/authors.md`** — author (Ian Mullens), a license statement pointing at
`LICENSE` (MIT), and a contributing pointer to
`https://github.com/IansGithubAcc/myst-baker` for issues/PRs.

## Root-level changes

- **`LICENSE`** — new MIT license file, copyright Ian Mullens, 2026.
- **`README.md`** — trimmed to a short pitch (what it is, one line) plus a
  link into `docs/index.md`. Install instructions are removed from the
  README entirely and live only in `docs/installation.md`.
- **`pyproject.toml`** — add `license = "MIT"`, an `authors` entry for Ian
  Mullens, and `[project.urls]` with `Homepage`/`Repository` pointing at
  `https://github.com/IansGithubAcc/myst-baker`.

## URL changes and test updates

Confirmed by reading mystmd's route-slugging code (`fileInfo2` in the
bundled `myst.cjs`): by default a page's slug comes from its **basename
only** — folder structure is ignored unless the project sets
`urlFolders: true` in `myst.yml` (it doesn't, and this design doesn't add
it). So moving pages into `docs/guide/` and `docs/examples/` does **not**
change their built routes:

- `docs/guide/inputs.md` → still `/inputs/`
- `docs/guide/outputs.md` → still `/outputs/`
- `docs/examples/gallery.md` → still `/gallery/`
- `docs/index.md` → still the site root (first `toc` entry)

`tests/test_e2e_browser.py`'s `inputs_page_url`/`outputs_page_url` fixtures
(lines 42-48) need no changes. Its explanatory comments (lines 117, 144, 185)
reference `content/inputs.md` / `content/outputs.md` by path and are updated
to say `docs/guide/inputs.md` / `docs/guide/outputs.md` so they stay
accurate, even though the fixtures themselves are untouched.

Historical plan/spec documents under `docs/superpowers/` that mention
`content/` (from prior development work) are left unchanged — they're a
record of past work, not living documentation, and editing them would
misrepresent history.

## Sequencing

1. Write all new `docs/` pages and root-level files (`LICENSE`, trimmed
   `README.md`, updated `pyproject.toml`).
2. Update `myst.yml` toc/frontmatter to point at `docs/`.
3. Update `tests/test_e2e_browser.py` fixtures/comments for the new routes.
4. Verify `uv run myst build` succeeds and the full test suite
   (`uv run pytest`) passes against the new paths.
5. Delete `content/` in a final step, once `docs/` fully replaces it.

## Out of scope

- Publishing to PyPI (installation docs note this isn't done yet, but doing
  it is not part of this overhaul).
- Adding a dedicated CONTRIBUTING.md — the contributing pointer on
  `docs/authors.md` is sufficient for the project's current size.
- API/reference documentation (docstring-generated docs) — the guide pages
  document the directives and fence syntax, not a Python API, since
  myst-baker's public surface is MyST directives, not an importable API.
