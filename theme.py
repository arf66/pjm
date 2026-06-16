"""Dark theme design system for PM Tracker (Cives-style)."""
from nicegui import ui

BG          = "#0d1117"
SURFACE     = "#161b22"
SURFACE2    = "#21262d"
BORDER      = "#30363d"
ACCENT      = "#2563eb"
TEXT        = "#e6edf3"
TEXT_MUTED  = "#8b949e"
SUCCESS     = "#3fb950"
DANGER      = "#f85149"
INFO        = "#58a6ff"

GLOBAL_CSS = f"""
body,html,.q-page,.nicegui-content{{background:{BG}!important;color:{TEXT}!important}}
/* Apply Inter only to non-icon elements */
body, button, input, select, textarea, label, p, span:not(.material-icons):not(.material-icons-outlined):not(.material-icons-round):not(.material-symbols-outlined), div, a{{font-family:'Inter','Segoe UI',sans-serif}}
/* Explicitly protect icon fonts */
.material-icons,.q-icon{{font-family:"Material Icons"!important;text-transform:none!important}}
.material-icons-outlined{{font-family:"Material Icons Outlined"!important;text-transform:none!important}}
.material-symbols-outlined{{font-family:"Material Symbols Outlined"!important;text-transform:none!important}}
.q-header{{background:{SURFACE}!important;border-bottom:1px solid {BORDER}!important;box-shadow:none!important}}
.q-card{{background:{SURFACE}!important;border:1px solid {BORDER}!important;box-shadow:0 4px 24px rgba(0,0,0,.4)!important;border-radius:10px!important;color:{TEXT}!important}}
.q-field__control{{background:{SURFACE2}!important;border-radius:6px!important}}
.q-field__control:before{{border-color:{BORDER}!important}}
.q-field__control:hover:before{{border-color:{ACCENT}!important}}
.q-field--focused .q-field__control:before{{border-color:{ACCENT}!important}}
.q-field__label{{color:{TEXT_MUTED}!important}}
.q-field__native,.q-field__input{{color:{TEXT}!important}}
.q-btn{{border-radius:6px!important}}
.q-menu{{background:{SURFACE2}!important;border:1px solid {BORDER}!important;box-shadow:0 8px 32px rgba(0,0,0,.5)!important;color:{TEXT}!important;border-radius:10px!important}}
.q-item{{color:{TEXT}!important}}
.q-item:hover{{background:{BORDER}!important}}
.q-separator{{background:{BORDER}!important;opacity:1!important}}
.q-table{{background:{SURFACE}!important;color:{TEXT}!important}}
.q-table__top,.q-table__bottom{{background:{SURFACE}!important}}
.q-table thead tr,.q-table th{{background:{SURFACE2}!important;color:{TEXT_MUTED}!important;font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;border-bottom:1px solid {BORDER}!important}}
.q-table tbody tr{{border-bottom:1px solid {BORDER}!important}}
.q-table tbody tr:hover{{background:rgba(48,54,61,.5)!important}}
.q-table td{{color:{TEXT}!important;border:none!important}}
.q-dialog__inner>div{{background:{SURFACE}!important;border:1px solid {BORDER}!important;box-shadow:0 16px 64px rgba(0,0,0,.7)!important;border-radius:12px!important;color:{TEXT}!important}}
.q-badge{{font-size:.65rem;font-weight:600;border-radius:4px;padding:2px 7px}}
.q-editor{{background:{SURFACE2}!important;border-color:{BORDER}!important;border-radius:6px!important}}
.q-editor__toolbar{{background:{SURFACE2}!important;border-color:{BORDER}!important}}
.q-editor__content{{background:{SURFACE2}!important;color:{TEXT}!important;min-height:80px}}
.q-editor__toolbar .q-btn{{color:{TEXT_MUTED}!important}}
.q-uploader{{background:{SURFACE2}!important;border-color:{BORDER}!important}}
.q-uploader__header{{background:{ACCENT}!important}}
.q-tooltip{{background:{SURFACE2}!important;color:{TEXT}!important;border:1px solid {BORDER};font-size:.75rem}}
.q-scrollarea__content{{background:transparent!important}}
.q-notification{{background:{SURFACE2}!important;border:1px solid {BORDER};color:{TEXT}!important}}
.q-checkbox__inner{{color:{TEXT_MUTED}!important}}
.q-checkbox__inner--truthy,.q-radio__inner--truthy{{color:{ACCENT}!important}}
.q-color-picker{{background:{SURFACE2}!important}}
.kanban-col{{background:{SURFACE}!important;border:1px solid {BORDER}!important;border-radius:10px}}
.kanban-card{{background:{SURFACE2}!important;border:1px solid {BORDER}!important;border-radius:8px!important;cursor:pointer;transition:border-color .15s,box-shadow .15s}}
.kanban-card:hover{{border-color:{ACCENT}!important;box-shadow:0 0 0 1px {ACCENT}!important}}
"""

def apply_theme():
    ui.add_head_html(f"""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
        <style>{GLOBAL_CSS}</style>
    """)
    ui.query("body").style(f"background:{BG};color:{TEXT};margin:0")
