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
- Compact feed with summaries and a “more…” link
- Dark mode (default) + light mode
- Mobile drawer sidebar, desktop persistent sidebar
- Server-side fetch/parse layer (no browser CORS issues)
- Background sync every 6 hours
- Two most recent changelog entries per app, shown as a uniform bullet list

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
    color: "#64748b"
    source_url: https://example.com/changelog
    parser: rss          # rss | todoist_html | notion_html | github_releases | capacities_html

  # GitHub Releases (Atom feed):
  - slug: my-project
    name: My Project
    color: "#64748b"
    github_repo: owner/repo
    parser: github_releases
```

Restart the container or reload the app — the server syncs all sources on startup.

## Project structure

```text
app/
  main.py                     FastAPI app, lifespan sync, static mount
  core/                       config, constants, db, models, migrations, dates
  domain/                     changelog types/rules, user preferences
  infra/                      HTTP client, logo thumbnails
  repositories/               SQLite access
  parsers/                    source-specific parsers
  services/                   ingest, sync, summarize, release enrichment
  web/
    routes/                   pages, API, health
    render.py                 Jinja setup + feed view models
    highlight.py              MTG Arena term highlighting
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
