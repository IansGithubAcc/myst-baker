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
:value: 0
:min: -3
:max: 3
:step: 0.5
```
````
```python{calc}
import math
def scale_line(k):
    x = [x * 0.1 for x in range(-60, 60)]
    y = [math.cos(k + xi) for xi in x]
    return x, y
```
````md
```{plot} scatter
:data: scale_line
:mode: lines
```
````

And here's that same block, live — drag the slider:

```{input-slider} k
:value: 0
:min: -3
:max: 3
:step: 0.5
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
- **[Damped oscillator](examples/damped-oscillator.md)**,
  **[projectile trajectory](examples/projectile-trajectory.md)**, and
  **[revenue vs. expenses](examples/revenue-vs-expenses.md)** — worked
  examples that combine several inputs, functions, and plots on one page.
- **[Two-source potential field](examples/potential-field-contour.md)** —
  a `{plot} figure` block combining a labeled contour trace, a scatter
  overlay marking the sources, and a dynamic annotation from one `calc`
  function.
