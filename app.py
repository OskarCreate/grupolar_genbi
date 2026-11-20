"""
Grupo Lar · Data Hub (inteligencia de negocio)

Punto de entrada de la aplicación Streamlit:
- Análisis: Resumen ejecutivo, Transferencias, Sedes y obras, Recursos.
- Gestión: Usuarios, Reportes.
- GenBI: Generar dashboard (prompt -> KPI y gráficos) y Pregunta a GenBI (NL-to-SQL).

Ejecutar desde la raíz del proyecto:
    streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Grupo Lar · Data Hub",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="auto",
)

from src.ui import inject_css, sidebar  # noqa: E402

resumen = st.Page("views/dashboard.py", title="Resumen ejecutivo", icon=":material/space_dashboard:", default=True)
transferencias = st.Page("views/transferencias.py", title="Transferencias", icon=":material/swap_horiz:")
sedes = st.Page("views/sedes.py", title="Sedes y obras", icon=":material/apartment:")
recursos = st.Page("views/recursos.py", title="Recursos", icon=":material/inventory_2:")
usuarios = st.Page("views/usuarios.py", title="Usuarios", icon=":material/group:")
reportes = st.Page("views/reportes.py", title="Reportes", icon=":material/description:")
generar = st.Page("views/generar.py", title="Generar dashboard", icon=":material/auto_awesome_mosaic:")
genbi = st.Page("views/genbi.py", title="Pregunta a GenBI", icon=":material/chat:")

groups = [
    ("ANÁLISIS", [resumen, transferencias, sedes, recursos]),
    ("GESTIÓN", [usuarios, reportes]),
    ("GENBI", [generar, genbi]),
]

navigation = st.navigation([resumen, transferencias, sedes, recursos, usuarios, reportes, generar, genbi], position="hidden")

inject_css()
sidebar(groups, generar)

navigation.run()
