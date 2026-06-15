# Changelogger v1.0

A lightweight web app that aggregates public changelogs for selected software and displays them as a compact timeline.

**Stack:** Python · FastAPI · Jinja2 · SQLite

## Features

- Unified feed with bullet highlights and source links
- Sidebar with mute, focus filter, and sync status
- Dark/light mode, responsive layout
- Server-side fetch and parse (RSS, HTML, GitHub Releases, and more)
- Background sync every full hour (Europe/Zurich)

## Quick start

```bat
start_app.bat
```

Or manually:

```bash
python -m venv .venv
.venv\Scripts\activate   # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 47173
```

Open http://127.0.0.1:47173

## Configuration

Apps are defined in `config/apps.yaml`:

```yaml
  - slug: my-app
    name: My App
    source_url: https://example.com/changelog
    parser: rss

  - slug: my-project
    name: My Project
    github_repo: owner/repo
    parser: github_releases
```

Parser types: `rss`, `github_releases`, `todoist_html`, `notion_html`, `capacities_html`, `cursor_html`, `microsoft_store_html`, `zendesk_articles`.

Restart the app after changes — sources sync on startup.
