# pymd

Precomputed interactive docs via a MyST executable plugin.

## Setup

```
uv sync
uv run python scripts/link_plugin_launcher.py
```

The second step is required, not optional. MyST's executable-plugin loader spawns the plugin
as a real process from a literal path configured in `myst.yml` (no PATH search, no per-OS
fallback), but `uv sync` generates that launcher at a platform-specific path
(`.venv/Scripts/pymd-plugin.exe` on Windows, `.venv/bin/pymd-plugin` on Linux/Mac). Running
`scripts/link_plugin_launcher.py` copies whichever one `uv sync` produced to a single fixed,
cross-platform name (`.venv/pymd-plugin-bin.exe`) that `myst.yml` references. Re-run it any
time the launcher is regenerated (e.g. after a fresh `uv sync`), or `myst build` will fail to
find the plugin.

Then build the docs with:

```
uv run myst build
```
