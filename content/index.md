# pymd

pymd is a MyST plugin for writing documentation with **live, interactive
examples that need no server**. You author three kinds of fenced blocks —
an input widget, a plain Python function, and a plot — and pymd runs your
function over every possible combination of input values *at build time*.
The result is baked into the page as a JSON lookup table: moving a slider in
the browser is just a key lookup and a chart redraw, with no Python running
anywhere at page-view time.

## The mental model

Every interactive figure in these docs is built from the same three pieces:

1. **`input-slider`** — declares a named numeric input and its range.
2. **`calc-python`** — a normal Python function whose parameter names match
   input names. pymd calls it once per combination of input values.
3. **`plot`** — a Plotly trace, fed by one `calc-python` function's output.

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

```{calc-python}
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

```{calc-python}
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

- **[Input widgets](inputs.md)** — slider configurations: single input,
  multiple inputs, fine steps, negative ranges.
- **[Calculations](calculations.md)** — how `calc-python` blocks work, and
  how several of them can share a page.
- **[Plot outputs](outputs.md)** — the different Plotly trace types and
  modes a `plot` block can render.
- **[Gallery](gallery.md)** — full worked examples that combine several
  inputs, functions, and plots on one page.
