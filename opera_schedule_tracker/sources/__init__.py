"""Schedule sources for individual opera houses.

``PARSERS`` maps the ``parser`` field in config/opera_houses.yaml to the
function that fetches + parses that house's schedule. Each function takes
``(opera_house: str, url: str, **extra_config)`` and returns a
``list[Performance]``.
"""

from opera_schedule_tracker.sources.generic_jsonld import fetch_jsonld_performances
from opera_schedule_tracker.sources.met_opera import fetch_met_opera_performances
from opera_schedule_tracker.sources.paris_opera import fetch_paris_opera_performances
from opera_schedule_tracker.sources.rbo import fetch_rbo_performances
from opera_schedule_tracker.sources.scala import fetch_scala_performances
from opera_schedule_tracker.sources.wiener_staatsoper import (
    fetch_wiener_staatsoper_performances,
)

PARSERS = {
    "jsonld": fetch_jsonld_performances,
    "scala": fetch_scala_performances,
    "wiener_staatsoper": fetch_wiener_staatsoper_performances,
    "rbo": fetch_rbo_performances,
    "paris_opera": fetch_paris_opera_performances,
    "met_opera": fetch_met_opera_performances,
}

__all__ = ["PARSERS", "fetch_jsonld_performances"]
