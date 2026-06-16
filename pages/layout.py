from contextlib import contextmanager
from nicegui import ui
import auth
import theme
from version import __version__


@contextmanager
def page_layout(title: str):
    theme.apply_theme()
    user = auth.current_user()

    with ui.header().style(
        f"background:{theme.SURFACE};border-bottom:1px solid {theme.BORDER};"
        "padding:0 24px;height:56px;box-shadow:none;"
    ).classes("items-center justify-between"):

        with ui.row().classes("items-center gap-3 no-wrap"):
            ui.image("/static/logo_white.svg").style(
                "width:36px;height:36px;border-radius:8px;"
            )
            with ui.column().classes("gap-0").style("line-height:1;"):
                ui.label("PM Tracker").style(
                    f"color:{theme.TEXT};font-size:.95rem;font-weight:700;"
                    "font-family:'JetBrains Mono',monospace;letter-spacing:.05em;"
                )
                ui.label("PROJECT MANAGEMENT").style(
                    f"color:{theme.TEXT_MUTED};font-size:.5rem;font-weight:600;"
                    "letter-spacing:.18em;"
                )

        with ui.row().classes("items-center gap-3"):
            if user:
                ui.label(user["full_name"] or user["username"]).style(
                    f"color:{theme.TEXT_MUTED};font-size:.8rem;"
                )

            def do_logout():
                auth.logout()
                ui.navigate.to("/")

            with ui.button(icon="menu").props("flat round dense").style(f"color:{theme.TEXT};"):
                with ui.menu():
                    ui.menu_item("Board", on_click=lambda: ui.navigate.to("/board"))
                    if user and user.get("is_admin"):
                        ui.menu_item("Users", on_click=lambda: ui.navigate.to("/users"))
                        ui.menu_item("Clients", on_click=lambda: ui.navigate.to("/clients"))
                    ui.separator()
                    ui.menu_item("Profile", on_click=lambda: ui.navigate.to("/profile"))
                    ui.menu_item("Logout", on_click=do_logout).style(f"color:{theme.DANGER};")
                    ui.separator()
                    ui.menu_item(f"Version {__version__}").props("disable").style(
                        f"color:{theme.TEXT_MUTED};font-size:.75rem;"
                    )

    with ui.column().classes("w-full").style(
        f"padding:24px 32px;background:{theme.BG};min-height:calc(100vh - 56px);"
    ):
        ui.label(title.upper()).style(
            f"color:{theme.TEXT};font-size:1.3rem;font-weight:700;"
            "letter-spacing:.03em;margin-bottom:16px;"
        )
        yield
