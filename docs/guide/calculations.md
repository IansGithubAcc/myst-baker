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

```{tip}
Add `:hide` inside the tag — `` ```python{calc:hide} `` — to keep a
block's source out of the rendered page while it still executes into the
page's calc namespace. Handy when a `calc` function exists purely to feed
a `plot` block and isn't meant to be read as an example.
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
````
```python{calc}
def compound_growth(rate):
    years = list(range(0, 11))
    balance = [1000 * (1 + rate) ** t for t in years]
    return years, balance
```
````
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

```{plot} scatter
:data: compound_growth
:mode: lines
```

### Several calculations sharing one input

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
````
```python{calc}
import math

def compound_growth(rate):
    years = list(range(0, 11))
    balance = [1000 * (1 + rate) ** t for t in years]
    return years, balance

def compound_continuous(rate):
    years = list(range(0, 11))
    balance = [1000 * math.exp(rate * t) for t in years]
    return years, balance
```
````
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

## Returning a dict for other trace types

A `calc` function isn't limited to the `(x, y)`-style tuples used above.
Returning a **dict** instead hands myst-baker the exact Plotly field names to
use, spread directly into the trace — which is how you drive any Plotly
trace type `plot` doesn't already know a positional field order for. Here,
a `heatmap` (not one of the six built-in types) is fed by a function
returning `{"z": [[...]]}`:

````md
```{input-slider} spread
:value: 3
:min: 1
:max: 6
:step: 0.5
```
````
```python{calc}
import math

def gaussian_heatmap(spread):
    size = 15
    center = size // 2
    return {
        "z": [
            [
                math.exp(-((x - center) ** 2 + (y - center) ** 2) / (2 * spread**2))
                for x in range(size)
            ]
            for y in range(size)
        ]
    }
```
````
```{plot} heatmap
:data: gaussian_heatmap
```
````

```{input-slider} spread
:value: 3
:min: 1
:max: 6
:step: 0.5
```

```{plot} heatmap
:data: gaussian_heatmap
```

```{tip}
A dict return works for the six built-in trace types too — it's not
exclusive to unsupported ones. Positional tuples are just a shorthand for
the common cases; see [Plot outputs](outputs.md) for the full field list.
```

## Hiding a calc block's source

Add `:hide` to the tag and a `calc` block still runs — it's still exec'd
into the page's namespace, still available to any `plot` block that
names it — but its source never reaches the rendered page. Useful when a
function is plumbing a `plot` needs rather than something worth reading:

````md
```{input-slider} k
:value: 1
:min: -3
:max: 3
:step: 0.5
```

```python{calc:hide}
def scale_line(k):
    x = list(range(-5, 6))
    return x, [k * xi for xi in x]
```

```{plot} scatter
:data: scale_line
:mode: lines
```
````

And here's that block, live. Please note that the definition above is just a citation.
The actual python function is defined below this text and is hidden.

```{input-slider} k
:value: 1
:min: -3
:max: 3
:step: 0.5
```

```python{calc:hide}
def scale_line(k):
    x = list(range(-5, 6))
    return x, [k * xi for xi in x]
```

```{plot} scatter
:data: scale_line
:mode: lines
```

```{tip}
`:hide` is per-block, not all-or-nothing for a page — a hidden and a
visible `calc` block can sit side by side, as in the
[Damped oscillator, two views](../examples/damped-oscillator.md) example.
```
