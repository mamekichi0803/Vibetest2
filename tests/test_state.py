import json
from pathlib import Path

from opera_schedule_tracker.models import Performance
from opera_schedule_tracker.state import diff_performances, load_state, save_state


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
