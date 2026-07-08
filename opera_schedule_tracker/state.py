"""Persist the last-seen schedule and diff it against a new snapshot."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from dateutil import parser as date_parser

from opera_schedule_tracker.models import Performance


@dataclass
class Diff:
    added: list[Performance]
    removed: list[Performance]
    changed: list[tuple[Performance, Performance]]  # (old, new)

    @property
    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.changed)


def load_state(path: Path) -> dict[str, Performance]:
    """Load the previously saved snapshot, keyed by ``Performance.key``."""
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {item["key"]: Performance.from_dict(item) for item in raw}


def save_state(path: Path, performances: list[Performance]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [dict(key=p.key, **p.to_dict()) for p in performances]
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _relevant_date(performance: Performance) -> date | None:
    """The date that determines whether a performance is still upcoming:
    its run's end date if there is one, otherwise its start date."""
    raw = performance.end_date or performance.start_date
    try:
        return date_parser.isoparse(raw).date()
    except (ValueError, TypeError):
        return None


def filter_upcoming(
    performances: Iterable[Performance], today: date | None = None
) -> list[Performance]:
    """Drop performances (or performance runs) that have already ended.

    A performance with an unparseable date is kept rather than silently
    dropped, since we'd rather over-report than hide a real listing.
    """
    today = today or date.today()
    return [
        p
        for p in performances
        if (relevant := _relevant_date(p)) is None or relevant >= today
    ]


def diff_performances(
    previous: dict[str, Performance], current: list[Performance]
) -> Diff:
    """Compare the previous snapshot to a freshly fetched one.

    - ``added``: performances whose key wasn't present before.
    - ``removed``: previously-known performances absent from the new fetch.
    - ``changed``: same key but different venue/url (date/title are part of
      the key, so a date change surfaces as an add + remove, which is the
      more useful signal for "the show moved").
    """
    current_by_key = {p.key: p for p in current}

    added = [p for key, p in current_by_key.items() if key not in previous]
    removed = [p for key, p in previous.items() if key not in current_by_key]
    changed = [
        (previous[key], current_by_key[key])
        for key in current_by_key.keys() & previous.keys()
        if previous[key] != current_by_key[key]
    ]

    return Diff(added=added, removed=removed, changed=changed)
