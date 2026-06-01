# App-Blueprint (Homelab / Einzelplatz-Web-Apps)

Referenz für neue Apps im Stil von **TMLNE**. In Cursor/Chats einfach diese Datei (oder eine Kopie im neuen Repo) nennen.

> **Abweichungen sind erwünscht**, wenn Idee, Skalierung oder Architektur es erfordern. Dieses Dokument beschreibt den **bevorzugten Default**, nicht ein starres Regelwerk — im Zweifel die bessere Lösung für die konkrete App wählen und hier nur das dokumentieren, was dauerhaft abweicht.

---

## Zielbild

| | |
|---|---|
| **Betrieb** | Einzelplatz, Homelab, Docker auf eigenem Server |
| **Nutzer** | Kein Login, kein Multi-Tenant, keine Cloud-Pflicht |
| **Daten** | Lokal persistent (`data/`), SQLite, Backup = Datei kopieren |
| **UI** | Server-rendered HTML, gezieltes Vanilla-JS (kein React/Vue), **hybride Navigation** (Soft-Nav + PRG) |
| **Sprache** | Deutsch + Englisch (UI); User-Inhalte (Namen, Titel) nicht übersetzen |
| **Feedback** | Erfolgs-Banner nach Mutationen; Bestätigung vor Destruktivem |

---

## Stack (Default)

- **Python 3.10+** (Docker: **3.12-slim**)
- **FastAPI** + **Uvicorn**
- **Jinja2** (SSR)
- **SQLAlchemy 2** + **SQLite** (`data/app.db`)
- **Pydantic** für Request-/Form-Validierung (`schemas.py`)
- Statisches CSS, **kein** Build-Step für Frontend
- **ReportLab** für PDF-Exporte in `services/` (optional je App)
- **python-multipart** für Form-Uploads

`requirements.txt`: obere Grenzen mit `<next-major`, z. B. `fastapi>=0.110,<1`.

---

## Projektstruktur

```text
app/
  main.py                 # FastAPI-App, Static mount, Router, /health, Startup
  constants.py            # Slugs, Cookie-Namen, Env-Defaults, geschützte IDs
  db.py                   # Engine, Session, get_db(), Composite-Indexes
  migrations.py           # SCHEMA_VERSION, schrittweise SQLite-Migrationen
  models.py               # SQLAlchemy-Tabellen
  schemas.py              # Pydantic Create/Update + Validatoren
  crud.py                 # DB-Zugriff, Seed, Activity-Log bei Mutations
  flash.py                # PRG-Erfolgsmeldungen (Query-Params → Banner)
  activity_changes.py     # Snapshots + Feld-Diffs für Reporting (optional)
  category_palette.py     # Theme-aware Farbpalette (optional)
  date_formats.py         # Locale-Datumsformate (dmY / iso)
  slugify.py              # Slug-Generierung für Views/Entitäten
  translations.py         # DE-Map, translate(), get_request_language()
  routers/
    pages.py              # Haupt-UI: HTML, Form-POST, JSON-Partial-APIs
    render.py             # Jinja-Setup, render_page(), Context, Form-Fehler
    trmnl.py              # E-Ink-Snapshot-Routen (optional)
  services/               # PDF, CSV, Domänenlogik, Import — ohne HTTP
    export_builders.py    # PDF/CSV-Export-Builder (von pages importiert)
  templates/
    base.html             # Layout + gesamtes Client-JS (~Soft-Nav, Modals, Banner)
    index.html            # Haupt-UI (Sidebar, Hauptinhalt, Modals, Settings)
  static/
    app.css               # Design-Tokens, Modals, Banner, Mobile-Regeln
    favicon.svg
data/                     # app.db (Git), README, .gitkeep; Docker-Volume
docker/
  Dockerfile, compose.yml, docker-entrypoint.sh, homelab.service.yml
compose.yml               # include → docker/compose.yml
.env.example              # TZ, Port, UID/GID, app-spezifische URLs
start_app.bat             # Windows-Dev: venv + uvicorn --reload
README.md                 # Schnellstart, Features, Struktur, Roadmap
LICENSE                   # Proprietary — siehe LICENSE
```

**Schichten:** Router → `render.py` → `crud` → `models` · schwere Logik in `services/`, nicht in Templates.

**Router-Wiring:** `main.py` bindet typisch einen `pages_router`. Export-Helfer leben in `services/export_builders.py` und werden von `pages.py` importiert — **kein** eigener HTTP-Router nötig. Zusätzliche Router (z. B. für öffentliche API oder Spezial-Ansichten) nur bei echtem Bedarf.

**Template-Muster:** Eine große `index.html` mit Feature-Flags (`form_mode`, `is_reporting`, …) statt vieler kleiner Seiten-Templates.

---

## Backend-Konventionen

### Startup (`main.py`)

1. `Base.metadata.create_all`
2. `run_migrations()` — versioniert, idempotent
3. `ensure_database_indexes()` — Composite-Indexes für häufige Filter
4. `seed_if_empty()` — nur bei leeren Tabellen

### HTTP & Rendering

- **`/health`:** DB-Ping → `{"status":"ok"}` (Docker-Healthcheck)
- **Router:** `APIRouter()` ohne Prefix; HTML via `response_class=HTMLResponse`; DB via `Depends(get_db)`
- **`routers/render.py`:** Jinja-Env, `render_page()` / `render_from_slug()`, Template-Globals (`t`, `static_asset_version`), Theme/Sprache/Sort aus Cookies
- **Konstanten & Cookies:** zentral in `constants.py`, Präfix `{app}_` (z. B. `tmlne_theme`, `tmlne_language`)
- **Geschützte Entitäten:** `frozenset` für System-Slugs; ggf. dynamisch aus DB ergänzen (z. B. Kategorie-Tabs)

### Mutationen — wann welches Muster?

| Muster | Wann | Beispiel |
|--------|------|----------|
| **PRG + Flash** | Form-POST, Redirect, Erfolgs-Banner | Line erstellen, archivieren, View löschen |
| **Re-Render + Kontext** | Validierungsfehler oder spezieller Report | Form-Fehler im Modal; CSV-Import mit `import_report` |
| **JSON Partial API** | Inline-Interaktion ohne Seitenwechsel | Timeline-Drag (Daten ändern), Settings-Cookies |
| **Soft-Submit (Fetch)** | PRG-Erfolg, aber ohne Full-Reload | Line-Create-Modal: `fetch` + Redirect folgen + DOM-Patch |
| **Soft-Nav (Fetch GET)** | View-Wechsel, Sortierung | Sidebar-Links, Sort-Select |

**PRG:** `RedirectResponse(status_code=303)` nach erfolgreichem Form-POST.

**Validierung:** Pydantic in `schemas.py`; Form-Fehler in Router normalisieren (`normalize_*_form_errors`) und per `render_from_slug(..., form_errors=…)` zurück ins Template.

**Activity-Log:** bei Create/Update/Delete; Updates mit Feld-Diff in `changes_json` für Reporting (`activity_changes.py`).

**Kein** separates Repository-Layer, solange `crud.py` überschaubar bleibt.

---

## Flash & Feedback (`flash.py`)

Erfolgsmeldungen nach Mutationen — **kein** Session-Flash, **kein** Toast-Framework.

### Server-seitig (PRG)

```python
# flash.py
redirect_with_flash(url, "line_created", name="Meine Line")
# → /view/admin?flash=line_created&flash_name=Meine+Line

resolve_flash_message(request, translate)  # in render_page()
```

- Action-Keys als Enum (`FLASH_ACTIONS`) + Übersetzungs-Keys in `translations.py`
- Platzhalter `{name}` für User-Inhalte (nicht übersetzt)
- Banner wird in `render_page()` als `flash_message` ans Template übergeben

### Client-seitig

- **Action-Banner:** kompaktes Overlay, zentriert im Header (`.main-content-header`), grünes Häkchen, Auto-Dismiss nach ~4 s
- **`showActionBanner(message)`** — für JSON-Mutationen (z. B. Timeline-Drag); Server liefert `flash_message` im JSON-Body
- **Import-Report:** separates `.import-report`-Banner (kein Flash) bei CSV-Import
- Flash-Query-Params werden nach Anzeige per `history.replaceState` entfernt

### Wichtig bei Soft-Nav

Hidden Fields (`return_slug`, Kategorie-Default im Modal) müssen beim View-Wechsel **clientseitig synchronisiert** werden — sonst landet PRG/Flash im falschen View. JSON-Mappings (z. B. `#category-by-slug`) in `<script type="application/json">`, **nicht** in HTML-Attributen mit Anführungszeichen.

---

## Soft-Navigation & DOM-Patch

Sidebar-Links werden abgefangen; statt Full-Reload:

1. `fetch(url, { headers: { "X-Requested-With": "fetch" } })`
2. `DOMParser` → gezielter Tausch:
   - `.timeline-canvas` / `.timeline-card`
   - `.sidebar-nav`
   - `.main-content-header` (Mobile-Titel + Desktop-Toolbar)
   - Status-Banner (`.action-banner-slot`, `.import-report`)
3. `history.pushState` / `popstate` → gleicher Mechanismus
4. Fallback: `window.location.assign` bei Fehler

Nach jedem Patch: UI-Helfer neu binden (`reinitializeTimelineUi()` — Sort, Drag, Modals, Banner, …).

Optional: `document.startViewTransition()` für Timeline-Patches.

**Soft-Submit** (nur wo sinnvoll): Form per `fetch` + `redirect: "follow"`; bei Validierungsfehler Modal offen lassen (`data-autoshow="true"`); bei Erfolg `applyTimelinePage(doc)`.

---

## Frontend & UX

### Grundlagen

- **Ein** Haupt-Stylesheet (`app.css`) mit **CSS-Variablen**; Light/Dark via `html[data-theme="dark"]`
- **Default Dark Mode**; Theme in `localStorage` + Cookie (Head-Script synchronisiert LS → Cookie vor Paint)
- **Schrift:** Inter (Google Fonts); Icons: Material Symbols Outlined
- **Breakpoint ~768px:** Desktop-Sidebar (einklappbar) vs. Mobile-Burger-Drawer
- **Cache-Bust:** Static `?v=` aus Datei-`mtime` (`static_asset_version`)

### Layout

- **`main-content-header`:** Mobile-Header + Desktop-Toolbar in einem Container; Action-Banner als **Overlay** (`position: absolute; inset: 0`), verschiebt Inhalt nicht
- **`index.html`:** Sidebar, Timeline, Modals, Settings — alles in einer Seite

### Modals & Formulare

- **`<dialog>`** für Create/Edit (Lines, Views, Kategorien, Import)
- **`data-required-form`** — Save-Button erst bei gültigen Pflichtfeldern aktiv
- **`data-dirty-form`** — Warnung beim Schließen ungespeicherter Änderungen (`shakeDialog`)
- **Custom Selects:** `[data-category-select]`, `[data-category-color-select]` — kein natives `<select>` für Kategorien/Farben
- **Bestätigungs-Popover** (`data-confirm-target`) vor Löschen/Archivieren/Clear
- **Feldtitel einheitlich:** In Line-/View-Modals (`modal-form-inner`, `line-detail-form`) alle sichtbaren Label gleich stylen — **kein** `text-transform: uppercase` (normale Schreibweise wie „Category“, „Notes“). Das globale `label { text-transform: uppercase }` gilt nur außerhalb dieser Modals; neue Modal-Felder (z. B. `textarea`) in dieselbe Ausnahme-Regel aufnehmen wie Select/Grid-Labels (`text-transform: none`, 12px, `font-weight: 600`, `color: var(--muted)`).

### Desktop vs. Mobile (Timeline)

| | Desktop (>768px) | Mobile (≤768px) |
|--|------------------|-----------------|
| Timeline | Drag End-Datum + Bar verschieben (JSON-API) | Read-only |
| Bearbeiten | Klick auf Bar → Edit-Modal | Tap → Edit-Modal |
| Sidebar | Einklappbar, dynamische Breite | Burger-Drawer |

### Einstellungen (Zahnrad)

Rubriken: Allgemein, Lokalisierung, Sidebar-Sichtbarkeit, domänenspezifische Bereiche (z. B. Timeline).  
Sprache/Format: `POST` → JSON + Cookie → Fetch-Refresh der Seite (ohne Full-Reload der gesamten App-Shell wo möglich).

---

## Cookie vs. localStorage

**Regel:** Alles, was **SSR** braucht (Theme, Sprache, Sort, Startseite) → **Cookie** (`{app}_*`, `SameSite=Lax`, 1 Jahr).  
Reine Client-UI (Sidebar collapsed, Bar-Höhe, Panel-Zustände) → **localStorage**.

| Concern | Cookie | localStorage | SSR-relevant |
|---------|--------|--------------|--------------|
| Theme | `{app}_theme` | `{app}-theme` | ja (Head-Sync) |
| Sprache | `{app}_language` | — | ja |
| Datumsformat | `{app}_date_format` | `{app}-date-format` | ja |
| Startseite | `{app}_start_page` | `{app}-start-page` | ja (`/` → Home-View) |
| Sortierung | `{app}_*_sort` | `{app}-*-sort` | ja |
| Sidebar-Sections | — | `{app}-sidebar-visible` | nein |
| Sidebar collapsed | — | `sidebar-collapsed` | nein |
| UI-only Prefs | — | `{app}-*` | nein |

Head-Bootstrap in `base.html`: kritische localStorage-Werte vor erstem Paint in Cookies spiegeln.

---

## Internationalisierung

- `translations.py`: `TRANSLATIONS["de"]` — **Englisch ist Quellsprache** (Keys auf Englisch)
- `translate(key, language, **kwargs)`; Template: `{{ t('Settings') }}`
- `get_request_language(request)` aus **Cookie** (`{app}_language`)
- **User-generierte Namen** (Lines, Views, Kategorien) nicht übersetzen — nur UI-Chrome
- Datumsformat: `date_formats.py`, Cookie + Anzeige-Helfer; Sprachwechsel kann Default-Format mitsetzen

Flash-Messages und Action-Banner nutzen dieselben Übersetzungs-Keys.

---

## Datenbank & Migrationen

- SQLite unter `data/app.db`; `DATA_DIR.mkdir(exist_ok=True)` in `db.py`
- `create_all` beim Start **plus** versionierte Migrationen in `migrations.py`
- Tabelle `schema_version`; `SCHEMA_VERSION` monoton erhöhen ab v1-Baseline (**0** = kein offenes Upgrade)
- Jede Migration: idempotent (`PRAGMA table_info`, `IF NOT EXISTS`)
- **Composite-Indexes** für häufige Filter (z. B. `archived + start_date + end_date`)
- **Seed** nur bei leeren Tabellen: Beispieldaten + Standard-Views/Kategorien
- **Backup vor Upgrade:** `cp data/app.db data/app.db.bak`

Pre-v1-Upgrade-Schritte sind entfernt; Schema steht in `models.py` + `ensure_database_indexes()`. Neue Schritte nur noch in `MIGRATIONS` nach v1.

---

## Kategorien & Farben (optional)

- **Speicherung:** Hex-Farbe pro Kategorie in DB (light-Variante als Kanon)
- **Anzeige:** theme-aware via `category_palette.py` (`resolve_category_colors`, `display_category_color`)
- **Migrationen:** bei Palette-Wechsel alte Hex-Werte normalisieren/mappen
- Jede Kategorie kann automatisch eine **geschützte View** (Tab) bekommen — Slug aus Kategoriename

---

## Docker & Homelab

- Build-Kontext = **Repo-Root**; `docker/Dockerfile` kopiert `app/` + `requirements.txt`
- **Non-root:** `user: "${UID:-1000}:${GID:-1000}"`, Volume `./data:/app/data`
- Root-`compose.yml` → `include: docker/compose.yml`; Port/TZ per `.env`
- **Healthcheck** gegen `/health`; `restart: unless-stopped`, `init: true`
- **`docker/docker-entrypoint.sh`:** `mkdir -p /app/data`
- **`docker/homelab.service.yml`:** Snippet für zentrales Homelab-Compose (Reverse Proxy → interner Service)

**Linux permissions:** `sudo chown -R "$(id -u):$(id -g)" data` oder `UID`/`GID` in Compose.

---

## Dokumentation & Repo-Hygiene

- **README:** Kurzbeschreibung, Stack-Tabelle, Docker + lokaler Start, Feature-Übersicht, Datenpfade, Strukturbaum, Roadmap (erledigt / offen), **aktuelle SCHEMA_VERSION**
- **APP_BLUEPRINT.md:** dieses Dokument — bei größeren Architektur-Änderungen mitziehen
- **`.env.example`** kommentiert, keine Secrets im Repo
- **`data/app.db`** in Git versionieren (Geräte-Sync); `data/README.md` mit Pull/Push-Workflow; `*.bak` und andere `*.db` ignorieren
- Lizenz **proprietary** (Copyright stuckydev, All rights reserved); keine Nutzung/Kopie/Verbreitung ohne schriftliche Erlaubnis — siehe [LICENSE](LICENSE)
- `.gitattributes` bei Bedarf (Line Endings)

---

## Bewusst weggelassen (bis explizit gebraucht)

- Authentifizierung / Mehrbenutzer
- SPA (React, Vue, SvelteKit)
- PostgreSQL / Redis (erst bei echtem Bedarf)
- Session-Flash / Redis-Queue / Celery
- CI/CD-Pflicht (optional später)
- Übermäßige Abstraktion (Services pro Zeile, generische Base-Classes)
- Toast-Library / UI-Framework

---

## Checkliste: Neue App starten

1. Repo von Struktur oben ableiten; App-Namen in Cookies/Env **konsistent prefixen** (`{app}_*`).
2. `models` + `schemas` + `crud` + `flash.py` + erste `pages`-Route + `base.html`/`index.html`/`app.css`.
3. `migrations.py` mit `SCHEMA_VERSION = 0` (Baseline); Seed definieren; Indexes in `db.py`.
4. `/health`, Docker-Compose, `.env.example`, README-Schnellstart.
5. Dark Mode + DE/EN von Anfang an; `translations.py` + `date_formats.py`.
6. **Feedback:** `flash.py` + Action-Banner-Overlay im Header; Bestätigungs-Popover für Deletes.
7. **Soft-Nav** erst einplanen, wenn mehrere Views/Tabs existieren — DOM-Patch-Vertrag (`main.content`, `.timeline-canvas`, `.sidebar-nav`, `.main-content-header`) von Anfang an stabil halten.
8. Hidden Form-Felder (`return_slug`, Defaults) bei Client-Navigation synchron halten.
9. Bei Abweichung: kurz in Projekt-README oder Kopf dieses Blueprints vermerken.

---

*Stand: abgeleitet von TMLNE (FastAPI, Homelab, SCHEMA_VERSION 0 Baseline, Soft-Nav, Flash-Banner). Projekt-spezifische Extras (z. B. Hardware-Displays) gehören ins jeweilige README, nicht in diesen Blueprint.*
