# Changelog

All notable changes to myst-baker are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## 0.1.0

Initial release.

### Added

- Three input widgets — `input-slider`, `input-checkbox`, and
  `input-dropdown` — each bound to a name that `calc` functions pick up by
  matching parameter names.
- `python{calc}` fence blocks: plain Python function definitions, executed
  once per page and called once per combination of their matched inputs'
  values.
- A `plot` output block backed by Plotly, with built-in field-order support
  for six trace types — `scatter`, `bar`, `histogram`, `pie`, `box`, and
  `violin` — and pass-through support for any other Plotly trace type via a
  `calc` function returning a dict of field names.
- A precomputed, static-build architecture: myst-baker runs every `calc`
  function over the full cartesian product of its inputs' values at *build*
  time and bakes the results into a JSON lookup table, so published pages
  need no backend, notebook kernel, or live Python process.
