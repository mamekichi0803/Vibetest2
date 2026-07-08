"""Orchestrator: fetch every configured opera house, diff, and notify."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import yaml

from opera_schedule_tracker.models import Performance
from opera_schedule_tracker.notifier import send_update_email
from opera_schedule_tracker.sources import PARSERS
from opera_schedule_tracker.state import (
    diff_performances,
    filter_upcoming,
    load_state,
    save_state,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "opera_houses.yaml"
DEFAULT_STATE_PATH = REPO_ROOT / "data" / "state.json"


def load_opera_houses(config_path: Path) -> list[dict]:
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return data["opera_houses"]


def fetch_all(opera_houses: list[dict]) -> list[Performance]:
    all_performances: list[Performance] = []
    for house in opera_houses:
        extra = {k: v for k, v in house.items() if k not in ("name", "url", "parser")}
        name, url = house["name"], house["url"]
        parser_name = house.get("parser", "jsonld")
        fetch = PARSERS.get(parser_name)
        if fetch is None:
            logger.error("Unknown parser %r for %s; skipping.", parser_name, name)
            continue

        logger.info("Fetching %s (%s) via %r parser", name, url, parser_name)
        try:
            performances = fetch(name, url, **extra)
        except Exception:  # noqa: BLE001 - one bad source shouldn't kill the run
            logger.exception("Error fetching %s; skipping.", name)
            continue
        logger.info("  -> %d performance(s)", len(performances))
        all_performances.extend(performances)
    return all_performances


def run(
    config_path: Path = DEFAULT_CONFIG_PATH,
    state_path: Path = DEFAULT_STATE_PATH,
    recipient: str | None = None,
    dry_run: bool = False,
) -> None:
    opera_houses = load_opera_houses(config_path)
    current = filter_upcoming(fetch_all(opera_houses))
    previous = {p.key: p for p in filter_upcoming(load_state(state_path).values())}
    diff = diff_performances(previous, current)

    logger.info(
        "Diff: %d added, %d removed, %d changed",
        len(diff.added),
        len(diff.removed),
        len(diff.changed),
    )

    if dry_run:
        logger.info("Dry run: not sending email or saving state.")
        return

    send_update_email(diff, recipient=recipient)
    save_state(state_path, current)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--recipient", type=str, default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and diff but don't send email or persist state.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    run(
        config_path=args.config,
        state_path=args.state,
        recipient=args.recipient,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
