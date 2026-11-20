"""Transferencias · evolución mensual (P5: gráfico de líneas)."""

import streamlit as st

from src import dash
from src.ui import entero, soles, pct, html, e

data = dash.load_data(dash.current_filters())

dash.topbar("Transferencias", data)
dash.page_header(
    "ANÁLISIS · TRANSFERENCIAS",
    "Evolución de transferencias",
    "¿Cómo varía el número de transferencias mes a mes? Tendencia, picos y valor por periodo.",
    data,
)
filters = dash.filter_bar()
dash.guard_empty(data)
dash.kpi_row(data, filters)

left, right = st.columns([1.5, 1], gap="medium")
with left:
    dash.chart_card(
        "card_linea", "Transferencias por mes",
        "Número de líneas de transferencia · enero a diciembre 2025",
        dash.fig_linea_mensual(data, filters),
        "Visualización óptima para P5: el gráfico de líneas muestra la tendencia temporal.",
    )
with right:
    dash.card_valor(data, filters, height=230)

m = data["mensual"].copy()
rows = []
for r in m.itertuples():
    rows.append(
        '<div class="dh-row dh-table-row" style="grid-template-columns:1.2fr 1fr 1fr 1fr 1fr">'
        f'<span class="dh-name">{e(r.nombre_mes)}</span>'
        f'<span class="dh-num">{entero(r.numero_transferencias)}</span>'
        f'<span class="dh-num">{entero(r.numero_comprobantes)}</span>'
        f'<span class="dh-num">{soles(r.valor_transferido, compact=False)}</span>'
        f'<span class="dh-num">{soles(r.monto_total_neto, compact=False)}</span></div>'
    )
with st.container(key="card_tabla_mes"):
    html('<div class="dh-card-title">Detalle mensual</div>'
         '<div class="dh-card-sub">Comprobantes = COUNT(DISTINCT num_comprobante); una transferencia es una línea del comprobante.</div>'
         '<div class="dh-scroll" style="margin-top:12px"><div style="min-width:620px">'
         '<div class="dh-row dh-th dh-table-head" style="grid-template-columns:1.2fr 1fr 1fr 1fr 1fr">'
         '<span>MES</span><span style="text-align:right">TRANSFERENCIAS</span><span style="text-align:right">COMPROBANTES</span>'
         '<span style="text-align:right">VALOR TRANSFERIDO</span><span style="text-align:right">MONTO NETO</span></div>'
         + "".join(rows) + '</div></div>')
dash.footer(data)
