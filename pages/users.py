from nicegui import ui
import database as db
import auth
from pages.layout import page_layout


def users_page():
    if not auth.is_authenticated():
        ui.navigate.to("/")
        return
    if not auth.is_admin():
        with page_layout("Users"):
            ui.label("Access denied. Administrator privileges required.").classes("text-red-500 text-lg")
        return

    with page_layout("User Management"):
        table_container = ui.column().classes("w-full gap-4")

        def refresh():
            table_container.clear()
            with table_container:
                render_users_table()

        def render_users_table():
            users = db.list_users()
            columns = [
                {"name": "username", "label": "Username", "field": "username", "align": "left"},
                {"name": "full_name", "label": "Full name", "field": "full_name", "align": "left"},
                {"name": "is_admin", "label": "Admin", "field": "is_admin", "align": "center"},
                {"name": "clients", "label": "Clients", "field": "clients", "align": "left"},
            ]
            rows = []
            for u in users:
                if u["is_admin"]:
                    clients_str = "All (Administrator)"
                else:
                    clients = db.get_user_clients(u["id"])
                    clients_str = ", ".join(c["name"] for c in clients) or "—"
                rows.append({
                    "id": u["id"],
                    "username": u["username"],
                    "full_name": u["full_name"] or "",
                    "is_admin": "Yes" if u["is_admin"] else "No",
                    "clients": clients_str,
                })
            table = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")
            table.add_slot("body-cell-username", """
                <q-td :props="props">
                    <span class="font-medium">{{ props.value }}</span>
                </q-td>
            """)

            with ui.row().classes("gap-2 mt-2"):
                ui.button("Add User", icon="add", on_click=lambda: open_user_dialog(None, refresh))

                def edit_selected():
                    if table.selected:
                        user_id = table.selected[0]["id"]
                        user = db.get_user_by_id(user_id)
                        open_user_dialog(user, refresh)
                    else:
                        ui.notify("Select a user first", color="warning")

                def delete_selected():
                    if not table.selected:
                        ui.notify("Select a user first", color="warning")
                        return
                    user_id = table.selected[0]["id"]
                    user = db.get_user_by_id(user_id)
                    if user["username"] == "admin":
                        ui.notify("Cannot delete the default admin user", color="negative")
                        return
                    db.delete_user(user_id)
                    ui.notify(f"User {user['username']} deleted")
                    refresh()

                ui.button("Edit Selected", icon="edit", on_click=edit_selected)
                ui.button("Delete Selected", icon="delete", color="negative", on_click=delete_selected)

            table.props("selection=single")

        refresh()


def open_user_dialog(user, on_done):
    """user is None for create, or a sqlite Row for edit."""
    is_edit = user is not None

    with ui.dialog() as dialog, ui.card().classes("w-96"):
        ui.label("Edit User" if is_edit else "Add User").classes("text-lg font-bold")

        username_input = ui.input("Username", value=user["username"] if is_edit else "").classes("w-full")
        if is_edit:
            username_input.disable()

        full_name_input = ui.input("Full name", value=user["full_name"] if is_edit else "").classes("w-full")
        password_input = ui.input(
            "Password" + (" (leave blank to keep current)" if is_edit else ""),
            password=True, password_toggle_button=True
        ).classes("w-full")
        admin_checkbox = ui.checkbox("Administrator", value=bool(user["is_admin"]) if is_edit else False)

        all_clients = db.list_clients()
        client_options = {c["id"]: c["name"] for c in all_clients}
        current_client_ids = db.get_user_client_ids(user["id"]) if is_edit else []

        clients_select = ui.select(
            client_options, label="Assigned Clients", multiple=True, value=current_client_ids,
            with_input=True, clearable=True
        ).classes("w-full")
        clients_select.props("use-chips")

        def update_clients_visibility():
            clients_select.set_visibility(not admin_checkbox.value)

        admin_checkbox.on_value_change(lambda e: update_clients_visibility())
        update_clients_visibility()

        if not all_clients:
            ui.label("No clients defined yet. Create clients on the Clients page.").classes(
                "text-xs text-gray-500"
            )

        error_label = ui.label("").classes("text-red-500")

        def save():
            username = username_input.value.strip()
            full_name = full_name_input.value.strip()
            password = password_input.value
            is_admin_val = admin_checkbox.value

            if not username:
                error_label.set_text("Username is required")
                return

            if not is_admin_val and not (clients_select.value or []):
                error_label.set_text("Non-administrator users must be assigned to at least one client")
                return

            if is_edit:
                # Prevent removing admin rights from the last admin
                if user["username"] == "admin" and not is_admin_val:
                    error_label.set_text("The default admin user must remain an administrator")
                    return
                db.update_user(user["id"], full_name, is_admin_val, password or None)
                if not is_admin_val:
                    db.set_user_clients(user["id"], clients_select.value or [])
                else:
                    db.set_user_clients(user["id"], [])
                ui.notify(f"User {username} updated")
            else:
                if not password:
                    error_label.set_text("Password is required for new users")
                    return
                if db.get_user(username):
                    error_label.set_text("Username already exists")
                    return
                db.create_user(username, password, full_name, is_admin_val)
                if not is_admin_val:
                    new_user = db.get_user(username)
                    db.set_user_clients(new_user["id"], clients_select.value or [])
                ui.notify(f"User {username} created")

            dialog.close()
            on_done()

        with ui.row().classes("w-full justify-end gap-2 mt-2"):
            ui.button("Cancel", on_click=dialog.close)
            ui.button("Save", on_click=save).props("color=primary")

    dialog.open()
