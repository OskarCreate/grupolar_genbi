"""Tema visual "Data Hub · Grupo Lar": estilos, íconos, formatos y barra lateral."""

from html import escape

import streamlit as st


# ------------------------------------------------------------------
# Paleta
# ------------------------------------------------------------------

ORANGE = "#F26B21"
ORANGE_DARK = "#D4560F"
ORANGE_SOFT = "#F7A877"
ORANGE_PALE = "#FDEBDD"
INK = "#26201D"
MUTED = "#857A75"
GRID = "#EEE8E4"
BAR_IDLE = "#E4DEDB"
GREEN = "#2F8559"
RED = "#C0392B"

PASTELS = [
    ("#FDEBDD", "#E0611B"),
    ("#ECEBFA", "#5B57B0"),
    ("#E5F4EC", "#2F8559"),
    ("#FBF0E1", "#B07A2E"),
    ("#E7EFFA", "#3F6BAE"),
    ("#F3E9F7", "#8A4AA6"),
]


# ------------------------------------------------------------------
# Íconos (trazo, estilo lucide)
# ------------------------------------------------------------------

_ICONS = {
    "arrows": '<path d="M8 3 4 7l4 4"/><path d="M4 7h16"/><path d="m16 21 4-4-4-4"/><path d="M20 17H4"/>',
    "box": '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
    "up": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    "down": '<polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/>',
    "flat": '<path d="M5 12h14"/>',
    "chart": '<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
    "grid": '<rect width="7" height="7" x="3" y="3" rx="1.5"/><rect width="7" height="7" x="14" y="3" rx="1.5"/><rect width="7" height="7" x="14" y="14" rx="1.5"/><rect width="7" height="7" x="3" y="14" rx="1.5"/>',
    "undo": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
    "calendar": '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
    "sparkles": '<path d="M9.94 15.5A2 2 0 0 0 8.5 14.06l-6.14-1.58a.5.5 0 0 1 0-.96L8.5 9.94A2 2 0 0 0 9.94 8.5l1.58-6.14a.5.5 0 0 1 .96 0L14.06 8.5a2 2 0 0 0 1.44 1.44l6.14 1.58a.5.5 0 0 1 0 .96l-6.14 1.58a2 2 0 0 0-1.44 1.44l-1.58 6.14a.5.5 0 0 1-.96 0z"/>',
    "file": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/>',
    "filter": '<path d="M3 6h18"/><path d="M7 12h10"/><path d="M10 18h4"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
}


def icon(name, size=18, color="currentColor", stroke=2):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{_ICONS[name]}</svg>'
    )


# ------------------------------------------------------------------
# Formatos (PEN)
# ------------------------------------------------------------------

def soles(value, compact=True):
    value = float(value or 0)
    if not compact:
        return f"S/ {value:,.0f}"
    if abs(value) >= 1_000_000:
        return f"S/ {value / 1_000_000:,.2f} M"
    if abs(value) >= 1_000:
        return f"S/ {value / 1_000:,.1f} mil"
    return f"S/ {value:,.0f}"


def entero(value):
    return f"{float(value or 0):,.0f}"


def pct(value, decimals=1):
    return f"{float(value or 0):.{decimals}f}%"


def e(text):
    return escape(str(text))


def html(markup):
    """Render trusted markup (already escaped). No blank lines, so Markdown never touches it."""
    st.markdown(markup, unsafe_allow_html=True)


# ------------------------------------------------------------------
# CSS global
# ------------------------------------------------------------------

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, .stApp, [data-testid="stSidebar"], .stMarkdown, button, input, select, textarea, [data-baseweb] {
  font-family: 'Plus Jakarta Sans', system-ui, -apple-system, 'Segoe UI', sans-serif !important;
}
.stApp { background: #F7F5F3; }
[data-testid="stHeader"] { background: transparent; }
.stAppDeployButton, [data-testid="stDecoration"] { display: none !important; }
[data-testid="stMainBlockContainer"] { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1480px; }
[data-testid="stVerticalBlock"] { gap: 1rem; }

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] > div:first-child {
  background: linear-gradient(180deg, #5B2510 0%, #3F1809 48%, #2A1006 100%);
}
[data-testid="stSidebar"] { border-right: none; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .35rem; }
[data-testid="stSidebar"] * { color: #F7ECE6; }
[data-testid="stSidebarCollapseButton"] svg, [data-testid="stSidebarHeader"] button svg { fill: #D7B8A8 !important; color: #D7B8A8 !important; }
.dh-brand { display:flex; align-items:center; gap:12px; padding: 0 4px 20px; }
.dh-logo { width:46px; height:46px; border-radius:13px; display:flex; flex-direction:column; align-items:center;
  justify-content:center; background: linear-gradient(135deg, #FF8A3D 0%, #E8590C 100%);
  box-shadow: 0 6px 16px rgba(242,107,33,.35); line-height:1; }
.dh-logo small { font-size:7.5px; font-weight:700; color:#FFE3D1 !important; letter-spacing:.04em; }
.dh-logo b { font-size:17px; font-weight:800; color:#fff !important; letter-spacing:-.02em; }
.dh-brand-name { font-weight:700; font-size:17px; line-height:1.2; color:#fff !important; }
.dh-brand-sub { font-size:12px; color:#D7B8A8 !important; }
.dh-nav-label { font-size:10.5px; letter-spacing:.14em; font-weight:600; color:#B8917F !important; margin: 14px 8px 6px; }
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
  border-radius:10px; padding: 9px 12px; border-left: 3px solid transparent; transition: background .15s;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover { background: rgba(255,255,255,.06); }
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"],
[data-testid="stSidebar"] [data-testid="stPageLink"] a[data-active="true"] {
  background: linear-gradient(90deg, rgba(242,107,33,.30), rgba(242,107,33,.10));
  border-left-color: #F26B21;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] p { font-weight:700; color:#fff !important; }
[data-testid="stSidebar"] [data-testid="stPageLink"] p { font-size:14.5px; font-weight:500; color:#F1DED4 !important; }
[data-testid="stSidebar"] [data-testid="stPageLink"] span[data-testid="stIconMaterial"] { color:#E9A57F !important; }
.dh-side-card { margin-top: 22px; padding:18px; border-radius:14px; background: rgba(255,255,255,.05);
  border:1px solid rgba(255,255,255,.08); }
.dh-side-card .dh-chip-ico { width:34px; height:34px; border-radius:10px; display:grid; place-items:center;
  background: rgba(242,107,33,.22); margin-bottom: 12px; }
.dh-side-card h4 { margin:0 0 6px; font-size:14.5px; font-weight:700; color:#fff !important; }
.dh-side-card p { margin:0; font-size:12.5px; line-height:1.5; color:#D7B8A8 !important; }
.dh-side-card { padding-bottom: 50px !important; }
.st-key-side_ask { margin-top: -30px; padding: 0 8px; position: relative; z-index: 1; }
.st-key-side_ask [data-testid="stPageLink"] a { padding: 4px 10px !important; background: transparent !important; border-left: none !important; }
.st-key-side_ask [data-testid="stPageLink"] p { color:#FF9A5C !important; font-weight:700 !important; font-size:13px !important; }
.dh-side-foot { margin-top: 18px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,.1);
  display:flex; gap:10px; align-items:center; }
.dh-avatar-s { width:36px; height:36px; border-radius:50%; display:grid; place-items:center; background:#FBE3D3;
  color:#B2470D !important; font-weight:700; font-size:12px; }
.dh-side-foot b { display:block; font-size:13px; color:#fff !important; }
.dh-side-foot span { font-size:11.5px; color:#B8917F !important; }

/* ---------- Topbar & header ---------- */
.dh-crumb { font-size:13px; color:#8F8480; }
.dh-crumb b { color:#E0611B; font-weight:600; }
.dh-topline { height:1px; background:#ECE6E2; margin: 4px 0 6px; }
.dh-kicker { font-size:11px; font-weight:700; letter-spacing:.14em; color:#E0611B; }
.dh-title { font-size:34px; font-weight:800; color:#26201D; margin: 4px 0 4px; letter-spacing:-.02em; line-height:1.15; }
.dh-subtitle { font-size:14px; color:#857A75; }
.dh-updated { font-size:12px; color:#857A75; display:flex; align-items:center; gap:7px; justify-content:flex-end; padding-bottom:4px; }
.dh-updated i { width:8px; height:8px; border-radius:50%; background:#2FB36B; box-shadow:0 0 0 3px rgba(47,179,107,.18); }
.stDownloadButton button, .stButton button { border-radius:12px; font-weight:600; min-height:42px; }
.st-key-export .stDownloadButton button { background: linear-gradient(135deg, #FF7B2E, #E8590C) !important; color:#fff !important;
  border:none !important; box-shadow: 0 6px 16px rgba(232,89,12,.28); }
.st-key-export .stDownloadButton button p { color:#fff !important; }
.st-key-ask_top [data-testid="stPageLink"] a { border:1px solid #E6DFDB; border-radius:12px; background:#fff; padding:8px 12px;
  justify-content:center; min-height:42px; }
.st-key-ask_top [data-testid="stPageLink"] p { font-size:13.5px; font-weight:600; color:#4A3F3B !important; }

/* ---------- Filter bar ---------- */
.st-key-card_filters { background:#fff; border:1px solid #EFE9E5; border-radius:16px; padding: 12px 18px 14px;
  box-shadow: 0 1px 2px rgba(38,32,29,.04), 0 8px 24px rgba(38,32,29,.04); }
.st-key-card_filters [data-testid="stWidgetLabel"] p { font-size:10.5px !important; font-weight:600; letter-spacing:.1em;
  color:#9A8E89 !important; text-transform:uppercase; }
.st-key-card_filters div[data-baseweb="select"] > div { border-radius:10px; border-color:#E6DFDB; min-height:38px; background:#fff; }
.dh-filter-label { display:flex; align-items:center; gap:8px; font-size:13.5px; font-weight:600; color:#4A3F3B; height:40px; white-space:nowrap; position:relative; top:-12px; }

/* ---------- Cards ---------- */
.dh-card { background:#fff; border:1px solid #EFE9E5; border-radius:18px; padding:20px 22px;
  box-shadow: 0 1px 2px rgba(38,32,29,.04), 0 8px 24px rgba(38,32,29,.04); }
div[class*="st-key-card_"]:not(.st-key-card_filters):not(.st-key-card_genbi) {
  background:#fff; border:1px solid #EFE9E5; border-radius:18px; padding:20px 22px 16px;
  box-shadow: 0 1px 2px rgba(38,32,29,.04), 0 8px 24px rgba(38,32,29,.04); }
.dh-card-title { font-size:16.5px; font-weight:700; color:#26201D; margin:0; }
.dh-card-sub { font-size:12.5px; color:#857A75; margin-top:3px; }
.dh-head { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom: 14px; }
.dh-pill { display:inline-flex; align-items:center; gap:6px; font-size:12px; color:#5E524D; background:#F7F2EF;
  border:1px solid #EDE5E1; padding:6px 10px; border-radius:10px; white-space:nowrap; }
.dh-link { font-size:12.5px; font-weight:700; color:#E0611B !important; text-decoration:none; }

/* KPI */
.dh-kpi { min-height: 160px; margin-bottom: 4px; }
.dh-kpi.is-main { border:1.5px solid #F6B48A; box-shadow: 0 0 0 4px rgba(242,107,33,.06), 0 8px 24px rgba(38,32,29,.05); }
.dh-kpi-ico { width:40px; height:40px; border-radius:12px; display:grid; place-items:center; margin-bottom:16px; }
.dh-kpi-label { font-size:11px; font-weight:600; letter-spacing:.09em; color:#857A75; white-space:nowrap; display:flex; gap:5px; align-items:center; }
.dh-kpi-value { font-size:30px; font-weight:700; color:#26201D; letter-spacing:-.02em; margin: 6px 0 8px; line-height:1.1; white-space:nowrap; }
.dh-delta { font-size:11.5px; color:#8F8480; display:flex; align-items:center; gap:5px; white-space:nowrap; }
.dh-delta b { font-weight:600; }

/* Rows & bars */
.dh-row { display:grid; align-items:center; gap:12px; }
.dh-track { height:6px; border-radius:99px; background:#F2EDEA; position:relative; overflow:hidden; }
.dh-fill { position:absolute; left:0; top:0; bottom:0; border-radius:99px; }
.dh-small { font-size:11.5px; color:#8F8480; }
.dh-name { font-size:13px; font-weight:600; color:#26201D; }
.dh-num { font-size:12.5px; color:#26201D; font-variant-numeric: tabular-nums; text-align:right; white-space:nowrap; }
.dh-avatar { width:36px; height:36px; border-radius:11px; display:grid; place-items:center; font-size:11.5px; font-weight:700; }
.dh-rank { width:24px; height:24px; border-radius:7px; display:grid; place-items:center; font-size:11.5px; font-weight:700;
  background:#FDEBDD; color:#D4560F; }
.dh-tag { font-size:10.5px; font-weight:600; padding:3px 8px; border-radius:99px; white-space:nowrap; }
.dh-cover { font-size:11.5px; font-weight:600; color:#2F7A55; background:#E6F4EC; border-radius:8px; padding:4px 9px; white-space:nowrap; }
.dh-legend { display:flex; gap:14px; font-size:11.5px; color:#857A75; }
.dh-legend i { display:inline-block; width:9px; height:9px; border-radius:3px; margin-right:6px; vertical-align:-1px; }
.dh-note { display:flex; align-items:center; gap:10px; font-size:12.5px; color:#6E625D; }
.dh-note .dh-dot { width:30px; height:30px; border-radius:9px; background:#FDEBDD; display:grid; place-items:center; flex:none; }
.dh-th { font-size:10.5px; font-weight:600; letter-spacing:.09em; color:#9A8E89; }
.dh-table-head { background:#FAF6F3; border-radius:10px; padding:10px 14px; }
.dh-table-row { padding:12px 14px; border-top:1px solid #F2EDEA; }
.dh-scroll { overflow-x:auto; }
.dh-source { font-size:11.5px; color:#9A8E89; margin-top: 6px; display:flex; flex-wrap:wrap; justify-content:space-between; gap:8px; }
.dh-caveat { font-size:11.5px; color:#9A8E89; display:flex; gap:6px; align-items:flex-start; margin-top:10px; }
.dh-caveat svg { flex:none; margin-top:1px; }

/* Segmented control inside cards */
div[class*="st-key-card_"] [data-testid="stButtonGroup"] button { min-height:30px; padding: 2px 12px; border-radius:9px; font-size:12px; }

/* Link-like buttons (Ver los 10 recursos, etc.) */
div[class*="st-key-more_"] [data-testid="stPageLink"] a { padding:2px 0 !important; background:transparent !important; }
div[class*="st-key-more_"] [data-testid="stPageLink"] p { color:#E0611B !important; font-weight:700 !important; font-size:12.5px !important; }
/* tarjetas de la misma fila con igual altura */
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:only-child:has(> div[class*="st-key-card_"]) {
  flex:1 1 auto; display:flex; flex-direction:column; }
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:only-child > div[class*="st-key-card_"] { flex:1 1 auto; }
.st-key-toggle_rec .stButton button { background:transparent !important; border:none !important; box-shadow:none !important; min-height:30px; }
.st-key-toggle_rec .stButton button p { color:#E0611B !important; font-weight:700; font-size:13px; }
.st-key-csv_rec .stDownloadButton button { background:#fff !important; border:1px solid #E6DFDB !important; color:#4A3F3B !important; min-height:38px; }
.st-key-csv_rec .stDownloadButton button p { color:#4A3F3B !important; font-size:13px; }

/* ---------- GenBI card (full width) ---------- */
.st-key-card_genbi { border-radius:20px; padding: 24px 28px 18px;
  background: radial-gradient(90% 140% at 100% 100%, #C2531A 0%, #7A2E0E 38%, #4A1C08 70%, #3A1506 100%);
  border:1px solid rgba(255,255,255,.06); box-shadow: 0 12px 32px rgba(74,28,8,.25); }
.st-key-card_genbi * { color:#FBEDE5; }
.dh-g-label { font-size:10.5px; letter-spacing:.14em; font-weight:700; color:#FFA26B !important; }
.dh-g-title { font-size:19px; font-weight:700; color:#fff !important; }
.dh-g-ico { width:42px; height:42px; border-radius:12px; display:grid; place-items:center; background: rgba(255,255,255,.1); }
.dh-g-text { font-size:14px; line-height:1.6; color:#F6E2D8 !important; margin: 14px 0; }
.dh-g-stat { display:flex; align-items:center; gap:16px; padding: 16px 0; border-top:1px solid rgba(255,255,255,.12);
  border-bottom:1px solid rgba(255,255,255,.12); flex-wrap:wrap; }
.dh-g-stat b { font-size:36px; font-weight:700; color:#FFA26B !important; letter-spacing:-.02em; }
.dh-g-stat span { font-size:13px; line-height:1.5; color:#F1D3C3 !important; }
.dh-g-finds { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:14px; margin: 16px 0 6px; }
.dh-g-find { display:flex; gap:10px; align-items:flex-start; font-size:12.5px; line-height:1.5; color:#F1D3C3 !important; }
.dh-g-find svg { flex:none; margin-top:2px; }
.dh-g-find b { color:#fff !important; }
.st-key-card_genbi .stButton button { background: transparent !important; border:none !important; box-shadow:none !important;
  padding-left:0; justify-content:flex-start; min-height:34px; }
.st-key-card_genbi .stButton button p { color:#FFA26B !important; font-weight:700; font-size:13.5px; }
.st-key-card_genbi .stButton button:hover p { color:#FFC199 !important; }
.st-key-card_genbi [data-testid="stCaptionContainer"] p { color:#D9B5A3 !important; }
.dh-g-out { margin-top: 6px; padding:16px; border-radius:14px; background: rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.1); }
.dh-g-h { margin:0 0 6px; font-size:14.5px; font-weight:700; color:#fff !important; }
.dh-g-p { margin:0; font-size:13.5px; line-height:1.6; color:#F6E2D8 !important; }
.dh-g-out small { display:block; margin-top:8px; font-size:11.5px; color:#D9B5A3 !important; }
/* ---------- Generar dashboard ---------- */
@media (max-width: 640px) { .dh-head { flex-wrap: wrap; } .dh-head > div:first-child { flex: 1 1 100%; } }
.st-key-card_prompt textarea { font-size:14px !important; line-height:1.55 !important; border-radius:12px !important; background:#FFFCFA !important; }
div[class*="st-key-chip_"] .stButton button { border-radius:99px !important; border:1px solid #F3D3BF !important; background:#FFF6F0 !important;
  min-height:32px; padding:2px 12px; }
div[class*="st-key-chip_"] .stButton button p { font-size:12.5px !important; color:#B2470D !important; font-weight:600; white-space:nowrap; }
div[class*="st-key-chip_"] .stButton button:hover { background:#FDEBDD !important; border-color:#F7A877 !important; }
.st-key-gen_go .stButton button { background: linear-gradient(135deg, #FF7B2E, #E8590C) !important; border:none !important;
  color:#fff !important; box-shadow: 0 6px 16px rgba(242,107,33,.28); min-height:42px; border-radius:12px; }
.st-key-gen_go .stButton button p { color:#fff !important; font-weight:700; }
.dh-plan { display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap:16px; }
.dh-chips { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; align-items:center; }
.dh-chip { font-size:12px; font-weight:600; padding:5px 10px; border-radius:99px; background:#FDEBDD; color:#B2470D; }
.dh-chip.is-chart { background:#F4EFEC; color:#4A3F3B; }
.dh-chip.is-filter { background:#E6F4EC; color:#2F7A55; }
.dh-gov { margin-top:14px; padding:12px 14px; border-radius:12px; background:#FAF6F3; font-size:12.5px; color:#5E524D; }
.dh-gov b { color:#26201D; font-size:12.5px; }
.dh-gov ul { margin:6px 0 0; padding-left:18px; }
.dh-gov li { margin:2px 0; }
.dh-gov.is-warn { background:#FFF4E5; }
.st-key-csv_gen .stDownloadButton button, .st-key-csv_plan .stDownloadButton button { background:#fff !important;
  border:1px solid #E6DFDB !important; min-height:40px; border-radius:12px; }
.st-key-csv_gen .stDownloadButton button p, .st-key-csv_plan .stDownloadButton button p { color:#4A3F3B !important; font-size:13px; }
</style>
"""


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)


# ------------------------------------------------------------------
# Identidad de AWS (para el pie de la barra lateral)
# ------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def aws_identity():
    """Return (user, account) from STS, or (None, None) if credentials are not available."""
    try:
        import boto3

        identity = boto3.client("sts").get_caller_identity()
        user = identity["Arn"].split("/")[-1]
        return user, identity["Account"]
    except Exception:
        return None, None


# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------

def sidebar(groups, genbi_page):
    """groups: list of (label, [st.Page, ...])."""
    with st.sidebar:
        html(
            '<div class="dh-brand"><div class="dh-logo"><small>grupo</small><b>lar</b></div>'
            '<div><div class="dh-brand-name">Data Hub</div>'
            '<div class="dh-brand-sub">Inteligencia de negocio</div></div></div>'
        )
        for label, pages in groups:
            html(f'<div class="dh-nav-label">{e(label)}</div>')
            for page in pages:
                st.page_link(page)

        html(
            '<div class="dh-side-card">'
            f'<div class="dh-chip-ico">{icon("sparkles", 18, "#FF9A5C")}</div>'
            '<h4>GenBI Insights</h4>'
            '<p>Describe el dashboard que necesitas: Bedrock elige métricas y gráficos, '
            'la capa semántica gobierna y Athena calcula.</p></div>'
        )
        with st.container(key="side_ask"):
            st.page_link(genbi_page, label="Generar dashboard →")

        user, account = aws_identity()
        if user:
            initials = "".join(part[0] for part in user.replace(".", " ").split()[:2]).upper() or user[:2].upper()
            initials = (user[:2] if len(initials) < 2 else initials).upper()
            footer = (f'<div class="dh-avatar-s">{e(initials)}</div>'
                      f'<div><b>{e(user)}</b><span>Cuenta AWS ••••{e(str(account)[-4:])}</span></div>')
        else:
            footer = ('<div class="dh-avatar-s">DH</div>'
                      '<div><b>Amazon Athena</b><span>grupolar_master · 2025</span></div>')
        html(f'<div class="dh-side-foot">{footer}</div>')
