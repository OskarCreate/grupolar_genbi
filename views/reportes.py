"""Reportes · cuentas contables (P2: treemap) y exportación."""

import streamlit as st

from src import dash

data = dash.load_data(dash.current_filters())

dash.topbar("Reportes", data)
dash.page_header(
    "GESTIÓN · REPORTES",
    "Cuentas contables",
    "¿En qué cuentas contables se concentra el monto neto de las transferencias? Debe − Haber por cuenta.",
    data,
)
filters = dash.filter_bar()
dash.guard_empty(data)

left, right = st.columns([1.5, 1], gap="medium")
with left:
    dash.chart_card(
        "card_treemap", "Monto neto por cuenta contable",
        "Treemap · el área de cada bloque es proporcional al monto neto (debe − haber)",
        dash.fig_treemap_cuentas(data),
        "Visualización óptima para P2: muestra la participación de cada cuenta sobre el total.",
    )
with right:
    dash.card_cuentas(data)

dash.card_genbi(data, filters)
dash.footer(data)
