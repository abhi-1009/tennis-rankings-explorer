"""Step 1: download raw JSON for each dataset and save it to data/raw/.

Saving raw responses means you can re-run transform/load without hitting the API again.
Run from the project root:  python -m api.extract
"""
import json
import logging

from api import config
from api.sportradar_client import SportRadarError, fetch_json

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def save_raw(name: str, payload: dict) -> None:
    """Write a raw API payload to data/raw/<name>.json."""
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = config.RAW_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Saved %s", path)


def main() -> None:
    for name in config.ENDPOINTS:
        try:
            logger.info("Fetching %s ...", name)
            save_raw(name, fetch_json(name))
        except SportRadarError as exc:
            logger.error("Skipping %s: %s", name, exc)


if __name__ == "__main__":
    main()
