from nicegui import ui
import database as db
import auth
from pages.layout import page_layout


def clients_page():
    if not auth.is_authenticated():
        ui.navigate.to("/")
        return
    if not auth.is_admin():
        with page_layout("Clients"):
            ui.label("Access denied. Administrator privileges required.").classes("text-red-500 text-lg")
        return

    with page_layout("Clients"):
        table_container = ui.column().classes("w-full gap-4")

        def refresh():
            table_container.clear()
            with table_container:
                render_clients_table()

        def render_clients_table():
            clients = db.list_clients()
            columns = [
                {"name": "color", "label": "Color", "field": "color", "align": "center"},
                {"name": "name", "label": "Name", "field": "name", "align": "left"},
                {"name": "description", "label": "Description", "field": "description", "align": "left"},
                {"name": "users", "label": "Assigned Users", "field": "users", "align": "left"},
            ]
            rows = []
            for cl in clients:
                users = db.get_client_users(cl["id"])
                user_names = ", ".join(u["full_name"] or u["username"] for u in users) or "—"
                rows.append({
                    "id": cl["id"],
                    "color": cl["color"],
                    "name": cl["name"],
                    "description": cl["description"] or "",
                    "users": user_names,
                })

            table = ui.table(columns=columns, rows=rows, row_key="id").classes("w-full")
            table.add_slot("body-cell-color", """
                <q-td :props="props">
                    <div :style="{
                        backgroundColor: props.value,
                        width: '24px',
                        height: '24px',
                        borderRadius: '4px',
                        margin: '0 auto'
                    }"></div>
                </q-td>
            """)
            table.props("selection=single")

            with ui.row().classes("gap-2 mt-2"):
                ui.button("Add Client", icon="add", on_click=lambda: open_client_dialog(None, refresh))

                def edit_selected():
                    if table.selected:
                        client_id = table.selected[0]["id"]
                        client = db.get_client(client_id)
                        open_client_dialog(client, refresh)
                    else:
                        ui.notify("Select a client first", color="warning")

                def delete_selected():
                    if not table.selected:
                        ui.notify("Select a client first", color="warning")
                        return
                    client_id = table.selected[0]["id"]
                    client = db.get_client(client_id)
                    confirm_delete_client(client, refresh)

                ui.button("Edit Selected", icon="edit", on_click=edit_selected)
                ui.button("Delete Selected", icon="delete", color="negative", on_click=delete_selected)

        refresh()


def open_client_dialog(client, on_done):
    """client is None for create, or a sqlite Row for edit."""
    is_edit = client is not None

    with ui.dialog() as dialog, ui.card().classes("w-96"):
        ui.label("Edit Client" if is_edit else "Add Client").classes("text-lg font-bold")

        name_input = ui.input("Name", value=client["name"] if is_edit else "").classes("w-full")
        description_input = ui.textarea(
            "Description", value=client["description"] if is_edit else ""
        ).classes("w-full")

        current_color = client["color"] if is_edit else db.DEFAULT_CLIENT_COLOR

        ui.label("Badge Color").classes("text-sm text-gray-600 mt-1")
        with ui.row().classes("items-center gap-2 w-full"):
            color_preview = ui.element("div").classes("rounded").style(
                f"width: 32px; height: 32px; background-color: {current_color}; border: 1px solid #ccc;"
            )
            color_input = ui.color_input(value=current_color, preview=True).classes("flex-grow")

            def update_preview(e):
                color_preview.style(f"background-color: {color_input.value};")

            color_input.on_value_change(update_preview)

        error_label = ui.label("").classes("text-red-500")

        def save():
            name = name_input.value.strip()
            description = description_input.value.strip()
            color = color_input.value or db.DEFAULT_CLIENT_COLOR

            if not name:
                error_label.set_text("Name is required")
                return

            existing = db.get_client_by_name(name)
            if existing and (not is_edit or existing["id"] != client["id"]):
                error_label.set_text("A client with this name already exists")
                return

            if is_edit:
                db.update_client(client["id"], name, description, color)
                ui.notify(f"Client {name} updated")
            else:
                db.create_client(name, description, color)
                ui.notify(f"Client {name} created")

            dialog.close()
            on_done()

        with ui.row().classes("w-full justify-end gap-2 mt-2"):
            ui.button("Cancel", on_click=dialog.close)
            ui.button("Save", on_click=save).props("color=primary")

    dialog.open()


def confirm_delete_client(client, on_done):
    with ui.dialog() as confirm, ui.card():
        ui.label(
            f"Delete client '{client['name']}'? Cards assigned to this client will keep "
            "their reference but the client will no longer be selectable. This cannot be undone."
        ).classes("text-base")
        with ui.row().classes("w-full justify-end gap-2 mt-2"):
            ui.button("Cancel", on_click=confirm.close)

            def do_delete():
                db.delete_client(client["id"])
                confirm.close()
                ui.notify(f"Client {client['name']} deleted")
                on_done()

            ui.button("Delete", color="negative", on_click=do_delete)
    confirm.open()
