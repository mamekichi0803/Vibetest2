"""Parser for the Royal Ballet and Opera's "tickets and events" page.

Source: https://www.rbo.org.uk/tickets-and-events

Confirmed against real rendered text from a GitHub Actions run
(2026-07-08). An earlier version of this parser was designed from a
screenshot showing a day-by-day accordion calendar with an "Expand all"
toggle — that turned out to be a different view (reached via a "Calendar"
tab) than what the page actually renders by default. The default view is
a "List" of event cards, each shaped like:

    Main Stage

    Opera and music

    I puritani

    9
    –19 July 2026

    A couple's faith is tested.

    See dates
    More info

i.e. venue, one or more category tags ("Opera and music" / "Ballet and
Dance" / "Tours"), title, then a date — either a range ("<day>" then
"–<day> <Month> <year>", or "<day> <Month>" then "–<day> <Month> <year>"
if the range crosses months) or a single day ("<day> <Month> <year>") —
then a description and call-to-action buttons we don't need. The title is
always the line immediately before the date, regardless of how many
venue/category lines precede it, so that's what this parser anchors on
rather than trying to classify every preceding line.

No "Expand all" click is needed for this view — all cards' dates are
already in the rendered text. If a run yields zero performances, check
the logged warning: the site may have swapped back to a different default
view, or the card shape has changed.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from opera_schedule_tracker.browser import get_rendered_text
from opera_schedule_tracker.models import Performance

logger = logging.getLogger(__name__)

# "10 July 2026" - a single-day event.
SINGLE_DATE_RE = re.compile(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$")
# "9 July" - the start of a range that crosses months (paired with
# RANGE_END_RE on the next line).
DAY_MONTH_RE = re.compile(r"^(\d{1,2})\s+([A-Za-z]+)$")
# "9" - the start of a range within a single month.
DAY_ONLY_RE = re.compile(r"^(\d{1,2})$")
# "–19 July 2026" - the end of a range, on the line after its start.
RANGE_END_RE = re.compile(r"^[-–—]\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$")


def _parse_date(day: str, month: str, year: str) -> str | None:
    try:
        return datetime.strptime(f"{day} {month} {year}", "%d %B %Y").date().isoformat()
    except ValueError:
        return None


def parse_events_text(text: str, opera_house: str, page_url: str) -> list[Performance]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    performances: list[Performance] = []

    for i, line in enumerate(lines):
        range_end_match = RANGE_END_RE.match(line)
        if range_end_match and i >= 2:
            end_day, end_month, year = range_end_match.groups()
            start_line = lines[i - 1]

            day_month_match = DAY_MONTH_RE.match(start_line)
            day_only_match = DAY_ONLY_RE.match(start_line)
            if day_month_match:
                start_day, start_month = day_month_match.groups()
            elif day_only_match:
                start_day, start_month = day_only_match.group(1), end_month
            else:
                continue

            title = lines[i - 2]
            start_date = _parse_date(start_day, start_month, year)
            end_date = _parse_date(end_day, end_month, year)
            if start_date is None or end_date is None:
                logger.warning(
                    "Could not parse date range for %r: %r / %r", title, start_line, line
                )
                continue

            performances.append(
                Performance(
                    opera_house=opera_house,
                    title=title,
                    start_date=start_date,
                    end_date=end_date,
                    url=page_url,
                )
            )
            continue

        single_date_match = SINGLE_DATE_RE.match(line)
        if single_date_match and i >= 1:
            day, month, year = single_date_match.groups()
            title = lines[i - 1]
            start_date = _parse_date(day, month, year)
            if start_date is None:
                logger.warning("Could not parse date for %r: %r", title, line)
                continue

            performances.append(
                Performance(
                    opera_house=opera_house,
                    title=title,
                    start_date=start_date,
                    url=page_url,
                )
            )

    return performances


def fetch_rbo_performances(opera_house: str, url: str) -> list[Performance]:
    try:
        text = get_rendered_text(url, wait_ms=3_000)
    except Exception as exc:  # noqa: BLE001 - log and continue with other sources
        logger.warning("Failed to render %s (%s): %s", opera_house, url, exc)
        return []

    performances = parse_events_text(text, opera_house, url)
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
