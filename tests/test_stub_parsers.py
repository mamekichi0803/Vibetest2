from opera_schedule_tracker.sources.met_opera import fetch_met_opera_performances


def test_stub_parser_returns_empty_and_warns(caplog):
    with caplog.at_level("WARNING"):
        result = fetch_met_opera_performances("Some Opera", "https://x")
    assert result == []
    assert "not yet implemented" in caplog.text
