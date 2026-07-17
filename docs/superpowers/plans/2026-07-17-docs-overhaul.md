# Documentation Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the ad-hoc `content/` example pages with a proper `docs/` tree (installation, guide, examples, changelog, authors) plus a LICENSE file and a trimmed README, matching what a Python package / MyST plugin's docs are expected to have.

**Architecture:** A single MyST site (unchanged `myst.yml` build, `book-theme`) whose pages move from `content/*.md` to `docs/*.md` (with `docs/guide/` and `docs/examples/` subfolders). `content/*.md` is used only as reference material while authoring the new pages, then deleted once `docs/` fully replaces it and the build/tests pass against the new tree.

**Tech Stack:** mystmd (MyST CLI, `uv run myst build`), pytest + pytest-playwright (`uv run pytest`), `uv` for dependency management.

## Global Constraints

- `requires-python = ">=3.13"` in `pyproject.toml` is unchanged by this work.
- License is MIT, copyright holder **Ian Mullens**, year **2026**.
- Repository URL is `https://github.com/IansGithubAcc/myst-baker` — use this exact URL everywhere a repo link is needed (pyproject.toml `[project.urls]`, `myst.yml`'s `project.github`, `docs/authors.md`).
- The executable-plugin path caveat must be preserved verbatim wherever it's documented: MyST resolves `plugins.executable.path` as a **literal path, not a PATH search**. `uv sync` puts the launcher at `.venv/Scripts/myst-baker-plugin.exe` on Windows and `.venv/bin/myst-baker-plugin` on Linux/Mac — the two are not interchangeable and whichever platform you're on must match `myst.yml`.
- `docs/changelog.md` follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format, with a single `## 0.1.0` entry (no per-commit history, no "Unreleased" section).
- mystmd derives a page's URL slug from its **filename only** — folder structure is ignored (confirmed by reading `fileInfo2` in the installed `mystmd` package's bundled `myst.cjs`; folder-based slugs are opt-in via `urlFolders`, which this project does not set). This means moving pages into `docs/guide/` and `docs/examples/` does **not** change their built routes (`inputs.md` is still served at `/inputs/`, etc.) — don't second-guess this when writing or reviewing tests.
- Out of scope: publishing to PyPI, a dedicated `CONTRIBUTING.md`, and API/reference documentation (myst-baker's public surface is MyST directives, not an importable Python API).
- `docs/superpowers/` (specs/plans, including this file) is not part of the published site and is never added to `myst.yml`'s `toc`.

---

### Task 1: License and package metadata

**Files:**
- Create: `LICENSE`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `LICENSE` (referenced by `docs/authors.md` in Task 2); `pyproject.toml`'s `[project.urls]` values (referenced nowhere else in this plan, but must exist for Task 2's `docs/authors.md` claim to be accurate).

- [ ] **Step 1: Create the LICENSE file**

Create `LICENSE`:

```
MIT License

Copyright (c) 2026 Ian Mullens

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Add license, authors, and URLs to pyproject.toml**

Replace the `[project]` table and add a `[project.urls]` table so `pyproject.toml` reads:

```toml
[project]
name = "myst-baker"
version = "0.1.0"
description = "Precomputed interactive docs via a MyST executable plugin"
readme = "README.md"
requires-python = ">=3.13"
license = "MIT"
authors = [
    { name = "Ian Mullens", email = "imullens@hes-heerema.com" },
]
dependencies = [
    "mystmd",
]

[project.urls]
Homepage = "https://github.com/IansGithubAcc/myst-baker"
Repository = "https://github.com/IansGithubAcc/myst-baker"

[project.scripts]
myst-baker-plugin = "myst_baker.plugin:main"

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

- [ ] **Step 3: Verify pyproject.toml still parses and installs cleanly**

Run: `uv sync`
Expected: exits `0`, no errors about `license`/`authors`/`[project.urls]` syntax.

- [ ] **Step 4: Commit**

```bash
git add LICENSE pyproject.toml uv.lock
git commit -m "chore: add MIT license and package metadata"
```

---

### Task 2: Author the new docs/ pages

**Files:**
- Create: `docs/index.md`
- Create: `docs/installation.md`
- Create: `docs/guide/inputs.md`
- Create: `docs/guide/calculations.md`
- Create: `docs/guide/outputs.md`
- Create: `docs/examples/gallery.md`
- Create: `docs/changelog.md`
- Create: `docs/authors.md`

**Interfaces:**
- Consumes: `LICENSE` (Task 1), for the link in `docs/authors.md`.
- Produces: all eight files above, at these exact paths — Task 3 wires them into `myst.yml`'s `toc` and links to them from `README.md` using these exact paths, and Task 4 changes comments in `tests/test_e2e_browser.py` to reference `docs/guide/inputs.md` / `docs/guide/outputs.md` by these exact paths.

None of these pages are reachable from the built site until Task 3 updates `myst.yml`'s `toc` — this task only creates the files and checks they exist on disk.

- [ ] **Step 1: Create docs/index.md**

```markdown
# myst-baker

myst-baker is a MyST plugin for writing documentation with **live, interactive
examples that need no server**. You author three kinds of fenced blocks —
an input widget, a plain Python function, and a plot — and myst-baker runs your
function over every possible combination of input values *at build time*.
The result is baked into the page as a JSON lookup table: moving a slider in
the browser is just a key lookup and a chart redraw, with no Python running
anywhere at page-view time.

## The mental model

Every interactive figure in these docs is built from the same three pieces:

1. **An input widget** (`input-slider`, `input-checkbox`, or
   `input-dropdown`) — declares a named input and the values myst-baker should
   precompute for it.
2. **`calc`** — a normal Python function whose parameter names match
   input names. myst-baker calls it once per combination of input values.
3. **`plot`** — a Plotly trace (scatter, bar, histogram, pie, box, violin,
   and more), fed by one `calc` function's output.

```{tip}
Because everything is precomputed, the published site is fully static
HTML/JS/JSON. It can be hosted anywhere — no backend, no notebook kernel,
no live Python process.
```

## A minimal example

Here's the whole pipeline in five lines: one slider, one function, one plot.

````md
```{input-slider} k
:value: 1
:min: -3
:max: 3
:step: 0.5
```

```python{calc}
def scale_line(k):
    x = list(range(-5, 6))
    y = [k * xi for xi in x]
    return x, y
```

```{plot} scatter
:data: scale_line
:mode: lines
```
````

And here's that same block, live — drag the slider:

```{input-slider} k
:value: 1
:min: -3
:max: 3
:step: 0.5
```

```python{calc}
def scale_line(k):
    x = list(range(-5, 6))
    y = [k * xi for xi in x]
    return x, y
```

```{plot} scatter
:data: scale_line
:mode: lines
```

## Where to go next

- **[Installation](installation.md)** — install myst-baker into your own
  MyST project, or set up this repo for development.
- **[Input widgets](guide/inputs.md)** — slider, checkbox, and dropdown
  configurations: single input, multiple inputs, fine steps and negative
  ranges, and choice-based inputs.
- **[Calculations](guide/calculations.md)** — how `calc` blocks work, and
  how several of them can share a page.
- **[Plot outputs](guide/outputs.md)** — the different Plotly trace types
  (scatter, bar, histogram, pie, box, violin) and modes a `plot` block can
  render.
- **[Gallery](examples/gallery.md)** — full worked examples that combine several
  inputs, functions, and plots on one page.
```

- [ ] **Step 2: Create docs/installation.md**

```markdown
# Installation

myst-baker is a MyST executable plugin: a small console script that MyST
invokes as a subprocess to resolve `input-slider`, `input-checkbox`,
`input-dropdown`, and `plot` directives at build time. Getting it working
means two things: the package needs to be installed somewhere Python can
find it, and your project's `myst.yml` needs an `executable` plugin entry
pointing at the installed console script.

```{warning}
myst-baker isn't published to PyPI yet. Until it is, install it from source
(a local checkout or a git URL) rather than `pip install myst-baker` /
`uv add myst-baker`.
```

## Add myst-baker to your own MyST project

1. Add myst-baker as a dependency of your project. With `uv`:

   ```
   uv add git+https://github.com/IansGithubAcc/myst-baker
   ```

   Or, from a local checkout:

   ```
   uv add /path/to/myst-baker
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

   If the plugin path is wrong, MyST fails to resolve `input-slider`,
   `input-checkbox`, `input-dropdown`, and `plot` directives — double-check
   the path matches your virtual environment's actual layout (it changes
   between Windows and Linux/Mac, and between package managers).

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
```

- [ ] **Step 3: Create docs/guide/inputs.md**

```markdown
# Input widgets

myst-baker ships three input widgets — `input-slider`, `input-checkbox`, and
`input-dropdown` — and any number of them can appear on a page in any
combination: each `calc` function picks up whichever ones match its
parameter names. This page runs through the configurations you'll actually
use: a single slider, multiple sliders sharing one function, fine steps and
negative ranges, a checkbox toggle, and a dropdown of named choices.

```{note}
An `input-slider`'s argument is the name other blocks refer to it by. Its
`:min:`/`:max:`/`:step:` options define the full set of values myst-baker
precomputes — every combination becomes one row in the build-time grid, so
narrower ranges and coarser steps mean smaller, faster builds.
```

## One slider

The simplest case: a single input driving a single-parameter function.

````md
```{input-slider} amplitude
:value: 1
:min: 0
:max: 2
:step: 0.25
```

```python{calc}
import math

def sine_amplitude(amplitude):
    x = [i / 10 for i in range(-31, 32)]
    y = [amplitude * math.sin(xi) for xi in x]
    return x, y
```

```{plot} scatter
:data: sine_amplitude
:mode: lines
```
````

```{input-slider} amplitude
:value: 1
:min: 0
:max: 2
:step: 0.25
```

```python{calc}
import math

def sine_amplitude(amplitude):
    x = [i / 10 for i in range(-31, 32)]
    y = [amplitude * math.sin(xi) for xi in x]
    return x, y
```

```{plot} scatter
:data: sine_amplitude
:mode: lines
```

## Two sliders

A function can take as many parameters as you like — myst-baker matches each one
to an `input-slider` by name and builds the cartesian product of their
values. Here, `a` and `b` together shape a parabola.

````md
```{input-slider} a
:value: 1
:min: -3
:max: 3
:step: 1
```

```{input-slider} b
:value: 0
:min: -3
:max: 3
:step: 1
```

```python{calc}
def parabola(a, b):
    x = [i / 2 for i in range(-10, 11)]
    y = [a * xi**2 + b for xi in x]
    return x, y
```

```{plot} scatter
:data: parabola
:mode: lines
```
````

```{input-slider} a
:value: 1
:min: -3
:max: 3
:step: 1
```

```{input-slider} b
:value: 0
:min: -3
:max: 3
:step: 1
```

```python{calc}
def parabola(a, b):
    x = [i / 2 for i in range(-10, 11)]
    y = [a * xi**2 + b for xi in x]
    return x, y
```

```{plot} scatter
:data: parabola
:mode: lines
```

## Fine steps and negative ranges

Slider options aren't limited to small integer ranges — `:step:` accepts
decimals and `:min:`/`:max:` can straddle zero. Here, a damping coefficient
runs from -0.5 (growth) to 1.0 (decay) in steps of 0.05.

````md
```{input-slider} damping
:value: 0.3
:min: -0.5
:max: 1.0
:step: 0.05
```

```python{calc}
import math

def damped_envelope(damping):
    x = [i / 5 for i in range(0, 26)]
    y = [math.exp(-damping * xi) for xi in x]
    return x, y
```

```{plot} scatter
:data: damped_envelope
:mode: lines
```
````

```{input-slider} damping
:value: 0.3
:min: -0.5
:max: 1.0
:step: 0.05
```

```python{calc}
import math

def damped_envelope(damping):
    x = [i / 5 for i in range(0, 26)]
    y = [math.exp(-damping * xi) for xi in x]
    return x, y
```

```{plot} scatter
:data: damped_envelope
:mode: lines
```

```{tip}
That last example precomputes 31 values for one input. Two sliders like the
"Two sliders" example above (7 x 7 = 49 combinations) is still trivial; the
build only starts to matter once a page's inputs multiply into the
thousands — see [Calculations](calculations.md) for how the grid is built.
```

## Checkbox

An `input-checkbox`'s argument is the name other blocks refer to it by, same
as `input-slider`. Its `:value:` option sets the initial state; myst-baker always
precomputes both `true` and `false`, regardless of which one a page starts
on.

````md
```{input-checkbox} inverted
:value: false
```

```python{calc}
import math

def maybe_inverted_sine(inverted):
    x = [i / 10 for i in range(-31, 32)]
    sign = -1 if inverted else 1
    y = [sign * math.sin(xi) for xi in x]
    return x, y
```

```{plot} scatter
:data: maybe_inverted_sine
:mode: lines
```
````

```{input-checkbox} inverted
:value: false
```

```python{calc}
import math

def maybe_inverted_sine(inverted):
    x = [i / 10 for i in range(-31, 32)]
    sign = -1 if inverted else 1
    y = [sign * math.sin(xi) for xi in x]
    return x, y
```

```{plot} scatter
:data: maybe_inverted_sine
:mode: lines
```

## Dropdown

An `input-dropdown`'s choices come from its body, one per line. Its
`:value:` option picks which one is initially selected — omit it and myst-baker
uses the first line. Every choice becomes one column of the precomputed
grid, so a three-choice dropdown is exactly as cheap as a three-step
slider.

````md
```{input-dropdown} waveform
:value: sine
sine
square
sawtooth
```

```python{calc}
import math

def waveform_curve(waveform):
    x = [i / 10 for i in range(-31, 32)]
    if waveform == "sine":
        y = [math.sin(xi) for xi in x]
    elif waveform == "square":
        y = [1.0 if math.sin(xi) >= 0 else -1.0 for xi in x]
    else:
        period = 2 * math.pi
        y = [2 * ((xi / period) % 1) - 1 for xi in x]
    return x, y
```

```{plot} scatter
:data: waveform_curve
:mode: lines
```
````

```{input-dropdown} waveform
:value: sine
sine
square
sawtooth
```

```python{calc}
import math

def waveform_curve(waveform):
    x = [i / 10 for i in range(-31, 32)]
    if waveform == "sine":
        y = [math.sin(xi) for xi in x]
    elif waveform == "square":
        y = [1.0 if math.sin(xi) >= 0 else -1.0 for xi in x]
    else:
        period = 2 * math.pi
        y = [2 * ((xi / period) % 1) - 1 for xi in x]
    return x, y
```

```{plot} scatter
:data: waveform_curve
:mode: lines
```
```

- [ ] **Step 4: Create docs/guide/calculations.md**

```markdown
# Calculations

A `calc` block is a plain Python function definition — no
decorators, no special API. myst-baker `exec`s its source into a shared namespace
once per page, then calls whichever function a `plot` block names, once for
every combination of that function's matched inputs.

```{note}
Because this all happens at *build* time, there's no runtime Python on the
published page — by the time a reader's browser loads it, every result is
already sitting in a JSON table. A `calc` function can do anything
ordinary Python can (import from the standard library, loop, branch); it
just needs to return an `(x, y)` pair of equal-length sequences for the
`plot` block that consumes it.
```

## A single calculation

There's nothing sine- or physics-specific about `calc` — any
computation that reduces to an `(x, y)` pair works, like this compound
interest curve:

````md
```{input-slider} rate
:value: 0.05
:min: 0
:max: 0.2
:step: 0.01
```

```python{calc}
def compound_growth(rate):
    years = list(range(0, 11))
    balance = [1000 * (1 + rate) ** t for t in years]
    return years, balance
```

```{plot} scatter
:data: compound_growth
:mode: lines
```
````

```{input-slider} rate
:value: 0.05
:min: 0
:max: 0.2
:step: 0.01
```

```python{calc}
def compound_growth(rate):
    years = list(range(0, 11))
    balance = [1000 * (1 + rate) ** t for t in years]
    return years, balance
```

```{plot} scatter
:data: compound_growth
:mode: lines
```

## Several calculations sharing one input

A page can hold as many `calc` blocks as it needs, and they can
share input sliders freely — myst-baker just matches each function's parameter
names to whatever `input-slider` blocks exist on the page. Below, one
`rate` slider drives *two* independent functions and *two* plots: discrete
annual compounding and continuous compounding.

````md
```{input-slider} rate
:value: 0.05
:min: 0
:max: 0.2
:step: 0.01
```

```python{calc}
def compound_growth(rate):
    years = list(range(0, 11))
    balance = [1000 * (1 + rate) ** t for t in years]
    return years, balance
```

```python{calc}
import math

def compound_continuous(rate):
    years = list(range(0, 11))
    balance = [1000 * math.exp(rate * t) for t in years]
    return years, balance
```

```{plot} scatter
:data: compound_growth
:mode: markers
```

```{plot} scatter
:data: compound_continuous
:mode: lines
```
````

```{input-slider} rate
:value: 0.05
:min: 0
:max: 0.2
:step: 0.01
```

```python{calc}
def compound_growth(rate):
    years = list(range(0, 11))
    balance = [1000 * (1 + rate) ** t for t in years]
    return years, balance
```

```python{calc}
import math

def compound_continuous(rate):
    years = list(range(0, 11))
    balance = [1000 * math.exp(rate * t) for t in years]
    return years, balance
```

Discrete compounding (markers):

```{plot} scatter
:data: compound_growth
:mode: markers
```

Continuous compounding (lines), same `rate` slider:

```{plot} scatter
:data: compound_continuous
:mode: lines
```

```{tip}
Nothing ties a `calc` block to the `plot` immediately below it in the
source — a function stays in scope for the whole page. `plot` blocks look
it up by the name given in `:data:`, so the order they appear in doesn't
matter, as long as the function is defined somewhere on the page.
```
```

- [ ] **Step 5: Create docs/guide/outputs.md**

```markdown
# Plot outputs

A `plot` block's argument is a Plotly trace type, and its `:data:` option
names the `calc` function supplying that trace's data. A calc
function can return either a dict of Plotly field names, spread directly
into the trace (`{"labels": [...], "values": [...]}`), or a plain
tuple/list, matched positionally against the field order myst-baker already knows
for six trace types: `scatter`, `bar`, `box`, and `violin` take `(x, y)`;
`histogram` takes `(x,)`; `pie` takes `(labels, values)`. Its `:mode:`
option is forwarded to Plotly for trace types that use one (the `scatter`
family: `lines`, `markers`, `lines+markers`).

```{note}
By design, `plot`'s argument can be any Plotly trace type — the directive
doesn't hardcode a list of chart kinds. `:data:` and `:mode:` are forwarded
verbatim into the trace; other trace-specific options aren't wired up yet.
The six trace types above have a known positional field order out of the
box; any other Plotly trace type still works as long as its calc function
returns a dict of the field names that trace needs.
```

## One dataset, three scatter modes

The same slider and the same `calc` function feed three `plot`
blocks below, differing only in `:mode:` — a clean look at what `mode`
alone changes.

````md
```{input-slider} amplitude
:value: 1
:min: 0
:max: 2
:step: 0.5
```

```python{calc}
import math

def cosine_curve(amplitude):
    x = list(range(-10, 11))
    y = [amplitude * math.cos(xi / 3) for xi in x]
    return x, y
```

```{plot} scatter
:data: cosine_curve
:mode: lines
```

```{plot} scatter
:data: cosine_curve
:mode: markers
```

```{plot} scatter
:data: cosine_curve
:mode: lines+markers
```
````

```{input-slider} amplitude
:value: 1
:min: 0
:max: 2
:step: 0.5
```

```python{calc}
import math

def cosine_curve(amplitude):
    x = list(range(-10, 11))
    y = [amplitude * math.cos(xi / 3) for xi in x]
    return x, y
```

`:mode: lines` — a line chart:

```{plot} scatter
:data: cosine_curve
:mode: lines
```

`:mode: markers` — a scatter plot:

```{plot} scatter
:data: cosine_curve
:mode: markers
```

`:mode: lines+markers` — both at once:

```{plot} scatter
:data: cosine_curve
:mode: lines+markers
```

## Bar charts

`:mode:` is a `scatter`-family concept; other trace types just ignore it.
A `bar` trace only needs categories on `x` and values on `y` — which a
`calc` function can return just as easily as numeric curves.

````md
```{input-slider} growth
:value: 0.1
:min: -0.2
:max: 0.5
:step: 0.05
```

```python{calc}
def revenue_by_quarter(growth):
    quarters = ["Q1", "Q2", "Q3", "Q4"]
    revenue = [100 * (1 + growth) ** i for i in range(4)]
    return quarters, revenue
```

```{plot} bar
:data: revenue_by_quarter
```
````

```{input-slider} growth
:value: 0.1
:min: -0.2
:max: 0.5
:step: 0.05
```

```python{calc}
def revenue_by_quarter(growth):
    quarters = ["Q1", "Q2", "Q3", "Q4"]
    revenue = [100 * (1 + growth) ** i for i in range(4)]
    return quarters, revenue
```

```{plot} bar
:data: revenue_by_quarter
```

See the [Gallery](../examples/gallery.md) for these pieces combined into larger,
multi-plot examples.

## Histogram

A `histogram` trace only needs one array — samples on `x`. A calc function
feeding a histogram should return a single-element tuple, `(x,)`, not a
bare list, so myst-baker can tell "one array" apart from "one array meant to be
unpacked positionally."

````md
```{input-slider} spread
:value: 1
:min: 0.5
:max: 3
:step: 0.5
```

```python{calc}
def scaled_samples(spread):
    base = [-2, -1.5, -1, -0.5, -0.5, 0, 0, 0, 0.5, 0.5, 1, 1.5, 2]
    samples = [spread * b for b in base]
    return (samples,)
```

```{plot} histogram
:data: scaled_samples
```
````

```{input-slider} spread
:value: 1
:min: 0.5
:max: 3
:step: 0.5
```

```python{calc}
def scaled_samples(spread):
    base = [-2, -1.5, -1, -0.5, -0.5, 0, 0, 0, 0.5, 0.5, 1, 1.5, 2]
    samples = [spread * b for b in base]
    return (samples,)
```

```{plot} histogram
:data: scaled_samples
```

## Pie chart

A `pie` trace needs `labels` and `values` rather than `x`/`y`. Its
`calc` function returns them in that order as a 2-tuple, the same
shape as a scatter's `(x, y)` — just a different pair of names.

````md
```{input-slider} marketing_share
:value: 20
:min: 5
:max: 40
:step: 5
```

```python{calc}
def budget_allocation(marketing_share):
    remaining = 100 - marketing_share
    labels = ["Marketing", "Engineering", "Operations"]
    values = [marketing_share, remaining * 0.6, remaining * 0.4]
    return labels, values
```

```{plot} pie
:data: budget_allocation
```
````

```{input-slider} marketing_share
:value: 20
:min: 5
:max: 40
:step: 5
```

```python{calc}
def budget_allocation(marketing_share):
    remaining = 100 - marketing_share
    labels = ["Marketing", "Engineering", "Operations"]
    values = [marketing_share, remaining * 0.6, remaining * 0.4]
    return labels, values
```

```{plot} pie
:data: budget_allocation
```

## Box and violin plots

`box` and `violin` traces take the same `(x, y)` shape as `bar` — repeated
`x` category labels group their matching `y` values into one distribution
per category. The same data feeds both trace types below.

````md
```{input-slider} shift
:value: 0
:min: -2
:max: 2
:step: 0.5
```

```python{calc}
def quarterly_measurements(shift):
    categories = []
    measurements = []
    base = {
        "Q1": [10, 11, 9, 10.5, 12],
        "Q2": [11, 12, 10, 13, 11.5],
        "Q3": [13, 14, 12.5, 15, 13],
        "Q4": [12, 13, 11, 12.5, 14],
    }
    for quarter, values in base.items():
        for v in values:
            categories.append(quarter)
            measurements.append(v + shift)
    return categories, measurements
```

```{plot} box
:data: quarterly_measurements
```

```{plot} violin
:data: quarterly_measurements
```
````

```{input-slider} shift
:value: 0
:min: -2
:max: 2
:step: 0.5
```

```python{calc}
def quarterly_measurements(shift):
    categories = []
    measurements = []
    base = {
        "Q1": [10, 11, 9, 10.5, 12],
        "Q2": [11, 12, 10, 13, 11.5],
        "Q3": [13, 14, 12.5, 15, 13],
        "Q4": [12, 13, 11, 12.5, 14],
    }
    for quarter, values in base.items():
        for v in values:
            categories.append(quarter)
            measurements.append(v + shift)
    return categories, measurements
```

```{plot} box
:data: quarterly_measurements
```

```{plot} violin
:data: quarterly_measurements
```
```

- [ ] **Step 6: Create docs/examples/gallery.md**

```markdown
# Gallery

Full examples that combine several inputs, `calc` functions, and
`plot` blocks on one page — the way a real doc page tends to look, rather
than one concept at a time.

## Damped oscillator, two views

Three sliders (`amplitude`, `damping`, `frequency`) drive one function; two
`plot` blocks render its output two different ways from the same
precomputed data.

````md
```{input-slider} amplitude
:value: 1
:min: 0.5
:max: 2
:step: 0.5
```

```{input-slider} damping
:value: 0.2
:min: 0
:max: 1
:step: 0.2
```

```{input-slider} frequency
:value: 1
:min: 0.5
:max: 2
:step: 0.5
```

```python{calc}
import math

def damped_oscillator(amplitude, damping, frequency):
    x = [i / 10 for i in range(0, 101)]
    y = [
        amplitude * math.exp(-damping * xi) * math.cos(frequency * xi)
        for xi in x
    ]
    return x, y
```

```{plot} scatter
:data: damped_oscillator
:mode: lines
```

```{plot} scatter
:data: damped_oscillator
:mode: markers
```
````

```{input-slider} amplitude
:value: 1
:min: 0.5
:max: 2
:step: 0.5
```

```{input-slider} damping
:value: 0.2
:min: 0
:max: 1
:step: 0.2
```

```{input-slider} frequency
:value: 1
:min: 0.5
:max: 2
:step: 0.5
```

```python{calc}
import math

def damped_oscillator(amplitude, damping, frequency):
    x = [i / 10 for i in range(0, 101)]
    y = [
        amplitude * math.exp(-damping * xi) * math.cos(frequency * xi)
        for xi in x
    ]
    return x, y
```

```{plot} scatter
:data: damped_oscillator
:mode: lines
```

```{plot} scatter
:data: damped_oscillator
:mode: markers
```

## Projectile trajectory

Two sliders (`velocity`, `angle`) parameterize a physical trajectory —
`calc` isn't limited to `y = f(x)`; `x` and `y` here are both derived
from a shared time parameter.

````md
```{input-slider} velocity
:value: 20
:min: 5
:max: 30
:step: 5
```

```{input-slider} angle
:value: 45
:min: 10
:max: 80
:step: 5
```

```python{calc}
import math

def projectile_trajectory(velocity, angle):
    g = 9.81
    theta = math.radians(angle)
    t_flight = 2 * velocity * math.sin(theta) / g
    steps = 50
    xs, ys = [], []
    for i in range(steps + 1):
        t = t_flight * i / steps
        xs.append(velocity * math.cos(theta) * t)
        ys.append(velocity * math.sin(theta) * t - 0.5 * g * t**2)
    return xs, ys
```

```{plot} scatter
:data: projectile_trajectory
:mode: lines
```
````

```{input-slider} velocity
:value: 20
:min: 5
:max: 30
:step: 5
```

```{input-slider} angle
:value: 45
:min: 10
:max: 80
:step: 5
```

```python{calc}
import math

def projectile_trajectory(velocity, angle):
    g = 9.81
    theta = math.radians(angle)
    t_flight = 2 * velocity * math.sin(theta) / g
    steps = 50
    xs, ys = [], []
    for i in range(steps + 1):
        t = t_flight * i / steps
        xs.append(velocity * math.cos(theta) * t)
        ys.append(velocity * math.sin(theta) * t - 0.5 * g * t**2)
    return xs, ys
```

```{plot} scatter
:data: projectile_trajectory
:mode: lines
```

## Revenue vs. expenses

One shared `growth` slider, two independent `calc` functions, two
`bar` plots side by side — a small dashboard from a handful of blocks.

````md
```{input-slider} growth
:value: 0.1
:min: -0.2
:max: 0.5
:step: 0.05
```

```python{calc}
def revenue_by_quarter(growth):
    quarters = ["Q1", "Q2", "Q3", "Q4"]
    revenue = [100 * (1 + growth) ** i for i in range(4)]
    return quarters, revenue
```

```python{calc}
def expenses_by_quarter(growth):
    quarters = ["Q1", "Q2", "Q3", "Q4"]
    expenses = [70 * (1 + growth * 0.6) ** i for i in range(4)]
    return quarters, expenses
```

```{plot} bar
:data: revenue_by_quarter
```

```{plot} bar
:data: expenses_by_quarter
```
````

```{input-slider} growth
:value: 0.1
:min: -0.2
:max: 0.5
:step: 0.05
```

```python{calc}
def revenue_by_quarter(growth):
    quarters = ["Q1", "Q2", "Q3", "Q4"]
    revenue = [100 * (1 + growth) ** i for i in range(4)]
    return quarters, revenue
```

```python{calc}
def expenses_by_quarter(growth):
    quarters = ["Q1", "Q2", "Q3", "Q4"]
    expenses = [70 * (1 + growth * 0.6) ** i for i in range(4)]
    return quarters, expenses
```

Revenue:

```{plot} bar
:data: revenue_by_quarter
```

Expenses, same `growth` slider:

```{plot} bar
:data: expenses_by_quarter
```
```

- [ ] **Step 7: Create docs/changelog.md**

```markdown
# Changelog

All notable changes to myst-baker are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 0.1.0

Initial release.

### Added

- Three input widgets — `input-slider`, `input-checkbox`, and
  `input-dropdown` — each bound to a name that `calc` functions pick up by
  matching parameter names.
- `python{calc}` fence blocks: plain Python function definitions, executed
  once per page and called once per combination of their matched inputs'
  values.
- A `plot` output block backed by Plotly, with built-in field-order support
  for six trace types — `scatter`, `bar`, `histogram`, `pie`, `box`, and
  `violin` — and pass-through support for any other Plotly trace type via a
  `calc` function returning a dict of field names.
- A precomputed, static-build architecture: myst-baker runs every `calc`
  function over the full cartesian product of its inputs' values at *build*
  time and bakes the results into a JSON lookup table, so published pages
  need no backend, notebook kernel, or live Python process.
```

- [ ] **Step 8: Create docs/authors.md**

```markdown
# Authors

myst-baker is written and maintained by **Ian Mullens**
(<imullens@hes-heerema.com>).

## License

myst-baker is licensed under the [MIT License](../LICENSE).

## Contributing

Found a bug, or want to propose a feature? Open an issue or a pull request
at [github.com/IansGithubAcc/myst-baker](https://github.com/IansGithubAcc/myst-baker).
```

- [ ] **Step 9: Verify all eight files exist**

Run: `find docs -maxdepth 2 -iname "*.md" | sort`
Expected output includes exactly these paths (plus the pre-existing `docs/superpowers/` tree, not shown by `-maxdepth 2`):
```
docs/authors.md
docs/changelog.md
docs/examples/gallery.md
docs/guide/calculations.md
docs/guide/inputs.md
docs/guide/outputs.md
docs/index.md
docs/installation.md
```

- [ ] **Step 10: Commit**

```bash
git add docs/index.md docs/installation.md docs/guide docs/examples docs/changelog.md docs/authors.md
git commit -m "docs: author new docs/ pages (installation, guide, examples, changelog, authors)"
```

---

### Task 3: Wire the new pages into the site and trim the README

**Files:**
- Modify: `myst.yml`
- Modify: `README.md`

**Interfaces:**
- Consumes: all eight files from Task 2, and `LICENSE` from Task 1 (linked from `README.md`'s "Documentation" section, indirectly via `docs/authors.md`).
- Produces: a fully-updated `myst.yml` `project.toc`/frontmatter that Task 5 (content/ deletion) relies on containing zero `content/` references.

- [ ] **Step 1: Replace myst.yml**

Replace the full contents of `myst.yml` with:

```yaml
# See docs at: https://mystmd.org/guide/frontmatter
version: 1
project:
  id: d58eaa1c-67af-451e-b63f-5caaa2041a78
  title: myst-baker
  description: Precomputed interactive docs via a MyST executable plugin
  authors:
    - name: Ian Mullens
  github: https://github.com/IansGithubAcc/myst-baker
  toc:
    - file: docs/index.md
    - file: docs/installation.md
    - title: Guide
      children:
        - file: docs/guide/inputs.md
        - file: docs/guide/calculations.md
        - file: docs/guide/outputs.md
    - title: Examples
      children:
        - file: docs/examples/gallery.md
    - file: docs/changelog.md
    - file: docs/authors.md
  plugins:
    - type: executable
      # Generated directly by `uv sync` (see docs/installation.md). MyST resolves this as a
      # literal path, not a PATH search, so it must match where uv puts the launcher.
      # Windows path shown below; on Linux/Mac use .venv/bin/myst-baker-plugin instead.
      path: .venv/Scripts/myst-baker-plugin.exe
site:
  template: book-theme
  options:
    favicon: favicon.ico
  #   logo: site_logo.png
```

- [ ] **Step 2: Replace README.md**

Replace the full contents of `README.md` with:

```markdown
# myst-baker

Precomputed interactive docs via a MyST executable plugin.

myst-baker lets you author live, interactive examples that need no server:
you write an input widget, a plain Python function, and a plot, and
myst-baker runs your function over every combination of input values at
*build* time. The result is baked into the page as a JSON lookup table —
moving a slider in the browser is just a key lookup and a chart redraw, with
no Python running anywhere at page-view time.

## Documentation

- [Installation](docs/installation.md) — add myst-baker to your own MyST
  project, or set up this repo for development.
- [Guide](docs/guide/inputs.md) — input widgets, `calc` blocks, and plot
  outputs.
- [Examples](docs/examples/gallery.md) — full worked pages.
- [Changelog](docs/changelog.md)
- [Authors](docs/authors.md)
```

- [ ] **Step 3: Build the site and verify it succeeds**

Run: `uv run myst build --html`
Expected: exits `0`, no errors.

- [ ] **Step 4: Verify every new page produced a route**

Run:
```bash
find _build/html -maxdepth 1 -iname "index.html"
find _build/html/installation _build/html/inputs _build/html/calculations _build/html/outputs _build/html/gallery _build/html/changelog _build/html/authors -iname "index.html"
```
Expected: `_build/html/index.html` exists, and each of `installation/index.html`, `inputs/index.html`, `calculations/index.html`, `outputs/index.html`, `gallery/index.html`, `changelog/index.html`, `authors/index.html` exists under `_build/html/`.

- [ ] **Step 5: Commit**

```bash
git add myst.yml README.md
git commit -m "docs: wire docs/ pages into myst.yml toc, trim README to a pointer"
```

---

### Task 4: Update test comments for the new page paths

**Files:**
- Modify: `tests/test_e2e_browser.py:117`
- Modify: `tests/test_e2e_browser.py:144`
- Modify: `tests/test_e2e_browser.py:185`

**Interfaces:**
- Consumes: nothing new — the `inputs_page_url`/`outputs_page_url` fixtures (lines 42-48) are unchanged, since routes don't depend on folder structure (see Global Constraints).

These are explanatory comments only; no test logic changes, since the built routes (`/inputs/`, `/outputs/`) are identical before and after the page moves.

- [ ] **Step 1: Update the three comments**

In `tests/test_e2e_browser.py`, line 117, change:
```python
    # content/inputs.md's live iframes: One slider (0), Two sliders (1),
```
to:
```python
    # docs/guide/inputs.md's live iframes: One slider (0), Two sliders (1),
```

Line 144, change:
```python
    # content/inputs.md's live iframes, in document order: One slider (0),
```
to:
```python
    # docs/guide/inputs.md's live iframes, in document order: One slider (0),
```

Line 185, change:
```python
    # content/outputs.md's live plots, in document order: 3 scatter-mode
```
to:
```python
    # docs/guide/outputs.md's live plots, in document order: 3 scatter-mode
```

- [ ] **Step 2: Run the e2e browser tests**

Run: `uv run pytest tests/test_e2e_browser.py -v`
Expected: all tests PASS (same pass/fail outcome as before this task — the change is comment-only).

- [ ] **Step 3: Commit**

```bash
git add tests/test_e2e_browser.py
git commit -m "test: update e2e comments to reference docs/guide/ paths"
```

---

### Task 5: Delete content/ and do a final full verification

**Files:**
- Delete: `content/index.md`
- Delete: `content/inputs.md`
- Delete: `content/calculations.md`
- Delete: `content/outputs.md`
- Delete: `content/gallery.md`

**Interfaces:**
- Consumes: the fully-updated `myst.yml` from Task 3 (already has zero `content/` references) and the passing test suite from Task 4.

- [ ] **Step 1: Delete the content/ directory**

```bash
git rm -r content/
```

- [ ] **Step 2: Build the site and verify it still succeeds without content/**

Run: `uv run myst build --html`
Expected: exits `0`, no errors, no warnings about missing `content/*.md` files (confirms `myst.yml` had already stopped referencing them in Task 3).

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest`
Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git commit -m "docs: remove content/ now that docs/ fully replaces it"
```
