"""Parser for Wiener Staatsoper's monthly calendar pages.

Source: https://www.wiener-staatsoper.at/en/calendar/<year>/<month>/
(e.g. .../en/calendar/2026/september/) — one page per month, so this
generates URLs for the current month plus ``months_ahead`` following months
and fetches each.

Confirmed against real rendered text from a GitHub Actions run
(2026-07-08, .../en/calendar/2026/september/): the page shows a
"<season start>/<season end short> Season" header (e.g. "2026/27 Season")
and a list of events, each shaped like:

    Fri
    04 Sep
    19:00—22:30
    GIUSEPPE VERDI
    DON CARLO
    OPERA Main Stage

    with Vittorio Grigolo, Étienne Dupuis, ...
    Show full cast
    BUY TICKETS
    DETAILS
    ...ticket price rows...

i.e. weekday / "<day> <month abbreviation>" (on one line — a first
screenshot-only-derived version of this parser wrongly assumed those were
two separate lines) / time range (using an em dash "—"), then a composer
line, a title line, a "<CATEGORY> <venue>" line, then cast/ticket noise we
don't need for diffing.

Months with nothing scheduled show a "There are no performances in
<month(s)>" message instead (confirmed for July/August 2026), which parses
to zero performances rather than an error. Months outside what the site
considers valid (also observed for July/August 2026, despite the "no
performances" messaging existing at the base /en/calendar/ URL) 404 at the
dedicated month URL; that also just yields zero performances here rather
than raising, since the 404 page's text matches none of our patterns.
"""

from __future__ import annotations

import calendar
import logging
import re
from datetime import date, datetime

from opera_schedule_tracker.browser import get_rendered_text
from opera_schedule_tracker.models import Performance

logger = logging.getLogger(__name__)

WEEKDAY_RE = re.compile(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)$")
DAY_MONTH_RE = re.compile(
    r"^(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$"
)
TIME_RANGE_RE = re.compile(r"^(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})$")
SEASON_RE = re.compile(r"^(\d{4})/(\d{2})\s+Season$")
KNOWN_VENUE_HINTS = ("Main Stage",)

_MONTH_NUM = {abbr: i for i, abbr in enumerate(calendar.month_abbr) if abbr}


def month_urls(base_url: str, months_ahead: int, today: date | None = None) -> list[str]:
    """Build one calendar URL per month, from the current month through
    ``months_ahead`` months after it (inclusive), e.g. months_ahead=3 with a
    July start yields July, August, September, October.
    """
    today = today or date.today()
    base = base_url.rstrip("/")
    urls = []
    year, month = today.year, today.month
    for offset in range(months_ahead + 1):
        m = (month - 1 + offset) % 12 + 1
        y = year + (month - 1 + offset) // 12
        month_name = calendar.month_name[m].lower()
        urls.append(f"{base}/{y}/{month_name}/")
    return urls


def _resolve_year(season_start_year: int | None, month_abbr: str) -> int | None:
    if season_start_year is None:
        return None
    # A Wiener Staatsoper season runs Sep(N) .. Aug(N+1).
    month_num = _MONTH_NUM[month_abbr]
    return season_start_year if month_num >= 9 else season_start_year + 1


def _find_venue(block: list[str]) -> str | None:
    for line in block:
        for venue in KNOWN_VENUE_HINTS:
            if venue in line:
                return venue
    return None


def parse_calendar_text(text: str, opera_house: str, page_url: str) -> list[Performance]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    performances: list[Performance] = []
    season_start_year: int | None = None

    i = 0
    while i < len(lines):
        season_match = SEASON_RE.match(lines[i])
        if season_match:
            season_start_year = int(season_match.group(1))
            i += 1
            continue

        day_month_match = DAY_MONTH_RE.match(lines[i + 1]) if i + 1 < len(lines) else None
        if (
            WEEKDAY_RE.match(lines[i])
            and i + 2 < len(lines)
            and day_month_match
            and TIME_RANGE_RE.match(lines[i + 2])
        ):
            day = int(day_month_match.group(1))
            month_abbr = day_month_match.group(2)
            time_match = TIME_RANGE_RE.match(lines[i + 2])
            start_time = time_match.group(1)
            i += 3

            year = _resolve_year(season_start_year, month_abbr)
            if year is None:
                logger.warning(
                    "Skipping event on %s %s: no season header seen yet to "
                    "resolve the year",
                    month_abbr,
                    day,
                )
                continue

            creator = lines[i] if i < len(lines) else None
            title = lines[i + 1] if i + 1 < len(lines) else None
            if title is None:
                continue

            block_end = i + 2
            while block_end < len(lines) and not WEEKDAY_RE.match(lines[block_end]):
                block_end += 1
            venue = _find_venue(lines[i + 2 : block_end])
            i = block_end

            try:
                start_dt = datetime.strptime(
                    f"{day} {month_abbr} {year} {start_time}", "%d %b %Y %H:%M"
                )
            except ValueError:
                logger.warning(
                    "Could not parse date/time for %r on %s %s %s (%s)",
                    title,
                    day,
                    month_abbr,
                    year,
                    start_time,
                )
                continue

            display_title = f"{title.title()} ({creator.title()})" if creator else title.title()

            performances.append(
                Performance(
                    opera_house=opera_house,
                    title=display_title,
                    start_date=start_dt.isoformat(),
                    venue=venue,
                    url=page_url,
                )
            )
            continue

        i += 1

    return performances


def fetch_wiener_staatsoper_performances(
    opera_house: str, url: str, months_ahead: int = 3
) -> list[Performance]:
    performances: list[Performance] = []
    for month_url in month_urls(url, months_ahead):
        try:
            text = get_rendered_text(month_url, wait_ms=3_000)
        except Exception as exc:  # noqa: BLE001 - log and continue with other months
            logger.warning("Failed to render %s (%s): %s", opera_house, month_url, exc)
            continue
        month_performances = parse_calendar_text(text, opera_house, month_url)
        if not month_performances:
            logger.warning(
                "No performances extracted for %s at %s. "
                "Rendered text (run with -v to see this):\n%s",
                opera_house,
                month_url,
                text,
            )
        performances.extend(month_performances)

    if not performances:
        logger.warning(
            "No performances extracted for %s across %d month(s) starting %s "
            "(page layout may differ from what this parser expects)",
            opera_house,
            months_ahead + 1,
            url,
        )
    return performances
