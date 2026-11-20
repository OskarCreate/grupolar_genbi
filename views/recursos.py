"""Recursos · top 10 por transferencias hacia obras (P3: barras horizontales)."""

import streamlit as st

from src import dash

data = dash.load_data(dash.current_filters())

dash.topbar("Recursos", data)
dash.page_header(
    "ANÁLISIS · RECURSOS",
    "Recursos con mayor rotación",
    "¿Qué recursos se transfieren con más frecuencia hacia las obras y cuántas obras cubren?",
    data,
)
filters = dash.filter_bar()
dash.guard_empty(data)

dash.chart_card(
    "card_barras_rec", "Top 10 recursos por número de transferencias",
    "Barras horizontales ordenadas · solo transferencias con destino OBRA",
    dash.fig_recursos_horizontal(data),
    "Visualización óptima para P3. La cantidad se muestra con su unidad de medida en la tabla, sin sumar unidades distintas.",
)
dash.card_recursos(data, show_all=True, title="Detalle de los 10 recursos",
                   subtitle="Cantidad con su unidad de medida · cobertura = obras de destino distintas")
dash.footer(data)
