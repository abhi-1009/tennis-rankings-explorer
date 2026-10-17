"""Central configuration.

Values come from environment variables (.env locally) or, when deployed on
Streamlit Community Cloud, from the app's Secrets (st.secrets).
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _get(key: str, default: str = "") -> str:
    """Read a setting from the environment first, then from st.secrets if available."""
    value = os.getenv(key)
    if value not in (None, ""):
        return value
    try:
        import streamlit as st
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:  # noqa: BLE001  (no secrets file, or not running under Streamlit)
        pass
    return default


API_KEY = _get("SPORTRADAR_API_KEY")
ACCESS_LEVEL = _get("SPORTRADAR_ACCESS_LEVEL", "trial")
LANGUAGE = _get("SPORTRADAR_LANGUAGE", "en")
BASE_URL = f"https://api.sportradar.com/tennis/{ACCESS_LEVEL}/v3/{LANGUAGE}"

# Tennis v3 paths. Competitions and doubles rankings confirmed in SportRadar docs.
ENDPOINTS = {
    "competitions": "/competitions.json",
    "complexes": "/complexes.json",
    "doubles_rankings": "/double_competitors_rankings.json",
}

REQUEST_DELAY_SECONDS = 1.5   # trial keys are limited to about 1 request/second
MAX_RETRIES = 4
TIMEOUT_SECONDS = 30

RAW_DIR = PROJECT_ROOT / "data" / "raw"

# URL.create escapes special characters (@, :, /, #) in the password safely.
DB_URL = URL.create(
    drivername="mysql+pymysql",
    username=_get("DB_USER", "root"),
    password=_get("DB_PASSWORD", ""),
    host=_get("DB_HOST", "localhost"),
    port=int(_get("DB_PORT", "3306")),
    database=_get("DB_NAME", "tennis_db"),
)

# Cloud databases such as Aiven require SSL. Set DB_SSL_CA to the path of ca.pem
# (relative paths are resolved from the project root). Leave it empty for local MySQL.
_ca = _get("DB_SSL_CA")
if _ca and not Path(_ca).is_absolute():
    _ca = str(PROJECT_ROOT / _ca)
DB_CONNECT_ARGS = {"ssl": {"ca": _ca}} if _ca else {}
