from pathlib import Path

APP_PREFIX = "clg"
COOKIE_SELECTED_APPS = f"{APP_PREFIX}_selected_apps"
COOKIE_THEME = f"{APP_PREFIX}_theme"

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config" / "apps.yaml"
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "changelogger.db"

DEFAULT_THEME = "dark"
USER_AGENT = "Changelogger/1.0 (+https://github.com/changelogger)"
REFRESH_INTERVAL_SECONDS = 6 * 60 * 60  # 6 h
HTTP_TIMEOUT = 30.0
HIGHLIGHT_LIMIT = 5
HIGHLIGHT_MAX_CHARS = 180
ZENDESK_HIGHLIGHT_LIMIT = 18
ENTRIES_PER_APP = 2
