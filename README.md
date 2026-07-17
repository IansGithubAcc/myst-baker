# myst-baker

Precomputed interactive docs via a MyST executable plugin.

myst-baker lets you author live, interactive examples that need no server:
you write an input widget, a plain Python function, and a plot, and
myst-baker runs your function over every combination of input values at
*build* time. The result is baked into the page as a JSON lookup table —
moving a slider in the browser is just a key lookup and a chart redraw, with
no Python running anywhere at page-view time.

## Documentation

- [Installation](docs/installation.md) — add myst-baker to your own MyST
  project, or set up this repo for development.
- [Guide](docs/guide/inputs.md) — input widgets, `calc` blocks, and plot
  outputs.
- [Examples](docs/examples/damped-oscillator.md) — worked examples using the framework.
- [Changelog](docs/changelog.md)
- [Authors](docs/authors.md)
