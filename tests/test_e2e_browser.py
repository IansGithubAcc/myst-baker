import functools
import http.server
import socketserver
import subprocess
import threading
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def built_site():
    subprocess.run(
        ["uv", "run", "myst", "build", "--html"], cwd=REPO_ROOT, check=True
    )
    html_dir = REPO_ROOT / "_build" / "html"

    # mystmd's static HTML export uses root-relative asset paths (e.g.
    # /build/entry.client-*.js), which only resolve correctly when the
    # directory is served over HTTP from its own root. Opening index.html
    # directly via a file:// URI causes those paths to resolve against the
    # filesystem drive root instead, so the client app's JS never loads.
    # Serve the built directory locally instead of navigating to it as a
    # file:// URI.
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(html_dir)
    )
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{port}/index.html"

    httpd.shutdown()
    thread.join()


@pytest.fixture(scope="module")
def inputs_page_url(built_site):
    return built_site.replace("/index.html", "/inputs/index.html")


@pytest.fixture(scope="module")
def outputs_page_url(built_site):
    return built_site.replace("/index.html", "/outputs/index.html")


def test_slider_updates_plot_with_no_console_errors(built_site, page):
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page_errors = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    page.goto(built_site)

    # The plot is rendered inside a same-page <iframe> (a `data:text/html;base64,...`
    # document produced by transform.py's _iframe_node) rather than directly in the
    # outer document -- mystmd's site renderer treats raw injected HTML as inert
    # escaped text, so render.py/transform.py embed a full standalone document in an
    # iframe instead. Locators must therefore target the iframe's content.
    plot_frame = page.frame_locator("iframe")
    plot_locator = plot_frame.locator(".js-plotly-plot").first
    plot_locator.wait_for(state="visible")

    before = plot_locator.evaluate("el => el.data[0].y.slice(0, 3)")

    # Tweakpane v4's root container class is `.tp-rotv` (not v3's `.tp-dfwv`), and its
    # number binding renders as a text input, not a native `input[type=range]`.
    slider_input = plot_frame.locator(".tp-rotv input[type='text']").first
    slider_input.fill("8")
    slider_input.press("Enter")

    page.wait_for_timeout(300)

    after = plot_locator.evaluate("el => el.data[0].y.slice(0, 3)")

    assert before != after
    assert console_errors == []
    assert page_errors == []

    # Regression check: the book-theme's iframe renderer fixes this iframe's
    # own height (a padding-bottom aspect-ratio box on the embedding page --
    # see transform.py's `_iframe_node` docstring) and ignores any `style`
    # we set on the mdast node, so render.py/runtime.js instead lay out the
    # controls+plot in a flexbox that fills exactly whatever height the
    # iframe gets. If that ever regresses, the body silently gains a
    # vertical scrollbar instead of throwing -- assert directly on it.
    body = plot_frame.locator("body")
    overflow = body.evaluate("el => el.scrollHeight - el.clientHeight")
    assert overflow <= 1


def test_slider_typed_value_reaching_grid_key_via_many_steps_from_origin(inputs_page_url, page):
    # Regression test: Tweakpane's step-constraint snaps a typed/dragged
    # value to a grid anchored at the slider's initial `:value:` (its
    # "origin"), not at `:min:`, using raw floating-point arithmetic with
    # no cleanup -- unlike precompute.input_values, which rounds to 10
    # decimal places. For the "Fine steps and negative ranges" example
    # (:value: 0.3, :min: -0.5, :step: 0.05), typing "-0.30" reaches that
    # value 12 steps of 0.05 away from the origin, and Tweakpane's snap
    # lands on -0.30000000000000004 instead of exactly -0.3 -- confirmed
    # empirically by monkeypatching window.Object.assign inside the iframe
    # to capture runtime.js's draw() call and inspecting the sender's
    # rawValue_. String(-0.30000000000000004) doesn't match the
    # precomputed grid's "-0.3" key, so the lookup misses and the plot
    # goes blank.
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page_errors = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    page.goto(inputs_page_url)

    # docs/guide/inputs.md's live iframes: Sliders (0), Fine steps and
    # negative ranges (1), Checkbox (2), Dropdown (3) -- "One slider" and
    # "Two sliders" were merged into one "Sliders" section as redundant
    # (a single slider is a trivial case of multiple sliders), shifting
    # every later section's index down by one.
    plot_frame = page.frame_locator("iframe").nth(1)
    plot_locator = plot_frame.locator(".js-plotly-plot").first
    plot_locator.wait_for(state="visible")

    damping_input = plot_frame.locator(".tp-rotv input[type='text']").first
    damping_input.fill("-0.30")
    damping_input.press("Enter")

    page.wait_for_timeout(300)

    y = plot_locator.evaluate("el => el.data[0].y")

    assert y, "plot data went empty -- the typed value's grid lookup key didn't match the precomputed grid"
    assert console_errors == []
    assert page_errors == []


def test_dropdown_updates_plot_with_no_console_errors(inputs_page_url, page):
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page_errors = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    page.goto(inputs_page_url)

    # docs/guide/inputs.md's live iframes, in document order: Sliders (0),
    # Fine steps and negative ranges (1), Checkbox (2), Dropdown (3) -- see
    # the comment above test_slider_typed_value_reaching_grid_key_via_many_steps_from_origin
    # for why the dropdown example shifted from the 5th to the 4th plot on
    # the page. Confirmed empirically: page.locator("iframe").count() == 4
    # on the built page.
    plot_frame = page.frame_locator("iframe").nth(3)
    plot_locator = plot_frame.locator(".js-plotly-plot").first
    plot_locator.wait_for(state="visible")

    before = plot_locator.evaluate("el => el.data[0].y.slice(0, 3)")

    # Tweakpane v4's list/dropdown binding renders as a `<select class="tp-lstv_s">`
    # inside a `.tp-lstv` wrapper, itself nested inside the pane's `.tp-rotv`
    # root container (the same root the number binding's
    # `.tp-rotv input[type='text']` lives under) -- discovered by inspecting
    # `frame.locator(".tp-rotv").first.inner_html()` against a real build, per
    # this project's convention of verifying Tweakpane's DOM empirically
    # rather than assuming from docs. The brief's draft selector
    # (`.tp-rotv select`) would have matched too since `.tp-lstv` nests inside
    # `.tp-rotv`, but `.tp-lstv select` names the actual binding wrapper.
    dropdown_select = plot_frame.locator(".tp-lstv select").first
    dropdown_select.select_option("square")

    page.wait_for_timeout(300)

    after = plot_locator.evaluate("el => el.data[0].y.slice(0, 3)")

    assert before != after
    assert console_errors == []
    assert page_errors == []


def test_new_output_types_render_with_no_console_errors(outputs_page_url, page):
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page_errors = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    page.goto(outputs_page_url)

    # docs/guide/outputs.md's live plots, in document order: 3 scatter-mode
    # plots, 1 bar, 1 combined-trace scatter (cosine + sine), 1 combined-trace
    # bar (revenue + expenses), 1 histogram, 1 pie, 1 box, 1 violin = 10
    # total. CORRECTED (verified empirically against the built page, which
    # shows 10 iframes -- confirmed by counting live, non-fenced `{plot}`
    # blocks in outputs.md's source): the previous count of 9 omitted the
    # "Multiple traces on one plot" section's *scatter* example
    # (`:data: cosine_curve,sine_curve`) -- only its bar counterpart further
    # down the same section was ever counted.
    iframe_count = page.locator("iframe").count()
    assert iframe_count == 10

    for i in range(iframe_count):
        frame = page.frame_locator("iframe").nth(i)
        frame.locator(".js-plotly-plot").first.wait_for(state="visible")

    assert console_errors == []
    assert page_errors == []
