# PM Tracker — Kanban Project Management App

A project management tracker built with **NiceGUI**, **FastAPI**, and **SQLite**.

## Features

- **Kanban board** with drag-and-drop across columns: Backlog → Committed → In progress → In testing → Done
- Three card types:
  - **Story**: description, assignee, expected delivery date, file attachments
  - **Bug**: same fields as Story
  - **Epic**: description plus links to multiple Stories/Bugs (click a link to jump straight to that card)
- **File attachments** on Stories/Bugs (stored under `uploads/<card_id>/`)
- **User management** (Administrators only): create, edit, delete users; assign/revoke admin rights
- Default admin account: `admin` / `1234`

## Setup

```bash
pip install -r requirements.txt
python3 main.py
```

The app starts on `http://localhost:8080`. The SQLite database (`pm_app.db`) and `uploads/` folder
are created automatically on first run.

## Project structure

```
pm_app/
├── main.py          # entry point, routes, static file serving
├── database.py       # SQLite schema and data access layer
├── auth.py            # session-based authentication helpers
├── requirements.txt
├── uploads/           # uploaded attachments (auto-created)
└── pages/
    ├── login.py       # login page
    ├── layout.py       # shared header/navigation
    ├── board.py        # Kanban board + card dialogs
    └── users.py         # user management (admin only)
```

## Notes

- **First login**: use `admin` / `1234`. Change the password via User Management → Edit Selected.
- **Security**: `storage_secret` in `main.py` should be changed to a random value for production use.
  Passwords are stored as SHA-256 hashes; for production consider a stronger scheme (e.g. bcrypt/argon2).
- **Drag and drop**: cards can be dragged between and within columns; ordering and column are persisted to SQLite.
- **Epics**: open an Epic card and use "Add Story/Bug to this Epic" to link existing Story/Bug cards.
  Linked items appear as clickable links on the Epic card and inside its dialog.
- **Attachments**: available once a Story/Bug card has been saved (i.e., when editing an existing card).
