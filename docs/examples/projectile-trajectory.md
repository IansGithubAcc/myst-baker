# Projectile trajectory

Two sliders (`velocity`, `angle`) parameterize a physical trajectory —
`calc` isn't limited to `y = f(x)`; `x` and `y` here are both derived
from a shared time parameter.

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

```python{calc}
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
