"""SQLite database setup and access layer for the PM app."""
import sqlite3
import hashlib
import os
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "pm_app.db")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

COLUMNS = ["Backlog", "Committed", "In progress", "In testing", "Done"]
CARD_TYPES = ["Epic", "Story", "Bug"]


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_type TEXT NOT NULL CHECK(card_type IN ('Epic','Story','Bug')),
                title TEXT NOT NULL,
                description TEXT,
                assignee TEXT,
                expected_delivery TEXT,
                column_name TEXT NOT NULL DEFAULT 'Backlog',
                position INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        # Link table: which stories/bugs belong to which epic
        c.execute("""
            CREATE TABLE IF NOT EXISTS epic_links (
                epic_id INTEGER NOT NULL,
                story_id INTEGER NOT NULL,
                PRIMARY KEY (epic_id, story_id),
                FOREIGN KEY (epic_id) REFERENCES cards(id) ON DELETE CASCADE,
                FOREIGN KEY (story_id) REFERENCES cards(id) ON DELETE CASCADE
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                color TEXT NOT NULL DEFAULT '#9e9e9e',
                created_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_clients (
                user_id INTEGER NOT NULL,
                client_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, client_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS card_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL,
                parent_id INTEGER,
                author_user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
                FOREIGN KEY (parent_id) REFERENCES card_comments(id) ON DELETE CASCADE,
                FOREIGN KEY (author_user_id) REFERENCES users(id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS card_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL,
                from_column TEXT,
                to_column TEXT NOT NULL,
                user_id INTEGER,
                epoch INTEGER NOT NULL,
                event_type TEXT NOT NULL DEFAULT 'column',
                extra TEXT,
                FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Migration: add client_id column to cards if missing
        existing_columns = [row["name"] for row in c.execute("PRAGMA table_info(cards)").fetchall()]
        if "client_id" not in existing_columns:
            c.execute("ALTER TABLE cards ADD COLUMN client_id INTEGER REFERENCES clients(id)")

        # Migration: add color column to clients if missing
        existing_client_columns = [row["name"] for row in c.execute("PRAGMA table_info(clients)").fetchall()]
        if "color" not in existing_client_columns:
            c.execute("ALTER TABLE clients ADD COLUMN color TEXT NOT NULL DEFAULT '#9e9e9e'")

        c.execute("""
            CREATE TABLE IF NOT EXISTS client_card_counter (
                client_id INTEGER PRIMARY KEY,
                last_number INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)

        # Migration: add card_number column to cards if missing
        if "card_number" not in existing_columns:
            c.execute("ALTER TABLE cards ADD COLUMN card_number TEXT")

        # Migration: add event_type and extra columns to card_history if missing
        existing_history_columns = [row["name"] for row in c.execute("PRAGMA table_info(card_history)").fetchall()]
        if "event_type" not in existing_history_columns:
            c.execute("ALTER TABLE card_history ADD COLUMN event_type TEXT NOT NULL DEFAULT 'column'")
        if "extra" not in existing_history_columns:
            c.execute("ALTER TABLE card_history ADD COLUMN extra TEXT")

        # Migration: add avatar_path and color columns to users if missing
        existing_user_columns = [row["name"] for row in c.execute("PRAGMA table_info(users)").fetchall()]
        if "avatar_path" not in existing_user_columns:
            c.execute("ALTER TABLE users ADD COLUMN avatar_path TEXT")
        if "color" not in existing_user_columns:
            c.execute("ALTER TABLE users ADD COLUMN color TEXT")

        # Seed admin user
        c.execute("SELECT COUNT(*) FROM users")
        if c.fetchone()[0] == 0:
            c.execute(
                "INSERT INTO users (username, password_hash, full_name, is_admin, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                ("admin", hash_password("1234"), "Administrator", 1, datetime.utcnow().isoformat())
            )


# ---------------- Users ----------------

def get_user(username: str):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def get_user_by_id(user_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def list_users():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users ORDER BY username").fetchall()


def create_user(username: str, password: str, full_name: str, is_admin: bool):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, is_admin, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (username, hash_password(password), full_name, int(is_admin), datetime.utcnow().isoformat())
        )


def update_user(user_id: int, full_name: str, is_admin: bool, password: str = None):
    with get_conn() as conn:
        if password:
            conn.execute(
                "UPDATE users SET full_name=?, is_admin=?, password_hash=? WHERE id=?",
                (full_name, int(is_admin), hash_password(password), user_id)
            )
        else:
            conn.execute(
                "UPDATE users SET full_name=?, is_admin=? WHERE id=?",
                (full_name, int(is_admin), user_id)
            )


def delete_user(user_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


def set_user_password(user_id: int, new_password: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (hash_password(new_password), user_id)
        )


def set_user_avatar(user_id: int, avatar_path: str):
    with get_conn() as conn:
        conn.execute("UPDATE users SET avatar_path=? WHERE id=?", (avatar_path, user_id))


def set_user_color(user_id: int, color: str):
    with get_conn() as conn:
        conn.execute("UPDATE users SET color=? WHERE id=?", (color, user_id))


def is_color_taken(color: str, exclude_user_id: int = None) -> bool:
    """Return True if the color is already used by another user."""
    with get_conn() as conn:
        if exclude_user_id:
            row = conn.execute(
                "SELECT id FROM users WHERE LOWER(color)=LOWER(?) AND id != ?",
                (color, exclude_user_id)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT id FROM users WHERE LOWER(color)=LOWER(?)", (color,)
            ).fetchone()
        return row is not None


def get_user_color_by_name(display_name: str):
    """Return the color hex of the user whose full_name or username matches display_name."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT color FROM users WHERE full_name=? OR username=?",
            (display_name, display_name)
        ).fetchone()
        return row["color"] if row else None


def verify_login(username: str, password: str):
    user = get_user(username)
    if user and user["password_hash"] == hash_password(password):
        return user
    return None


# ---------------- Clients ----------------

def list_clients():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM clients ORDER BY name").fetchall()


def get_client(client_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()


def get_client_by_name(name: str):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM clients WHERE name = ?", (name,)).fetchone()


DEFAULT_CLIENT_COLOR = "#9e9e9e"


def create_client(name: str, description: str = None, color: str = DEFAULT_CLIENT_COLOR):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO clients (name, description, color, created_at) VALUES (?, ?, ?, ?)",
            (name, description, color or DEFAULT_CLIENT_COLOR, datetime.utcnow().isoformat())
        )
        return cur.lastrowid


def update_client(client_id: int, name: str, description: str = None, color: str = DEFAULT_CLIENT_COLOR):
    with get_conn() as conn:
        conn.execute(
            "UPDATE clients SET name = ?, description = ?, color = ? WHERE id = ?",
            (name, description, color or DEFAULT_CLIENT_COLOR, client_id)
        )


def delete_client(client_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))


# ---------------- User <-> Client assignments ----------------

def get_user_clients(user_id: int):
    """Return clients assigned to a user."""
    with get_conn() as conn:
        return conn.execute("""
            SELECT cl.* FROM clients cl
            JOIN user_clients uc ON uc.client_id = cl.id
            WHERE uc.user_id = ?
            ORDER BY cl.name
        """, (user_id,)).fetchall()


def get_user_client_ids(user_id: int):
    with get_conn() as conn:
        rows = conn.execute("SELECT client_id FROM user_clients WHERE user_id = ?", (user_id,)).fetchall()
        return [row["client_id"] for row in rows]


def set_user_clients(user_id: int, client_ids: list):
    """Replace the set of clients assigned to a user."""
    with get_conn() as conn:
        conn.execute("DELETE FROM user_clients WHERE user_id = ?", (user_id,))
        for cid in client_ids:
            conn.execute(
                "INSERT OR IGNORE INTO user_clients (user_id, client_id) VALUES (?, ?)",
                (user_id, cid)
            )


def get_client_users(client_id: int):
    """Return users assigned to a client."""
    with get_conn() as conn:
        return conn.execute("""
            SELECT u.* FROM users u
            JOIN user_clients uc ON uc.user_id = u.id
            WHERE uc.client_id = ?
            ORDER BY u.username
        """, (client_id,)).fetchall()


def user_accessible_client_ids(user):
    """Return the list of client IDs a user can see. Admins see all (returns None to mean 'all')."""
    if user.get("is_admin"):
        return None  # signal: no restriction
    return get_user_client_ids(user["user_id"])


# ---------------- Cards ----------------

def list_cards(client_ids=None, assignee_filter=None):
    """List cards, optionally restricted to a set of client IDs and/or an assignee.

    :param client_ids: list of allowed client IDs, or None for no restriction (admin/all).
    :param assignee_filter: if set, only return cards whose assignee matches this string.
    """
    with get_conn() as conn:
        conditions = []
        params = []

        if client_ids is not None:
            if not client_ids:
                return []
            placeholders = ",".join("?" for _ in client_ids)
            conditions.append(f"client_id IN ({placeholders})")
            params.extend(client_ids)

        if assignee_filter is not None:
            conditions.append("assignee = ?")
            params.append(assignee_filter)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return conn.execute(
            f"SELECT * FROM cards {where} ORDER BY column_name, position",
            params
        ).fetchall()


def get_card(card_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()


def next_position(column_name: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS p FROM cards WHERE column_name = ?",
            (column_name,)
        ).fetchone()
        return row["p"]


def _generate_card_number(conn, client_id: int) -> str:
    """Atomically increment the per-client counter and return a formatted card ID like ACM-0001."""
    client = conn.execute("SELECT name FROM clients WHERE id = ?", (client_id,)).fetchone()
    prefix = (client["name"][:3].upper() if client else "UNK")

    row = conn.execute(
        "SELECT last_number FROM client_card_counter WHERE client_id = ?", (client_id,)
    ).fetchone()
    if row:
        new_num = row["last_number"] + 1
        conn.execute(
            "UPDATE client_card_counter SET last_number = ? WHERE client_id = ?",
            (new_num, client_id)
        )
    else:
        new_num = 1
        conn.execute(
            "INSERT INTO client_card_counter (client_id, last_number) VALUES (?, ?)",
            (client_id, new_num)
        )
    return f"{prefix}-{new_num:04d}"


def create_card(card_type, title, description=None, assignee=None, expected_delivery=None,
                 column_name="Backlog", client_id=None, user_id=None):
    import time as _t
    now = datetime.utcnow().isoformat()
    epoch = int(_t.time())
    pos = next_position(column_name)
    with get_conn() as conn:
        card_number = _generate_card_number(conn, client_id) if client_id else None
        cur = conn.execute(
            "INSERT INTO cards (card_type, title, description, assignee, expected_delivery, "
            "column_name, position, client_id, card_number, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (card_type, title, description, assignee, expected_delivery, column_name, pos, client_id, card_number, now, now)
        )
        new_id = cur.lastrowid
        # Record creation event: from_column=None means "created here"
        conn.execute(
            "INSERT INTO card_history (card_id, from_column, to_column, user_id, epoch, event_type) VALUES (?,?,?,?,?,?)",
            (new_id, None, column_name, user_id, epoch, "column")
        )
        return new_id


def update_card(card_id, **fields):
    if not fields:
        return
    fields["updated_at"] = datetime.utcnow().isoformat()
    with get_conn() as conn:
        # If client_id is being set and the card has no card_number yet, generate one
        if "client_id" in fields and fields["client_id"]:
            card = conn.execute("SELECT card_number FROM cards WHERE id = ?", (card_id,)).fetchone()
            if card and not card["card_number"]:
                fields["card_number"] = _generate_card_number(conn, fields["client_id"])
        keys = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values()) + [card_id]
        conn.execute(f"UPDATE cards SET {keys} WHERE id = ?", values)


def move_card(card_id, new_column, new_position, user_id=None):
    """Move a card to a new column/position, shifting other cards accordingly."""
    import time as _t
    with get_conn() as conn:
        card = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
        if not card:
            return
        old_column = card["column_name"]
        old_position = card["position"]

        if old_column == new_column:
            # Reorder within same column — no history event
            if new_position > old_position:
                conn.execute(
                    "UPDATE cards SET position = position - 1 "
                    "WHERE column_name = ? AND position > ? AND position <= ?",
                    (old_column, old_position, new_position)
                )
            elif new_position < old_position:
                conn.execute(
                    "UPDATE cards SET position = position + 1 "
                    "WHERE column_name = ? AND position >= ? AND position < ?",
                    (old_column, new_position, old_position)
                )
        else:
            # Column change — record history
            conn.execute(
                "UPDATE cards SET position = position - 1 "
                "WHERE column_name = ? AND position > ?",
                (old_column, old_position)
            )
            conn.execute(
                "UPDATE cards SET position = position + 1 "
                "WHERE column_name = ? AND position >= ?",
                (new_column, new_position)
            )
            conn.execute(
                "INSERT INTO card_history (card_id, from_column, to_column, user_id, epoch, event_type) VALUES (?,?,?,?,?,?)",
                (card_id, old_column, new_column, user_id, int(_t.time()), "column")
            )

        conn.execute(
            "UPDATE cards SET column_name = ?, position = ?, updated_at = ? WHERE id = ?",
            (new_column, new_position, datetime.utcnow().isoformat(), card_id)
        )


def delete_card(card_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))


# ---------------- Epic links ----------------

def link_story_to_epic(epic_id: int, story_id: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO epic_links (epic_id, story_id) VALUES (?, ?)",
            (epic_id, story_id)
        )


def unlink_story_from_epic(epic_id: int, story_id: int):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM epic_links WHERE epic_id = ? AND story_id = ?",
            (epic_id, story_id)
        )


def get_epic_stories(epic_id: int):
    with get_conn() as conn:
        return conn.execute("""
            SELECT c.* FROM cards c
            JOIN epic_links el ON el.story_id = c.id
            WHERE el.epic_id = ?
            ORDER BY c.column_name, c.position
        """, (epic_id,)).fetchall()


def get_card_epics(story_id: int):
    """Return epics that this story/bug belongs to."""
    with get_conn() as conn:
        return conn.execute("""
            SELECT c.* FROM cards c
            JOIN epic_links el ON el.epic_id = c.id
            WHERE el.story_id = ?
        """, (story_id,)).fetchall()


# ---------------- Attachments ----------------

def add_attachment(card_id: int, filename: str, stored_path: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO attachments (card_id, filename, stored_path, uploaded_at) VALUES (?,?,?,?)",
            (card_id, filename, stored_path, datetime.utcnow().isoformat())
        )


def get_attachments(card_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM attachments WHERE card_id = ? ORDER BY uploaded_at", (card_id,)
        ).fetchall()


def delete_attachment(attachment_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,)).fetchone()
        if row:
            try:
                os.remove(row["stored_path"])
            except OSError:
                pass
            conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))


# ---------------- Comments ----------------

def add_comment(card_id: int, author_user_id: int, content: str, parent_id: int = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO card_comments (card_id, parent_id, author_user_id, content, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (card_id, parent_id, author_user_id, content, datetime.utcnow().isoformat())
        )
        return cur.lastrowid


def get_comments(card_id: int):
    """Return all comments for a card ordered by created_at ascending, with author info joined."""
    with get_conn() as conn:
        return conn.execute("""
            SELECT cc.*,
                   u.full_name  AS author_name,
                   u.color      AS author_color,
                   u.avatar_path AS author_avatar
            FROM card_comments cc
            JOIN users u ON u.id = cc.author_user_id
            WHERE cc.card_id = ?
            ORDER BY cc.created_at ASC
        """, (card_id,)).fetchall()


def delete_comment(comment_id: int, requesting_user_id: int, is_admin: bool) -> bool:
    """Delete a comment. Users may only delete their own; admins may delete any."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM card_comments WHERE id = ?", (comment_id,)).fetchone()
        if not row:
            return False
        if not is_admin and row["author_user_id"] != requesting_user_id:
            return False
        conn.execute("DELETE FROM card_comments WHERE id = ?", (comment_id,))
        return True


# ---------------- Card History ----------------

import time as _time

def add_history_event(card_id: int, to_column: str, user_id: int = None, from_column: str = None):
    """Record a column transition for a card."""
    epoch = int(_time.time())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO card_history (card_id, from_column, to_column, user_id, epoch, event_type) VALUES (?,?,?,?,?,?)",
            (card_id, from_column, to_column, user_id, epoch, "column")
        )


def add_assignment_history_event(card_id: int, from_assignee: str, to_assignee: str, user_id: int = None, current_column: str = "Backlog"):
    """Record an assignee change for a card."""
    epoch = int(_time.time())
    # extra stores JSON-like: 'from_assignee→to_assignee'
    extra = f"{from_assignee or ''}→{to_assignee or ''}"
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO card_history (card_id, from_column, to_column, user_id, epoch, event_type, extra) VALUES (?,?,?,?,?,?,?)",
            (card_id, current_column, current_column, user_id, epoch, "assignment", extra)
        )


def get_card_history(card_id: int):
    """Return history events for a card, oldest first, with user info joined."""
    with get_conn() as conn:
        return conn.execute("""
            SELECT ch.id, ch.card_id, ch.from_column, ch.to_column, ch.epoch,
                   ch.event_type, ch.extra,
                   u.full_name  AS user_name,
                   u.color      AS user_color,
                   u.avatar_path AS user_avatar,
                   u.username   AS username
            FROM card_history ch
            LEFT JOIN users u ON u.id = ch.user_id
            WHERE ch.card_id = ?
            ORDER BY ch.epoch ASC
        """, (card_id,)).fetchall()
