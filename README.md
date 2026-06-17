# PM Tracker

> **Current version: `0.21`**
> Update this badge and the [Version History](#version-history) section with every release.

A self-hosted, dark-themed project management application built with **Python + NiceGUI + FastAPI + SQLite**. It provides a Kanban board with drag-and-drop columns, per-client card identifiers, threaded comments, column-transition history tracking, user profiles with avatars and color coding, and an admin control panel for users and clients.

---

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Project Structure](#project-structure)
3. [Installation](#installation)
4. [Running the App](#running-the-app)
5. [Database Schema](#database-schema)
6. [Architecture & Key Decisions](#architecture--key-decisions)
7. [Feature Reference](#feature-reference)
8. [Design System (theme.py)](#design-system-themepy)
9. [API / Route Map](#api--route-map)
10. [Development Guidelines](#development-guidelines)
11. [Known Constraints & NiceGUI Gotchas](#known-constraints--nicegui-gotchas)
12. [Version History](#version-history)

---

## Tech Stack

| Layer | Library | Pinned Version |
|---|---|---|
| UI framework | NiceGUI | 3.13.0 |
| Web server | FastAPI | 0.137.1 |
| ASGI server | Uvicorn | 0.49.0 |
| Database | SQLite (stdlib) | — |
| Python | CPython | 3.12+ |
| Fonts | Inter + JetBrains Mono | Google Fonts CDN |
| Icons | Material Icons | NiceGUI bundled |

Full pinned dependency list is in `requirements.txt`.

---

## Project Structure

```
pm_app/
├── main.py                  # App entry point, routes, static file mounts, port 3120
├── database.py              # All SQLite schema, migrations, and CRUD functions
├── auth.py                  # Session auth helpers (NiceGUI storage-based)
├── theme.py                 # Dark design system: palette constants + GLOBAL_CSS injector
├── version.py               # Single source of truth: __version__ = "0.21"
├── requirements.txt         # Pinned dependencies
│
├── pages/
│   ├── login.py             # Full-screen dark login page with SVG background
│   ├── layout.py            # Shared dark header with logo, burger menu, page wrapper
│   ├── board.py             # Kanban board + card dialog + comments + history (largest file)
│   ├── users.py             # Admin-only user management (create/edit/delete/assign clients)
│   ├── clients.py           # Admin-only client management (name/color/assignments)
│   └── profile.py           # Per-user profile: avatar upload, color picker, change password
│
├── static/
│   ├── logo_white.svg       # App logo (served at /static/logo_white.svg)
│   └── login_bg.svg         # Gantt+Kanban hybrid dark background for login page
│
└── uploads/                 # Runtime upload storage (created automatically)
    ├── avatars/<user_id>/   # User avatar images
    └── <card_id>/           # Card file attachments
```

---

## Installation

```bash
# Clone the repo
git clone <repo-url> pm_app
cd pm_app

# Create a virtual environment (strongly recommended)
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install pinned dependencies
pip install -r requirements.txt
```

> **Python 3.12 is required.** The app has not been tested on 3.11 or earlier.

---

## Running the App

```bash
python main.py
```

The app starts on **port 3120** at `http://localhost:3120`.

**Default admin credentials** (created automatically on first run if no users exist):
- Username: `admin`
- Password: `1234`

> Change the admin password immediately via **Menu → Profile → Change Password**.

### Production notes

- Change `storage_secret` in `main.py` before deploying.
- Run behind a reverse proxy (nginx/Caddy) for HTTPS.
- The `uploads/` directory must be writable by the process user.
- SQLite database file `pm_app.db` is created in the project root on first run.

---

## Database Schema

All tables are created and migrated by `database.init_db()` on startup. Migrations use `PRAGMA table_info` + `ALTER TABLE` so they are safe to run on existing databases.

### Tables

#### `users`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `username` | TEXT UNIQUE | Login name |
| `password_hash` | TEXT | SHA-256 hex digest |
| `full_name` | TEXT | Display name |
| `is_admin` | INTEGER | 0 or 1 |
| `avatar_path` | TEXT | Absolute path to uploaded avatar file (migration-added) |
| `color` | TEXT | Hex color `#rrggbb`, must be unique per user (migration-added) |
| `created_at` | TEXT | ISO datetime |

#### `clients`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT UNIQUE | |
| `description` | TEXT | |
| `color` | TEXT | Hex color for client badge |
| `created_at` | TEXT | |

#### `user_clients`
Junction table. `user_id` ↔ `client_id`. Non-admin users see only cards belonging to their assigned clients.

#### `cards`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `card_type` | TEXT | `'Epic'`, `'Story'`, or `'Bug'` |
| `title` | TEXT | |
| `description` | TEXT | HTML (from `ui.editor`) |
| `assignee` | TEXT | `full_name` or `username` of assigned user |
| `expected_delivery` | TEXT | ISO date string |
| `column_name` | TEXT | One of the 5 Kanban columns |
| `position` | INTEGER | Zero-based order within column |
| `client_id` | INTEGER FK → clients | Migration-added |
| `card_number` | TEXT | e.g. `ACM-0001` — first 3 chars of client name + sequential number (migration-added) |
| `created_at` | TEXT | |
| `updated_at` | TEXT | |

#### `epic_links`
Junction: `epic_id` ↔ `story_id`. Links Story/Bug cards to an Epic card.

#### `attachments`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `card_id` | INTEGER FK | Cascades on card delete |
| `filename` | TEXT | Original filename |
| `stored_path` | TEXT | Absolute path on disk |
| `uploaded_at` | TEXT | |

#### `client_card_counter`
| Column | Type | Notes |
|---|---|---|
| `client_id` | INTEGER PK FK | |
| `last_number` | INTEGER | Last assigned sequential number for this client |

Used by `_generate_card_number()` which atomically increments within the same transaction as card creation.

#### `card_comments`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `card_id` | INTEGER FK | Cascades on card delete |
| `parent_id` | INTEGER FK → card_comments | `NULL` = top-level comment; non-null = threaded reply |
| `author_user_id` | INTEGER FK → users | |
| `content` | TEXT | HTML (from `ui.editor`) |
| `created_at` | TEXT | ISO datetime |

#### `card_history`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `card_id` | INTEGER FK | Cascades on card delete |
| `from_column` | TEXT | `NULL` means "card was created here" |
| `to_column` | TEXT | Destination column |
| `user_id` | INTEGER FK → users | Who performed the action |
| `epoch` | INTEGER | Unix timestamp (seconds) |

---

## Architecture & Key Decisions

### Auth
`auth.py` uses NiceGUI's `app.storage.user` (server-side per-session dict). `login()` writes a dict with `user_id`, `username`, `full_name`, `is_admin`. `current_user()` reads it. No JWTs or cookies managed manually.

### Routing
All routes are NiceGUI `@ui.page()` decorators in `main.py`. Every page function immediately calls the corresponding `_page()` function from `pages/`. Each page checks `auth.is_authenticated()` and redirects to `/` if not logged in.

### Static files
- `app.add_static_files("/uploads", db.UPLOAD_DIR)` — card attachments and avatars
- `app.add_static_files("/static", os.path.join(_BASE_DIR, "static"))` — logo and login background SVG

Paths use `os.path.dirname(os.path.abspath(__file__))` to be deployment-location agnostic.

### Kanban board
- 5 columns: `Backlog`, `Committed`, `In progress`, `In testing`, `Done` — defined in `database.COLUMNS`.
- Cards rendered via `ui.sortable` with `group="kanban"` so cards can be dragged across columns.
- `card_list.props(f"data-column='{col_name}'")`  stores column identity on the DOM element.
- In `on_end`, `e.target._props.get("data-column")` retrieves the destination column.
- Reordering within the same column does **not** write a history event; only column changes do.
- The board re-renders fully on every `refresh_board()` call (stateless render from DB).

### Card identifier format
`{CLIENT_PREFIX}-{NNNN}` where:
- `CLIENT_PREFIX` = first 3 characters of the client name, uppercased (e.g. `Acme Corp` → `ACM`)
- `NNNN` = zero-padded 4-digit integer, sequential **per client**, starting at `0001`
- Generated atomically inside `_generate_card_number()` within the same DB transaction as `INSERT INTO cards`
- A card without a client has no `card_number` (`NULL`); one is assigned automatically when a client is later set via `update_card()`

### Card dialog
- New card: narrow dialog (`w-[600px]`), no right panel.
- Existing card: wide two-column dialog (`w-[1160px]`):
  - **Left panel** (560px, scrollable): card type (locked after creation), title, client, rich-text description, assignee, delivery date, attachments, Epic links.
  - **Right panel** (flex-grow): Comments / History tabs using `@ui.refreshable`.

### `@ui.refreshable` pattern (critical)
Inside NiceGUI dialogs, `element.clear()` + `with element:` **does not reliably update the client DOM**. The only correct pattern for dynamic content inside a dialog is `@ui.refreshable` + `.refresh()`. This is used for the Comments/History tab panel in `board.py`.

### History tracking
- `create_card()` inserts `(NULL → column_name)` history row atomically.
- `move_card()` inserts `(old_column → new_column)` only when the column actually changes.
- Timestamps stored as Unix epoch integers; converted to browser local time via `ui.run_javascript()` on render using `new Date(epoch * 1000).toLocaleString()`.
- **Do not use `<script>` tags inside `ui.html()`** — NiceGUI sanitizes them and causes the enclosing loop to produce only 1 rendered item.

### User color system
Each user can pick a unique hex color in their Profile. This color is used:
1. As the fill of the colored dot next to the assignee name on kanban cards.
2. As the fill of the initials circle avatar when no photo is uploaded.
3. As the dot color on history timeline entries.
`is_color_taken()` accepts `exclude_user_id` so users can re-save their existing color.

### Admin vs non-admin
- Admins see all clients' cards on the board.
- Non-admins see only cards belonging to their assigned clients (`user_clients` table).
- Admin-only features: User management page, Client management page, avatar filter strip on board.
- The avatar filter strip (between the page title and columns) allows admins to filter the board by a single assignee. It acts as a radio button — click to select, click again to deselect.

---

## Feature Reference

### Login page (`/`)
- Full-screen dark background: `static/login_bg.svg` (Gantt chart left half, Kanban board right half).
- Frosted-glass login card, right-aligned.
- Branding: logo, "PM Tracker" in JetBrains Mono, "PROJECT MANAGEMENT" letterspaced subtitle.
- Password toggle via NiceGUI's `password_toggle_button=True`.
- SIGN IN button: `ui.button(...).props("no-caps unelevated")` with `.sign-in-btn` CSS class forcing white text.
- Enter key on password field triggers login.

### Kanban Board (`/board`)
- 5 drag-and-drop columns.
- **NEW CARD** button (top-right).
- Admin-only avatar filter strip between heading and columns.
- Each card shows: type icon, type badge, card identifier (`ACM-0001`), client badge, title, assignee dot + name (for Story/Bug), delivery date if set.
- Click card → opens edit dialog.
- Card types: `Epic` (purple), `Story` (blue), `Bug` (red).

### Card Dialog
- **Edit Card** with card number pill in title (`ACM-0001` — white text, dark blue background, blue border).
- Left panel: all editable fields.
- Right panel: **Comments** and **History** tabs.
  - **Comments**: threaded replies (↩ Reply), rich-text composer (`ui.editor`), delete own/admin.
  - **History**: vertical timeline, each entry shows user dot (profile color), action text, local timestamp.
- Attachments: upload any file type; stored under `uploads/<card_id>/`.
- Epic linking: Stories/Bugs can be linked to Epics; jump to linked cards via hyperlink.

### Profile (`/profile`)
Three panels side-by-side:
1. **Avatar** — upload image (jpg/png/gif/webp), stored at `uploads/avatars/<user_id>/avatar.<ext>`. Falls back to initials circle in user color.
2. **My Color** — hex color picker, uniqueness enforced. Used across the app to identify the user.
3. **Change Password** — current password verification, minimum 4 characters.

### Users (`/users`) — admin only
- Table of all users with color swatches.
- Add / Edit / Delete users.
- Assign users to one or more clients.
- Password set on create; optional on edit.

### Clients (`/clients`) — admin only
- Table of all clients with color swatches.
- Add / Edit / Delete clients.
- Color picker for client badge color (used on cards).

---

## Design System (theme.py)

`theme.apply_theme()` must be called once per page. It injects:
1. Google Fonts link (Inter + JetBrains Mono).
2. `GLOBAL_CSS` — a single minified CSS string covering all Quasar components.

### Palette constants

```python
BG         = "#0d1117"   # Page background
SURFACE    = "#161b22"   # Cards, header, panels
SURFACE2   = "#21262d"   # Inputs, editor, menus
BORDER     = "#30363d"   # All borders
ACCENT     = "#2563eb"   # Blue — primary buttons, active tabs, links
TEXT       = "#e6edf3"   # Primary text
TEXT_MUTED = "#8b949e"   # Secondary/placeholder text
SUCCESS    = "#3fb950"   # Green
DANGER     = "#f85149"   # Red — errors, delete actions
INFO       = "#58a6ff"   # Light blue — links, reply indicators
```

### Critical font rule
The `*` selector **must not** be used for `font-family` overrides because it overwrites the Material Icons ligature font, causing icon names (e.g. `menu`, `bookmark`, `visibility_off`) to render as raw text. The theme scopes Inter to explicit element types and explicitly protects `.material-icons` and `.q-icon`.

### CSS classes
| Class | Applied to | Effect |
|---|---|---|
| `.kanban-col` | Column container | Dark surface + border + rounded corners |
| `.kanban-card` | Card element | Darker surface + hover accent border glow |
| `.sign-in-btn` | Login button | Forces white text via `.q-btn__content` |

---

## API / Route Map

| Route | Page Function | Access |
|---|---|---|
| `GET /` | `login_page()` | Public (redirects if authed) |
| `GET /board` | `board_page()` | Authenticated |
| `GET /users` | `users_page()` | Admin only |
| `GET /clients` | `clients_page()` | Admin only |
| `GET /profile` | `profile_page()` | Authenticated |
| `GET /uploads/*` | Static files | Authenticated (NiceGUI serves) |
| `GET /static/*` | Static files | Public (logo, login bg) |

All routes are NiceGUI `@ui.page()` decorators — no REST API, no JSON endpoints. All data access is synchronous SQLite via `database.py`.

---

## Development Guidelines

These rules must be followed when extending or modifying the app.

### 1. File delivery
When modifying the app, deliver **only the files that changed**. Do not re-deliver unchanged files.

### 2. Version bumping
- Every revision increments the **minor** version by 1 (e.g. `0.21` → `0.22`).
- On explicit request to bump major, increment major and reset minor to 0 (e.g. `1.0`).
- Update `version.py` and the version badge at the top of this README on every release.

### 3. Dark theme
- All inline styles must use hex values from `theme.py` constants, not Tailwind light-mode classes (e.g. `text-gray-500`).
- When a Tailwind class is unavoidable, chain `.style(f"color:{theme.TEXT_MUTED}")` instead.
- Never use `.classes("text-gray-*")`, `.classes("bg-white")`, or similar light-mode classes.

### 4. NiceGUI dialog content — use `@ui.refreshable`
Dynamic content inside a dialog that needs to change after page load **must** use `@ui.refreshable`. Using `element.clear()` + `with element:` inside a callback does not reliably update the client DOM in NiceGUI 3.x dialogs.

### 5. No `<script>` tags in `ui.html()`
NiceGUI sanitizes `<script>` tags from `ui.html()`. Using them causes the enclosing rendering loop to silently produce only 1 DOM element. For JavaScript execution after render, use `ui.run_javascript()`.

### 6. Icon font protection
Never set `font-family` on `*` or on `.q-icon` / `.material-icons` — this breaks Material Icons rendering (icon names render as text). Always scope font overrides to specific element types.

### 7. Kanban drag-and-drop
- Column identity is stored via `.props(f"data-column='{col_name}'")`  → accessible as `element._props.get("data-column")`.
- `e.target` in `on_end` is the **destination** container (mapped from `evt.to` in SortableJS). It correctly holds `data-column` of the drop target.
- Always pass `user_id` to `move_card()` so history is recorded.

### 8. History recording
- Card creation: `create_card(..., user_id=uid)` records `(NULL → column)`.
- Card move: `move_card(card_id, new_column, new_pos, user_id=uid)` records `(old → new)` only on column change.
- Reordering within the same column does NOT record history.

### 9. Database migrations
Add new columns via `ALTER TABLE` inside `init_db()` protected by a `PRAGMA table_info` check. Never drop columns. All migrations must be idempotent.

### 10. Auth pattern
Always check `auth.is_authenticated()` at the top of every page function and call `ui.navigate.to("/")` if not authenticated. Use `auth.current_user()` to get the session user dict.

### 11. Card number generation
`_generate_card_number(conn, client_id)` must be called inside an active `get_conn()` context so the counter increment and card insert happen in the same transaction.

### 12. Static path
The static directory is mounted as `os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")` — never hardcode an absolute path.

---

## Known Constraints & NiceGUI Gotchas

| Issue | Cause | Fix |
|---|---|---|
| Icon names appear as text (`menu`, `bookmark`) | `font-family` override on `*` clobbers Material Icons | Scope Inter font to explicit element types; protect `.material-icons` and `.q-icon` |
| Dynamic content in dialog doesn't update | `element.clear()` + `with element:` deferred in dialog context | Use `@ui.refreshable` |
| `<script>` in `ui.html()` breaks loops | NiceGUI HTML sanitizer strips script tags | Use `ui.run_javascript()` after loop |
| `set_visibility(False)` during construction | Element never serialized to client | Never hide-then-show; build content on demand instead |
| SIGN IN button text invisible | Native `<button>` color defaults; Quasar q-btn theme | Use `.sign-in-btn` CSS class overriding `.q-btn__content` color |
| Horizontal Kanban wrap | Quasar `.row` has `flex-wrap:wrap !important` | Use `ui.row(wrap=False)` for the board container |
| "ES modules" error on server | NiceGUI version mismatch between local and server | Pin to `nicegui==3.13.0`; install via `requirements.txt` |
| `e.target._props` vs DOM attributes | `.props("data-column='X'")` stores in `_props` dict | Access as `element._props.get("data-column")` |

---

## Version History

| Version | Date | Summary |
|---|---|---|
| **0.21** | 2026-06-16 | Fixed history panel: all column-transition events now render. Root causes: `set_visibility(False)` during construction never serializes to client; `<script>` in `ui.html()` breaks loops. Fixed with `@ui.refreshable` + `ui.run_javascript()`. |
| **0.20** | 2026-06-16 | Card history tracking: `card_history` table, `create_card` and `move_card` record events with user + epoch. Comments/History tabs in card dialog using `@ui.refreshable`. |
| **0.19** | 2026-06-16 | Card ID badge color improved (white on blue pill in dialog, light slate on board). Default port changed to 3120. |
| **0.18** | 2026-06-16 | Per-client card identifiers: `ACM-0001` format. `client_card_counter` table, atomic generation in `create_card`. ID shown on card and in dialog title. |
| **0.17** | 2026-06-16 | Login background replaced with Gantt+Kanban hybrid SVG (split left/right). |
| **0.16** | 2026-06-16 | SIGN IN button text fixed (white on blue). Login background SVG dark data-viz scene. |
| **0.15** | 2026-06-16 | Fixed icon rendering bug (`visibility_off`, `menu`, `bookmark` as text). Scoped font-family away from `.material-icons`/`.q-icon`. |
| **0.14** | 2026-06-16 | Full dark Cives-style theme (`theme.py`), Inter + JetBrains Mono fonts, logo embedded, dark login page with glass card. Board kanban columns/cards use dark CSS classes. |
| **0.13** | 2026-06-16 | Comments system: threaded replies, rich-text editor, avatar+color per user, delete own/admin. Card dialog doubles in width, split left (fields) / right (comments). |
| **0.12** | 2026-06-16 | Admin avatar filter strip on board (radio-button toggle by assignee). `list_cards` accepts `assignee_filter`. |
| **0.11** | 2026-06-16 | Profile page: avatar upload, user color picker (uniqueness enforced), change password. User color shown as dot on assigned cards. |
| **0.10** | 2026-06-16 | Change password in burger menu (dialog with current-password verification). |
| **0.9** | 2026-06-16 | Client badge color fixed (hex via `color=` kwarg on `ui.badge`). |
| **0.8** | 2026-06-16 | Admin-configurable client badge color. |
| **0.7** | 2026-06-16 | Clients table, user-client assignments, board scoping by client. |
| **0.6** | 2026-06-16 | Fixed empty-string assignee crash (coerce to `None`). |
| **0.5** | 2026-06-16 | Assignee dropdown populated from `users` table. |
| **0.4** | 2026-06-16 | Rich-text description (`ui.editor`), file attachments. |
| **0.3** | 2026-06-16 | Fixed horizontal Kanban columns (initial render context bug). |
| **0.2** | 2026-06-16 | Burger menu, version indicator. |
| **0.1** | 2026-06-16 | Initial: Kanban board, users, login. |
