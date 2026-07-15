# pymd

Precomputed interactive docs via a MyST executable plugin.

## Setup

```
uv sync
```

`uv sync` installs the `pymd-plugin` console_scripts entry point at `.venv/Scripts/pymd-plugin.exe`,
which `myst.yml` references directly. MyST's executable-plugin loader resolves that path
literally (no PATH search), so this project currently targets Windows only.

Then build the docs with:

```
uv run myst build
```
