# Changelogger

A lightweight web app that aggregates public changelogs for selected software products and displays them as a compact timeline.

## Stack

| Area | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Frontend | Jinja2 (SSR), Vanilla JS, CSS |
| Cache | SQLite (`data/changelogger.db`) |
| Configuration | `config/apps.yaml` |
| Deployment | Docker Compose |

## Features

- Sidebar app list with mute + temporary focus filter
- Compact feed with bullet highlights and a „mehr…" link
- Dark mode (default) + light mode
- Mobile drawer sidebar, desktop persistent sidebar
- Sync error indicator per app in the sidebar
- Server-side fetch/parse layer (no browser CORS issues)
- Background sync every 6 hours
- Two most recent changelog entries per app

## Quick start (local)

```bat
start_app.bat
```

Or manually:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 47173
```

App: http://127.0.0.1:47173

## Docker

```bash
cp .env.example .env
docker compose up --build -d
```

Default port: `47173` (adjust via `.env`).

## Add a new app

Entry in `config/apps.yaml`:

```yaml
  - slug: my-app
    name: My App
    source_url: https://example.com/changelog
    parser: rss

  # GitHub Releases (Atom feed):
  - slug: my-project
    name: My Project
    github_repo: owner/repo
    parser: github_releases
```

Parser types: `rss`, `todoist_html`, `notion_html`, `github_releases`, `capacities_html`, `cursor_html`, `microsoft_store_html`, `zendesk_articles`.

Restart the container or reload the app — the server syncs all sources on startup.

## Project structure

```text
app/
  bootstrap.py                FastAPI factory, lifespan, sync loop
  main.py                     Uvicorn entry (re-exports bootstrap.app)
  settings.py                 paths, cookies, sync limits
  catalog/                    apps.yaml loader (AppConfig)
  models/                     shared domain types (ParsedEntry)
  storage/                    SQLite db, ORM, migrations, repositories
  ingestion/                  fetch, parse, normalize, sync, parsers
  presentation/               routes, view models, Jinja, feed context
  user_prefs/                 cookie-based mute + theme prefs
  infra/                      HTTP client, logo thumbnails
  utils/                      date parsing and display helpers
  templates/                  SSR + feed partial
  static/                     CSS, JS, favicon, logos
config/apps.yaml              app sources
data/                         SQLite volume
docker/                       Dockerfile, compose, entrypoint
scripts/fetch_logos.py        refresh logos from official sources
```

## Logos

Official logos live in `app/static/logos/` and are resolved automatically (`png` → `ico` → `webp` → `svg`).

Refresh from official sources:

```bash
python scripts/fetch_logos.py
```

Override per app in `config/apps.yaml` with `logo_url:` if needed.

## Tracked apps

Configured in `config/apps.yaml` (currently 11 apps across SaaS, self-hosted, games, and utilities).
