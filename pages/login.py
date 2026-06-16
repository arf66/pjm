from nicegui import ui
import database as db
import auth
import theme


def login_page():
    if auth.is_authenticated():
        ui.navigate.to("/board")
        return

    theme.apply_theme()

    ui.add_head_html("""
    <style>
    .login-bg {
        position: fixed; inset: 0; z-index: 0;
        background: url('/static/login_bg.svg') center center / cover no-repeat;
    }
    .login-wrap {
        position: fixed; inset: 0; z-index: 1;
        display: flex; align-items: center; justify-content: flex-end;
        padding-right: 8%;
    }
    .login-card {
        background: rgba(22, 27, 34, 0.92);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(48, 54, 61, 0.9);
        border-radius: 18px;
        padding: 48px 40px 40px;
        width: 390px;
        box-shadow: 0 32px 80px rgba(0,0,0,0.75);
    }
    .sign-in-btn .q-btn__content { color: #ffffff !important; }
    .sign-in-btn { background: #2563eb !important; border-radius: 8px !important; }
    .sign-in-btn:hover { background: #1d4ed8 !important; }
    </style>
    """)

    ui.element("div").classes("login-bg")

    with ui.element("div").classes("login-wrap"):
        with ui.element("div").classes("login-card"):

            with ui.column().classes("items-center gap-1").style("margin-bottom:28px;"):
                ui.image("/static/logo_white.svg").style("width:72px;height:72px;")
                ui.label("PM Tracker").style(
                    f"color:{theme.TEXT};font-size:1.55rem;font-weight:700;"
                    "font-family:'JetBrains Mono',monospace;letter-spacing:.05em;"
                    "margin-top:8px;"
                )
                ui.label("PROJECT MANAGEMENT").style(
                    f"color:{theme.TEXT_MUTED};font-size:.6rem;font-weight:600;"
                    "letter-spacing:.22em;"
                )

            error_label = ui.label("").style(
                f"color:{theme.DANGER};font-size:.8rem;min-height:1.2em;"
                "text-align:center;width:100%;display:block;margin-bottom:4px;"
            )

            username = ui.input("Username").classes("w-full").style("margin-bottom:8px;")
            username.props("outlined dense dark")

            password = ui.input("Password", password=True, password_toggle_button=True).classes("w-full")
            password.props("outlined dense dark")

            def do_login():
                user = db.verify_login(username.value.strip(), password.value)
                if user:
                    auth.login(user)
                    ui.navigate.to("/board")
                else:
                    error_label.set_text("Invalid username or password")

            password.on("keydown.enter", do_login)

            # Use ui.button with classes that override everything via CSS above
            (ui.button("SIGN IN", on_click=do_login)
                .classes("w-full sign-in-btn")
                .props("no-caps unelevated")
                .style("height:50px;font-size:.88rem;font-weight:700;"
                       "letter-spacing:.14em;margin-top:20px;color:#ffffff;"))
