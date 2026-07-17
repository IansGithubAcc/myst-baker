# Revenue vs. expenses

One shared `growth` slider, two independent `calc` functions, two
`bar` plots side by side — a small dashboard from a handful of blocks.

```{input-slider} growth
:value: 0.1
:min: -0.2
:max: 0.5
:step: 0.05
```

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

Revenue:

```{plot} bar
:data: revenue_by_quarter
```

Expenses, same `growth` slider:

```{plot} bar
:data: expenses_by_quarter
```
