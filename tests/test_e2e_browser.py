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
