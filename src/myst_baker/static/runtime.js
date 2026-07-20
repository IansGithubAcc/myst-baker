function mystBakerInitPlot(containerId, inputSpecs, grid, traceType, traceOptions) {
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
    // no special-casing needed on this side for that.
    //
    // Numeric (slider) values do need cleanup, though: Tweakpane's own
    // step-constraint snaps a typed/dragged value to a grid anchored at the
    // binding's *initial* value (its "origin"), not at :min:, using raw
    // floating-point arithmetic with no rounding -- unlike
    // precompute.input_values, which rounds every grid value to 10 decimal
    // places. Confirmed empirically: with :value: 0.3, :min: -0.5, :step:
    // 0.05, typing "-0.30" (12 steps of 0.05 from the origin) lands on
    // -0.30000000000000004 instead of exactly -0.3, so String(v) here would
    // produce a key the precomputed grid never has. Rounding to the same 10
    // decimal places before stringifying keeps this side's keys aligned
    // with precompute.input_values regardless of which value a Tweakpane
    // binding's own math actually landed on.
    return inputSpecs
      .map((spec) => {
        const v = params[spec.name];
        return String(typeof v === 'number' ? Math.round(v * 1e10) / 1e10 : v);
      })
      .join('|');
  }

  function currentData() {
    return grid[currentKey()];
  }

  function draw() {
    const data = currentData();
    if (traceType === 'figure') {
      // A full figure already carries its own per-trace `type` and a
      // complete `layout` (see render.py's _figure_json) -- no
      // type/traceOptions merge here, unlike the trace-building path
      // below; the whole point of figure mode is that the calc function
      // has full control.
      const layout = Object.assign({ autosize: true }, data.layout);
      Plotly.react(plotEl, data.data, layout, { responsive: true });
      return;
    }
    // A single combined `calc` function's grid entry is a bare object (see
    // render.py); combining several into one plot makes it an array, one
    // trace object per function. Normalizing here keeps a single draw path
    // for both shapes instead of branching the whole function in two.
    const traces = (Array.isArray(data) ? data : [data]).map((d) =>
      Object.assign({ type: traceType }, d, traceOptions)
    );
    const layout = { autosize: true };
    if (traceType === 'bar' && traces.length > 1) {
      layout.barmode = 'group';
    }
    Plotly.react(plotEl, traces, layout, { responsive: true });
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
