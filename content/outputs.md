# Plot outputs

A `plot` block's argument is a Plotly trace type, and its `:data:` option
names the `calc-python` function supplying `(x, y)`. Its `:mode:` option is
forwarded to Plotly for trace types that use one (the `scatter` family:
`lines`, `markers`, `lines+markers`).

```{note}
By design, `plot`'s argument can be any Plotly trace type — the directive
doesn't hardcode a list of chart kinds. This build forwards `:data:` and
`:mode:` verbatim into the trace; other trace-specific options aren't wired
up yet, so today's practical range is whatever a bare `type` + `mode` +
`x`/`y` can express — which already covers line charts, scatter plots, and
bar charts, as below.
```

## One dataset, three scatter modes

The same slider and the same `calc-python` function feed three `plot`
blocks below, differing only in `:mode:` — a clean look at what `mode`
alone changes.

````md
```{input-slider} amplitude
:value: 1
:min: 0
:max: 2
:step: 0.5
```

```{calc-python}
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

```{calc-python}
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
`calc-python` function can return just as easily as numeric curves.

````md
```{input-slider} growth
:value: 0.1
:min: -0.2
:max: 0.5
:step: 0.05
```

```{calc-python}
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

```{calc-python}
def revenue_by_quarter(growth):
    quarters = ["Q1", "Q2", "Q3", "Q4"]
    revenue = [100 * (1 + growth) ** i for i in range(4)]
    return quarters, revenue
```

```{plot} bar
:data: revenue_by_quarter
```

See the [Gallery](gallery.md) for these pieces combined into larger,
multi-plot examples.
