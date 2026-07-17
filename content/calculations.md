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
