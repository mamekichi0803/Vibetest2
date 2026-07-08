"""Headless-browser page rendering.

Several opera houses' schedule pages render their calendar client-side with
JavaScript (most notably the Met Opera), so a plain HTTP GET returns an
empty shell. Rendering with a real (headless) browser sidesteps that, and
also presents a realistic browser fingerprint which helps with sites that
block obvious script traffic.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from playwright.sync_api import Page, sync_playwright

logger = logging.getLogger(__name__)

# A realistic, current desktop Chrome UA + locale, to reduce the chance of
# being blocked as an obvious bot (see also opera_houses.yaml notes on 403s).
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT_MS = 30_000


@contextmanager
def open_page(url: str, wait_until: str = "domcontentloaded") -> Iterator[Page]:
    """Load ``url`` in headless Chromium and yield the Playwright ``Page``.

    Use this (instead of :func:`get_rendered_text`) when a source needs to
    interact with the page — e.g. clicking an "expand all" toggle — before
    reading its text.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(user_agent=USER_AGENT, locale="en-US")
            page.goto(url, timeout=DEFAULT_TIMEOUT_MS, wait_until=wait_until)
            yield page
        finally:
            browser.close()


def get_rendered_text(
    url: str,
    wait_selector: str | None = None,
    wait_ms: int = 2_000,
) -> str:
    """Load ``url`` in headless Chromium and return the visible body text.

    :param wait_selector: optional CSS selector to wait for before reading
        the page (use for pages whose calendar widget loads asynchronously).
    :param wait_ms: extra fixed delay after load/selector, to let any
        remaining async rendering (e.g. a calendar grid) settle.
    """
    with open_page(url) as page:
        if wait_selector:
            page.wait_for_selector(wait_selector, timeout=DEFAULT_TIMEOUT_MS)
        page.wait_for_timeout(wait_ms)
        return page.inner_text("body")
