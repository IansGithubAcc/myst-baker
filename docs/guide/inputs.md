# Input widgets

myst-baker ships three input widgets — `input-slider`, `input-checkbox`, and
`input-dropdown` — and any number of them can appear on a page in any
combination: each `calc` function picks up whichever ones match its
parameter names. This page runs through the configurations you'll actually
use: sliders (including multiple sliders sharing one function, and
fine-grained or negative ranges), a checkbox toggle, and a dropdown of named
choices.

```{note}
An `input-slider`'s argument is the name other blocks refer to it by. Its
`:min:`/`:max:`/`:step:` options define the full set of values myst-baker
precomputes — every combination becomes one row in the build-time grid, so
narrower ranges and coarser steps mean smaller, faster builds.
```

## Sliders

An `input-slider`'s argument is the name other blocks refer to it by, and a
`calc` function's parameters are matched to sliders by name — a single
slider drives a single-parameter function exactly the same way multiple
sliders drive a multi-parameter one. A function can take as many slider
parameters as it needs; myst-baker builds the cartesian product of all of
their values. Here, `a` and `b` together shape a parabola.

````md
```{input-slider} a
:value: 1
:min: -3
:max: 3
:step: 1
```

```{input-slider} b
:value: 0
:min: -3
:max: 3
:step: 1
```
````
```python{calc}
def parabola(a, b):
    x = [i / 2 for i in range(-10, 11)]
    y = [a * xi**2 + b for xi in x]
    return x, y
```
````
```{plot} scatter
:data: parabola
:mode: lines
```
````

```{input-slider} a
:value: 1
:min: -3
:max: 3
:step: 1
```

```{input-slider} b
:value: 0
:min: -3
:max: 3
:step: 1
```

```{plot} scatter
:data: parabola
:mode: lines
```

### Fine steps and negative ranges

Slider options aren't limited to small integer ranges — `:step:` accepts
decimals and `:min:`/`:max:` can straddle zero. Here, a damping coefficient
runs from -0.5 (growth) to 1.0 (decay) in steps of 0.05.

````md
```{input-slider} damping
:value: 0.3
:min: -0.5
:max: 1.0
:step: 0.05
```
````
```python{calc}
import math

def damped_envelope(damping):
    x = [i / 5 for i in range(0, 26)]
    y = [math.exp(-damping * xi) for xi in x]
    return x, y
```
````
```{plot} scatter
:data: damped_envelope
:mode: lines
```
````

```{input-slider} damping
:value: 0.3
:min: -0.5
:max: 1.0
:step: 0.05
```

```{plot} scatter
:data: damped_envelope
:mode: lines
```

```{tip}
That last example precomputes 31 values for one input. Two sliders like the
"Sliders" example above (7 x 7 = 49 combinations) is still trivial; the
build only starts to matter once a page's inputs multiply into the
thousands — see [Calculations](calculations.md) for how the grid is built.
```

## Checkbox

An `input-checkbox`'s argument is the name other blocks refer to it by, same
as `input-slider`. Its `:value:` option sets the initial state; myst-baker always
precomputes both `true` and `false`, regardless of which one a page starts
on.

````md
```{input-checkbox} inverted
:value: false
```
````
```python{calc}
import math

def maybe_inverted_sine(inverted):
    x = [i / 10 for i in range(-31, 32)]
    sign = -1 if inverted else 1
    y = [sign * math.sin(xi) for xi in x]
    return x, y
```
````
```{plot} scatter
:data: maybe_inverted_sine
:mode: lines
```
````

```{input-checkbox} inverted
:value: false
```

```{plot} scatter
:data: maybe_inverted_sine
:mode: lines
```

## Dropdown

An `input-dropdown`'s choices come from its body, one per line. Its
`:value:` option picks which one is initially selected — omit it and myst-baker
uses the first line. Every choice becomes one column of the precomputed
grid, so a three-choice dropdown is exactly as cheap as a three-step
slider.

````md
```{input-dropdown} waveform
:value: sine
sine
square
sawtooth
```
````
```python{calc}
import math

def waveform_curve(waveform):
    x = [i / 10 for i in range(-31, 32)]
    if waveform == "sine":
        y = [math.sin(xi) for xi in x]
    elif waveform == "square":
        y = [1.0 if math.sin(xi) >= 0 else -1.0 for xi in x]
    else:
        period = 2 * math.pi
        y = [2 * ((xi / period) % 1) - 1 for xi in x]
    return x, y
```
````
```{plot} scatter
:data: waveform_curve
:mode: lines
```
````

```{input-dropdown} waveform
:value: sine
sine
square
sawtooth
```

```{plot} scatter
:data: waveform_curve
:mode: lines
```
