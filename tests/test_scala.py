from opera_schedule_tracker.sources.scala import parse_calendar_text

# Modeled on a screenshot of https://www.teatroallascala.org/en/calendar.html
# taken 2026-07-08 (July 2026 view). Not verified against live markup.
CALENDAR_TEXT = """
CALENDAR
July 2026

Mon Tue Wed Thu Fri Sat Sun

6
08:00 PM
LUCIA DI LAMMERMOOR
Gaetano Donizetti
Series O Mini Subs.
GSA U35

7
08:00 PM
DON QUIXOTE
Rudolf Nureyev
Series M Mini Subs.
HD LIVE
GSA U35

8
08:00 PM
DON QUIXOTE
Rudolf Nureyev
Out Of Subs.
GSA U35

9
08:00 PM
LUCIA DI LAMMERMOOR
Gaetano Donizetti
Out Of Subs.
GSA
"""


def test_parses_all_events_in_grid():
    performances = parse_calendar_text(
        CALENDAR_TEXT, "Teatro alla Scala", "https://www.teatroallascala.org/en/calendar.html"
    )
    assert len(performances) == 4


def test_extracts_title_date_and_time():
    performances = parse_calendar_text(
        CALENDAR_TEXT, "Teatro alla Scala", "https://www.teatroallascala.org/en/calendar.html"
    )
    first = performances[0]
    assert first.title == "Lucia Di Lammermoor"
    assert first.start_date == "2026-07-06T20:00:00"
    assert first.opera_house == "Teatro alla Scala"
    assert "Series O Mini Subs." in first.venue


def test_distinguishes_repeated_titles_by_date():
    performances = parse_calendar_text(
        CALENDAR_TEXT, "Teatro alla Scala", "https://www.teatroallascala.org/en/calendar.html"
    )
    lucia_dates = sorted(p.start_date for p in performances if p.title == "Lucia Di Lammermoor")
    assert lucia_dates == ["2026-07-06T20:00:00", "2026-07-09T20:00:00"]


def test_out_of_subs_series_label_is_captured():
    performances = parse_calendar_text(
        CALENDAR_TEXT, "Teatro alla Scala", "https://www.teatroallascala.org/en/calendar.html"
    )
    don_quixote_8th = next(
        p for p in performances if p.title == "Don Quixote" and p.start_date.startswith("2026-07-08")
    )
    assert "Out Of Subs." in don_quixote_8th.venue


def test_empty_text_returns_no_performances():
    assert parse_calendar_text("", "Teatro alla Scala", "https://x") == []


def test_text_without_month_header_is_ignored():
    text = "6\n08:00 PM\nLUCIA DI LAMMERMOOR\n"
    assert parse_calendar_text(text, "Teatro alla Scala", "https://x") == []
