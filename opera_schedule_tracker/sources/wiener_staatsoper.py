"""Parser for Wiener Staatsoper's monthly calendar pages.

Source: https://www.wiener-staatsoper.at/en/calendar/<year>/<month>/
(e.g. .../en/calendar/2026/september/) — one page per month, so this
generates URLs for the current month plus ``months_ahead`` following months
and fetches each.

STATUS: URL generation is implemented, but the page-text parser is not yet
written — we have not seen the actual page content. Once a screenshot (or
copied HTML/text) of a real month page is available, replace
``parse_calendar_text`` below with real logic, following the pattern used in
opera_schedule_tracker/sources/scala.py.
"""

from __future__ import annotations

import calendar
import logging
from datetime import date

from opera_schedule_tracker.models import Performance

logger = logging.getLogger(__name__)


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


def parse_calendar_text(text: str, opera_house: str, page_url: str) -> list[Performance]:
    # TODO: implement once we have real page content to design the parser
    # against (see module docstring).
    return []


def fetch_wiener_staatsoper_performances(
    opera_house: str, url: str, months_ahead: int = 3
) -> list[Performance]:
    logger.warning(
        "%s parser is not yet implemented (awaiting a sample of the real "
        "page content) — skipping.",
        opera_house,
    )
    return []
