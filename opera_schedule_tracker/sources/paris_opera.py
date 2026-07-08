"""Parser for Opera national de Paris's programme page.

Source: https://www.operadeparis.fr/en/programme-and-tickets

Based on screenshots (2026-07-08), this page is a card grid (not a
day-by-day calendar like the other sources) — each card is a *production*,
not a single performance, shaped like:

    OPERA
    Il Barbiere di Siviglia
    Gioacchino Rossini
    Opéra Bastille
    from 12 Sep to 05 Nov 2026
    BOOK

i.e. category / title / composer / venue / run date-range / booking button.
The date range is either "from D to D Mon YYYY" (same month) or
"from D Mon to D Mon YYYY" (different months). So unlike the other four
sources, what we extract here is one entry per *production run*
(start_date/end_date = the run's first/last day), not one per individual
performance date — Opéra national de Paris just doesn't expose individual
dates on this overview page.

The category is used as the anchor to find each card, so
``CATEGORY_WHITELIST`` needs extending if a category besides "OPERA" shows
up in practice (we've only confirmed OPERA from the screenshots). The page
also appears to lazy-load additional cards ("22 RESULTS" total, only 2
visible without scrolling), so the fetcher scrolls a few times before
reading the page.

This has not been verified against the live site's actual markup (only
screenshots) — if extraction yields far fewer than the page's stated
result count, check the logged warning and inspect a fresh render.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from opera_schedule_tracker.browser import open_page
from opera_schedule_tracker.models import Performance

logger = logging.getLogger(__name__)

CATEGORY_WHITELIST = {"OPERA", "BALLET", "CONCERT", "RECITAL", "MASTERCLASS", "EVENT"}

SAME_MONTH_RANGE_RE = re.compile(
    r"^from (?P<start_day>\d{1,2}) to (?P<end_day>\d{1,2}) "
    r"(?P<month>[A-Za-z]+) (?P<year>\d{4})$"
)
DIFFERENT_MONTH_RANGE_RE = re.compile(
    r"^from (?P<start_day>\d{1,2}) (?P<start_month>[A-Za-z]+) to "
    r"(?P<end_day>\d{1,2}) (?P<end_month>[A-Za-z]+) (?P<year>\d{4})$"
)
# How many lines past the title we'll scan looking for a date-range line
# before giving up on a card (guards against runaway scans on unexpected
# layouts).
MAX_LOOKAHEAD = 6


def _parse_date_range(line: str) -> tuple[str, str] | None:
    m = SAME_MONTH_RANGE_RE.match(line)
    if m:
        year = m["year"]
        start = datetime.strptime(f"{m['start_day']} {m['month']} {year}", "%d %b %Y")
        end = datetime.strptime(f"{m['end_day']} {m['month']} {year}", "%d %b %Y")
        return start.date().isoformat(), end.date().isoformat()

    m = DIFFERENT_MONTH_RANGE_RE.match(line)
    if m:
        year = m["year"]
        start = datetime.strptime(f"{m['start_day']} {m['start_month']} {year}", "%d %b %Y")
        end = datetime.strptime(f"{m['end_day']} {m['end_month']} {year}", "%d %b %Y")
        return start.date().isoformat(), end.date().isoformat()

    return None


def parse_programme_text(text: str, opera_house: str, page_url: str) -> list[Performance]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    performances: list[Performance] = []
    i = 0
    while i < len(lines):
        if lines[i] not in CATEGORY_WHITELIST or i + 1 >= len(lines):
            i += 1
            continue

        title = lines[i + 1]

        date_idx = None
        parsed_range = None
        for j in range(i + 2, min(i + 2 + MAX_LOOKAHEAD, len(lines))):
            parsed_range = _parse_date_range(lines[j])
            if parsed_range is not None:
                date_idx = j
                break

        if date_idx is None:
            i += 1
            continue

        venue = lines[date_idx - 1] if date_idx - 1 > i + 1 else None
        start_date, end_date = parsed_range

        performances.append(
            Performance(
                opera_house=opera_house,
                title=title,
                start_date=start_date,
                end_date=end_date,
                venue=venue,
                url=page_url,
            )
        )
        i = date_idx + 1

    return performances


def fetch_paris_opera_performances(
    opera_house: str, url: str, max_scrolls: int = 5
) -> list[Performance]:
    try:
        with open_page(url) as page:
            page.wait_for_timeout(2_000)
            previous_height = None
            for _ in range(max_scrolls):
                page.mouse.wheel(0, 3_000)
                page.wait_for_timeout(1_000)
                height = page.evaluate("document.body.scrollHeight")
                if height == previous_height:
                    break
                previous_height = height
            text = page.inner_text("body")
    except Exception as exc:  # noqa: BLE001 - log and continue with other sources
        logger.warning("Failed to render %s (%s): %s", opera_house, url, exc)
        return []

    performances = parse_programme_text(text, opera_house, url)
    if not performances:
        logger.warning(
            "No performances extracted for %s at %s "
            "(page layout may differ from what this parser expects). "
            "Rendered text (run with -v to see this):\n%s",
            opera_house,
            url,
            text,
        )
    return performances
