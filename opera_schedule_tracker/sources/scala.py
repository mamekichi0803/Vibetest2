"""Parser for Teatro alla Scala's calendar page.

Source: https://www.teatroallascala.org/en/calendar.html

This page does not expose schema.org JSON-LD, so instead of matching
brittle CSS class names (which we have not been able to inspect directly —
see the project README for why), this parses the *rendered, visible text*
of the calendar grid. Based on a screenshot of the page (2026-07-08), each
day cell looks like:

    <day-of-month>
    <start time, e.g. "08:00 PM">
    <title, e.g. "LUCIA DI LAMMERMOOR">
    <composer/choreographer, e.g. "Gaetano Donizetti">
    <series label, e.g. "Series O Mini Subs." or "Out Of Subs.">
    <tag chips, e.g. "HD LIVE", "GSA", "U35">

preceded by a "CALENDAR" / "<Month> <Year>" header. This has not been
verified against the live site's actual markup — if extraction yields zero
performances, check the logged warning and inspect a fresh render.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from opera_schedule_tracker.browser import get_rendered_text
from opera_schedule_tracker.models import Performance

logger = logging.getLogger(__name__)

DEFAULT_VENUE = "Teatro alla Scala"

MONTH_YEAR_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(\d{4})$"
)
DAY_RE = re.compile(r"^\d{1,2}$")
TIME_RE = re.compile(r"^\d{1,2}:\d{2}\s*(AM|PM)$", re.IGNORECASE)
SERIES_HINT_RE = re.compile(r"(Series|Subs\.)", re.IGNORECASE)


def parse_calendar_text(text: str, opera_house: str, page_url: str) -> list[Performance]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    performances: list[Performance] = []
    month_name: str | None = None
    year: int | None = None
    current_day: int | None = None

    i = 0
    while i < len(lines):
        line = lines[i]

        month_match = MONTH_YEAR_RE.match(line)
        if month_match:
            month_name, year = month_match.group(1), int(month_match.group(2))
            i += 1
            continue

        if DAY_RE.match(line) and month_name is not None:
            current_day = int(line)
            i += 1
            continue

        if TIME_RE.match(line) and current_day is not None and month_name is not None:
            time_str = line.upper().replace(" ", "")
            i += 1

            block: list[str] = []
            while i < len(lines) and not TIME_RE.match(lines[i]) and not DAY_RE.match(lines[i]):
                block.append(lines[i])
                i += 1

            if not block:
                continue

            title = block[0]
            series_label = next((b for b in block[1:] if SERIES_HINT_RE.search(b)), None)

            try:
                event_dt = datetime.strptime(
                    f"{current_day} {month_name} {year} {time_str}",
                    "%d %B %Y %I:%M%p",
                )
                start_date = event_dt.isoformat()
            except ValueError:
                logger.warning(
                    "Could not parse date/time for %r on %s %s %s (%s)",
                    title,
                    current_day,
                    month_name,
                    year,
                    time_str,
                )
                continue

            performances.append(
                Performance(
                    opera_house=opera_house,
                    title=title.title(),
                    start_date=start_date,
                    venue=DEFAULT_VENUE + (f" ({series_label})" if series_label else ""),
                    url=page_url,
                )
            )
            continue

        i += 1

    return performances


def fetch_scala_performances(opera_house: str, url: str) -> list[Performance]:
    try:
        text = get_rendered_text(url, wait_ms=3_000)
    except Exception as exc:  # noqa: BLE001 - log and continue with other sources
        logger.warning("Failed to render %s (%s): %s", opera_house, url, exc)
        return []

    performances = parse_calendar_text(text, opera_house, url)
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
