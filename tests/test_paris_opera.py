from opera_schedule_tracker.sources import paris_opera
from opera_schedule_tracker.sources.paris_opera import (
    fetch_paris_opera_performances,
    parse_programme_text,
)

# Modeled on screenshots of https://www.operadeparis.fr/en/programme-and-tickets
# taken 2026-07-08. Not verified against live markup.
PROGRAMME_TEXT = """
22 RESULTS

OPERA
Black Pearl: meditations for Josephine
Tyshawn Sorey
Palais Garnier
from 09 to 19 Sep 2026
BOOK

OPERA
Il Barbiere di Siviglia
Gioacchino Rossini
Opera Bastille
from 12 Sep to 05 Nov 2026
BOOK
"""

URL = "https://www.operadeparis.fr/en/programme-and-tickets"


def test_parses_both_cards():
    performances = parse_programme_text(PROGRAMME_TEXT, "Opera national de Paris", URL)
    titles = {p.title for p in performances}
    assert titles == {"Black Pearl: meditations for Josephine", "Il Barbiere di Siviglia"}


def test_same_month_date_range():
    performances = parse_programme_text(PROGRAMME_TEXT, "Opera national de Paris", URL)
    black_pearl = next(p for p in performances if "Black Pearl" in p.title)
    assert black_pearl.start_date == "2026-09-09"
    assert black_pearl.end_date == "2026-09-19"
    assert black_pearl.venue == "Palais Garnier"


def test_different_month_date_range():
    performances = parse_programme_text(PROGRAMME_TEXT, "Opera national de Paris", URL)
    barbiere = next(p for p in performances if "Barbiere" in p.title)
    assert barbiere.start_date == "2026-09-12"
    assert barbiere.end_date == "2026-11-05"
    assert barbiere.venue == "Opera Bastille"


def test_unknown_category_card_is_skipped():
    text = "SCREENING SPECIAL\nSome Film\nfrom 01 to 02 Jan 2026\n"
    assert parse_programme_text(text, "Opera national de Paris", URL) == []


def test_card_without_closing_date_range_is_skipped():
    text = "OPERA\nUnfinished Card\nSome Composer\nSome Venue\n"
    assert parse_programme_text(text, "Opera national de Paris", URL) == []


def test_empty_text_returns_no_performances():
    assert parse_programme_text("", "Opera national de Paris", URL) == []


class _FakePage:
    def __init__(self, text: str):
        self._text = text
        self.mouse = self
        self.scroll_calls = 0

    def wheel(self, x, y):
        self.scroll_calls += 1

    def wait_for_timeout(self, ms):
        pass

    def evaluate(self, script):
        return 1000  # constant height => scrolling stops after first check

    def inner_text(self, selector):
        return self._text


def test_fetch_scrolls_and_parses(monkeypatch):
    from contextlib import contextmanager

    fake_page = _FakePage(PROGRAMME_TEXT)

    @contextmanager
    def fake_open_page(url):
        yield fake_page

    monkeypatch.setattr(paris_opera, "open_page", fake_open_page)

    result = fetch_paris_opera_performances("Opera national de Paris", URL)

    assert len(result) == 2
    assert fake_page.scroll_calls >= 1


def test_fetch_returns_empty_list_on_render_failure(monkeypatch, caplog):
    from contextlib import contextmanager

    @contextmanager
    def fake_open_page(url):
        raise RuntimeError("net::ERR_TUNNEL_CONNECTION_FAILED")
        yield  # pragma: no cover

    monkeypatch.setattr(paris_opera, "open_page", fake_open_page)

    with caplog.at_level("WARNING"):
        result = fetch_paris_opera_performances("Opera national de Paris", URL)

    assert result == []
    assert "Failed to render" in caplog.text
