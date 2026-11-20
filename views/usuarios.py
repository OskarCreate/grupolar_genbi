"""Usuarios · actividad por mes (P4: mapa de calor)."""

import streamlit as st

from src import dash

data = dash.load_data(dash.current_filters())

dash.topbar("Usuarios", data)
dash.page_header(
    "GESTIÓN · USUARIOS",
    "Actividad por usuario",
    "¿Qué usuarios registran más transferencias y cómo se distribuye su actividad durante el año?",
    data,
)
filters = dash.filter_bar()
dash.guard_empty(data)

left, right = st.columns([1.7, 1], gap="medium")
with left:
    dash.chart_card(
        "card_heatmap", "Transferencias por usuario y mes",
        "Mapa de calor · intensidad = número de transferencias registradas",
        dash.fig_heatmap_usuarios(data),
        "Visualización óptima para P4: cruza dos dimensiones (usuario × mes) en una sola vista.",
    )
with right:
    dash.card_usuarios(data, filters)
dash.footer(data)
