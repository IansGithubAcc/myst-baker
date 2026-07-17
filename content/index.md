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

- **[Input widgets](inputs.md)** — slider, checkbox, and dropdown
  configurations: single input, multiple inputs, fine steps and negative
  ranges, and choice-based inputs.
- **[Calculations](calculations.md)** — how `calc` blocks work, and
  how several of them can share a page.
- **[Plot outputs](outputs.md)** — the different Plotly trace types
  (scatter, bar, histogram, pie, box, violin) and modes a `plot` block can
  render.
- **[Gallery](gallery.md)** — full worked examples that combine several
  inputs, functions, and plots on one page.
