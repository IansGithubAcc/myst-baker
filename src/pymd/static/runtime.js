function pymdInitPlot(containerId, inputSpecs, grid, traceType, traceOptions) {
  const container = document.getElementById(containerId);
  const controlsEl = document.createElement('div');
  const plotEl = document.createElement('div');
  container.appendChild(controlsEl);
  container.appendChild(plotEl);

  const pane = new Tweakpane.Pane({ container: controlsEl });
  const params = {};
  inputSpecs.forEach((spec) => {
    params[spec.name] = spec.value;
  });

  function currentKey() {
    // Must match precompute.py's _stringify. JS numbers have no int/float
    // distinction, so String(1) is already "1" for any whole-number value
    // regardless of how it arrived (typed input, slider drag, JSON default) --
    // no special-casing needed on this side, only on the Python side.
    return inputSpecs.map((spec) => String(params[spec.name])).join('|');
  }

  function currentData() {
    return grid[currentKey()];
  }

  function draw() {
    const data = currentData();
    const trace = Object.assign({ type: traceType, x: data[0], y: data[1] }, traceOptions);
    Plotly.react(plotEl, [trace], {});
  }

  inputSpecs.forEach((spec) => {
    pane
      .addBinding(params, spec.name, {
        min: spec.min,
        max: spec.max,
        step: spec.step,
      })
      .on('change', draw);
  });

  draw();
}
