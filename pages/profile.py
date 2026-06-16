import os
from nicegui import ui, events
import database as db
import auth
from pages.layout import page_layout

AVATAR_DIR = os.path.join(db.UPLOAD_DIR, "avatars")
os.makedirs(AVATAR_DIR, exist_ok=True)


def profile_page():
    if not auth.is_authenticated():
        ui.navigate.to("/")
        return

    user = auth.current_user()
    db_user = db.get_user_by_id(user["user_id"])

    with page_layout("Profile"):
        with ui.row().classes("w-full gap-8 items-start flex-wrap"):

            # ── Avatar card ─────────────────────────────────────────────────
            with ui.card().classes("p-6 gap-4 items-center").style("min-width:260px;"):
                ui.label("Avatar").classes("text-lg font-semibold")

                avatar_container = ui.column().classes("items-center gap-2")

                def render_avatar():
                    avatar_container.clear()
                    with avatar_container:
                        fresh = db.get_user_by_id(user["user_id"])
                        if fresh and fresh["avatar_path"] and os.path.exists(fresh["avatar_path"]):
                            rel = fresh["avatar_path"].replace(db.UPLOAD_DIR, "").lstrip("/\\")
                            ui.image(f"/uploads/{rel}").classes(
                                "rounded-full object-cover"
                            ).style("width:120px; height:120px;")
                        else:
                            # Placeholder initials circle
                            initials = (fresh["full_name"] or fresh["username"] or "?")[0].upper()
                            ui.element("div").classes(
                                "rounded-full flex items-center justify-center text-white text-4xl font-bold"
                            ).style(
                                f"width:120px; height:120px; "
                                f"background-color:{fresh['color'] or '#9e9e9e'};"
                            ).text = initials

                render_avatar()

                async def handle_avatar_upload(e: events.UploadEventArguments):
                    user_avatar_dir = os.path.join(AVATAR_DIR, str(user["user_id"]))
                    os.makedirs(user_avatar_dir, exist_ok=True)
                    # Keep only image files, overwrite with same name
                    ext = os.path.splitext(e.file.name)[1].lower()
                    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                        ui.notify("Only image files are allowed (jpg, png, gif, webp)", color="negative")
                        return
                    dest = os.path.join(user_avatar_dir, f"avatar{ext}")
                    await e.file.save(dest)
                    db.set_user_avatar(user["user_id"], dest)
                    ui.notify("Avatar updated")
                    render_avatar()

                ui.upload(
                    label="Upload avatar", on_upload=handle_avatar_upload, auto_upload=True
                ).props("accept='image/*'").classes("w-full")

            # ── Color card ──────────────────────────────────────────────────
            with ui.card().classes("p-6 gap-4").style("min-width:300px;"):
                ui.label("My Color").classes("text-lg font-semibold")
                ui.label(
                    "Used to mark cards assigned to you. Must be unique."
                ).classes("text-sm text-gray-500")

                current_color = db_user["color"] or "#9e9e9e"
                color_preview = ui.element("div").classes("rounded").style(
                    f"width:40px; height:40px; background-color:{current_color}; "
                    "border:1px solid #ccc; margin-bottom:4px;"
                )
                color_inp = ui.color_input(value=current_color, preview=True).classes("w-full")

                def update_color_preview(e=None):
                    color_preview.style(
                        f"background-color:{color_inp.value}; "
                        "width:40px; height:40px; border:1px solid #ccc; "
                        "margin-bottom:4px;"
                    )

                color_inp.on_value_change(update_color_preview)

                color_error = ui.label("").classes("text-red-500 text-sm")

                def save_color():
                    color = color_inp.value.strip()
                    if not color:
                        color_error.set_text("Please choose a color")
                        return
                    if db.is_color_taken(color, exclude_user_id=user["user_id"]):
                        color_error.set_text("This color is already taken by another user")
                        return
                    color_error.set_text("")
                    db.set_user_color(user["user_id"], color)
                    # Update avatar placeholder immediately if no avatar
                    render_avatar()
                    ui.notify("Color saved")

                ui.button("Save Color", icon="palette", on_click=save_color).props("color=primary")

            # ── Change Password card ─────────────────────────────────────────
            with ui.card().classes("p-6 gap-4").style("min-width:320px;"):
                ui.label("Change Password").classes("text-lg font-semibold")

                current_pw = ui.input(
                    "Current Password", password=True, password_toggle_button=True
                ).classes("w-full")
                new_pw = ui.input(
                    "New Password", password=True, password_toggle_button=True
                ).classes("w-full")
                confirm_pw = ui.input(
                    "Confirm New Password", password=True, password_toggle_button=True
                ).classes("w-full")

                pw_error = ui.label("").classes("text-red-500 text-sm")

                def save_password():
                    current = current_pw.value
                    new = new_pw.value
                    confirm = confirm_pw.value

                    if not current or not new or not confirm:
                        pw_error.set_text("All fields are required")
                        return

                    fresh = db.get_user_by_id(user["user_id"])
                    if not fresh or fresh["password_hash"] != db.hash_password(current):
                        pw_error.set_text("Current password is incorrect")
                        return

                    if new != confirm:
                        pw_error.set_text("New passwords do not match")
                        return

                    if len(new) < 4:
                        pw_error.set_text("New password must be at least 4 characters")
                        return

                    pw_error.set_text("")
                    db.set_user_password(user["user_id"], new)
                    current_pw.set_value("")
                    new_pw.set_value("")
                    confirm_pw.set_value("")
                    ui.notify("Password changed successfully")

                ui.button("Change Password", icon="lock", on_click=save_password).props("color=primary")
