"""Sedes y obras · enviado vs recibido (P1: barras apiladas)."""

import streamlit as st

from src import dash

data = dash.load_data(dash.current_filters())

dash.topbar("Sedes y obras", data)
dash.page_header(
    "ANÁLISIS · SEDES Y OBRAS",
    "Sedes y obras",
    "¿Qué sedes envían y cuáles reciben más recursos? Los almacenes abastecen; las obras consumen.",
    data,
)
filters = dash.filter_bar()
dash.guard_empty(data)

dash.chart_card(
    "card_apiladas", "Valor enviado y recibido por sede",
    "Barras apiladas · sede en el eje X, dividida en enviado (origen) y recibido (destino)",
    dash.fig_sedes_apiladas(data),
    "Visualización óptima para P1. Se usa el valor en soles porque la cantidad mezcla unidades distintas.",
)
dash.card_sedes(data, key="card_sedes_detalle", show_profile=True)
dash.footer(data)
