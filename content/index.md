# pymd MVP demo

$ y = a * x^2 + b$

```{input-slider} a
:value: 0
:min: -6
:max: 6
:step: 1
```

```{input-slider} b
:value: 0
:min: -3
:max: 3
:step: 1
```

```{calc-python}
import math

def get_plot_data(a, b):
    x = list(range(-10, 10))
    y = [math.cos(a * xi/10) + b for xi in x]
    return x, y
```

```{plot} bar
:data: get_plot_data
:mode: lines
```
Ain't it beautiful?