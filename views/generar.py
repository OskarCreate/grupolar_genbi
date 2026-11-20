"""Generar dashboard: el usuario describe el dashboard y GenBI lo construye."""

import io
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import dash
from src.dashboard_generator import (
    CHART_TYPES, TIME_DIMENSIONS, VIRTUAL_SEDE_ROL, GeneratedDashboard,
    measure_kind, plan_dashboard, validate_plan,
)
from src.insight import generate_insight
from src.ui import (
    BAR_IDLE, GRID, INK, MUTED, ORANGE, ORANGE_SOFT, PASTELS,
    e, entero, html, icon, pct, soles,
)

EJEMPLOS = {
    "Prompt ejecutivo (PPT)": (
        "Quiero un dashboard ejecutivo de las transferencias internas de recursos de Grupo Lar en 2025, con KPIs de "
        "número de transferencias, cantidad transferida, valor transferido, monto total neto y porcentaje revertido; "
        "la evolución mensual del valor transferido; una comparación de los recursos enviados y recibidos por cada sede "
        "u obra; las cuentas contables con mayor monto y su porcentaje revertido; el top 10 de recursos con mayor "
        "rotación entre obras; y la participación de cada usuario en el registro de transferencias. Con filtros por "
        "año, mes, sede, tipo de sede y cuenta."
    ),
    "Abastecimiento de obras": (
        "Muéstrame en agosto cuánto valor y cuántos comprobantes se enviaron a las obras, qué familias de recursos "
        "pesan más y qué obras recibieron más. Con filtro por sede."
    ),
    "Control de reversiones": (
        "Quiero controlar las reversiones: porcentaje revertido y monto haber, su evolución mensual y qué cuentas "
        "contables tienen mayor porcentaje revertido. Con filtros por mes y cuenta."
    ),
    "Carga por usuario": (
        "¿Cómo se reparte el registro de transferencias entre los usuarios a lo largo del año? Incluye cuántos "
        "comprobantes registra cada uno."
    ),
}
TYPE_LABEL = {"line": "Línea", "bar": "Barras", "hbar": "Barras horizontales", "stacked_bar": "Barras apiladas",
              "treemap": "Treemap", "donut": "Dona", "heatmap": "Mapa de calor", "table": "Tabla"}
FONT = dash.FONT
SERIES_COLORS = [ORANGE, "#7A3210", "#F7A877", "#5E524D", "#E3A61B", "#B3A7A2", "#2F7A55", "#3F1809"]


def set_prompt(text):
    st.session_state["gen_prompt"] = text


semantic = dash.semantic_layer()
settings, _, athena, bedrock = dash.get_context()
measures = semantic["measures"]
dimensions = semantic["dimensions"]


def mlabel(name):
    return measures[name]["label"].split(" (")[0]


def dlabel(name):
    if name == VIRTUAL_SEDE_ROL:
        return "Sede (envía / recibe)"
    if name == "periodo_mes":
        return "Mes"
    return dimensions[name].get("label", name).split(" (")[0]


def fmt(value, kind, compact=True):
    if value is None or pd.isna(value):
        return "—"
    return soles(value, compact=compact) if kind == "money" else (pct(value) if kind == "pct" else entero(value))


def hover_fmt(kind, axis="y"):
    return {"money": f"S/ %{{{axis}:,.2f}}", "pct": f"%{{{axis}:.1f}}%", "count": f"%{{{axis}:,.0f}}"}[kind]


# ==================================================================
# Encabezado y prompt
# ==================================================================

dash.topbar("Generar dashboard")
html(
    '<div class="dh-kicker">GENBI · DASHBOARD GENERATIVO</div>'
    '<div class="dh-title">Generar dashboard</div>'
    '<div class="dh-subtitle">Describe el dashboard que necesitas. Bedrock elige las métricas y los gráficos, '
    'la capa semántica los gobierna y Athena calcula cada cifra.</div>'
)

if "gen_prompt" not in st.session_state:
    st.session_state["gen_prompt"] = EJEMPLOS["Prompt ejecutivo (PPT)"]

with st.container(key="card_prompt"):
    html(f'<div class="dh-head"><div><div class="dh-card-title">¿Qué dashboard necesitas?</div>'
         '<div class="dh-card-sub">Escribe en lenguaje natural: KPI, análisis, gráficos y filtros. Puedes partir de un ejemplo.</div></div>'
         f'<div class="dh-pill">{icon("sparkles", 14, ORANGE)}Bedrock · {e(settings["bedrock_model_id"].split(".")[-1].split(":")[0])}</div></div>')
    chips = st.columns(len(EJEMPLOS), gap="small")
    for col, (label, text) in zip(chips, EJEMPLOS.items()):
        with col:
            with st.container(key=f"chip_{list(EJEMPLOS).index(label)}"):
                st.button(label, on_click=set_prompt, args=(text,), width="stretch")
    prompt = st.text_area("Prompt", key="gen_prompt", height=118, label_visibility="collapsed",
                          placeholder="Ej.: Quiero ver el valor transferido por mes y qué obras reciben más recursos…")
    go_col, info_col = st.columns([1.1, 4], vertical_alignment="center")
    with go_col:
        with st.container(key="gen_go"):
            generate = st.button("Generar dashboard", icon=":material/auto_awesome:", type="primary", width="stretch")
    with info_col:
        html('<div class="dh-small">Una llamada a Bedrock por generación. Bedrock no escribe SQL: solo elige medidas y '
             'dimensiones aprobadas; el SQL se arma con las fórmulas de la capa semántica y pasa por el SQL Guard.</div>')

if generate:
    if len(prompt.strip()) < 12:
        st.warning("Describe un poco más el dashboard que necesitas.")
    else:
        with st.spinner("Bedrock está diseñando el dashboard…"):
            try:
                raw = plan_dashboard(bedrock, prompt, semantic)
                plan, notes = validate_plan(raw, semantic)
                st.session_state["gen_result"] = {"prompt": prompt, "raw": raw, "plan": plan, "notes": notes}
                dash.set_filters(plan["filters"])
                st.session_state.pop("gen_insight", None)
            except Exception as exc:
                st.error("Bedrock no pudo generar el plan del dashboard. Revisa el modelo en settings.json o reformula el pedido.")
                st.exception(exc)

result = st.session_state.get("gen_result")
if not result:
    html('<div class="dh-card" style="text-align:center;padding:42px 24px">'
         f'<div class="dh-kpi-ico" style="background:#FDEBDD;margin:0 auto 14px">{icon("sparkles", 19, ORANGE)}</div>'
         '<div class="dh-card-title">Tu dashboard aparecerá aquí</div>'
         '<div class="dh-card-sub" style="margin-top:6px">Elige un ejemplo o escribe tu pedido y pulsa «Generar dashboard».</div></div>')
    st.stop()

plan, notes = result["plan"], result["notes"]

# ==================================================================
# Cómo lo interpretó Bedrock
# ==================================================================

with st.container(key="card_plan"):
    chips_kpi = "".join(f'<span class="dh-chip">{e(mlabel(k))}</span>' for k in plan["kpis"])
    chips_chart = "".join(
        f'<span class="dh-chip is-chart">{e(TYPE_LABEL[c["type"]])} · {e(mlabel(c["measure"]))} por {e(dlabel(c["dimension"]))}'
        + (f' × {e(dlabel(c["series"]))}' if c["series"] else "") + '</span>'
        for c in plan["charts"])
    pretty = {"mes": lambda v: f"Mes: {dash.MESES[int(v) - 1]}", "sede": lambda v: f"Sede: {v}",
              "tipo_sede": lambda v: f"Destino: {'Obra' if v == 'OBRA' else 'Almacén'}", "cuenta": lambda v: f"Cuenta: {v}"}
    active = [pretty[k](v) for k, v in plan["filters"].items() if v]
    chips_filter = "".join(f'<span class="dh-chip is-filter">{e(x)}</span>' for x in active) or '<span class="dh-small">Sin filtros previos</span>'
    controls = ", ".join({"anio": "año", "mes": "mes", "sede": "sede", "tipo_sede": "tipo de sede", "cuenta": "cuenta"}[c]
                         for c in plan["filter_controls"]) or "ninguno"
    gov = "".join(f'<li>{e(n)}</li>' for n in notes)
    unsupported = "".join(f'<li>{e(n)}</li>' for n in plan["not_supported"])
    html(
        f'<div class="dh-head"><div><div class="dh-card-title">Cómo interpretó GenBI tu pedido</div>'
        f'<div class="dh-card-sub">{e(plan["interpretation"])}</div></div>'
        f'<div class="dh-pill">{icon("info", 14, "#5E524D")}Plan validado con la capa semántica</div></div>'
        '<div class="dh-plan">'
        f'<div><div class="dh-th">KPI</div><div class="dh-chips">{chips_kpi}</div></div>'
        f'<div><div class="dh-th">GRÁFICOS</div><div class="dh-chips">{chips_chart}</div></div>'
        f'<div><div class="dh-th">FILTROS</div><div class="dh-chips">{chips_filter}'
        f'<span class="dh-small">Selectores: {e(controls)}</span></div></div></div>'
        + (f'<div class="dh-gov"><b>Ajustes de gobierno</b><ul>{gov}</ul></div>' if gov else "")
        + (f'<div class="dh-gov is-warn"><b>No disponible con estos datos</b><ul>{unsupported}</ul></div>' if unsupported else "")
    )

# ==================================================================
# Dashboard generado
# ==================================================================

html(f'<div style="margin-top:10px" class="dh-kicker">DASHBOARD GENERADO</div>'
     f'<div class="dh-title" style="font-size:28px">{e(plan["title"])}</div>'
     f'<div class="dh-subtitle">{e(plan["subtitle"])}</div>')

if plan["filter_controls"]:
    shown = dash.filter_bar(plan["filter_controls"])
    filters = {}
    for key in ("mes", "sede", "tipo_sede", "cuenta"):
        filters[key] = shown[key] if key in plan["filter_controls"] else plan["filters"].get(key)
else:
    filters = dict(plan["filters"])


@st.cache_data(ttl=600, show_spinner=False)
def run_plan(plan_json, filter_items):
    _, sem, ath, _ = dash.get_context()
    return GeneratedDashboard(ath, sem).run_plan(json.loads(plan_json), dict(filter_items))


with st.spinner("Consultando Athena…"):
    results, errors, sqls = run_plan(json.dumps(plan, sort_keys=True),
                                     tuple(sorted((k, v) for k, v in filters.items() if v)))

if "kpis" in errors:
    st.error("No se pudieron calcular los KPI en Athena.")
    st.code(errors["kpis"])
    st.stop()

periodo = dash.periodo_texto(filters)
k = results["kpis"].iloc[0]
if float(k.get("numero_transferencias", 1) or 0) == 0 and "numero_transferencias" in plan["kpis"]:
    st.info("No hay transferencias para esta combinación de filtros.")

# ---- KPI
kpi_icons = {"money": "up", "pct": "grid", "count": "arrows"}
cols = st.columns(len(plan["kpis"]), gap="small")
for i, (col, name) in enumerate(zip(cols, plan["kpis"])):
    kind = measure_kind(name)
    bg, fg = PASTELS[i % len(PASTELS)]
    tip = ""
    if name in ("cantidad_transferida", "costo_unitario_promedio"):
        tip = (f'<span title="Suma unidades de medida distintas: referencial." style="display:inline-flex;cursor:help">'
               f'{icon("info", 12, "#B3A7A2")}</span>')
    with col:
        html(f'<div class="dh-card dh-kpi{" is-main" if i == 0 else ""}">'
             f'<div class="dh-kpi-ico" style="background:{bg}">{icon(kpi_icons[kind] if name != "cantidad_transferida" else "box", 19, fg)}</div>'
             f'<div class="dh-kpi-label" title="{e(measures[name]["label"])}">{e(mlabel(name).upper())}{tip}</div>'
             f'<div class="dh-kpi-value">{fmt(k[name], kind)}</div>'
             f'<div class="dh-delta">{icon("calendar", 13, "#A0948F")}<span>{e(periodo.capitalize())}</span></div></div>')


# ---- Gráficos
def labels_for(df, dimension, column="dim"):
    if dimension == "periodo_mes" and "mes" in df:
        return [dash.ABREV[int(m) - 1] for m in df["mes"]]
    if dimension == "cuenta_contable" and "descripcion_cuenta" in df:
        return [f"{c} · {dash.clean_account(d, c)}" for c, d in zip(df[column], df["descripcion_cuenta"])]
    if dimension == "trimestre":
        return [f"T{int(float(x))}" for x in df[column]]
    return [str(x) for x in df[column]]


def wrap(text, width=16):
    words, lines, line = str(text).split(), [], ""
    for w in words:
        if len(line) + len(w) + 1 > width and line:
            lines.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    lines.append(line)
    return "<br>".join(lines[:3])


def base(fig, height=330, legend=False):
    fig.update_layout(
        height=height, margin=dict(l=0, r=10, t=10, b=0), showlegend=legend,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", dragmode=False,
        font=dict(family=FONT, color=MUTED, size=11),
        hoverlabel=dict(bgcolor=INK, font=dict(color="#fff", family=FONT)),
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(size=11.5), traceorder="normal"),
    )
    fig.update_xaxes(fixedrange=True, showgrid=False)
    fig.update_yaxes(fixedrange=True, gridcolor=GRID, griddash="dash", zeroline=False)
    return fig


def build_figure(chart, df):
    kind = measure_kind(chart["measure"])
    hv = hover_fmt(kind)
    dim, series, ctype = chart["dimension"], chart["series"], chart["type"]
    df = df.copy()

    # Ejes: si la dimensión principal es tiempo y la serie no, se invierte para heatmap/series.
    swap_rows = ctype in ("heatmap", "stacked_bar") and dim in TIME_DIMENSIONS and series not in TIME_DIMENSIONS
    swap_line = ctype == "line" and dim not in TIME_DIMENSIONS and series in TIME_DIMENSIONS
    if series and (swap_rows or swap_line):
        df = df.rename(columns={"dim": "serie", "serie": "dim"})
        dim, series = series, dim

    if dim == VIRTUAL_SEDE_ROL:
        piv = df.pivot_table(index=["dim", "tipo_sede"], columns="serie", values="valor", aggfunc="sum", fill_value=0).reset_index()
        for c in ("ENVIADO", "RECIBIDO"):
            if c not in piv:
                piv[c] = 0.0
        piv = piv.assign(total=piv["ENVIADO"] + piv["RECIBIDO"]).sort_values(["tipo_sede", "total"], ascending=[True, False])
        piv = piv.iloc[::-1]
        y = list(piv["dim"])
        hx = hv.replace("y", "x")
        fig = go.Figure([
            go.Bar(y=y, x=piv["ENVIADO"], name="Enviado", orientation="h", marker_color=ORANGE,
                   hovertemplate=f"<b>%{{y}}</b><br>Enviado: {hx}<extra></extra>"),
            go.Bar(y=y, x=piv["RECIBIDO"], name="Recibido", orientation="h", marker_color=ORANGE_SOFT,
                   hovertemplate=f"<b>%{{y}}</b><br>Recibido: {hx}<extra></extra>"),
        ])
        fig = base(fig, max(300, 34 * len(y) + 70), legend=True).update_layout(barmode="stack", bargap=0.36, barcornerradius=5)
        fig.update_yaxes(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=11.5, color=INK))
        fig.update_xaxes(showgrid=True, gridcolor=GRID, griddash="dash",
                         tickprefix="S/ " if kind == "money" else "", tickformat="~s")
        return fig

    if dim in TIME_DIMENSIONS:
        df = df.sort_values("mes" if (dim == "periodo_mes" and "mes" in df) else "dim", kind="stable")
    df["label"] = labels_for(df, dim)
    if series:
        df["serie_label"] = labels_for(df.rename(columns={"dim": "_d", "serie": "dim"}), series)

    if ctype == "heatmap":
        order_cols = list(dict.fromkeys(df.sort_values("serie")["serie_label"])) if series == "periodo_mes" else sorted(df["serie_label"].unique())
        grid = df.pivot_table(index="label", columns="serie_label", values="valor", aggfunc="sum", fill_value=0)
        grid = grid.reindex(columns=order_cols, fill_value=0)
        grid = grid.loc[grid.sum(axis=1).sort_values().index]
        text = [[fmt(v, kind) for v in row] for row in grid.values]
        fig = go.Figure(go.Heatmap(
            z=grid.values, x=list(grid.columns), y=list(grid.index), xgap=4, ygap=4, text=text, texttemplate="%{text}",
            colorscale=[[0, "#FBF4EF"], [0.35, "#F9C4A2"], [0.7, "#F5874A"], [1, "#D4560F"]],
            hovertemplate=f"<b>%{{y}}</b> · %{{x}}<br>{hv.replace('y', 'z')}<extra></extra>",
            colorbar=dict(thickness=10, outlinewidth=0, tickfont=dict(size=10)), textfont=dict(size=10.5, family=FONT),
        ))
        return base(fig, max(300, 46 * len(grid) + 60)).update_layout(xaxis=dict(side="top"))

    if series and ctype in ("line", "bar", "stacked_bar", "hbar"):
        fig = go.Figure()
        for i, (name, part) in enumerate(df.groupby("serie_label", sort=False)):
            color = SERIES_COLORS[i % len(SERIES_COLORS)]
            if ctype == "line":
                fig.add_trace(go.Scatter(x=part["label"], y=part["valor"], name=name, mode="lines+markers",
                                         line=dict(color=color, width=2.5), marker=dict(size=6),
                                         hovertemplate=f"<b>{e(name)}</b> · %{{x}}<br>{hv}<extra></extra>"))
            else:
                fig.add_trace(go.Bar(x=part["label"], y=part["valor"], name=name, marker_color=color,
                                     hovertemplate=f"<b>{e(name)}</b> · %{{x}}<br>{hv}<extra></extra>"))
        return base(fig, 350, legend=True).update_layout(barmode="stack" if ctype == "stacked_bar" else "group",
                                                         barcornerradius=4)

    second = chart["second_measure"]
    kind2 = measure_kind(second) if second else None
    custom = df[["valor_2"]] if second else None
    extra_hover = f"<br>{mlabel(second)}: {hover_fmt(kind2, 'customdata[0]')}" if second else ""

    if ctype == "line":
        fig = go.Figure(go.Scatter(
            x=df["label"], y=df["valor"], mode="lines+markers", name=mlabel(chart["measure"]),
            line=dict(color=ORANGE, width=3, shape="spline", smoothing=0.6),
            marker=dict(size=8, color="#fff", line=dict(color=ORANGE, width=2.5)),
            fill="tozeroy", fillcolor="rgba(242,107,33,.08)", customdata=custom,
            hovertemplate=f"<b>%{{x}}</b><br>{hv}{extra_hover}<extra></extra>"))
        if second:
            fig.add_trace(go.Scatter(x=df["label"], y=df["valor_2"], yaxis="y2", mode="lines", name=mlabel(second),
                                     line=dict(color="#8A3B12", width=2, dash="dot"),
                                     hovertemplate=f"<b>%{{x}}</b><br>{hover_fmt(kind2)}<extra></extra>"))
            fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False, fixedrange=True, tickformat="~s",
                                          tickprefix="S/ " if kind2 == "money" else "",
                                          ticksuffix="%" if kind2 == "pct" else ""))
        fig = base(fig, 320, legend=bool(second))
        fig.update_layout(yaxis=dict(tickprefix="S/ " if kind == "money" else "", tickformat="~s" if kind != "pct" else ".1f",
                                     ticksuffix="%" if kind == "pct" else ""))
        return fig

    if ctype in ("treemap", "donut"):
        total = float(df["valor"].sum()) or 1
        df["share"] = df["valor"] / total * 100
        if ctype == "donut":
            df = df.sort_values("valor", ascending=False)
            if len(df) > 6:
                rest = df.iloc[5:]
                df = pd.concat([df.iloc[:5], pd.DataFrame([{"label": "Otros", "valor": rest["valor"].sum(),
                                                             "share": rest["share"].sum()}])], ignore_index=True)
            shades = ["#E8590C", "#F26B21", "#F5874A", "#F7A877", "#F9C4A2", "#E4DEDB"]
            fig = go.Figure(go.Pie(labels=df["label"], values=df["valor"], hole=0.62, sort=False,
                                   marker=dict(colors=shades[: len(df)], line=dict(color="#fff", width=2)),
                                   textinfo="percent", texttemplate="%{percent:.0%}", textposition="inside",
                                   insidetextorientation="horizontal", textfont=dict(family=FONT, size=12),
                                   hovertemplate=f"<b>%{{label}}</b><br>{hv.replace('y', 'value')}<br>%{{percent}}<extra></extra>"))
            return base(fig, 320, legend=True).update_layout(legend=dict(orientation="v", x=1.02, y=0.5, xanchor="left"),
                                                             uniformtext=dict(minsize=10, mode="hide"))
        shades = ["#E8590C", "#F26B21", "#F5874A", "#F7A877", "#F9C4A2", "#FBDCC8"]
        colors = [shades[min(i, len(shades) - 1)] for i in range(len(df))]
        fig = go.Figure(go.Treemap(
            labels=df["label"], parents=[""] * len(df), values=df["valor"], customdata=df[["share"]],
            marker=dict(colors=colors, line=dict(color="#fff", width=3)),
            texttemplate="<b>%{label}</b><br>%{customdata[0]:.1f}%", branchvalues="total", tiling=dict(pad=3),
            textfont=dict(family=FONT, size=12.5, color=["#fff" if i < 3 else INK for i in range(len(df))]),
            hovertemplate=f"<b>%{{label}}</b><br>{hv.replace('y', 'value')}<br>%{{customdata[0]:.1f}}% del total<extra></extra>"))
        return base(fig, 340).update_layout(margin=dict(l=0, r=0, t=4, b=0), uniformtext=dict(minsize=10, mode="hide"))

    if ctype == "hbar":
        df = df.sort_values("valor")
        text = [fmt(v, kind) + (f" · {fmt(v2, kind2)}" if second else "") for v, v2 in
                zip(df["valor"], df["valor_2"] if second else df["valor"])]
        fig = go.Figure(go.Bar(
            y=[wrap(x, 34) for x in df["label"]], x=df["valor"], orientation="h", text=text, textposition="outside",
            marker=dict(color=[ORANGE if i == len(df) - 1 else ORANGE_SOFT for i in range(len(df))]),
            textfont=dict(color=INK, size=11.5, family=FONT), cliponaxis=False,
            customdata=df[["valor_2"]] if second else None,
            hovertemplate=f"<b>%{{y}}</b><br>{hv.replace('y', 'x')}{extra_hover}<extra></extra>"))
        return base(fig, max(260, 34 * len(df) + 50)).update_layout(
            barcornerradius=5, bargap=0.32, margin=dict(l=0, r=130 if second else 60, t=4, b=0),
            yaxis=dict(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=11.5, color=INK)), xaxis=dict(showticklabels=False))

    # bar (vertical)
    top = df["valor"].max()
    fig = go.Figure(go.Bar(
        x=[wrap(x, 14) for x in df["label"]], y=df["valor"], customdata=custom,
        marker=dict(color=[ORANGE if v == top else BAR_IDLE for v in df["valor"]]),
        text=[fmt(v, kind) if v == top else "" for v in df["valor"]], textposition="outside",
        textfont=dict(color=ORANGE, size=12, family=FONT), cliponaxis=False,
        hovertemplate=f"<b>%{{x}}</b><br>{hv}{extra_hover}<extra></extra>"))
    return base(fig, 320).update_layout(barcornerradius=6, bargap=0.4, yaxis=dict(showticklabels=False))


def render_table(chart, df):
    kind = measure_kind(chart["measure"])
    out = pd.DataFrame({dlabel(chart["dimension"]): labels_for(df, chart["dimension"])})
    if chart["series"]:
        out[dlabel(chart["series"])] = labels_for(df.rename(columns={"dim": "_d", "serie": "dim"}), chart["series"])
    if "unidad_medida" in df:
        out["Unidad"] = df["unidad_medida"].tolist()
    out[mlabel(chart["measure"])] = [fmt(v, kind, compact=False) for v in df["valor"]]
    if chart["second_measure"]:
        out[mlabel(chart["second_measure"])] = [fmt(v, measure_kind(chart["second_measure"]), compact=False) for v in df["valor_2"]]
    st.dataframe(out, hide_index=True, width="stretch", height=min(420, 38 * len(out) + 40))


def chart_block(chart):
    with st.container(key=f"card_gen_{chart['id']}"):
        sub = f'{TYPE_LABEL[chart["type"]]} · {mlabel(chart["measure"])} por {dlabel(chart["dimension"])}'
        if chart["series"]:
            sub += f' y {dlabel(chart["series"])}'
        if chart["only_obras"]:
            sub += " · solo destino OBRA"
        if chart["top_n"]:
            sub += f" · top {chart['top_n']}"
        html(f'<div class="dh-head"><div><div class="dh-card-title">{e(chart["title"])}</div>'
             f'<div class="dh-card-sub">{e(sub)}</div></div></div>')
        if chart["id"] in errors:
            st.warning("Este gráfico no se pudo calcular.")
            st.caption(errors[chart["id"]][:300])
            return
        df = results[chart["id"]]
        if df.empty:
            st.info("Sin datos para los filtros elegidos.")
            return
        if chart["type"] == "table":
            render_table(chart, df)
        else:
            st.plotly_chart(build_figure(chart, df), key=f"fig_{chart['id']}", config={"displayModeBar": False}, width="stretch")
        if chart["reason"]:
            html(f'<div class="dh-caveat">{icon("sparkles", 13, "#E9A57F")}<span>{e(chart["reason"])}</span></div>')


pending = []
for chart in plan["charts"]:
    if chart["width"] == "full":
        for c in pending:
            chart_block(c)
        pending = []
        chart_block(chart)
        continue
    pending.append(chart)
    if len(pending) == 2:
        left, right = st.columns(2, gap="medium")
        with left:
            chart_block(pending[0])
        with right:
            chart_block(pending[1])
        pending = []
for c in pending:
    chart_block(c)

# ---- Lectura con Bedrock
with st.container(key="card_genbi"):
    html(f'<div style="display:flex;gap:14px;align-items:center"><div class="dh-g-ico">{icon("sparkles", 20, "#FFA26B")}</div>'
         '<div><div class="dh-g-label">ANÁLISIS GENERADO</div><div class="dh-g-title">Lectura ejecutiva del dashboard</div></div></div>'
         '<div class="dh-g-text">Bedrock redacta la lectura usando solo las cifras calculadas arriba (no consulta otros datos).</div>')
    if st.button("Generar lectura con Bedrock →", key="btn_gen_insight"):
        frames = [results["kpis"].assign(tabla="kpis")]
        for chart in plan["charts"]:
            if chart["id"] in results:
                frames.append(results[chart["id"]].head(12).assign(tabla=chart["title"]))
        with st.spinner("Bedrock está analizando…"):
            try:
                st.session_state["gen_insight"] = generate_insight(
                    bedrock, f"{plan['title']} ({periodo}). Pedido: {result['prompt']}",
                    pd.concat(frames, ignore_index=True), semantic_layer=semantic, max_rows=60)
            except Exception as exc:
                st.session_state["gen_insight"] = {"headline": "No se pudo generar la lectura", "insight": str(exc), "caveat": ""}
    insight = st.session_state.get("gen_insight")
    if insight:
        html('<div class="dh-g-out">'
             f'<div class="dh-g-h">{e(insight.get("headline", ""))}</div>'
             f'<div class="dh-g-p">{e(insight.get("insight", ""))}</div>'
             + (f'<small>{e(insight["caveat"])}</small>' if insight.get("caveat") else "") + '</div>')

# ---- Descargas y trazabilidad
buffer = io.StringIO()
buffer.write(f"{plan['title']}\nPrompt: {result['prompt']}\n\nKPI\n")
results["kpis"].to_csv(buffer, index=False)
for chart in plan["charts"]:
    if chart["id"] in results:
        buffer.write(f"\n{chart['title'].upper()}\n")
        results[chart["id"]].to_csv(buffer, index=False)
d1, d2, _ = st.columns([1.2, 1.2, 3])
with d1:
    with st.container(key="csv_gen"):
        st.download_button("Descargar datos (CSV)", buffer.getvalue().encode("utf-8-sig"), file_name="dashboard_generado.csv",
                           mime="text/csv", icon=":material/download:", width="stretch")
with d2:
    with st.container(key="csv_plan"):
        st.download_button("Descargar plan (JSON)", json.dumps({"prompt": result["prompt"], "plan": plan, "ajustes": notes,
                                                                "sql": sqls}, ensure_ascii=False, indent=2).encode("utf-8"),
                           file_name="dashboard_plan.json", mime="application/json", icon=":material/data_object:", width="stretch")

html('<div class="dh-source"><span>Fuente: Amazon Athena · grupolar_master.vw_grupolar_genbi_transferencias · '
     'plan de Amazon Bedrock validado con la capa semántica</span>'
     '<span>Transferencias, recursos y sedes simulados con fines académicos</span></div>')
with st.expander("Ver plan original de Bedrock y SQL gobernado"):
    st.markdown("**Plan devuelto por Bedrock (antes de validar)**")
    st.json(result["raw"], expanded=False)
    for name, sql in sqls.items():
        title = "KPI" if name == "kpis" else next(c["title"] for c in plan["charts"] if c["id"] == name)
        st.markdown(f"**{title}**")
        st.code(sql, language="sql")
