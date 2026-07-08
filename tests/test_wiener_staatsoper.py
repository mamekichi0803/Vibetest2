from datetime import date

from opera_schedule_tracker.sources.wiener_staatsoper import (
    fetch_wiener_staatsoper_performances,
    month_urls,
)


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


def test_stub_parser_returns_empty_and_warns(caplog):
    with caplog.at_level("WARNING"):
        result = fetch_wiener_staatsoper_performances("Wiener Staatsoper", "https://x")
    assert result == []
    assert "not yet implemented" in caplog.text
