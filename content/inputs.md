# Input widgets

pymd currently ships one input widget — `input-slider` — but a single
directive covers a lot of ground: any number of sliders can appear on a
page, and each `calc-python` function picks up whichever ones match its
parameter names. This page runs through the configurations you'll actually
use: one input, several inputs, fine steps, and negative ranges.

```{note}
An `input-slider`'s argument is the name other blocks refer to it by. Its
`:min:`/`:max:`/`:step:` options define the full set of values pymd
precomputes — every combination becomes one row in the build-time grid, so
narrower ranges and coarser steps mean smaller, faster builds.
```

## One slider

The simplest case: a single input driving a single-parameter function.

````md
```{input-slider} amplitude
:value: 1
:min: 0
:max: 2
:step: 0.25
```

```{calc-python}
import math

def sine_amplitude(amplitude):
    x = [i / 10 for i in range(-31, 32)]
    y = [amplitude * math.sin(xi) for xi in x]
    return x, y
```

```{plot} scatter
:data: sine_amplitude
:mode: lines
```
````

```{input-slider} amplitude
:value: 1
:min: 0
:max: 2
:step: 0.25
```

```{calc-python}
import math

def sine_amplitude(amplitude):
    x = [i / 10 for i in range(-31, 32)]
    y = [amplitude * math.sin(xi) for xi in x]
    return x, y
```

```{plot} scatter
:data: sine_amplitude
:mode: lines
```

## Two sliders

A function can take as many parameters as you like — pymd matches each one
to an `input-slider` by name and builds the cartesian product of their
values. Here, `a` and `b` together shape a parabola.

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

```{calc-python}
def parabola(a, b):
    x = [i / 2 for i in range(-10, 11)]
    y = [a * xi**2 + b for xi in x]
    return x, y
```

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

```{calc-python}
def parabola(a, b):
    x = [i / 2 for i in range(-10, 11)]
    y = [a * xi**2 + b for xi in x]
    return x, y
```

```{plot} scatter
:data: parabola
:mode: lines
```

## Three sliders

Nothing changes structurally with a third input — the precomputed grid just
grows by another factor. Amplitude, frequency, and phase together drive one
sine curve.

````md
```{input-slider} amp
:value: 1
:min: 0
:max: 2
:step: 0.5
```

```{input-slider} freq
:value: 1
:min: 0.5
:max: 2
:step: 0.5
```

```{input-slider} phase
:value: 0
:min: 0
:max: 6
:step: 1
```

```{calc-python}
import math

def sine_wave_phase(amp, freq, phase):
    x = [i / 10 for i in range(-31, 32)]
    y = [amp * math.sin(freq * xi + phase) for xi in x]
    return x, y
```

```{plot} scatter
:data: sine_wave_phase
:mode: lines
```
````

```{input-slider} amp
:value: 1
:min: 0
:max: 2
:step: 0.5
```

```{input-slider} freq
:value: 1
:min: 0.5
:max: 2
:step: 0.5
```

```{input-slider} phase
:value: 0
:min: 0
:max: 6
:step: 1
```

```{calc-python}
import math

def sine_wave_phase(amp, freq, phase):
    x = [i / 10 for i in range(-31, 32)]
    y = [amp * math.sin(freq * xi + phase) for xi in x]
    return x, y
```

```{plot} scatter
:data: sine_wave_phase
:mode: lines
```

## Fine steps and negative ranges

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

```{calc-python}
import math

def damped_envelope(damping):
    x = [i / 5 for i in range(0, 26)]
    y = [math.exp(-damping * xi) for xi in x]
    return x, y
```

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

```{calc-python}
import math

def damped_envelope(damping):
    x = [i / 5 for i in range(0, 26)]
    y = [math.exp(-damping * xi) for xi in x]
    return x, y
```

```{plot} scatter
:data: damped_envelope
:mode: lines
```

```{tip}
That last example precomputes 31 values for one input. Three sliders like
the one above (5 x 4 x 7 = 140 combinations) is still trivial; the build
only starts to matter once a page's inputs multiply into the thousands —
see [Calculations](calculations.md) for how the grid is built.
```
