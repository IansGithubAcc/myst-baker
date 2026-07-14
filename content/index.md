# pymd MVP demo

```{input-slider} a
:value: 3
:min: 0
:max: 10
:step: 1
```

```{calc-python}
def get_plot_data(a):
    x = list(range(10))
    y = [a * xi for xi in x]
    return x, y
```

```{plot} scatter
:data: get_plot_data
:mode: lines
```
