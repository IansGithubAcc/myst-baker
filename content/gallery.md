# Gallery

Full examples that combine several inputs, `calc-python` functions, and
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

```{calc-python}
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

```{calc-python}
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
`calc-python` isn't limited to `y = f(x)`; `x` and `y` here are both derived
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

```{calc-python}
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

```{calc-python}
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

One shared `growth` slider, two independent `calc-python` functions, two
`bar` plots side by side — a small dashboard from a handful of blocks.

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

```{calc-python}
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

```{calc-python}
def revenue_by_quarter(growth):
    quarters = ["Q1", "Q2", "Q3", "Q4"]
    revenue = [100 * (1 + growth) ** i for i in range(4)]
    return quarters, revenue
```

```{calc-python}
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
