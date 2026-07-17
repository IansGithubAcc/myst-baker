# myst-baker

Precomputed interactive docs via a MyST executable plugin.

## Setup

```
uv sync
```

`uv sync` installs the `myst-baker-plugin` console_scripts entry point, and `myst.yml` references
that file directly — MyST's executable-plugin loader resolves the configured path literally
(no PATH search), so the path must match where `uv sync` puts it on your platform:

- Windows: `.venv/Scripts/myst-baker-plugin.exe` (the default in `myst.yml`)
- Linux/Mac: `.venv/bin/myst-baker-plugin` — update the `path` in `myst.yml`'s `plugins` entry to this

Then build the docs with:

```
uv run myst build
```
