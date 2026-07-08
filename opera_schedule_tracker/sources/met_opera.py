"""Parser for the Metropolitan Opera's calendar page.

Source: https://www.metopera.org/calendar/ — renders its schedule via
JavaScript, so opera_schedule_tracker.browser (headless Chromium) is
needed just to get the schedule into the DOM at all, before any parsing.

Confirmed against real rendered text from a GitHub Actions run
(2026-07-08). An earlier version of this parser was designed from
screenshots of what turned out to be a day-detail popup, not the default
page — the default view is a month grid, shaped like:

    Jul 2026
    ...
    EVENTS FOR OCTOBER
    9

    Learn more about
    Sylvia - ABT

    7:30 PM

    BUY TICKETS
    TO SYLVIA - ABT

    EVENTS FOR OCTOBER
    10
    ...

i.e. a "<Mon> <year>" header giving the year (oddly paired with an
"EVENTS FOR OCTOBER" grid in the one real run we've seen — the displayed
month name and the header didn't match, for reasons we don't know; we
just trust "EVENTS FOR <MONTH>" for the month and the header for the
year), then per calendar cell: "EVENTS FOR <MONTH>" + day-of-month,
followed by zero or more events each as "Learn more about" / title / time
/ booking button lines. Multiple same-day events repeat the
title/time/button block without repeating the "EVENTS FOR <MONTH>" + day
header.

LIMITATION: this only reads whatever the page renders on initial load. We
haven't automated changing the displayed month (a date-picker widget
interaction), so this only captures whatever month(s) happen to be
rendered by default.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from opera_schedule_tracker.browser import get_rendered_text
from opera_schedule_tracker.models import Performance

logger = logging.getLogger(__name__)

MONTH_YEAR_RE = re.compile(
    r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})"
)
EVENTS_FOR_RE = re.compile(r"^EVENTS FOR ([A-Z]+)$")
DAY_RE = re.compile(r"^\d{1,2}$")
LEARN_MORE_RE = re.compile(r"^Learn more about$")
TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", re.IGNORECASE)

_FULL_MONTH_NUM = {
    "JANUARY": 1,
    "FEBRUARY": 2,
    "MARCH": 3,
    "APRIL": 4,
    "MAY": 5,
    "JUNE": 6,
    "JULY": 7,
    "AUGUST": 8,
    "SEPTEMBER": 9,
    "OCTOBER": 10,
    "NOVEMBER": 11,
    "DECEMBER": 12,
}


def parse_calendar_text(text: str, opera_house: str, page_url: str) -> list[Performance]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    performances: list[Performance] = []
    year: int | None = None
    current_month_num: int | None = None
    current_day: int | None = None

    i = 0
    while i < len(lines):
        line = lines[i]

        month_year_match = MONTH_YEAR_RE.match(line)
        if month_year_match:
            year = int(month_year_match.group(2))
            i += 1
            continue

        events_for_match = EVENTS_FOR_RE.match(line)
        if events_for_match:
            month_num = _FULL_MONTH_NUM.get(events_for_match.group(1))
            i += 1
            if month_num is not None and i < len(lines) and DAY_RE.match(lines[i]):
                current_month_num = month_num
                current_day = int(lines[i])
                i += 1
            continue

        if (
            LEARN_MORE_RE.match(line)
            and current_day is not None
            and current_month_num is not None
            and year is not None
            and i + 2 < len(lines)
        ):
            title = lines[i + 1]
            time_match = TIME_RE.match(lines[i + 2])
            if time_match is None:
                i += 1
                continue

            hour, minute, ampm = time_match.groups()
            try:
                start_dt = datetime.strptime(
                    f"{current_day} {current_month_num} {year} {hour}:{minute}{ampm.upper()}",
                    "%d %m %Y %I:%M%p",
                )
            except ValueError:
                logger.warning(
                    "Could not parse date/time for %r on %s/%s/%s (%s:%s%s)",
                    title,
                    current_month_num,
                    current_day,
                    year,
                    hour,
                    minute,
                    ampm,
                )
                i += 3
                continue

            performances.append(
                Performance(
                    opera_house=opera_house,
                    title=title,
                    start_date=start_dt.isoformat(),
                    url=page_url,
                )
            )
            i += 3
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
