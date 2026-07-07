"""Persist the last-seen schedule and diff it against a new snapshot."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

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
