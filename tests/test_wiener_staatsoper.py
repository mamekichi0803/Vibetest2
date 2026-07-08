from datetime import date

from opera_schedule_tracker.sources import wiener_staatsoper
from opera_schedule_tracker.sources.wiener_staatsoper import (
    fetch_wiener_staatsoper_performances,
    month_urls,
    parse_calendar_text,
)

# Modeled on a screenshot of
# https://www.wiener-staatsoper.at/en/calendar/2026/september/ taken
# 2026-07-08. Not verified against live markup.
SEPTEMBER_TEXT = """
2026/27 Season

SEP OCT NOV DEC JAN FEB MAR APR

Fri
04
Sep
19:00-22:30

GIUSEPPE VERDI
DON CARLO
OPERA
Main Stage
with Vittorio Grigolo, Étienne Dupuis, Ain Anger
Conductor: Pier Giorgio Morandi

Sat
05
Sep
18:00-21:00

WOLFGANG AMADEUS MOZART
THE MAGIC FLUTE
OPERA
Main Stage
with Someone Else
Conductor: Another Conductor
"""

JANUARY_TEXT = """
2026/27 Season

Thu
14
Jan
19:30-22:00

GIACOMO PUCCINI
TOSCA
OPERA
Main Stage
with A Singer
Conductor: A Conductor
"""

NO_PERFORMANCES_TEXT = """
There are no performances in July and August. Join us for a guided tour instead.
The events in July and August are organized by third parties.
"""


def test_month_urls_generates_current_plus_ahead():
    urls = month_urls(
        "https://www.wiener-staatsoper.at/en/calendar/",
        months_ahead=3,
        today=date(2026, 7, 8),
    )
    assert urls == [
        "https://www.wiener-staatsoper.at/en/calendar/2026/july/",
        "https://www.wiener-staatsoper.at/en/calendar/2026/august/",
        "https://www.wiener-staatsoper.at/en/calendar/2026/september/",
        "https://www.wiener-staatsoper.at/en/calendar/2026/october/",
    ]


def test_month_urls_rolls_over_year_boundary():
    urls = month_urls(
        "https://www.wiener-staatsoper.at/en/calendar/",
        months_ahead=2,
        today=date(2026, 11, 15),
    )
    assert urls == [
        "https://www.wiener-staatsoper.at/en/calendar/2026/november/",
        "https://www.wiener-staatsoper.at/en/calendar/2026/december/",
        "https://www.wiener-staatsoper.at/en/calendar/2027/january/",
    ]


def test_month_urls_strips_trailing_slash_from_base():
    urls = month_urls(
        "https://www.wiener-staatsoper.at/en/calendar",
        months_ahead=0,
        today=date(2026, 7, 8),
    )
    assert urls == ["https://www.wiener-staatsoper.at/en/calendar/2026/july/"]


def test_parses_events_within_season_start_year():
    performances = parse_calendar_text(
        SEPTEMBER_TEXT, "Wiener Staatsoper", "https://x/2026/september/"
    )
    assert len(performances) == 2
    don_carlo = performances[0]
    assert don_carlo.title == "Don Carlo (Giuseppe Verdi)"
    assert don_carlo.start_date == "2026-09-04T19:00:00"
    assert don_carlo.venue == "Main Stage"


def test_resolves_year_across_season_boundary():
    performances = parse_calendar_text(
        JANUARY_TEXT, "Wiener Staatsoper", "https://x/2027/january/"
    )
    assert len(performances) == 1
    assert performances[0].start_date == "2027-01-14T19:30:00"


def test_no_performances_message_yields_empty_list():
    assert (
        parse_calendar_text(NO_PERFORMANCES_TEXT, "Wiener Staatsoper", "https://x")
        == []
    )


def test_event_before_season_header_is_skipped(caplog):
    text = SEPTEMBER_TEXT.split("2026/27 Season", 1)[1]
    with caplog.at_level("WARNING"):
        result = parse_calendar_text(text, "Wiener Staatsoper", "https://x")
    assert result == []
    assert "no season header" in caplog.text


def test_fetch_renders_each_month_and_aggregates(monkeypatch):
    rendered = {
        "https://www.wiener-staatsoper.at/en/calendar/2026/september/": SEPTEMBER_TEXT,
        "https://www.wiener-staatsoper.at/en/calendar/2026/october/": NO_PERFORMANCES_TEXT,
    }
    monkeypatch.setattr(
        wiener_staatsoper,
        "month_urls",
        lambda base, ahead: list(rendered.keys()),
    )
    monkeypatch.setattr(
        wiener_staatsoper, "get_rendered_text", lambda url, wait_ms=0: rendered[url]
    )

    result = fetch_wiener_staatsoper_performances(
        "Wiener Staatsoper", "https://www.wiener-staatsoper.at/en/calendar/"
    )
    assert len(result) == 2


def test_fetch_continues_when_one_month_fails_to_render(monkeypatch, caplog):
    def fake_get_rendered_text(url, wait_ms=0):
        if "october" in url:
            raise RuntimeError("boom")
        return SEPTEMBER_TEXT

    monkeypatch.setattr(
        wiener_staatsoper,
        "month_urls",
        lambda base, ahead: [
            "https://x/2026/september/",
            "https://x/2026/october/",
        ],
    )
    monkeypatch.setattr(wiener_staatsoper, "get_rendered_text", fake_get_rendered_text)

    with caplog.at_level("WARNING"):
        result = fetch_wiener_staatsoper_performances("Wiener Staatsoper", "https://x/")

    assert len(result) == 2
    assert "boom" in caplog.text
