from opera_schedule_tracker.sources.generic_jsonld import parse_jsonld_performances

SINGLE_EVENT_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TheaterEvent",
  "name": "Madama Butterfly",
  "startDate": "2026-09-12T19:30:00-04:00",
  "endDate": "2026-09-12T22:15:00-04:00",
  "location": {"@type": "Place", "name": "Main Stage"},
  "url": "https://example.com/madama-butterfly"
}
</script>
</head><body></body></html>
"""

LIST_AND_GRAPH_HTML = """
<html><head>
<script type="application/ld+json">
[
  {
    "@type": "MusicEvent",
    "name": "La Traviata",
    "startDate": "2026-10-01",
    "location": {"name": "Grand Hall"}
  },
  {
    "@type": "WebPage",
    "name": "Not an event, should be ignored"
  }
]
</script>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {"@type": "Event", "name": "Carmen", "startDate": "2026-11-05T20:00:00Z"}
  ]
}
</script>
</head></html>
"""

NO_EVENT_HTML = "<html><head></head><body>No structured data here.</body></html>"

MALFORMED_JSON_HTML = """
<html><head>
<script type="application/ld+json">
{ this is not valid json }
</script>
</head></html>
"""


def test_parses_single_event():
    performances = parse_jsonld_performances(
        SINGLE_EVENT_HTML, "Test Opera", "https://example.com/season"
    )
    assert len(performances) == 1
    p = performances[0]
    assert p.opera_house == "Test Opera"
    assert p.title == "Madama Butterfly"
    assert p.start_date == "2026-09-12T19:30:00-04:00"
    assert p.venue == "Main Stage"
    assert p.url == "https://example.com/madama-butterfly"


def test_parses_list_and_graph_and_ignores_non_events():
    performances = parse_jsonld_performances(
        LIST_AND_GRAPH_HTML, "Test Opera", "https://example.com/season"
    )
    titles = {p.title for p in performances}
    assert titles == {"La Traviata", "Carmen"}
    traviata = next(p for p in performances if p.title == "La Traviata")
    assert traviata.venue == "Grand Hall"
    # falls back to the page URL when the event has none of its own
    assert traviata.url == "https://example.com/season"


def test_no_structured_data_returns_empty_list():
    assert parse_jsonld_performances(NO_EVENT_HTML, "Test Opera", "https://x") == []


def test_malformed_json_is_skipped_without_raising():
    assert parse_jsonld_performances(MALFORMED_JSON_HTML, "Test Opera", "https://x") == []


def test_duplicate_events_are_deduplicated():
    html = SINGLE_EVENT_HTML + SINGLE_EVENT_HTML
    performances = parse_jsonld_performances(html, "Test Opera", "https://x")
    assert len(performances) == 1
