"""Componentes del dashboard Data Hub (compartidos por todas las páginas)."""

import io
import re
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.athena import AthenaClient
from src.bedrock import BedrockClient
from src.config import load_json, load_settings
from src.dashboard_data import DashboardData
from src.insight import generate_insight
from src.ui import (
    BAR_IDLE, GREEN, GRID, INK, MUTED, ORANGE, ORANGE_SOFT, PASTELS, RED,
    e, entero, html, icon, pct, soles,
)

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]
ABREV = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Set", "Oct", "Nov", "Dic"]
TIPO_SEDE = {"ALMACEN": "Almacén", "OBRA": "Obra"}
FONT = "Plus Jakarta Sans, system-ui, sans-serif"
TODOS = "Todos"
GENBI_PAGE = "views/genbi.py"


# ==================================================================
# Contexto y datos
# ==================================================================

@st.cache_resource(show_spinner=False)
def get_context():
    settings = load_settings()
    semantic = load_json("config/semantic_layer.json")
    athena = AthenaClient(
        region=settings["aws_region"],
        database=settings["athena_database"],
        output_s3=settings["athena_output_s3"],
        workgroup=settings.get("athena_workgroup", "primary"),
    )
    bedrock = BedrockClient(region=settings["aws_region"], model_id=settings["bedrock_model_id"])
    return settings, semantic, athena, bedrock


@st.cache_data(ttl=600, show_spinner=False)
def _load(filter_items):
    _, semantic, athena, _ = get_context()
    return DashboardData(athena, semantic).load(dict(filter_items))


def load_data(filters):
    """Load (cached 10 min) all datasets for the given filters, or stop the page with a clear error."""
    try:
        with st.spinner("Consultando Athena…"):
            return _load(tuple(sorted((k, v) for k, v in filters.items() if v)))
    except Exception as exc:
        st.error("No se pudieron cargar los datos desde Athena.")
        st.caption(
            "Revisa que exista `config/settings.json`, que `aws sts get-caller-identity` funcione "
            "y que la vista `vw_grupolar_genbi_transferencias` esté creada en `grupolar_master`."
        )
        st.exception(exc)
        st.stop()


def semantic_layer():
    return get_context()[1]


# ==================================================================
# Filtros (persisten entre páginas)
# ==================================================================

DEFAULTS = {"anio": "2025", "mes": TODOS, "sede": "Todas las sedes", "tipo_sede": TODOS, "cuenta": "Todas"}


def _state():
    if "F" not in st.session_state:
        st.session_state["F"] = dict(DEFAULTS)
    return st.session_state["F"]


def _sync(name):
    st.session_state["F"][name] = st.session_state[f"w_{name}"]


def set_filters(values):
    """Preset filters (from a generated plan) before the selectors are drawn."""
    f = _state()
    f["mes"] = MESES[values["mes"] - 1] if values.get("mes") else TODOS
    f["sede"] = values.get("sede") or DEFAULTS["sede"]
    f["tipo_sede"] = {"OBRA": "Obra", "ALMACEN": "Almacén"}.get(values.get("tipo_sede"), TODOS)
    f["cuenta"] = values.get("cuenta") or DEFAULTS["cuenta"]
    for name in ("mes", "sede", "tipo_sede", "cuenta"):
        st.session_state[f"w_{name}"] = f[name]


def set_mes(mes_num):
    label = MESES[mes_num - 1] if mes_num else TODOS
    _state()["mes"] = label
    st.session_state["w_mes"] = label


def current_filters():
    """Filters in the form DashboardData expects."""
    f = _state()
    return {
        "mes": None if f["mes"] == TODOS else MESES.index(f["mes"]) + 1,
        "sede": None if f["sede"] == DEFAULTS["sede"] else f["sede"],
        "tipo_sede": None if f["tipo_sede"] == TODOS else {"Almacén": "ALMACEN", "Obra": "OBRA"}[f["tipo_sede"]],
        "cuenta": None if f["cuenta"] == DEFAULTS["cuenta"] else f["cuenta"].split(" · ")[0],
    }


def periodo_texto(filters):
    return "ene – dic 2025" if not filters.get("mes") else f"{MESES[filters['mes'] - 1].lower()} 2025"


def filter_bar(controls=None):
    """controls: subset of anio, mes, sede, tipo_sede, cuenta (all by default)."""
    f = _state()
    sem = semantic_layer()
    sedes = [DEFAULTS["sede"]] + sem["dimensions"]["sede_origen"].get("values", [])
    cuentas = [DEFAULTS["cuenta"]] + sem["dimensions"]["cuenta_contable"].get("values", [])
    options = {
        "anio": ["2025"],
        "mes": [TODOS] + MESES,
        "sede": sedes,
        "tipo_sede": [TODOS, "Almacén", "Obra"],
        "cuenta": cuentas,
    }
    labels = {"anio": "Año", "mes": "Mes", "sede": "Sede", "tipo_sede": "Tipo de sede", "cuenta": "Cuenta"}
    helps = {
        "sede": "Incluye las transferencias que la sede envía y las que recibe.",
        "tipo_sede": "Se aplica a la sede de destino (la que recibe), según la capa semántica.",
    }
    with st.container(key="card_filters"):
        names = [n for n in ["anio", "mes", "sede", "tipo_sede", "cuenta"] if not controls or n in controls]
        widths = {"anio": 1, "mes": 1.15, "sede": 1.6, "tipo_sede": 1.15, "cuenta": 1.15}
        spare = [6.05 - 0.9 - sum(widths[n] for n in names)] if len(names) < 5 else []
        cols = st.columns([0.9] + [widths[n] for n in names] + spare, vertical_alignment="bottom", gap="small")
        with cols[0]:
            html(f'<div class="dh-filter-label">{icon("filter", 17, "#4A3F3B")}Filtrar por</div>')
        for col, name in zip(cols[1:], names):
            with col:
                key = f"w_{name}"
                if key not in st.session_state:
                    st.session_state[key] = f[name] if f[name] in options[name] else options[name][0]
                st.selectbox(labels[name], options[name], key=key, on_change=_sync, args=(name,),
                             help=helps.get(name))
    return current_filters()


# ==================================================================
# Encabezado de página
# ==================================================================

def topbar(crumb, data=None):
    left, ask, export = st.columns([4.6, 1.05, 1.25], vertical_alignment="center")
    with left:
        html(f'<div class="dh-crumb"><b>Data Mart</b> &nbsp;/&nbsp; {e(crumb)}</div>')
    with ask:
        with st.container(key="ask_top"):
            st.page_link(GENBI_PAGE, label="Preguntar", icon=":material/search:")
    with export:
        with st.container(key="export"):
            if data is not None:
                buffer = io.StringIO()
                buffer.write("Grupo Lar - Data Hub - Transferencias internas\n")
                for name in ("kpis", "mensual", "sedes", "cuentas", "recursos", "usuarios"):
                    buffer.write(f"\n{name.upper()}\n")
                    data[name].to_csv(buffer, index=False)
                st.download_button("Exportar reporte", buffer.getvalue().encode("utf-8-sig"),
                                   file_name="grupolar_reporte.csv", mime="text/csv",
                                   icon=":material/download:", width="stretch")
    html('<div class="dh-topline"></div>')


def page_header(kicker, title, subtitle, data):
    left, right = st.columns([3, 1], vertical_alignment="bottom")
    with left:
        html(f'<div class="dh-kicker">{e(kicker)}</div><div class="dh-title">{e(title)}</div>'
             f'<div class="dh-subtitle">{e(subtitle)}</div>')
    with right:
        minutes = int((time.time() - data["loaded_at"]) // 60)
        when = "hace menos de 1 min" if minutes < 1 else f"hace {minutes} min"
        html(f'<div class="dh-updated"><i></i>Actualizado {when}</div>')


def footer(data):
    html(
        '<div class="dh-source"><span>Fuente: Amazon Athena · grupolar_master.vw_grupolar_genbi_transferencias · '
        'métricas de la capa semántica aprobada</span>'
        '<span>Plan de cuentas real (CONCAR) · transferencias, recursos y sedes simulados con fines académicos</span></div>'
    )
    with st.expander("Ver SQL gobernado de esta página"):
        for name, sql in data["sql"].items():
            st.markdown(f"**{name}**")
            st.code(sql, language="sql")


# ==================================================================
# KPI
# ==================================================================

def _delta(current, previous, filters, kind="pct", higher_is_better=True):
    if previous is None:
        text = "Acumulado ene – dic 2025" if not filters.get("mes") else "Primer mes del año"
        return f'<div class="dh-delta">{icon("calendar", 13, "#A0948F")}<span>{text}</span></div>'
    current, previous = float(current or 0), float(previous or 0)
    if kind == "pp":
        change = current - previous
        value = f"{change:+.1f} pp"
    else:
        change = (current - previous) / previous * 100 if previous else 0
        value = f"{change:+.1f}%"
    good = (change >= 0) == higher_is_better
    color = GREEN if good else RED
    ico = "flat" if abs(change) < 0.05 else ("up" if change > 0 else "down")
    return (f'<div class="dh-delta">{icon(ico, 13, color)}<b style="color:{color}">{value}</b>'
            f'<span>vs. {MESES[filters["mes"] - 2].lower()}</span></div>')


def kpi_row(data, filters):
    k = data["kpis"].iloc[0]
    p = data["kpis_anterior"].iloc[0] if "kpis_anterior" in data else None
    g = (lambda col: None if p is None else p[col])
    cards = [
        ("arrows", PASTELS[0], "TRANSFERENCIAS", entero(k.numero_transferencias),
         _delta(k.numero_transferencias, g("numero_transferencias"), filters), ""),
        ("box", PASTELS[1], "CANTIDAD TRANSFERIDA", entero(k.cantidad_transferida),
         _delta(k.cantidad_transferida, g("cantidad_transferida"), filters),
         "Suma unidades de recursos distintos (bolsas, m3, kg…): referencial."),
        ("up", PASTELS[2], "VALOR TRANSFERIDO", soles(k.valor_transferido),
         _delta(k.valor_transferido, g("valor_transferido"), filters), ""),
        ("chart", PASTELS[3], "MONTO NETO", soles(k.monto_total_neto),
         _delta(k.monto_total_neto, g("monto_total_neto"), filters), ""),
        ("grid", PASTELS[4], "PORCENTAJE REVERTIDO", pct(k.porcentaje_revertido),
         _delta(k.porcentaje_revertido, g("porcentaje_revertido"), filters, kind="pp", higher_is_better=False), ""),
    ]
    for i, (col, (ico, (bg, fg), label, value, delta, tip)) in enumerate(zip(st.columns(5, gap="small"), cards)):
        with col:
            info = (f'<span title="{e(tip)}" style="display:inline-flex;cursor:help">{icon("info", 12, "#B3A7A2")}</span>'
                    if tip else "")
            html(f'<div class="dh-card dh-kpi{" is-main" if i == 0 else ""}">'
                 f'<div class="dh-kpi-ico" style="background:{bg}">{icon(ico, 19, fg)}</div>'
                 f'<div class="dh-kpi-label">{label}{info}</div><div class="dh-kpi-value">{value}</div>{delta}</div>')


# ==================================================================
# Valor transferido por mes (columnas, clic filtra)
# ==================================================================

def _on_month_click():
    event = st.session_state.get("chart_mes")
    try:
        points = event["selection"]["points"] if event else []
    except (KeyError, TypeError):
        points = []
    if points and points[0].get("x") in ABREV:
        set_mes(ABREV.index(points[0]["x"]) + 1)


def _base_layout(fig, height):
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=26, b=0), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=MUTED, size=11), dragmode=False,
        hoverlabel=dict(bgcolor=INK, font=dict(color="#fff", family=FONT)),
    )
    return fig


def card_valor(data, filters, height=255):
    mensual = data["mensual"].copy()
    mensual["mes"] = mensual["mes"].astype(int)
    k = data["kpis"].iloc[0]
    with st.container(key="card_valor"):
        if mensual.empty:
            html('<div class="dh-card-title">Valor transferido</div>')
            st.info("No hay transferencias para estos filtros.")
            return
        pico = mensual.loc[mensual["valor_transferido"].idxmax()]
        destacado = filters.get("mes") or int(pico["mes"])
        html(
            '<div class="dh-head"><div><div class="dh-card-title">Valor transferido</div>'
            '<div class="dh-card-sub">Evolución mensual del monto transferido · clic en un mes para filtrar</div></div>'
            f'<div class="dh-pill">{icon("calendar", 14, "#5E524D")}Ene – Dic 2025</div></div>'
            '<div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap">'
            f'<span style="font-size:28px;font-weight:700;color:{INK};letter-spacing:-.02em;white-space:nowrap">'
            f'{soles(k.valor_transferido)}</span>'
            f'<span class="dh-small">monto bruto transferido · {e(periodo_texto(filters))}</span></div>'
        )
        x = [ABREV[m - 1] for m in mensual["mes"]]
        y = mensual["valor_transferido"].astype(float).tolist()
        fig = go.Figure(go.Bar(
            x=x, y=y,
            marker=dict(color=[ORANGE if m == destacado else BAR_IDLE for m in mensual["mes"]]),
            text=[f"{v / 1000:,.0f}k" if m == destacado else "" for m, v in zip(mensual["mes"], y)],
            textposition="outside", textfont=dict(color=ORANGE, size=12, family=FONT),
            customdata=mensual["numero_transferencias"],
            hovertemplate="<b>%{x}</b><br>S/ %{y:,.2f}<br>%{customdata} transferencias<extra></extra>",
            selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)), cliponaxis=False,
        ))
        _base_layout(fig, height).update_layout(
            barcornerradius=7, bargap=0.42,
            xaxis=dict(showgrid=False, tickfont=dict(size=11, color=MUTED), fixedrange=True),
            yaxis=dict(showgrid=True, gridcolor=GRID, griddash="dash", zeroline=False, showticklabels=False, fixedrange=True),
        )
        st.plotly_chart(fig, key="chart_mes", on_select=_on_month_click, selection_mode="points",
                        config={"displayModeBar": False}, width="stretch")
        html(f'<div class="dh-note"><div class="dh-dot">{icon("sparkles", 15, ORANGE)}</div>'
             f'<span>{e(pico["nombre_mes"])} registró el pico anual con {soles(pico["valor_transferido"])} transferidos '
             f'({entero(pico["numero_transferencias"])} transferencias).</span></div>')


# ==================================================================
# Usuarios
# ==================================================================

def card_usuarios(data, filters, limit=None, min_height=None):
    usuarios = data["usuarios"]
    total = float(usuarios["numero_transferencias"].sum()) or 1
    max_t = float(usuarios["numero_transferencias"].max() if len(usuarios) else 1) or 1
    shown = usuarios if limit is None else usuarios.head(limit)
    rows = []
    for i, u in enumerate(shown.itertuples()):
        bg, fg = PASTELS[i % len(PASTELS)]
        rows.append(
            '<div class="dh-row" style="grid-template-columns:36px 1fr 46px;margin-bottom:16px">'
            f'<div class="dh-avatar" style="background:{bg};color:{fg}">{e(str(u.usuario)[:2])}</div>'
            '<div><div style="display:flex;justify-content:space-between;gap:8px;margin-bottom:7px">'
            f'<span class="dh-name">{e(u.usuario)}</span>'
            f'<span class="dh-small">{entero(u.numero_transferencias)} transferencias</span></div>'
            f'<div class="dh-track"><div class="dh-fill" style="width:{u.numero_transferencias / max_t * 100:.1f}%;'
            f'background:{ORANGE}"></div></div></div>'
            f'<div class="dh-num">{pct(u.numero_transferencias / total * 100)}</div></div>'
        )
    with st.container(key="card_usuarios"):
        html('<div class="dh-head"><div><div class="dh-card-title">Transferencias por usuario</div>'
             f'<div class="dh-card-sub">Participación en el periodo · {e(periodo_texto(filters))}</div></div></div>'
             + "".join(rows))
        if limit is not None and len(usuarios) > limit:
            with st.container(key="more_usuarios"):
                st.page_link("views/usuarios.py", label=f"Ver todos los usuarios ({len(usuarios)}) →")


# ==================================================================
# Sedes (valor o cantidad)
# ==================================================================

def sedes_pivot(data, measure):
    sedes = data["sedes"]
    if sedes.empty:
        return pd.DataFrame(columns=["sede", "tipo_sede", "ENVIADO", "RECIBIDO", "total"])
    pivot = sedes.pivot_table(index=["sede", "tipo_sede"], columns="rol", values=measure,
                              aggfunc="sum", fill_value=0).reset_index()
    for column in ("ENVIADO", "RECIBIDO"):
        if column not in pivot:
            pivot[column] = 0.0
    pivot["total"] = pivot["ENVIADO"] + pivot["RECIBIDO"]
    return pivot.sort_values(["tipo_sede", "total"], ascending=[True, False])


def card_sedes(data, key="card_sedes", show_profile=False):
    with st.container(key=key):
        head, toggle = st.columns([2.2, 1.4], vertical_alignment="top")
        with head:
            html('<div class="dh-card-title">Movimiento por sede</div>'
                 '<div class="dh-card-sub">Recursos enviados (origen) vs. recibidos (destino)</div>')
        with toggle:
            metric = st.segmented_control("Medida", ["Cantidad", "Valor S/"], default="Cantidad",
                                          key=f"seg_{key}", label_visibility="collapsed")
        metric = metric or "Cantidad"
        measure = "cantidad_transferida" if metric == "Cantidad" else "valor_transferido"
        fmt = entero if metric == "Cantidad" else (lambda v: soles(v))
        pivot = sedes_pivot(data, measure)
        max_v = float(pivot[["ENVIADO", "RECIBIDO"]].to_numpy().max()) if len(pivot) else 1
        max_v = max_v or 1
        cols = "minmax(140px,1.3fr) minmax(90px,2.4fr) 72px 72px" + (" 96px" if show_profile else "")
        rows = []
        for s in pivot.itertuples():
            tag = ""
            if show_profile:
                receptora = s.RECIBIDO > s.ENVIADO
                tag = ('<div style="text-align:right"><span class="dh-tag" style="background:#FDEBDD;color:#C2500D">Receptora</span></div>'
                       if receptora else
                       '<div style="text-align:right"><span class="dh-tag" style="background:#F1ECEA;color:#5E524D">Proveedora</span></div>')
            rows.append(
                f'<div class="dh-row" style="grid-template-columns:{cols};padding:10px 0;border-top:1px solid #F2EDEA">'
                f'<div><div class="dh-name">{e(s.sede)}</div><div class="dh-small">{e(TIPO_SEDE.get(s.tipo_sede, s.tipo_sede))}</div></div>'
                '<div style="display:flex;flex-direction:column;gap:5px">'
                f'<div class="dh-track"><div class="dh-fill" style="width:{s.ENVIADO / max_v * 100:.1f}%;background:{ORANGE}"></div></div>'
                f'<div class="dh-track"><div class="dh-fill" style="width:{s.RECIBIDO / max_v * 100:.1f}%;background:{ORANGE_SOFT}"></div></div></div>'
                f'<div class="dh-num">{fmt(s.ENVIADO)}</div><div class="dh-num">{fmt(s.RECIBIDO)}</div>{tag}</div>'
            )
        header = (f'<div class="dh-row dh-th" style="grid-template-columns:{cols};padding:4px 0 8px">'
                  '<span>SEDE</span>'
                  f'<span class="dh-legend"><span><i style="background:{ORANGE}"></i>Enviado</span>'
                  f'<span><i style="background:{ORANGE_SOFT}"></i>Recibido</span></span>'
                  '<span style="text-align:right">ENVIADO</span><span style="text-align:right">RECIBIDO</span>'
                  + ('<span style="text-align:right">PERFIL</span>' if show_profile else '') + '</div>')
        note = ("La cantidad suma unidades de recursos distintos; para comparar sedes usa «Valor S/» (regla de la capa semántica)."
                if metric == "Cantidad" else "Valor transferido = SUM(monto_debe), métrica gobernada.")
        html(f'<div class="dh-scroll"><div style="min-width:{560 if show_profile else 450}px">{header}{"".join(rows)}</div></div>'
             f'<div class="dh-caveat">{icon("info", 13, "#B3A7A2")}<span>{e(note)}</span></div>')
        return pivot


# ==================================================================
# Cuentas contables
# ==================================================================

def clean_account(description, code):
    """'Materias primas - Materias primas - Costo [24111]' -> 'Materias primas · Costo'."""
    text = re.sub(rf"\s*\[{re.escape(str(code))}\]\s*$", "", str(description))
    parts = [p.strip() for p in text.split(" - ")]
    deduped = [p for i, p in enumerate(parts) if i == 0 or p != parts[i - 1]]
    return " · ".join(deduped)


def card_cuentas(data, min_height=None):
    cuentas = data["cuentas"]
    total = float(cuentas["monto_total_neto"].sum()) or 1
    max_c = float(cuentas["monto_total_neto"].max() if len(cuentas) else 1) or 1
    rows = []
    for i, c in enumerate(cuentas.itertuples(), start=1):
        share = c.monto_total_neto / total * 100
        rows.append(
            '<div style="padding:9px 0;border-top:1px solid #F2EDEA">'
            '<div class="dh-row" style="grid-template-columns:24px 1fr auto 52px;gap:10px">'
            f'<span class="dh-rank">{i}</span>'
            f'<div style="min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
            f'<b style="font-size:13px;color:{INK}">{e(c.codigo_cuenta)}</b>'
            f'<span class="dh-small" style="margin-left:8px">{e(clean_account(c.descripcion_cuenta, c.codigo_cuenta))}</span></div>'
            f'<span class="dh-num" style="font-weight:600">{soles(c.monto_total_neto, compact=False)}</span>'
            f'<span class="dh-num" style="color:{ORANGE};font-weight:700">{pct(share)}</span></div>'
            f'<div class="dh-track" style="margin:7px 62px 0 34px"><div class="dh-fill" style="width:{c.monto_total_neto / max_c * 100:.1f}%;'
            f'background:{ORANGE if i <= 2 else ORANGE_SOFT}"></div></div></div>'
        )
    top2 = cuentas.head(2)
    share2 = float(top2["monto_total_neto"].sum()) / total * 100 if len(top2) else 0
    note = (f'Las cuentas {" y ".join(e(x) for x in top2["codigo_cuenta"])} concentran el {pct(share2)} del monto neto.'
            if len(top2) > 1 else "")
    with st.container(key="card_cuentas"):
        html('<div class="dh-head"><div><div class="dh-card-title">Cuentas contables</div>'
             '<div class="dh-card-sub">Participación sobre el monto neto</div></div>'
             '<div class="dh-pill">Debe − Haber</div></div>' + "".join(rows)
             + f'<div class="dh-small" style="margin-top:12px;padding-top:10px;border-top:1px solid #F2EDEA">{note}</div>')


# ==================================================================
# GenBI Insights (ancho completo)
# ==================================================================

def card_genbi(data, filters):
    k = data["kpis"].iloc[0]
    cuentas = data["cuentas"]
    pivot = sedes_pivot(data, "valor_transferido")
    mensual = data["mensual"]
    if cuentas.empty or pivot.empty or mensual.empty:
        return
    total = float(cuentas["monto_total_neto"].sum()) or 1
    top2 = cuentas.head(2)
    share2 = float(top2["monto_total_neto"].sum()) / total * 100
    proveedora = pivot.sort_values("ENVIADO", ascending=False).iloc[0]
    receptora = pivot.sort_values("RECIBIDO", ascending=False).iloc[0]
    pico = mensual.loc[mensual["valor_transferido"].idxmax()]
    descs = " y ".join(e(clean_account(r.descripcion_cuenta, r.codigo_cuenta).lower()) for r in top2.itertuples())
    periodo = periodo_texto(filters)

    with st.container(key="card_genbi"):
        html(
            f'<div style="display:flex;gap:14px;align-items:center"><div class="dh-g-ico">{icon("sparkles", 20, "#FFA26B")}</div>'
            '<div><div class="dh-g-label">ANÁLISIS GENERADO</div><div class="dh-g-title">GenBI Insights</div></div></div>'
            f'<div class="dh-g-text">Los almacenes abastecen a las obras: {e(proveedora.sede)} es la principal sede proveedora '
            f'({soles(proveedora.ENVIADO)} enviados) y {e(receptora.sede)} la principal receptora ({soles(receptora.RECIBIDO)}) '
            f'en {e(periodo)}, con una concentración marcada en dos cuentas contables.</div>'
            f'<div class="dh-g-stat"><b>{pct(share2)}</b><span>del monto neto se concentra en las cuentas '
            f'{" y ".join(e(x) for x in top2["codigo_cuenta"])} ({descs}).</span></div>'
            '<div class="dh-g-finds">'
            f'<div class="dh-g-find">{icon("calendar", 15, "#FFA26B")}<span>Mes pico: <b>{e(pico["nombre_mes"])}</b>, '
            f'con {soles(pico["valor_transferido"])} transferidos.</span></div>'
            f'<div class="dh-g-find">{icon("undo", 15, "#FFA26B")}<span>Se revirtió el <b>{pct(k.porcentaje_revertido)}</b> '
            f'del valor ({soles(k.monto_haber)} en devoluciones o anulaciones).</span></div>'
            f'<div class="dh-g-find">{icon("file", 15, "#FFA26B")}<span><b>{entero(k.numero_comprobantes)}</b> comprobantes '
            f'con {entero(k.numero_transferencias)} líneas de transferencia.</span></div></div>'
        )
        cache_key = f"genbi_insight_{periodo}_{filters.get('sede')}_{filters.get('tipo_sede')}_{filters.get('cuenta')}"
        if st.button("Ver análisis completo con Bedrock →", key="btn_genbi"):
            resumen = pd.concat([
                data["kpis"].assign(tabla="kpis"),
                cuentas.head(6).assign(tabla="cuentas"),
                pivot[["sede", "tipo_sede", "ENVIADO", "RECIBIDO"]].assign(tabla="sedes_valor_soles"),
            ], ignore_index=True)
            with st.spinner("Bedrock está analizando…"):
                try:
                    st.session_state[cache_key] = generate_insight(
                        get_context()[3],
                        f"Resumen ejecutivo de transferencias internas de Grupo Lar ({periodo})",
                        resumen, semantic_layer=semantic_layer(), max_rows=40,
                    )
                except Exception as exc:
                    st.session_state[cache_key] = {"headline": "No se pudo generar el análisis",
                                                   "insight": str(exc), "caveat": ""}
        result = st.session_state.get(cache_key)
        if result:
            html('<div class="dh-g-out">'
                 f'<div class="dh-g-h">{e(result.get("headline", ""))}</div>'
                 f'<div class="dh-g-p">{e(result.get("insight", ""))}</div>'
                 + (f'<small>{e(result["caveat"])}</small>' if result.get("caveat") else "") + '</div>')


# ==================================================================
# Recursos con mayor rotación (tabla)
# ==================================================================

def card_recursos(data, show_all=False, allow_toggle=True, title="Recursos con mayor rotación",
                  subtitle="Top de recursos transferidos entre obras"):
    recursos = data["recursos"]
    n_obras = len(semantic_layer()["dimensions"]["sede_destino"].get("values", [])) or 6
    expanded = show_all or st.session_state.get("rec_all", False)
    shown = recursos if expanded else recursos.head(5)
    max_r = float(recursos["numero_transferencias"].max()) if len(recursos) else 1
    cols = "44px minmax(220px,2.6fr) 1fr 1fr 1.1fr 1.1fr"
    with st.container(key="card_recursos"):
        head, btn = st.columns([4, 1.1], vertical_alignment="top")
        with head:
            html(f'<div class="dh-card-title">{e(title)}</div><div class="dh-card-sub">{e(subtitle)}</div>')
        with btn:
            with st.container(key="csv_rec"):
                st.download_button("Descargar CSV", recursos.to_csv(index=False).encode("utf-8-sig"),
                                   file_name="grupolar_recursos_rotacion.csv", mime="text/csv",
                                   icon=":material/download:", width="stretch")
        rows = []
        for i, r in enumerate(shown.itertuples(), start=1):
            rows.append(
                f'<div class="dh-row dh-table-row" style="grid-template-columns:{cols}">'
                f'<span class="dh-rank">{i}</span>'
                f'<div style="min-width:0"><div class="dh-name" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
                f'{e(r.descripcion_recurso)}</div><div class="dh-small">{e(str(r.familia_recurso).capitalize())}</div></div>'
                f'<span class="dh-num" style="text-align:left">{entero(r.numero_transferencias)}</span>'
                f'<span class="dh-num" style="text-align:left">{entero(r.cantidad_transferida)} '
                f'<span class="dh-small">{e(r.unidad_medida)}</span></span>'
                f'<span><span class="dh-cover">{entero(r.obras_destino)} de {n_obras} obras</span></span>'
                f'<div class="dh-track" style="max-width:130px"><div class="dh-fill" '
                f'style="width:{r.numero_transferencias / max_r * 100:.1f}%;background:{ORANGE}"></div></div></div>'
            )
        header = (f'<div class="dh-row dh-th dh-table-head" style="grid-template-columns:{cols}">'
                  '<span>#</span><span>RECURSO</span><span>TRANSFERENCIAS</span><span>CANTIDAD</span>'
                  '<span>COBERTURA</span><span>ROTACIÓN</span></div>')
        html(f'<div class="dh-scroll" style="margin-top:10px"><div style="min-width:760px">{header}{"".join(rows)}</div></div>')
        if allow_toggle and not show_all and len(recursos) > 5:
            _, mid, _ = st.columns([2, 1.2, 2])
            with mid:
                with st.container(key="toggle_rec"):
                    label = "Ver menos ↑" if expanded else f"Ver los {len(recursos)} recursos →"
                    if st.button(label, width="stretch"):
                        st.session_state["rec_all"] = not expanded
                        st.rerun()


# ==================================================================
# Gráficos de la Parte B (visualización óptima por pregunta)
# ==================================================================

def chart_card(key, title, subtitle, figure, note=None):
    with st.container(key=key):
        html(f'<div class="dh-head"><div><div class="dh-card-title">{e(title)}</div>'
             f'<div class="dh-card-sub">{e(subtitle)}</div></div></div>')
        st.plotly_chart(figure, config={"displayModeBar": False}, width="stretch")
        if note:
            html(f'<div class="dh-caveat">{icon("info", 13, "#B3A7A2")}<span>{e(note)}</span></div>')


def fig_linea_mensual(data, filters):
    """P5 · Línea: evolución mensual de las transferencias."""
    m = data["mensual"].copy()
    m["mes"] = m["mes"].astype(int)
    x = [ABREV[i - 1] for i in m["mes"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=m["numero_transferencias"], mode="lines+markers", name="Transferencias",
        line=dict(color=ORANGE, width=3, shape="spline", smoothing=0.6),
        marker=dict(size=8, color="#fff", line=dict(color=ORANGE, width=2.5)),
        fill="tozeroy", fillcolor="rgba(242,107,33,.08)",
        hovertemplate="<b>%{x}</b><br>%{y} transferencias<extra></extra>",
    ))
    if filters.get("mes"):
        sel = m[m["mes"] == filters["mes"]]
        if len(sel):
            fig.add_trace(go.Scatter(x=[ABREV[filters["mes"] - 1]], y=sel["numero_transferencias"], mode="markers",
                                     marker=dict(size=13, color=ORANGE), hoverinfo="skip"))
    _base_layout(fig, 300).update_layout(
        xaxis=dict(showgrid=False, fixedrange=True),
        yaxis=dict(gridcolor=GRID, griddash="dash", zeroline=False, fixedrange=True, title=None),
    )
    return fig


def fig_sedes_apiladas(data, measure="valor_transferido"):
    """P1 · Barras apiladas: sedes en el eje X, divididas en enviado / recibido."""
    pivot = sedes_pivot(data, measure)
    def wrap(name):
        words = name.replace(" - ", " ").split()
        half = (len(words) + 1) // 2
        return " ".join(words[:half]) + "<br>" + " ".join(words[half:])
    labels = [wrap(s) for s in pivot["sede"]]
    money = measure == "valor_transferido"
    tpl = "S/ %{y:,.0f}" if money else "%{y:,.0f}"
    fig = go.Figure([
        go.Bar(x=labels, y=pivot["ENVIADO"], name="Enviado", marker_color=ORANGE,
               hovertemplate=f"<b>%{{x}}</b><br>Enviado: {tpl}<extra></extra>"),
        go.Bar(x=labels, y=pivot["RECIBIDO"], name="Recibido", marker_color=ORANGE_SOFT,
               hovertemplate=f"<b>%{{x}}</b><br>Recibido: {tpl}<extra></extra>"),
    ])
    _base_layout(fig, 360).update_layout(
        barmode="stack", bargap=0.45, barcornerradius=6, showlegend=True,
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right", font=dict(size=12), traceorder="normal"),
        xaxis=dict(showgrid=False, fixedrange=True, tickfont=dict(size=11), tickangle=0),
        yaxis=dict(gridcolor=GRID, griddash="dash", zeroline=False, fixedrange=True,
                   tickprefix="S/ " if money else "", tickformat=",.0s" if money else ",.0f"),
    )
    return fig


def fig_treemap_cuentas(data):
    """P2 · Treemap: cuentas contables por monto neto."""
    c = data["cuentas"].copy()
    total = float(c["monto_total_neto"].sum()) or 1
    c["label"] = [f"{r.codigo_cuenta} · {clean_account(r.descripcion_cuenta, r.codigo_cuenta)}" for r in c.itertuples()]
    c["share"] = c["monto_total_neto"] / total * 100
    shades = ["#E8590C", "#F26B21", "#F5874A", "#F7A877", "#F9C4A2", "#FBDCC8"]
    fig = go.Figure(go.Treemap(
        labels=c["label"], parents=[""] * len(c), values=c["monto_total_neto"],
        customdata=c[["share", "porcentaje_revertido"]],
        marker=dict(colors=shades[: len(c)], line=dict(color="#fff", width=3)),
        texttemplate="<b>%{label}</b><br>S/ %{value:,.0f}<br>%{customdata[0]:.1f}%",
        hovertemplate="<b>%{label}</b><br>Monto neto: S/ %{value:,.2f}<br>Participación: %{customdata[0]:.1f}%"
                      "<br>% revertido: %{customdata[1]:.1f}%<extra></extra>",
        textfont=dict(family=FONT, size=13, color=["#fff"] * 3 + [INK] * max(len(c) - 3, 0)),
        tiling=dict(pad=3), branchvalues="total",
    ))
    _base_layout(fig, 380).update_layout(margin=dict(l=0, r=0, t=6, b=0),
                                         uniformtext=dict(minsize=10, mode="hide"))
    return fig


def fig_recursos_horizontal(data):
    """P3 · Barras horizontales ordenadas por número de transferencias."""
    r = data["recursos"].sort_values("numero_transferencias")
    fig = go.Figure(go.Bar(
        y=r["descripcion_recurso"], x=r["numero_transferencias"], orientation="h",
        marker=dict(color=[ORANGE if i == len(r) - 1 else ORANGE_SOFT for i in range(len(r))]),
        text=r["numero_transferencias"], textposition="outside",
        textfont=dict(color=INK, size=12, family=FONT),
        customdata=r[["cantidad_transferida", "unidad_medida", "obras_destino"]],
        hovertemplate="<b>%{y}</b><br>%{x} transferencias<br>%{customdata[0]:,.0f} %{customdata[1]}"
                      "<br>%{customdata[2]} obras<extra></extra>",
        cliponaxis=False,
    ))
    _base_layout(fig, 420).update_layout(
        barcornerradius=5, bargap=0.35, margin=dict(l=0, r=30, t=6, b=0),
        xaxis=dict(gridcolor=GRID, griddash="dash", zeroline=False, fixedrange=True),
        yaxis=dict(showgrid=False, fixedrange=True, tickfont=dict(size=12, color=INK)),
    )
    return fig


def fig_heatmap_usuarios(data):
    """P4 · Mapa de calor: usuarios (filas) x meses (columnas), intensidad = transferencias."""
    um = data["usuario_mes"].copy()
    um["mes"] = um["mes"].astype(int)
    grid = um.pivot_table(index="usuario", columns="mes", values="numero_transferencias", fill_value=0)
    grid = grid.reindex(columns=range(1, 13), fill_value=0)
    grid = grid.loc[grid.sum(axis=1).sort_values().index]
    fig = go.Figure(go.Heatmap(
        z=grid.values, x=ABREV, y=grid.index, xgap=4, ygap=4,
        colorscale=[[0, "#FBF4EF"], [0.35, "#F9C4A2"], [0.7, "#F5874A"], [1, "#D4560F"]],
        text=grid.values, texttemplate="%{text}", textfont=dict(size=11, family=FONT),
        hovertemplate="<b>%{y}</b> · %{x}<br>%{z} transferencias<extra></extra>",
        colorbar=dict(thickness=10, outlinewidth=0, tickfont=dict(size=10)),
    ))
    _base_layout(fig, 330).update_layout(
        margin=dict(l=0, r=0, t=6, b=0),
        xaxis=dict(showgrid=False, fixedrange=True, side="top"),
        yaxis=dict(showgrid=False, fixedrange=True, tickfont=dict(size=12, color=INK)),
    )
    return fig


def guard_empty(data):
    """Stop the page with a friendly message when the filter combination returns no rows."""
    if float(data["kpis"].iloc[0].numero_transferencias or 0) > 0:
        return
    html(f'<div class="dh-card" style="text-align:center;padding:48px 24px">'
         f'<div class="dh-kpi-ico" style="background:#FDEBDD;margin:0 auto 14px">{icon("filter", 19, ORANGE)}</div>'
         '<div class="dh-card-title">No hay transferencias para esta combinación de filtros</div>'
         '<div class="dh-card-sub" style="margin-top:6px">Recuerda que «Tipo de sede» se aplica a la sede de destino: '
         'en Grupo Lar los almacenes solo envían, por eso «Almacén» no devuelve filas. Cambia o limpia los filtros.</div></div>')
    st.button("Limpiar filtros", key="btn_clear", icon=":material/restart_alt:", on_click=reset_filters)
    st.stop()


def reset_filters():
    st.session_state["F"] = dict(DEFAULTS)
    for name, value in DEFAULTS.items():
        st.session_state[f"w_{name}"] = value
