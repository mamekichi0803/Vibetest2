"""Parser for the Royal Ballet and Opera's "tickets and events" page.

Source: https://www.rbo.org.uk/tickets-and-events

STATUS: not yet implemented — we have not seen the real page content.
Once a screenshot (or copied HTML/text) is available, implement
``parse_page_text`` (or a DOM-based parser, if we get real HTML) following
the pattern in opera_schedule_tracker/sources/scala.py.
"""

from __future__ import annotations

import logging

from opera_schedule_tracker.models import Performance

logger = logging.getLogger(__name__)


def fetch_rbo_performances(opera_house: str, url: str) -> list[Performance]:
    logger.warning(
        "%s parser is not yet implemented (awaiting a sample of the real "
        "page content) — skipping.",
        opera_house,
    )
    return []
