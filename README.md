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

Parser types: `rss`, `github_releases`, `todoist_html`, `notion_html`, `cursor_html`, `microsoft_store_html`, `zendesk_articles`.

Restart the app after changes — sources sync on startup.

## Deploy (Arcane)

Deploy on a host running [Arcane](https://getarcane.app) via Git Sync so pushes to `main` are picked up and redeployed automatically.

### One-time setup in Arcane

1. **GitOps** → add repository `https://github.com/stuckydev/changelogger.git` (PAT if private).
2. **Projects** → **Create Project** → **From Git Repo**:
   - Branch: `main`
   - Compose file: `compose.yml`
   - **Sync entire directory**: on (needs `Dockerfile`, `app/`, etc.)
   - **Auto Sync**: on (e.g. 5 min interval)
3. Open the project → set `.env` (not in git):

   ```env
   TZ=Europe/Berlin
   PORT=47173
   UID=1000
   GID=1000
   ```

   Use the host user's UID/GID for volume permissions (`id -u` / `id -g`).

4. **Build & Deploy** for the first run. Leave the project running — Arcane only auto-redeploys running projects.

`compose.yml` omits a pinned `image:` tag so Arcane rebuilds the image on each deploy after a git sync.

### Day-to-day

```text
edit → git commit → git push → Arcane syncs & redeploys (within the sync interval)
```

Use **Sync** on the project page to pull immediately instead of waiting for the poll.
