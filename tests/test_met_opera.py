from opera_schedule_tracker.sources.met_opera import (
    fetch_met_opera_performances,
    parse_calendar_text,
)

# Modeled on screenshots of https://www.metopera.org/calendar/ taken
# 2026-07-08 (Jul 2026 view). Not verified against live markup.
CALENDAR_TEXT = """
Jul 2026

FILTERS+

THU, JUL 9

ON STAGE

7:30 PM
LEO DELIBES
Sylvia - ABT
Barker; Shevchenko, Royal III

BUY TICKETS

FRI, JUL 10

ON STAGE

7:30 PM
GIACOMO PUCCINI
Madama Butterfly
Some Cast Here

BUY TICKETS

7:30 PM
LEO DELIBES
Sylvia - ABT
Barker; Shevchenko, Royal III

BUY TICKETS
"""

URL = "https://www.metopera.org/calendar/"


def test_parses_all_events():
    performances = parse_calendar_text(CALENDAR_TEXT, "Metropolitan Opera", URL)
    assert len(performances) == 3


def test_extracts_title_and_datetime():
    performances = parse_calendar_text(CALENDAR_TEXT, "Metropolitan Opera", URL)
    sylvia = next(p for p in performances if p.start_date == "2026-07-09T19:30:00")
    assert sylvia.title == "Sylvia - ABT"
    assert sylvia.opera_house == "Metropolitan Opera"


def test_handles_multiple_events_same_day():
    performances = parse_calendar_text(CALENDAR_TEXT, "Metropolitan Opera", URL)
    friday_events = [p for p in performances if p.start_date.startswith("2026-07-10")]
    assert len(friday_events) == 2
    assert {p.title for p in friday_events} == {"Madama Butterfly", "Sylvia - ABT"}


def test_no_month_year_header_yields_empty_list():
    text = "THU, JUL 9\n\n7:30 PM\nLEO DELIBES\nSylvia - ABT\n"
    assert parse_calendar_text(text, "Metropolitan Opera", URL) == []


def test_empty_text_returns_no_performances():
    assert parse_calendar_text("", "Metropolitan Opera", URL) == []


def test_fetch_returns_empty_list_and_warns_on_render_failure(monkeypatch, caplog):
    import opera_schedule_tracker.sources.met_opera as met_opera_module

    def boom(url, wait_ms=0):
        raise RuntimeError("net::ERR_TUNNEL_CONNECTION_FAILED")

    monkeypatch.setattr(met_opera_module, "get_rendered_text", boom)

    with caplog.at_level("WARNING"):
        result = fetch_met_opera_performances("Metropolitan Opera", URL)

    assert result == []
    assert "Failed to render" in caplog.text


def test_fetch_parses_rendered_text(monkeypatch):
    import opera_schedule_tracker.sources.met_opera as met_opera_module

    monkeypatch.setattr(
        met_opera_module, "get_rendered_text", lambda url, wait_ms=0: CALENDAR_TEXT
    )

    result = fetch_met_opera_performances("Metropolitan Opera", URL)
    assert len(result) == 3
