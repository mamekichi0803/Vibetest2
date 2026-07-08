from opera_schedule_tracker.sources import rbo
from opera_schedule_tracker.sources.rbo import fetch_rbo_performances, parse_events_text

# Modeled on the actual rendered text captured from a GitHub Actions run
# (2026-07-08) fetching https://www.rbo.org.uk/tickets-and-events (the
# default "List" view, not the day-by-day "Calendar" view we originally
# assumed).
EVENTS_TEXT = """
Royal Opera House

Tours

Behind the Scenes Tour

9 July
–30 October 2026

Take a look in the areas that are normally off-limits to the public.

Buy tickets
More info

Main Stage

Opera and music

I puritani

9
–19 July 2026

A couple's faith is tested.

See dates
More info

Paul Hamlyn Hall

Opera and music

Ballet and dance

Live at Lunch

10 July 2026

Free performances featuring Royal Ballet and Opera and guest artists.

See dates
More info

Royal Opera House

Tours

Beyond the Bridge Tour: Celebrating 100 Years of The Royal Ballet School

13 July 2026

Mark the centenary of The Royal Ballet School with this limited edition tour.

Sold out
More info
"""

URL = "https://www.rbo.org.uk/tickets-and-events"


def test_parses_all_cards():
    performances = parse_events_text(EVENTS_TEXT, "Royal Ballet and Opera", URL)
    titles = {p.title for p in performances}
    assert titles == {
        "Behind the Scenes Tour",
        "I puritani",
        "Live at Lunch",
        "Beyond the Bridge Tour: Celebrating 100 Years of The Royal Ballet School",
    }


def test_range_crossing_months():
    performances = parse_events_text(EVENTS_TEXT, "Royal Ballet and Opera", URL)
    tour = next(p for p in performances if p.title == "Behind the Scenes Tour")
    assert tour.start_date == "2026-07-09"
    assert tour.end_date == "2026-10-30"


def test_range_within_single_month():
    performances = parse_events_text(EVENTS_TEXT, "Royal Ballet and Opera", URL)
    puritani = next(p for p in performances if p.title == "I puritani")
    assert puritani.start_date == "2026-07-09"
    assert puritani.end_date == "2026-07-19"


def test_single_day_event():
    performances = parse_events_text(EVENTS_TEXT, "Royal Ballet and Opera", URL)
    lunch = next(p for p in performances if p.title == "Live at Lunch")
    assert lunch.start_date == "2026-07-10"
    assert lunch.end_date is None


def test_title_is_line_immediately_before_date_regardless_of_tag_count():
    # "Live at Lunch" has two category tags before it (Opera and music /
    # Ballet and dance) vs one for the others; title detection shouldn't
    # care how many tag lines precede it.
    performances = parse_events_text(EVENTS_TEXT, "Royal Ballet and Opera", URL)
    assert any(p.title == "Live at Lunch" for p in performances)


def test_empty_text_returns_no_performances():
    assert parse_events_text("", "Royal Ballet and Opera", URL) == []


def test_fetch_returns_empty_list_and_warns_on_render_failure(monkeypatch, caplog):
    def boom(url, wait_ms=0):
        raise RuntimeError("net::ERR_TUNNEL_CONNECTION_FAILED")

    monkeypatch.setattr(rbo, "get_rendered_text", boom)

    with caplog.at_level("WARNING"):
        result = fetch_rbo_performances("Royal Ballet and Opera", URL)

    assert result == []
    assert "Failed to render" in caplog.text


def test_fetch_parses_rendered_text(monkeypatch):
    monkeypatch.setattr(rbo, "get_rendered_text", lambda url, wait_ms=0: EVENTS_TEXT)

    result = fetch_rbo_performances("Royal Ballet and Opera", URL)
    assert len(result) == 4
