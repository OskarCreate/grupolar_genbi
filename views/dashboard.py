"""Resumen ejecutivo · Transferencias internas (wireframe Data Hub)."""

import streamlit as st

from src import dash

filters_ui = dash.current_filters()
data = dash.load_data(filters_ui)

dash.topbar("Transferencias internas", data)
dash.page_header(
    "OPERACIONES · 2025",
    "Transferencias internas",
    "Monitorea el movimiento de recursos entre almacenes y obras, su valor y las cuentas contables asociadas.",
    data,
)
filters = dash.filter_bar()
dash.guard_empty(data)

dash.kpi_row(data, filters)

left, right = st.columns([1.85, 1], gap="medium")
with left:
    dash.card_valor(data, filters)
with right:
    dash.card_usuarios(data, filters, limit=4)

left, right = st.columns([1.35, 1], gap="medium")
with left:
    dash.card_sedes(data)
with right:
    dash.card_cuentas(data)

dash.card_genbi(data, filters)
dash.card_recursos(data)
dash.footer(data)
