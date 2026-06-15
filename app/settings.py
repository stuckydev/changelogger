from pathlib import Path

APP_PREFIX = "clg"
COOKIE_MUTED_APPS = f"{APP_PREFIX}_muted_apps"
COOKIE_THEME = f"{APP_PREFIX}_theme"

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config" / "apps.yaml"
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "changelogger.db"
STATIC_DIR = ROOT_DIR / "app" / "static"
TEMPLATES_DIR = ROOT_DIR / "app" / "templates"

DEFAULT_THEME = "dark"
USER_AGENT = "Changelogger/1.0 (+https://github.com/changelogger)"
HTTP_TIMEOUT = 30.0
HIGHLIGHT_LIMIT = 5
HIGHLIGHT_MAX_CHARS = 180
ZENDESK_HIGHLIGHT_LIMIT = 18
ENTRIES_PER_APP = 2
