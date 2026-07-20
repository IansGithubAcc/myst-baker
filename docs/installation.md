# Installation

myst-baker is a MyST executable plugin: a small console script that MyST
invokes as a subprocess to resolve `input-slider`, `input-checkbox`,
`input-dropdown`, and `plot` directives at build time. Getting it working
means two things: the package needs to be installed somewhere Python can
find it, and your project's `myst.yml` needs an `executable` plugin entry
pointing at the installed console script.

```{warning}
myst-baker isn't published to PyPI yet. Until it is, install it from its git
URL rather than `pip install myst-baker` / `uv add myst-baker`.
```

## Add myst-baker to your own MyST project

1. Add myst-baker as a dependency of your project. With `uv`:

   ```
   uv add git+https://github.com/IansGithubAcc/myst-baker
   ```

   With `pip` instead:

   ```
   pip install git+https://github.com/IansGithubAcc/myst-baker
   ```

2. Point your project's `myst.yml` at the installed console script.
   Installing the package creates a `myst-baker-plugin` console-script entry
   point, but MyST's executable-plugin loader resolves the configured `path`
   **literally** — it does not search `PATH` — so the path in `myst.yml` has
   to match exactly where your package manager put the launcher:

   ```yaml
   project:
     plugins:
       - type: executable
         path: .venv/Scripts/myst-baker-plugin.exe   # Windows
         # path: .venv/bin/myst-baker-plugin          # Linux/Mac
   ```

3. Build your docs:

   ```
   uv run myst build
   ```

   (with `pip`, activate your virtual environment first, then run
   `myst build` directly.)

   If the plugin path is wrong, MyST fails to resolve `input-slider`,
   `input-checkbox`, `input-dropdown`, and `plot` directives — double-check
   the path matches your virtual environment's actual layout (it changes
   between Windows and Linux/Mac, and between package managers).

## Optional: full Plotly figures

`{plot} figure` blocks (see the [outputs guide](guide/outputs.md)) let
a calc function build a complete Plotly figure instead of a single
trace. If it does so using `plotly.graph_objects` or `plotly.express`
directly, install the optional `plotly` extra alongside myst-baker:

```
uv add "myst-baker[plotly]"
```

or with `pip`:

```
pip install "myst-baker[plotly]"
```

This isn't required if a calc function instead returns a plain
`{"data": [...], "layout": {...}}` dict by hand.

## Developing this repo

Clone the repo, then:

```
uv sync
```

`uv sync` installs the `myst-baker-plugin` console-script entry point at
`.venv/Scripts/myst-baker-plugin.exe` (Windows) or
`.venv/bin/myst-baker-plugin` (Linux/Mac) — this repo's own `myst.yml`
already points at the Windows path, so on Linux/Mac update its `plugins`
entry to match before building.

Then build the docs with:

```
uv run myst build
```

Run the test suite with:

```
uv run pytest
```
