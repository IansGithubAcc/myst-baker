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

## Histogram

A `histogram` trace only needs one array — samples on `x`. A calc function
feeding a histogram should return a single-element tuple, `(x,)`, not a
bare list, so pymd can tell "one array" apart from "one array meant to be
unpacked positionally."

````md
```{input-slider} spread
:value: 1
:min: 0.5
:max: 3
:step: 0.5
```

```{calc-python}
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

```{calc-python}
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
`calc-python` function returns them in that order as a 2-tuple, the same
shape as a scatter's `(x, y)` — just a different pair of names.

````md
```{input-slider} marketing_share
:value: 20
:min: 5
:max: 40
:step: 5
```

```{calc-python}
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

```{calc-python}
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

```{calc-python}
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

```{calc-python}
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
