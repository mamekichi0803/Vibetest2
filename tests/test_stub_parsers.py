import pytest

from opera_schedule_tracker.sources.met_opera import fetch_met_opera_performances
from opera_schedule_tracker.sources.paris_opera import fetch_paris_opera_performances


@pytest.mark.parametrize(
    "fetch",
    [fetch_met_opera_performances, fetch_paris_opera_performances],
)
def test_stub_parser_returns_empty_and_warns(fetch, caplog):
    with caplog.at_level("WARNING"):
        result = fetch("Some Opera", "https://x")
    assert result == []
    assert "not yet implemented" in caplog.text
