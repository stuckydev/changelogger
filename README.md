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

- App chips for filtering (preference stored in cookies)
- Compact feed with summaries, category badges, and a “more…” link
- Dark mode (default) + light mode
- Mobile-first layout with horizontally scrollable chips
- Server-side fetch/parse layer (no browser CORS issues)
- Background sync every 2 hours
- One latest changelog entry per app, shown as a uniform bullet list

## Quick start (local)

```bat
start_app.bat
```

Or manually:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
```

App: http://127.0.0.1:8080

## Docker

```bash
cp .env.example .env
docker compose up --build -d
```

Default port: `8080` (adjust via `.env`).

## Add a new app

Entry in `config/apps.yaml`:

```yaml
  - slug: my-app
    name: My App
    color: "#64748b"
    source_url: https://example.com/changelog
    parser: rss          # rss | todoist_html | notion_html | github_releases

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
  main.py                 FastAPI, startup sync, static mount
  config.py               loads config/apps.yaml
  constants.py            cookie names, paths
  models.py / crud.py     SQLite cache
  routers/                HTML + JSON API
  services/               fetch, parse, sync
  templates/              SSR + feed partial
  static/                 CSS, JS, favicon, logos
config/apps.yaml          app sources (manual)
data/                     SQLite volume
docker/                   Dockerfile, compose, entrypoint
```

## Logos

Official logos live in `app/static/logos/` and are resolved automatically (`png` → `ico` → `webp` → `svg`).

Refresh from official sources:

```bash
python scripts/fetch_logos.py
```

| App | Source |
|---|---|
| Todoist | [todoist.com apple-touch-icon](https://www.todoist.com/static/apple-touch-icon.png) |
| 1Password | [1password.com apple-touch-icon](https://1password.com/apple-touch-icon.png) |
| Notion | [notion.com logo-ios](https://www.notion.com/front-static/logo-ios.png) |
| Actual Budget | [actualbudget/actual favicon](https://github.com/actualbudget/actual) |
| WinUtil | [ChrisTitusTech GitHub avatar](https://github.com/ChrisTitusTech) |

Override per app in `config/apps.yaml` with `logo_url:` if needed.

## Tracked apps

- Todoist — HTML changelog (Help Center)
- 1Password (Windows) — RSS (`stable/index.xml`)
- Notion — HTML releases page
- Actual Budget — GitHub Releases (`actualbudget/actual`)
- WinUtil — GitHub Releases (`ChrisTitusTech/winutil`)

## Roadmap

- [x] Initial scaffold with 5 apps
- [x] Docker deployment
- [ ] Parsers for more formats
- [ ] Manual sync trigger (`POST /api/sync`)

## Deviations from APP_BLUEPRINT.md

Intentionally simplified:

- No PRG/flash, no soft-nav (single-page read app)
- No migrations/seed tables for user data
- English-only UI (no i18n layer)
- SQLite used only as changelog cache, not as a user DB
