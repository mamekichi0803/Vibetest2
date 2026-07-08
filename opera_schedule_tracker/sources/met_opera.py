"""Parser for the Metropolitan Opera's calendar page.

Source: https://www.metopera.org/calendar/ — renders its schedule via
JavaScript, so opera_schedule_tracker.browser (headless Chromium) is
needed just to get the schedule into the DOM at all, before any parsing.

Based on screenshots (2026-07-08), the page shows a month header ("Jul
2026") with a date-picker dropdown, then a day-by-day agenda:

    THU, JUL 9

    ON STAGE

    7:30 PM
    LEO DELIBES
    Sylvia - ABT
    Barker; Shevchenko, Royal III
    BUY TICKETS

    FRI, JUL 10
    ...

i.e. a "<WEEKDAY>, <MON> <day>" date header, a section label ("ON STAGE",
possibly others we haven't seen e.g. for Live in HD screenings), then per
event: time, composer/creator, title, cast line, and a call-to-action
button — of which we only need the first three.

LIMITATION: this only reads whatever the page renders on initial load,
which appears to be the current month only ("Jul 2026" in the screenshot).
Changing month is a date-picker widget interaction (see the second
screenshot: clicking the month label opens a calendar with next/prev
arrows and a confirm checkmark), not a URL change like Wiener Staatsoper —
we have not implemented driving that widget, so unlike wiener_staatsoper's
months_ahead this only ever returns the current month's schedule. Revisit
if multi-month coverage turns out to matter in practice.

This has not been verified against the live site's actual markup (only
screenshots) — if extraction yields zero performances, check the logged
warning and inspect a fresh render.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from opera_schedule_tracker.browser import get_rendered_text
from opera_schedule_tracker.models import Performance

logger = logging.getLogger(__name__)

_WEEKDAYS = "MON|TUE|WED|THU|FRI|SAT|SUN"
_MONTHS = "JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC"

DATE_HEADER_RE = re.compile(rf"^({_WEEKDAYS}), ({_MONTHS}) (\d{{1,2}})$")
TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", re.IGNORECASE)
MONTH_YEAR_RE = re.compile(
    r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})"
)


def parse_calendar_text(text: str, opera_house: str, page_url: str) -> list[Performance]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    performances: list[Performance] = []
    year: int | None = None
    current_date: tuple[str, int] | None = None  # (month abbr upper, day)

    i = 0
    while i < len(lines):
        line = lines[i]

        month_year_match = MONTH_YEAR_RE.match(line)
        if month_year_match:
            year = int(month_year_match.group(2))
            i += 1
            continue

        date_match = DATE_HEADER_RE.match(line)
        if date_match:
            current_date = (date_match.group(2), int(date_match.group(3)))
            i += 1
            continue

        time_match = TIME_RE.match(line)
        if time_match and current_date is not None and year is not None:
            hour, minute, ampm = time_match.groups()
            i += 1

            block: list[str] = []
            while i < len(lines) and not TIME_RE.match(lines[i]) and not DATE_HEADER_RE.match(
                lines[i]
            ):
                block.append(lines[i])
                i += 1

            if len(block) < 2:
                continue
            title = block[1]

            month_abbr, day = current_date
            try:
                start_dt = datetime.strptime(
                    f"{day} {month_abbr.title()} {year} {hour}:{minute}{ampm.upper()}",
                    "%d %b %Y %I:%M%p",
                )
            except ValueError:
                logger.warning(
                    "Could not parse date/time for %r on %s %s %s (%s:%s%s)",
                    title,
                    month_abbr,
                    day,
                    year,
                    hour,
                    minute,
                    ampm,
                )
                continue

            performances.append(
                Performance(
                    opera_house=opera_house,
                    title=title,
                    start_date=start_dt.isoformat(),
                    url=page_url,
                )
            )
            continue

        i += 1

    return performances


def fetch_met_opera_performances(opera_house: str, url: str) -> list[Performance]:
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
