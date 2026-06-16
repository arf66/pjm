import os
from nicegui import ui, events
import theme
import database as db
import auth
from pages.layout import page_layout

CARD_TYPE_COLORS = {
    "Epic": "purple-6",
    "Story": "blue-6",
    "Bug": "red-6",
}

CARD_TYPE_ICONS = {
    "Epic": "auto_awesome",
    "Story": "bookmark",
    "Bug": "bug_report",
}


def board_page():
    if not auth.is_authenticated():
        ui.navigate.to("/")
        return

    user = auth.current_user()
    client_ids = db.user_accessible_client_ids(user)  # None = all (admin)
    is_admin = user.get("is_admin", False)

    # Shared filter state
    state = {"assignee_filter": None}

    with page_layout("Kanban Board"):
        if client_ids is not None and not client_ids:
            ui.label(
                "You are not assigned to any clients yet. Please contact an administrator."
            ).classes("text-red-500 text-lg")
            return

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("New Card", icon="add",
                      on_click=lambda: open_card_dialog(None, refresh_board, client_ids))

        # ── Admin-only user filter strip ──────────────────────────────────
        if is_admin:
            strip_container = ui.row().classes("w-full gap-3 items-center py-2 flex-wrap")

            def render_strip():
                strip_container.clear()
                all_users = db.list_users()
                with strip_container:
                    for u in all_users:
                        display_name = u["full_name"] or u["username"]
                        color = u["color"] or "#9e9e9e"
                        is_selected = state["assignee_filter"] == display_name

                        # outer wrapper: ring when selected
                        ring_style = (
                            f"border: 3px solid {color}; border-radius: 50%; padding: 2px;"
                            if is_selected else
                            "border: 3px solid transparent; border-radius: 50%; padding: 2px;"
                        )

                        with ui.element("div").style(ring_style + " cursor: pointer;") \
                                .tooltip(display_name) as avatar_wrap:

                            if (u["avatar_path"] and
                                    os.path.exists(u["avatar_path"])):
                                rel = u["avatar_path"].replace(db.UPLOAD_DIR, "").lstrip("/\\")
                                avatar_el = ui.image(f"/uploads/{rel}").style(
                                    "width:44px; height:44px; border-radius:50%;"
                                    "object-fit:cover; display:block;"
                                )
                            else:
                                initials = display_name[0].upper()
                                avatar_el = ui.element("div").style(
                                    f"width:44px; height:44px; border-radius:50%;"
                                    f"background-color:{color}; color:white;"
                                    "display:flex; align-items:center; justify-content:center;"
                                    "font-weight:bold; font-size:18px;"
                                ).text = initials

                            def make_toggle(name=display_name):
                                def toggle():
                                    if state["assignee_filter"] == name:
                                        state["assignee_filter"] = None
                                    else:
                                        state["assignee_filter"] = name
                                    render_strip()
                                    refresh_board()
                                return toggle

                            avatar_wrap.on("click", make_toggle())

                    # Show active filter label
                    if state["assignee_filter"]:
                        with ui.row().classes("items-center gap-1 text-sm").style("color:color:#8b949e"):
                            ui.icon("filter_alt", size="16px")
                            ui.label(f"Showing cards for: {state['assignee_filter']}")

            render_strip()

        # ── Board columns ─────────────────────────────────────────────────
        board_container = ui.row(wrap=False).classes("w-full gap-4 items-start overflow-x-auto")

        def refresh_board():
            board_container.clear()
            with board_container:
                render_columns(refresh_board, client_ids, state["assignee_filter"])

        with board_container:
            render_columns(refresh_board, client_ids, state["assignee_filter"])


def render_columns(refresh_board, client_ids, assignee_filter=None):
    all_cards = db.list_cards(client_ids, assignee_filter=assignee_filter)
    cards_by_column = {col: [] for col in db.COLUMNS}
    for card in all_cards:
        cards_by_column.setdefault(card["column_name"], []).append(card)

    for col_name in db.COLUMNS:
        with ui.column().classes(
            "kanban-col p-3 gap-2 flex-shrink-0"
        ).style("min-height: 60vh; width: 280px; min-width: 280px;"):
            with ui.row().classes("w-full justify-between items-center"):
                ui.label(col_name).classes("text-lg font-bold")
                ui.badge(str(len(cards_by_column[col_name]))).props("color=grey-6")

            card_list = ui.column().classes("w-full gap-2 min-h-[50vh]")
            card_list.props(f"data-column='{col_name}'")

            with card_list:
                for card in cards_by_column[col_name]:
                    render_card(card, refresh_board, client_ids)

            def make_on_end(refresh):
                def on_end(e: events.SortableEventArguments):
                    target_column = e.target._props.get("data-column")
                    card_id = getattr(e.item, "card_id", None)
                    if card_id is not None and target_column:
                        current_user = auth.current_user()
                        uid = current_user["user_id"] if current_user else None
                        db.move_card(card_id, target_column, e.new_index, user_id=uid)
                    refresh()
                return on_end

            card_list.make_sortable(
                group="kanban",
                on_end=make_on_end(refresh_board),
                animation=0.15,
                ghost_class="opacity-30",
            )


def render_card(card, refresh_board, client_ids):
    card_type = card["card_type"]
    color = CARD_TYPE_COLORS.get(card_type, "grey-6")
    icon = CARD_TYPE_ICONS.get(card_type, "note")

    element = ui.card().classes("kanban-card w-full p-3")
    element.card_id = card["id"]  # custom attribute used to identify the card on drag end

    with element:
        with ui.row().classes("items-center justify-between w-full no-wrap"):
            with ui.row().classes("items-center gap-2 no-wrap"):
                ui.icon(icon, color=color)
                ui.badge(card_type).props(f"color={color}")
                if card["card_number"]:
                    ui.label(card["card_number"]).style(
                        "font-family:'JetBrains Mono',monospace;"
                        "font-size:.65rem;font-weight:600;letter-spacing:.03em;"
                        "color:#94a3b8;"
                    )

            if card["client_id"]:
                client = db.get_client(card["client_id"])
                if client:
                    ui.badge(client["name"], color=client["color"]).style("color: white;")

        ui.label(card["title"]).classes("font-semibold mt-1 break-words")

        if card_type in ("Story", "Bug"):
            if card["assignee"]:
                assignee_color = db.get_user_color_by_name(card["assignee"])
                with ui.row().classes("items-center gap-1 text-xs").style("color:color:#8b949e"):
                    if assignee_color:
                        ui.element("div").style(
                            f"width:12px; height:12px; border-radius:50%; "
                            f"background-color:{assignee_color}; flex-shrink:0;"
                        )
                    else:
                        ui.icon("person", size="16px")
                    ui.label(card["assignee"])
            if card["expected_delivery"]:
                with ui.row().classes("items-center gap-1 text-xs").style("color:color:#8b949e"):
                    ui.icon("event", size="16px")
                    ui.label(card["expected_delivery"])
            attachments = db.get_attachments(card["id"])
            if attachments:
                with ui.row().classes("items-center gap-1 text-xs").style("color:color:#8b949e"):
                    ui.icon("attach_file", size="16px")
                    ui.label(f"{len(attachments)} file(s)")

        if card_type == "Epic":
            stories = db.get_epic_stories(card["id"])
            if stories:
                with ui.column().classes("gap-0 mt-1"):
                    for s in stories[:5]:
                        ui.label(f"• {s['card_type']}: {s['title']}").classes(
                            "text-xs truncate"
                        ).style("color:#58a6ff")
                    if len(stories) > 5:
                        ui.label(f"... and {len(stories) - 5} more").classes("text-xs").style("color:#8b949e")

    element.on("click", lambda: open_card_dialog(card["id"], refresh_board, client_ids))


# ------------------------------------------------------------------
# Card dialog (create/edit)
# ------------------------------------------------------------------

def open_card_dialog(card_id, refresh_board, client_ids):
    card = db.get_card(card_id) if card_id else None
    is_edit = card is not None

    # Determine which clients this user/dialog may choose from
    if client_ids is None:
        available_clients = db.list_clients()
    else:
        all_clients = db.list_clients()
        available_clients = [c for c in all_clients if c["id"] in client_ids]

    client_options = {c["id"]: c["name"] for c in available_clients}
    current_client_id = card["client_id"] if is_edit else None
    if current_client_id is not None and current_client_id not in client_options:
        existing_client = db.get_client(current_client_id)
        if existing_client:
            client_options[existing_client["id"]] = existing_client["name"]

    current_user = auth.current_user()
    dialog_width = "w-[1160px]" if is_edit else "w-[600px]"

    with ui.dialog().props("persistent") as dialog, \
            ui.card().classes(f"{dialog_width} max-w-[96vw] p-0 overflow-hidden"):

        with ui.row(wrap=False).classes("w-full h-full"):

            # ── LEFT PANEL — card fields ────────────────────────────────────
            left_width = "w-[560px]" if is_edit else "w-full"
            with ui.column().classes(f"{left_width} flex-shrink-0 p-5 gap-3").style(
                "border-right: 1px solid #30363d; max-height: 82vh; overflow-y: auto;"
            ):
                with ui.row().classes("items-center gap-3 no-wrap"):
                    ui.label("Edit Card" if is_edit else "New Card").classes("text-lg font-bold")
                    if is_edit and card["card_number"]:
                        ui.label(card["card_number"]).style(
                            "font-family:'JetBrains Mono',monospace;"
                            "font-size:.8rem;font-weight:600;letter-spacing:.06em;"
                            "color:#e2e8f0;padding:2px 8px;"
                            f"background:#1e3a5f;border-radius:4px;border:1px solid #2563eb;"
                        )

                type_select = ui.select(
                    db.CARD_TYPES, label="Card Type",
                    value=card["card_type"] if is_edit else "Story"
                ).classes("w-full")
                if is_edit:
                    type_select.disable()

                title_input = ui.input("Title", value=card["title"] if is_edit else "").classes("w-full")

                default_client_id = current_client_id
                if default_client_id is None and len(client_options) == 1:
                    default_client_id = next(iter(client_options))

                client_select = ui.select(
                    client_options, label="Client", value=default_client_id, with_input=True
                ).classes("w-full")
                if not client_options:
                    ui.label(
                        "No clients available. Ask an administrator to create a client."
                    ).classes("text-xs").style("color:color:#f85149")

                dynamic_container = ui.column().classes("w-full gap-2")
                field_refs = {}

                def render_dynamic_fields(card_type):
                    dynamic_container.clear()
                    field_refs.clear()
                    with dynamic_container:
                        if card_type in ("Story", "Bug"):
                            ui.label("Description").classes("text-sm mt-1").style("color:color:#8b949e")
                            field_refs["description"] = ui.editor(
                                value=card["description"] if is_edit and card["description"] else ""
                            ).classes("w-full")
                            user_options = [u["full_name"] or u["username"] for u in db.list_users()]
                            current_assignee = (card["assignee"] if is_edit else None) or None
                            if current_assignee and current_assignee not in user_options:
                                user_options.append(current_assignee)
                            field_refs["assignee"] = ui.select(
                                user_options, label="Assignee", value=current_assignee,
                                with_input=True, clearable=True
                            ).classes("w-full")
                            field_refs["expected_delivery"] = ui.input(
                                "Expected Delivery Date",
                                value=card["expected_delivery"] if is_edit else ""
                            ).classes("w-full")
                            field_refs["expected_delivery"].props("type=date")

                            if is_edit:
                                ui.label("Attachments").classes("font-semibold mt-2")
                                attachments_container = ui.column().classes("w-full gap-1")
                                render_attachments(attachments_container, card["id"])

                                async def handle_upload(e: events.UploadEventArguments):
                                    upload_dir = os.path.join(db.UPLOAD_DIR, str(card["id"]))
                                    os.makedirs(upload_dir, exist_ok=True)
                                    dest_path = os.path.join(upload_dir, e.file.name)
                                    await e.file.save(dest_path)
                                    db.add_attachment(card["id"], e.file.name, dest_path)
                                    ui.notify(f"Uploaded {e.file.name}")
                                    render_attachments(attachments_container, card["id"])

                                ui.upload(on_upload=handle_upload, auto_upload=True).props(
                                    "accept='*'"
                                ).classes("w-full")
                            else:
                                ui.label("Save the card first to add attachments.").classes("text-xs").style("color:#8b949e")

                            if is_edit:
                                epics = db.get_card_epics(card["id"])
                                if epics:
                                    ui.label("Belongs to Epic(s):").classes("font-semibold mt-2")
                                    for ep in epics:
                                        with ui.row().classes("items-center gap-1"):
                                            ui.icon("auto_awesome", color="purple-6", size="16px")
                                            ui.link(ep["title"], "#").on(
                                                "click",
                                                lambda e, eid=ep["id"]: jump_to_card(
                                                    dialog, eid, refresh_board, client_ids)
                                            )

                        elif card_type == "Epic":
                            ui.label("Description").classes("text-sm mt-1").style("color:color:#8b949e")
                            field_refs["description"] = ui.editor(
                                value=card["description"] if is_edit and card["description"] else ""
                            ).classes("w-full")

                            ui.label("Linked Stories / Bugs").classes("font-semibold mt-2")
                            linked_container = ui.column().classes("w-full gap-1")

                            if is_edit:
                                render_linked_stories(
                                    linked_container, card["id"], refresh_board, dialog, client_ids)

                                ui.label("Add Story/Bug to this Epic").classes("font-semibold mt-2")
                                all_cards = db.list_cards(client_ids)
                                candidates = {
                                    c["id"]: f"{c['card_type']}: {c['title']}"
                                    for c in all_cards
                                    if c["card_type"] in ("Story", "Bug") and c["id"] != card["id"]
                                }
                                linked_ids = {s["id"] for s in db.get_epic_stories(card["id"])}
                                candidates = {k: v for k, v in candidates.items() if k not in linked_ids}

                                with ui.row().classes("w-full items-center gap-2"):
                                    select_story = ui.select(
                                        candidates, label="Select Story/Bug"
                                    ).classes("flex-grow")

                                    def add_link():
                                        if select_story.value:
                                            db.link_story_to_epic(card["id"], select_story.value)
                                            ui.notify("Linked")
                                            dialog.close()
                                            open_card_dialog(card["id"], refresh_board, client_ids)
                                            refresh_board()

                                    ui.button("Link", icon="link", on_click=add_link)
                            else:
                                ui.label("Save the Epic first to link stories.").classes("text-xs").style("color:#8b949e")

                render_dynamic_fields(type_select.value)
                type_select.on_value_change(lambda e: render_dynamic_fields(e.value))

                error_label = ui.label("").style("color:#f85149")

                with ui.row().classes("w-full justify-between mt-2"):
                    if is_edit:
                        ui.button("Delete", icon="delete", color="negative",
                                  on_click=lambda: confirm_delete(card["id"], dialog, refresh_board))
                    else:
                        ui.element("div")

                    with ui.row().classes("gap-2"):
                        ui.button("Cancel", on_click=dialog.close)

                        def save():
                            title = title_input.value.strip()
                            if not title:
                                error_label.set_text("Title is required")
                                return
                            if not client_select.value:
                                error_label.set_text("Client is required")
                                return

                            card_type = type_select.value

                            if is_edit:
                                updates = {"title": title, "client_id": client_select.value}
                                if card_type in ("Story", "Bug"):
                                    updates["description"] = field_refs.get("description").value if "description" in field_refs else None
                                    updates["assignee"] = field_refs.get("assignee").value if "assignee" in field_refs else None
                                    updates["expected_delivery"] = field_refs.get("expected_delivery").value if "expected_delivery" in field_refs else None
                                elif card_type == "Epic":
                                    updates["description"] = field_refs.get("description").value if "description" in field_refs else None
                                db.update_card(card["id"], **updates)
                                ui.notify("Card updated")
                            else:
                                kwargs = {"column_name": "Backlog", "client_id": client_select.value,
                                          "user_id": current_user["user_id"] if current_user else None}
                                if card_type in ("Story", "Bug"):
                                    kwargs["description"] = field_refs.get("description").value if "description" in field_refs else None
                                    kwargs["assignee"] = field_refs.get("assignee").value if "assignee" in field_refs else None
                                    kwargs["expected_delivery"] = field_refs.get("expected_delivery").value if "expected_delivery" in field_refs else None
                                elif card_type == "Epic":
                                    kwargs["description"] = field_refs.get("description").value if "description" in field_refs else None
                                db.create_card(card_type, title, **kwargs)
                                ui.notify("Card created")

                            dialog.close()
                            refresh_board()

                        ui.button("Save", on_click=save).props("color=primary")

            # ── RIGHT PANEL — comments + history (edit mode only) ────────────
            if is_edit:
                with ui.column().classes("flex-grow p-5 gap-0").style(
                    "max-height: 82vh; min-width: 0;"
                ):
                    panel_state = {"active": "comments"}
                    reply_state = {"parent_id": None, "parent_author": None}

                    # Tab header
                    with ui.row().classes("items-center gap-0").style(
                        "border-bottom:1px solid #30363d; margin-bottom:8px;"
                    ):
                        def tab_style(name):
                            active = panel_state["active"] == name
                            return (
                                "padding:6px 18px;font-size:.85rem;font-weight:600;cursor:pointer;"
                                "border-bottom:2px solid " + ("#2563eb" if active else "transparent") + ";"
                                "color:" + ("#e2e8f0" if active else "#64748b") + ";"
                            )
                        comments_tab_el = ui.label("Comments").style(tab_style("comments"))
                        history_tab_el  = ui.label("History").style(tab_style("history"))

                    @ui.refreshable
                    def right_panel():
                        if panel_state["active"] == "history":
                            events_list = db.get_card_history(card["id"])
                            with ui.scroll_area().classes("w-full").style(
                                "height:calc(82vh - 130px);min-height:180px;"
                            ):
                                with ui.column().classes("w-full").style("gap:0;padding:4px 2px;"):
                                    if not events_list:
                                        ui.label("No history yet.").style(
                                            "color:#8b949e;font-size:.85rem;"
                                            "margin-top:16px;text-align:center;width:100%;"
                                        )
                                    else:
                                        for i, ev in enumerate(events_list):
                                            is_last    = (i == len(events_list) - 1)
                                            user_name  = ev["user_name"] or ev["username"] or "System"
                                            user_color = ev["user_color"] or "#64748b"
                                            epoch      = ev["epoch"]
                                            from_col   = ev["from_column"]
                                            to_col     = ev["to_column"]

                                            with ui.row().classes("w-full gap-3 items-start").style("padding:6px 2px;"):
                                                with ui.column().classes("items-center").style("width:18px;flex-shrink:0;gap:0;"):
                                                    ui.element("div").style(
                                                        f"width:10px;height:10px;border-radius:50%;"
                                                        f"background:{user_color};margin-top:5px;"
                                                        f"border:2px solid #0d1117;flex-shrink:0;"
                                                    )
                                                    if not is_last:
                                                        ui.element("div").style(
                                                            "width:2px;height:34px;background:#30363d;"
                                                            "margin:3px auto 0;flex-shrink:0;"
                                                        )
                                                with ui.column().classes("flex-grow").style("gap:2px;"):
                                                    if from_col is None:
                                                        action = (
                                                            f'<span style="color:#e2e8f0;font-weight:600">{user_name}</span>'
                                                            f'<span style="color:#94a3b8"> created this card in </span>'
                                                            f'<span style="color:#60a5fa;font-weight:600">{to_col}</span>'
                                                        )
                                                    else:
                                                        action = (
                                                            f'<span style="color:#e2e8f0;font-weight:600">{user_name}</span>'
                                                            f'<span style="color:#94a3b8"> moved </span>'
                                                            f'<span style="color:#94a3b8">{from_col}</span>'
                                                            f'<span style="color:#475569"> → </span>'
                                                            f'<span style="color:#60a5fa;font-weight:600">{to_col}</span>'
                                                        )
                                                    ui.html(action).style("font-size:.85rem;line-height:1.5;")
                                                    # Timestamp: store epoch in data attr, convert via page-level JS
                                                    ui.html(
                                                        f'<span class="epoch-ts" data-epoch="{epoch}" '
                                                        f'style="font-size:.72rem;color:#64748b;">…</span>'
                                                    )
                                        # Convert all epoch spans to local time
                                        ui.run_javascript(
                                            "document.querySelectorAll('.epoch-ts').forEach("
                                            "el => el.textContent = new Date(parseInt(el.dataset.epoch)*1000).toLocaleString()"
                                            ");"
                                        )
                        else:
                            with ui.scroll_area().classes("w-full").style(
                                "height:calc(82vh - 260px);min-height:180px;"
                            ):
                                feed_inner = ui.column().classes("w-full").style("gap:0;")

                            def render_feed():
                                feed_inner.clear()
                                with feed_inner:
                                    comments  = db.get_comments(card["id"])
                                    top_level = [c for c in comments if c["parent_id"] is None]
                                    replies   = {}
                                    for c in comments:
                                        if c["parent_id"]:
                                            replies.setdefault(c["parent_id"], []).append(c)
                                    if not comments:
                                        ui.label("No comments yet. Be the first!").style(
                                            "color:#8b949e;font-size:.85rem;margin-top:16px;"
                                            "text-align:center;width:100%;"
                                        )

                                    def render_comment(c, indent=0):
                                        author_color = c["author_color"] or "#9e9e9e"
                                        with ui.column().classes("w-full gap-1").style(
                                            f"margin-left:{indent*22}px;margin-bottom:10px;"
                                        ):
                                            with ui.row().classes("items-center gap-2 w-full"):
                                                if c["author_avatar"] and os.path.exists(c["author_avatar"]):
                                                    rel = c["author_avatar"].replace(db.UPLOAD_DIR, "").lstrip("/\\")
                                                    ui.image(f"/uploads/{rel}").style(
                                                        "width:24px;height:24px;border-radius:50%;"
                                                        "object-fit:cover;flex-shrink:0;"
                                                    )
                                                else:
                                                    ui.element("div").style(
                                                        f"width:24px;height:24px;border-radius:50%;"
                                                        f"background:{author_color};flex-shrink:0;"
                                                        "display:flex;align-items:center;justify-content:center;"
                                                        "color:white;font-size:11px;font-weight:bold;"
                                                    ).text = (c["author_name"] or "?")[0].upper()
                                                ui.label(c["author_name"] or "Unknown").classes("font-semibold text-sm")
                                                ui.label(c["created_at"][:16].replace("T", " ")).classes("text-xs").style("color:#8b949e")
                                                if current_user and (
                                                    current_user["user_id"] == c["author_user_id"]
                                                    or current_user.get("is_admin")
                                                ):
                                                    def make_delete(cid=c["id"]):
                                                        def do_del():
                                                            db.delete_comment(cid, current_user["user_id"], current_user.get("is_admin", False))
                                                            render_feed()
                                                        return do_del
                                                    ui.button(icon="delete", on_click=make_delete()).props("flat round dense size=xs color=grey")
                                            ui.html(c["content"]).classes("text-sm ml-8 leading-relaxed").style(
                                                "background:#21262d;border-radius:6px;"
                                                "padding:8px 10px;margin-top:2px;color:#e6edf3;"
                                            )
                                            def make_reply(cid=c["id"], cname=c["author_name"]):
                                                def do_reply():
                                                    reply_state["parent_id"]     = cid
                                                    reply_state["parent_author"] = cname
                                                    reply_indicator.set_text(f"↩ Replying to {cname}")
                                                    cancel_btn.set_visibility(True)
                                                return do_reply
                                            ui.link("Reply", "#").classes("text-xs ml-8").style("color:#58a6ff;").on("click", make_reply())
                                            for r in replies.get(c["id"], []):
                                                render_comment(r, indent=indent + 1)
                                    for c in top_level:
                                        render_comment(c)

                            render_feed()

                            with ui.column().classes("w-full gap-1 mt-2").style(
                                "border-top:1px solid #30363d;padding-top:10px;flex-shrink:0;"
                            ):
                                with ui.row().classes("items-center gap-2"):
                                    reply_indicator = ui.label("").classes("text-xs italic").style("color:#58a6ff;")
                                    def cancel_reply():
                                        reply_state["parent_id"]     = None
                                        reply_state["parent_author"] = None
                                        reply_indicator.set_text("")
                                        cancel_btn.set_visibility(False)
                                    cancel_btn = ui.button(icon="close", on_click=cancel_reply).props("flat round dense size=xs")
                                    cancel_btn.set_visibility(False)
                                comment_editor = ui.editor(placeholder="Write a comment…").classes("w-full")
                                comment_editor.style("max-height:120px;overflow-y:auto;")
                                def post_comment():
                                    content_val = comment_editor.value.strip()
                                    if not content_val or content_val in ("<p></p>", "<p><br></p>"):
                                        ui.notify("Comment cannot be empty", color="warning")
                                        return
                                    db.add_comment(card["id"], current_user["user_id"], content_val, parent_id=reply_state["parent_id"])
                                    comment_editor.set_value("")
                                    cancel_reply()
                                    render_feed()
                                ui.button("Post Comment", icon="send", on_click=post_comment).props("color=primary dense").classes("self-end")

                    right_panel()

                    def switch_tab(name):
                        panel_state["active"] = name
                        comments_tab_el.style(tab_style("comments"))
                        history_tab_el.style(tab_style("history"))
                        right_panel.refresh()

                    comments_tab_el.on("click", lambda: switch_tab("comments"))
                    history_tab_el.on("click",  lambda: switch_tab("history"))

    dialog.open()


def render_attachments(container, card_id):
    container.clear()
    attachments = db.get_attachments(card_id)
    with container:
        if not attachments:
            ui.label("No attachments yet").classes("text-xs").style("color:color:#8b949e")
        for att in attachments:
            with ui.row().classes("items-center gap-2"):
                ui.icon("description", size="16px")
                ui.label(att["filename"]).classes("text-sm")

                def make_delete(att_id=att["id"]):
                    def delete():
                        db.delete_attachment(att_id)
                        render_attachments(container, card_id)
                    return delete

                ui.button(icon="close", on_click=make_delete()).props("flat round dense size=sm")


def render_linked_stories(container, epic_id, refresh_board, dialog, client_ids):
    container.clear()
    stories = db.get_epic_stories(epic_id)
    with container:
        if not stories:
            ui.label("No stories linked yet").classes("text-xs").style("color:color:#8b949e")
        for s in stories:
            with ui.row().classes("items-center gap-2 w-full"):
                ui.icon(CARD_TYPE_ICONS.get(s["card_type"]), color=CARD_TYPE_COLORS.get(s["card_type"]), size="16px")
                ui.link(f"{s['card_type']}: {s['title']}", "#").classes("flex-grow").on(
                    "click", lambda e, sid=s["id"]: jump_to_card(dialog, sid, refresh_board, client_ids)
                )
                ui.badge(s["column_name"]).props("color=grey-6")

                def make_unlink(story_id=s["id"]):
                    def unlink():
                        db.unlink_story_from_epic(epic_id, story_id)
                        ui.notify("Unlinked")
                        render_linked_stories(container, epic_id, refresh_board, dialog, client_ids)
                    return unlink

                ui.button(icon="link_off", on_click=make_unlink()).props("flat round dense size=sm")


def jump_to_card(current_dialog, target_card_id, refresh_board, client_ids):
    current_dialog.close()
    open_card_dialog(target_card_id, refresh_board, client_ids)


def confirm_delete(card_id, parent_dialog, refresh_board):
    with ui.dialog() as confirm, ui.card():
        ui.label("Delete this card? This cannot be undone.").classes("text-base")
        with ui.row().classes("w-full justify-end gap-2 mt-2"):
            ui.button("Cancel", on_click=confirm.close)

            def do_delete():
                db.delete_card(card_id)
                confirm.close()
                parent_dialog.close()
                ui.notify("Card deleted")
                refresh_board()

            ui.button("Delete", color="negative", on_click=do_delete)
    confirm.open()
