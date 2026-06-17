from nicegui import ui, app
import os
import database as db
from pages.login import login_page
from pages.board import board_page
from pages.users import users_page
from pages.clients import clients_page
from pages.profile import profile_page

db.init_db()

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.add_static_files("/uploads", db.UPLOAD_DIR)
app.add_static_files("/static", os.path.join(_BASE_DIR, "static"))


@ui.page("/")
def index():
    login_page()


@ui.page("/board")
def board():
    board_page()


@ui.page("/users")
def users():
    users_page()


@ui.page("/clients")
def clients():
    clients_page()


@ui.page("/profile")
def profile():
    profile_page()


ui.run(
    title="PM Tracker",
    favicon="/static/favicon.png",
    storage_secret="pm-tracker-secret-key-change-in-production",
    port=3320,
    reload=False,
)
