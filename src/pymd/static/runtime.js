function pymdInitPlot(containerId, inputSpecs, grid, traceType, traceOptions) {
  const container = document.getElementById(containerId);
  const controlsEl = document.createElement('div');
  const plotEl = document.createElement('div');
  controlsEl.style.flex = '0 0 auto';
  // flex-basis 0 + min-height 0 lets this shrink below Plotly's intrinsic
  // default size so it fills exactly what's left under the controls,
  // instead of overflowing the fixed-height container (see render.py).
  plotEl.style.flex = '1 1 0';
  plotEl.style.minHeight = '0';
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
    const trace = Object.assign({ type: traceType }, data, traceOptions);
    Plotly.react(plotEl, [trace], { autosize: true }, { responsive: true });
  }

  window.addEventListener('resize', () => Plotly.Plots.resize(plotEl));

  inputSpecs.forEach((spec) => {
    // Each input kind needs different Tweakpane binding options: a slider
    // needs min/max/step, a checkbox needs none (Tweakpane infers a checkbox
    // from the bound value already being a boolean), and a dropdown needs an
    // `options` map of {label: value} pairs to render as a <select>.
    let bindingOptions = {};
    if (spec.kind === 'slider') {
      bindingOptions = { min: spec.min, max: spec.max, step: spec.step };
    } else if (spec.kind === 'dropdown') {
      const options = {};
      spec.choices.forEach((choice) => {
        options[choice] = choice;
      });
      bindingOptions = { options };
    }
    pane.addBinding(params, spec.name, bindingOptions).on('change', draw);
  });

  draw();
}
