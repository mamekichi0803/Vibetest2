import json
from datetime import date
from pathlib import Path

from opera_schedule_tracker.models import Performance
from opera_schedule_tracker.state import (
    diff_performances,
    filter_upcoming,
    load_state,
    save_state,
)


def make_performance(title="Carmen", start="2026-09-01", venue="Main Hall", url="https://x/1"):
    return Performance(
        opera_house="Test Opera",
        title=title,
        start_date=start,
        venue=venue,
        url=url,
    )


def test_save_and_load_round_trip(tmp_path: Path):
    state_path = tmp_path / "state.json"
    performances = [make_performance(), make_performance(title="Tosca", start="2026-09-05")]

    save_state(state_path, performances)
    loaded = load_state(state_path)

    assert set(loaded.keys()) == {p.key for p in performances}
    assert loaded[performances[0].key] == performances[0]


def test_load_state_missing_file_returns_empty_dict(tmp_path: Path):
    assert load_state(tmp_path / "nope.json") == {}


def test_diff_detects_added_and_removed():
    previous = {make_performance().key: make_performance()}
    current = [make_performance(title="Tosca", start="2026-09-05")]

    diff = diff_performances(previous, current)

    assert len(diff.added) == 1
    assert diff.added[0].title == "Tosca"
    assert len(diff.removed) == 1
    assert diff.removed[0].title == "Carmen"
    assert diff.changed == []
    assert not diff.is_empty


def test_diff_detects_changed_venue():
    old = make_performance(venue="Main Hall")
    new = make_performance(venue="Annex Hall")
    previous = {old.key: old}

    diff = diff_performances(previous, [new])

    assert diff.added == []
    assert diff.removed == []
    assert len(diff.changed) == 1
    assert diff.changed[0] == (old, new)


def test_diff_empty_when_nothing_changed():
    p = make_performance()
    diff = diff_performances({p.key: p}, [p])
    assert diff.is_empty


def test_save_state_creates_parent_directory(tmp_path: Path):
    state_path = tmp_path / "nested" / "state.json"
    save_state(state_path, [make_performance()])
    assert state_path.exists()
    data = json.loads(state_path.read_text())
    assert len(data) == 1


def test_filter_upcoming_drops_past_start_dates():
    today = date(2026, 7, 8)
    past = make_performance(title="Old Show", start="2026-07-01")
    future = make_performance(title="New Show", start="2026-07-09")
    today_show = make_performance(title="Today Show", start="2026-07-08")

    result = filter_upcoming([past, future, today_show], today=today)

    assert {p.title for p in result} == {"New Show", "Today Show"}


def test_filter_upcoming_keeps_ongoing_runs_by_end_date():
    today = date(2026, 7, 8)
    ongoing_run = Performance(
        opera_house="Test Opera",
        title="Long Run",
        start_date="2026-06-01",
        end_date="2026-08-01",
    )
    finished_run = Performance(
        opera_house="Test Opera",
        title="Finished Run",
        start_date="2026-06-01",
        end_date="2026-07-01",
    )

    result = filter_upcoming([ongoing_run, finished_run], today=today)

    assert {p.title for p in result} == {"Long Run"}


def test_filter_upcoming_keeps_datetime_start_dates():
    today = date(2026, 7, 8)
    p = make_performance(title="Tonight", start="2026-07-08T19:30:00")
    assert filter_upcoming([p], today=today) == [p]


def test_filter_upcoming_keeps_unparseable_dates_rather_than_dropping():
    p = make_performance(title="Weird Date", start="not-a-date")
    assert filter_upcoming([p], today=date(2026, 7, 8)) == [p]


def test_filter_upcoming_defaults_to_today():
    # Just confirm the default `today=None` path doesn't crash and behaves
    # sanely relative to "now" without needing to freeze time.
    far_future = make_performance(title="Far Future", start="2999-01-01")
    far_past = make_performance(title="Far Past", start="2000-01-01")
    result = filter_upcoming([far_future, far_past])
    assert result == [far_future]
