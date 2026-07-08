from contextlib import contextmanager

from opera_schedule_tracker.sources import rbo
from opera_schedule_tracker.sources.rbo import fetch_rbo_performances, parse_events_text

# Modeled on a screenshot of https://www.rbo.org.uk/tickets-and-events taken
# 2026-07-08 (July 2026 view, "Opera and Music" filter). Not verified
# against live markup.
EVENTS_TEXT = """
All events
Opera and Music
Ballet and Dance

July, 2026

Expand all

Wednesday
8

Thursday
9
I puritani
7PM

Friday
10
Live at Lunch: Music
1PM
La fille du regiment
7:30PM
"""


def test_parses_events_with_weekday_and_day_on_separate_lines():
    performances = parse_events_text(
        EVENTS_TEXT, "Royal Ballet and Opera", "https://www.rbo.org.uk/tickets-and-events"
    )
    titles = {p.title for p in performances}
    assert titles == {"I puritani", "Live at Lunch: Music", "La fille du regiment"}


def test_extracts_correct_date_and_time():
    performances = parse_events_text(
        EVENTS_TEXT, "Royal Ballet and Opera", "https://www.rbo.org.uk/tickets-and-events"
    )
    i_puritani = next(p for p in performances if p.title == "I puritani")
    assert i_puritani.start_date == "2026-07-09T19:00:00"
    assert i_puritani.opera_house == "Royal Ballet and Opera"


def test_handles_multiple_events_on_same_day():
    performances = parse_events_text(
        EVENTS_TEXT, "Royal Ballet and Opera", "https://www.rbo.org.uk/tickets-and-events"
    )
    friday_events = [p for p in performances if p.start_date.startswith("2026-07-10")]
    assert len(friday_events) == 2
    lunch = next(p for p in friday_events if p.title == "Live at Lunch: Music")
    assert lunch.start_date == "2026-07-10T13:00:00"


def test_weekday_and_day_on_same_line():
    text = "July, 2026\n\nThursday 9\nI puritani\n7PM\n"
    performances = parse_events_text(text, "Royal Ballet and Opera", "https://x")
    assert len(performances) == 1
    assert performances[0].start_date == "2026-07-09T19:00:00"


def test_empty_day_produces_no_performance():
    text = "July, 2026\n\nWednesday\n8\n\nThursday\n9\n"
    assert parse_events_text(text, "Royal Ballet and Opera", "https://x") == []


def test_no_month_header_yields_empty_list():
    text = "Thursday\n9\nI puritani\n7PM\n"
    assert parse_events_text(text, "Royal Ballet and Opera", "https://x") == []


class _FakeLocator:
    def __init__(self, raise_on_click: bool):
        self._raise_on_click = raise_on_click

    def click(self, timeout=None):
        if self._raise_on_click:
            raise TimeoutError("element not found")


class _FakePage:
    def __init__(self, text: str, raise_on_click: bool = False):
        self._text = text
        self._raise_on_click = raise_on_click

    def get_by_text(self, text, exact=False):
        return _FakeLocator(self._raise_on_click)

    def wait_for_timeout(self, ms):
        pass

    def inner_text(self, selector):
        return self._text


def test_fetch_clicks_expand_all_and_parses(monkeypatch):
    @contextmanager
    def fake_open_page(url):
        yield _FakePage(EVENTS_TEXT)

    monkeypatch.setattr(rbo, "open_page", fake_open_page)

    result = fetch_rbo_performances(
        "Royal Ballet and Opera", "https://www.rbo.org.uk/tickets-and-events"
    )
    assert len(result) == 3


def test_fetch_continues_when_expand_all_click_fails(monkeypatch, caplog):
    @contextmanager
    def fake_open_page(url):
        yield _FakePage(EVENTS_TEXT, raise_on_click=True)

    monkeypatch.setattr(rbo, "open_page", fake_open_page)

    with caplog.at_level("WARNING"):
        result = fetch_rbo_performances(
            "Royal Ballet and Opera", "https://www.rbo.org.uk/tickets-and-events"
        )

    assert len(result) == 3
    assert "Could not click" in caplog.text


def test_fetch_returns_empty_list_when_page_fails_to_load(monkeypatch, caplog):
    @contextmanager
    def fake_open_page(url):
        raise RuntimeError("net::ERR_TUNNEL_CONNECTION_FAILED")
        yield  # pragma: no cover

    monkeypatch.setattr(rbo, "open_page", fake_open_page)

    with caplog.at_level("WARNING"):
        result = fetch_rbo_performances("Royal Ballet and Opera", "https://x")

    assert result == []
    assert "Failed to render" in caplog.text
