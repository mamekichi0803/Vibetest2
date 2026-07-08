"""Generic scraper that reads schema.org ``Event`` JSON-LD blocks.

Most modern "what's on" / season pages embed structured data
(``<script type="application/ld+json">``) describing each performance for
search-engine rich results. Reading that structured data is far more
resilient to redesigns than hand-written CSS selectors, so it is the
default strategy for every opera house in ``config/opera_houses.yaml``.

If a given page does not expose JSON-LD (or exposes it in a shape this
parser does not understand), :func:`fetch_jsonld_performances` simply
returns an empty list; the caller logs a warning and moves on to the next
source instead of crashing the whole run.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Iterable

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from opera_schedule_tracker.models import Performance

logger = logging.getLogger(__name__)

# schema.org types that count as a "performance" for our purposes.
EVENT_TYPES = {
    "Event",
    "TheaterEvent",
    "MusicEvent",
    "PublicEvent",
    "Festival",
    "ScreeningEvent",
    "PerformingArtsEvent",
}

REQUEST_TIMEOUT_SECONDS = 20
# A realistic desktop Chrome UA (rather than an honest bot UA) plus the
# headers a real browser sends, to reduce the chance of a bare 403 from
# sites that block obvious script traffic.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _iter_jsonld_blocks(html: str) -> Iterable[Any]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.text
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        yield data


def _flatten(data: Any) -> Iterable[dict]:
    """Yield every dict found in a JSON-LD payload, including @graph entries."""
    if isinstance(data, list):
        for item in data:
            yield from _flatten(item)
    elif isinstance(data, dict):
        if "@graph" in data and isinstance(data["@graph"], list):
            for item in data["@graph"]:
                yield from _flatten(item)
        else:
            yield data


def _is_event(node: dict) -> bool:
    node_type = node.get("@type")
    if isinstance(node_type, list):
        return any(t in EVENT_TYPES for t in node_type)
    return node_type in EVENT_TYPES


def _extract_location_name(node: dict) -> str | None:
    location = node.get("location")
    if isinstance(location, dict):
        return location.get("name")
    if isinstance(location, list) and location:
        first = location[0]
        if isinstance(first, dict):
            return first.get("name")
    if isinstance(location, str):
        return location
    return None


def _to_performance(node: dict, opera_house: str, fallback_url: str) -> Performance | None:
    title = node.get("name")
    start_date = node.get("startDate")
    if not title or not start_date:
        return None
    try:
        # Normalise to ISO-8601 so diffing/sorting is stable even if the
        # source uses varying date/time formats.
        start_date = date_parser.isoparse(start_date).isoformat()
    except (ValueError, TypeError):
        pass

    end_date = node.get("endDate")
    if end_date:
        try:
            end_date = date_parser.isoparse(end_date).isoformat()
        except (ValueError, TypeError):
            pass

    url = node.get("url") or fallback_url

    return Performance(
        opera_house=opera_house,
        title=title.strip(),
        start_date=start_date,
        end_date=end_date,
        venue=_extract_location_name(node),
        url=url,
    )


def parse_jsonld_performances(html: str, opera_house: str, page_url: str) -> list[Performance]:
    """Pure parsing step, split out from the network fetch for easy testing."""
    performances: list[Performance] = []
    seen_keys: set[str] = set()

    for block in _iter_jsonld_blocks(html):
        for node in _flatten(block):
            if not isinstance(node, dict) or not _is_event(node):
                continue
            performance = _to_performance(node, opera_house, page_url)
            if performance is None:
                continue
            if performance.key in seen_keys:
                continue
            seen_keys.add(performance.key)
            performances.append(performance)

    return performances


def fetch_jsonld_performances(opera_house: str, url: str) -> list[Performance]:
    """Fetch ``url`` and parse any schema.org Event JSON-LD found on it."""
    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers=REQUEST_HEADERS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Failed to fetch %s (%s): %s", opera_house, url, exc)
        return []

    performances = parse_jsonld_performances(response.text, opera_house, url)
    if not performances:
        logger.warning(
            "No JSON-LD Event data found for %s at %s "
            "(the page may not use structured data, or its markup changed)",
            opera_house,
            url,
        )
    return performances
