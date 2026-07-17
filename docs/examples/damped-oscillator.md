# Damped oscillator, two views

Three sliders (`amplitude`, `damping`, `frequency`) drive one function; two
`plot` blocks render its output two different ways from the same
precomputed data.

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

```python{calc:hide}
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
