from opera_schedule_tracker.sources.met_opera import (
    fetch_met_opera_performances,
    parse_calendar_text,
)

# Modeled on the actual rendered text captured from a GitHub Actions run
# (2026-07-08) fetching https://www.metopera.org/calendar/ (the default
# month-grid view, not the day-detail popup we originally assumed).
CALENDAR_TEXT = """
Jul 2026
Page
Previous month
Next month
EVENTS FOR OCTOBER
9

Learn more about
Sylvia - ABT

7:30 PM

BUY TICKETS
TO SYLVIA - ABT

EVENTS FOR OCTOBER
10

Learn more about
Sylvia - ABT

2:00 PM

BUY TICKETS
TO SYLVIA - ABT

Learn more about
Sylvia - ABT

7:30 PM

BUY TICKETS
TO SYLVIA - ABT

EVENTS FOR OCTOBER
11

EVENTS FOR OCTOBER
12

Learn more about
Swan Lake - ABT

7:30 PM

BUY TICKETS
TO SWAN LAKE - ABT
"""

URL = "https://www.metopera.org/calendar/"


def test_parses_all_events():
    performances = parse_calendar_text(CALENDAR_TEXT, "Metropolitan Opera", URL)
    assert len(performances) == 4


def test_extracts_title_and_datetime():
    performances = parse_calendar_text(CALENDAR_TEXT, "Metropolitan Opera", URL)
    first = next(p for p in performances if p.start_date == "2026-10-09T19:30:00")
    assert first.title == "Sylvia - ABT"
    assert first.opera_house == "Metropolitan Opera"


def test_handles_multiple_events_same_day_without_repeated_header():
    performances = parse_calendar_text(CALENDAR_TEXT, "Metropolitan Opera", URL)
    day_10_events = [p for p in performances if p.start_date.startswith("2026-10-10")]
    assert len(day_10_events) == 2
    assert {p.start_date for p in day_10_events} == {
        "2026-10-10T14:00:00",
        "2026-10-10T19:30:00",
    }


def test_empty_day_cells_produce_no_performances():
    performances = parse_calendar_text(CALENDAR_TEXT, "Metropolitan Opera", URL)
    day_11_events = [p for p in performances if p.start_date.startswith("2026-10-11")]
    assert day_11_events == []


def test_day_after_empty_cell_still_parses():
    performances = parse_calendar_text(CALENDAR_TEXT, "Metropolitan Opera", URL)
    swan_lake = next(p for p in performances if p.title == "Swan Lake - ABT")
    assert swan_lake.start_date == "2026-10-12T19:30:00"


def test_no_month_year_header_yields_empty_list():
    text = "EVENTS FOR OCTOBER\n9\n\nLearn more about\nSylvia - ABT\n\n7:30 PM\n"
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
    assert len(result) == 4
