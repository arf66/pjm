"""Simple session-based authentication helpers using NiceGUI's storage."""
from nicegui import app


def current_user():
    """Return dict with username/is_admin/full_name/user_id if logged in, else None."""
    return app.storage.user.get("auth")


def login(user_row):
    app.storage.user["auth"] = {
        "user_id": user_row["id"],
        "username": user_row["username"],
        "full_name": user_row["full_name"],
        "is_admin": bool(user_row["is_admin"]),
    }


def logout():
    app.storage.user.pop("auth", None)


def is_authenticated() -> bool:
    return current_user() is not None


def is_admin() -> bool:
    user = current_user()
    return bool(user and user.get("is_admin"))
