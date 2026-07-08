"""Parser for the Metropolitan Opera's calendar page.

Source: https://www.metopera.org/calendar/ — renders its schedule via
JavaScript, so opera_schedule_tracker.browser (headless Chromium) is needed
just to get the schedule into the DOM at all, before any parsing.

STATUS: not yet implemented — we have not seen the real page content.
Once a screenshot of the rendered page (and, ideally, the underlying
XHR/fetch API request the calendar widget makes — see browser DevTools'
Network tab) is available, implement a parser following the pattern in
opera_schedule_tracker/sources/scala.py. If a JSON API endpoint can be
identified, prefer calling it directly over parsing rendered text.
"""

from __future__ import annotations

import logging

from opera_schedule_tracker.models import Performance

logger = logging.getLogger(__name__)


def fetch_met_opera_performances(opera_house: str, url: str) -> list[Performance]:
    logger.warning(
        "%s parser is not yet implemented (awaiting a sample of the real "
        "page content, ideally including its data API) — skipping.",
        opera_house,
    )
    return []
