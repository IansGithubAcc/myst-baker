# Plot outputs

A `plot` block's argument is a Plotly trace type, and its `:data:` option
names the `calc` function supplying that trace's data — or a
comma-separated list of `calc` function names to render as several
traces on one plot (see [Multiple traces on one plot](#multiple-traces-on-one-plot)
below). A calc function can return either a dict of Plotly field names,
spread directly into the trace (`{"labels": [...], "values": [...]}`), or
a plain tuple/list, matched positionally against the field order
myst-baker already knows for six trace types: `scatter`, `bar`, `box`,
and `violin` take `(x, y)`; `histogram` takes `(x,)`; `pie` takes
`(labels, values)`. Its `:mode:` option is forwarded to Plotly for trace
types that use one (the `scatter` family: `lines`, `markers`,
`lines+markers`).

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
````
```python{calc}
import math

def cosine_curve(amplitude):
    x = list(range(-10, 11))
    y = [amplitude * math.cos(xi / 3) for xi in x]
    return x, y
```
````
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
````
```python{calc}
def revenue_by_quarter(growth):
    quarters = ["Q1", "Q2", "Q3", "Q4"]
    revenue = [100 * (1 + growth) ** i for i in range(4)]
    return quarters, revenue
```
````
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

```{plot} bar
:data: revenue_by_quarter
```

See the [examples](../examples/revenue-vs-expenses.md) for these pieces combined into larger,
multi-plot pages.

## Multiple traces on one plot

Give `:data:` a comma-separated list of `calc` function names instead of
one, and they render as separate traces on the *same* plot rather than
separate plots — each function still runs independently, but Plotly draws
them together. The functions must
share the same parameters, since one control panel drives all of them.
Each trace's legend name defaults to its function name (underscores
become spaces); a function returning a dict can set its own `"name"` to
override that default.

````
```{input-slider} amplitude_1
:value: 1
:min: 0
:max: 2
:step: 0.5
```
```{input-slider} amplitude_2
:value: 1
:min: 0
:max: 2
:step: 0.5
```
````

```{input-slider} amplitude_1
:value: 1
:min: 0
:max: 2
:step: 0.5
```
```{input-slider} amplitude_2
:value: 1
:min: 0
:max: 2
:step: 0.5
```
```python{calc}
import math

def cosine_curve(amplitude_1, amplitude_2):
    x = list(range(-10, 11))
    y = [amplitude_1 * math.cos(xi / 3) for xi in x]
    return x, y

def sine_curve(amplitude_1, amplitude_2):
    x = list(range(-10, 11))
    y = [amplitude_2 * math.sin(xi / 3) for xi in x]
    return x, y
```
````
```{plot} scatter
:data: cosine_curve,sine_curve
```
````
```{plot} scatter
:data: cosine_curve,sine_curve
```

When using multiple traces with `bar` plots they will be grouped side by side.

````md
```{input-slider} growth
:value: 0.1
:min: -0.2
:max: 0.5
:step: 0.05
```
````
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
````
```{plot} bar
:data: revenue_by_quarter,expenses_by_quarter
```
````

```{input-slider} growth
:value: 0.1
:min: -0.2
:max: 0.5
:step: 0.05
```

```{plot} bar
:data: revenue_by_quarter,expenses_by_quarter
```

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
````
```python{calc}
def scaled_samples(spread):
    base = [-2, -1.5, -1, -0.5, -0.5, 0, 0, 0, 0.5, 0.5, 1, 1.5, 2]
    samples = [spread * b for b in base]
    return (samples,)
```
````
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
````
```python{calc}
def budget_allocation(marketing_share):
    remaining = 100 - marketing_share
    labels = ["Marketing", "Engineering", "Operations"]
    values = [marketing_share, remaining * 0.6, remaining * 0.4]
    return labels, values
```
````
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
````
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
````
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

```{plot} box
:data: quarterly_measurements
```

```{plot} violin
:data: quarterly_measurements
```

## Full Plotly figures

Every trace type above hands `plot` a single calc function whose return
value is spread into one trace, with `plot`'s argument naming that
trace's Plotly type. For full control over the chart — axis titles,
tick formatting, annotations, or several differently-typed traces on
one plot — give `plot` the reserved argument `figure` instead of a
trace type, and have its calc function return a complete figure rather
than a single trace's fields.

```{warning}
Figure mode only needs the optional `plotly` extra
(`pip install myst-baker[plotly]` / `uv add "myst-baker[plotly]"`) if
the calc function builds a real `plotly.graph_objects`/`plotly.express`
figure. A calc function can also return a plain
`{"data": [...], "layout": {...}}` dict by hand instead, with no extra
install required.
```

A `figure` block's calc function isn't combinable with others —
`:data:` names exactly one function — and `:mode:` (or any other
directive option) is ignored, since the figure already fully specifies
its own styling.

````md
```{input-slider} phase
:value: 0
:min: -3
:max: 3
:step: 0.25
```
````
```python{calc}
import math
import plotly.graph_objects as go

def phase_shifted_wave(phase):
    x = list(range(-10, 11))
    y = [math.sin(xi / 3 + phase) for xi in x]
    fig = go.Figure(data=[go.Scatter(x=x, y=y, mode="lines")])
    fig.update_layout(
        title="Phase-shifted wave",
        xaxis_title="x",
        yaxis_title='sin(x/3 + phase)',
        annotations=[
            dict(x=0, y=y[10], text=f"phase = {phase:.2f}", showarrow=True, arrowhead=2)
        ],
    )
    return fig
```
````
```{plot} figure
:data: phase_shifted_wave
```
````

```{input-slider} phase
:value: 0
:min: -3
:max: 3
:step: 0.25
```

```{plot} figure
:data: phase_shifted_wave
```
