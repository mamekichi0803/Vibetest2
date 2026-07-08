"""Parser for the Royal Ballet and Opera's "tickets and events" page.

Source: https://www.rbo.org.uk/tickets-and-events

Based on a screenshot (2026-07-08), the page groups events under a month
header ("July, 2026") and then per-day sections ("Wednesday" / "8", i.e.
weekday name and day-of-month — possibly on the same line, possibly on two,
since we can't tell from a screenshot alone; this parser accepts both).
Each day section, once expanded, lists its events as a title line followed
by a time line (e.g. "I puritani" / "7PM"). Days with no events shown in
the screenshot may just be collapsed by default — the fetcher clicks the
page's "Expand all" toggle (via Playwright's text-based locator, so it
does not depend on knowing a CSS class name) before reading the page, so
collapsed days should still be picked up if that click succeeds.

This has not been verified against the live site's actual markup (only a
screenshot) — if extraction yields zero performances, check the logged
warning and inspect a fresh render. In particular: we've only seen the
current month; whether/how the page exposes future months (pagination,
infinite scroll, ...) is unknown, so this may currently only pick up
what's rendered on initial load.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from opera_schedule_tracker.browser import open_page
from opera_schedule_tracker.models import Performance

logger = logging.getLogger(__name__)

WEEKDAY_RE = re.compile(
    r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(?:\s+(\d{1,2}))?$"
)
DAY_ONLY_RE = re.compile(r"^\d{1,2}$")
MONTH_HEADER_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|"
    r"October|November|December),\s*(\d{4})$"
)
TIME_RE = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)$", re.IGNORECASE)


def parse_events_text(text: str, opera_house: str, page_url: str) -> list[Performance]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    performances: list[Performance] = []
    month_name: str | None = None
    year: int | None = None
    current_day: int | None = None
    pending_title: str | None = None

    i = 0
    while i < len(lines):
        line = lines[i]

        month_match = MONTH_HEADER_RE.match(line)
        if month_match:
            month_name, year = month_match.group(1), int(month_match.group(2))
            pending_title = None
            i += 1
            continue

        weekday_match = WEEKDAY_RE.match(line)
        if weekday_match:
            day_num = weekday_match.group(2)
            i += 1
            if day_num is None and i < len(lines) and DAY_ONLY_RE.match(lines[i]):
                day_num = lines[i]
                i += 1
            current_day = int(day_num) if day_num else None
            pending_title = None
            continue

        time_match = TIME_RE.match(line)
        if time_match and current_day is not None and month_name and year and pending_title:
            hour, minute, ampm = time_match.groups()
            minute = minute or "00"
            try:
                start_dt = datetime.strptime(
                    f"{current_day} {month_name} {year} {hour}:{minute}{ampm.upper()}",
                    "%d %B %Y %I:%M%p",
                )
                performances.append(
                    Performance(
                        opera_house=opera_house,
                        title=pending_title,
                        start_date=start_dt.isoformat(),
                        url=page_url,
                    )
                )
            except ValueError:
                logger.warning(
                    "Could not parse date/time for %r on %s %s %s (%s)",
                    pending_title,
                    current_day,
                    month_name,
                    year,
                    line,
                )
            pending_title = None
            i += 1
            continue

        if DAY_ONLY_RE.match(line):
            # a stray day-of-month line not attached to a weekday we
            # recognised (e.g. the first line after an unmatched header)
            i += 1
            continue

        # Anything else is a candidate event title, to be confirmed if the
        # next matching line is a time.
        pending_title = line
        i += 1

    return performances


def fetch_rbo_performances(opera_house: str, url: str) -> list[Performance]:
    try:
        with open_page(url) as page:
            try:
                page.get_by_text("Expand all", exact=False).click(timeout=5_000)
            except Exception:  # noqa: BLE001 - proceed with whatever is already expanded
                logger.warning(
                    "Could not click 'Expand all' on %s; some events may be missing.",
                    opera_house,
                )
            page.wait_for_timeout(2_000)
            text = page.inner_text("body")
    except Exception as exc:  # noqa: BLE001 - log and continue with other sources
        logger.warning("Failed to render %s (%s): %s", opera_house, url, exc)
        return []

    performances = parse_events_text(text, opera_house, url)
    if not performances:
        logger.warning(
            "No performances extracted for %s at %s "
            "(page layout may differ from what this parser expects)",
            opera_house,
            url,
        )
    return performances
