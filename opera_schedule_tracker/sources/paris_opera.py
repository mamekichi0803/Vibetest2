"""Parser for Opera national de Paris's programme page.

Source: https://www.operadeparis.fr/en/programme-and-tickets

STATUS: not yet implemented — we have not seen the real page content.
Once a screenshot (or copied HTML/text) is available, implement a parser
following the pattern in opera_schedule_tracker/sources/scala.py.
"""

from __future__ import annotations

import logging

from opera_schedule_tracker.models import Performance

logger = logging.getLogger(__name__)


def fetch_paris_opera_performances(opera_house: str, url: str) -> list[Performance]:
    logger.warning(
        "%s parser is not yet implemented (awaiting a sample of the real "
        "page content) — skipping.",
        opera_house,
    )
    return []
