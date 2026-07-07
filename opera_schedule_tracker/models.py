"""Data model for a single opera performance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Performance:
    """A single performance (one date) at one opera house."""

    opera_house: str
    title: str
    start_date: str  # ISO-8601 date or datetime string
    end_date: Optional[str] = None
    venue: Optional[str] = None
    url: Optional[str] = None

    @property
    def key(self) -> str:
        """Stable identity used to match the same performance across runs."""
        return f"{self.opera_house}|{self.title}|{self.start_date}"

    def to_dict(self) -> dict:
        return {
            "opera_house": self.opera_house,
            "title": self.title,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "venue": self.venue,
            "url": self.url,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Performance":
        return cls(
            opera_house=data["opera_house"],
            title=data["title"],
            start_date=data["start_date"],
            end_date=data.get("end_date"),
            venue=data.get("venue"),
            url=data.get("url"),
        )
