from pathlib import Path

import yaml

from opera_schedule_tracker import main as main_module
from opera_schedule_tracker.models import Performance


def test_run_end_to_end(tmp_path: Path, monkeypatch):
    config_path = tmp_path / "opera_houses.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "opera_houses": [
                    {"name": "Test Opera", "url": "https://example.com/season"}
                ]
            }
        )
    )
    state_path = tmp_path / "state.json"

    fetched = [
        Performance(
            opera_house="Test Opera",
            title="Carmen",
            start_date="2026-09-01",
            venue="Main Hall",
            url="https://example.com/carmen",
        )
    ]
    monkeypatch.setattr(
        main_module, "fetch_jsonld_performances", lambda name, url: fetched
    )

    sent_diffs = []
    monkeypatch.setattr(
        main_module,
        "send_update_email",
        lambda diff, recipient=None: sent_diffs.append(diff),
    )

    main_module.run(config_path=config_path, state_path=state_path)

    assert len(sent_diffs) == 1
    assert len(sent_diffs[0].added) == 1
    assert state_path.exists()

    # second run with the same data should produce an empty diff
    main_module.run(config_path=config_path, state_path=state_path)
    assert sent_diffs[1].is_empty


def test_run_dry_run_does_not_send_or_save(tmp_path: Path, monkeypatch):
    config_path = tmp_path / "opera_houses.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {"opera_houses": [{"name": "Test Opera", "url": "https://example.com"}]}
        )
    )
    state_path = tmp_path / "state.json"

    monkeypatch.setattr(main_module, "fetch_jsonld_performances", lambda name, url: [])

    calls = []
    monkeypatch.setattr(
        main_module, "send_update_email", lambda *a, **k: calls.append(1)
    )

    main_module.run(config_path=config_path, state_path=state_path, dry_run=True)

    assert calls == []
    assert not state_path.exists()
