import pandas as pd
import streamlit as st

from src.athena import AthenaClient
from src.bedrock import BedrockClient
from src.config import load_json, load_settings
from src.insight import generate_insight
from src.sql_generator import generate_sql
from src.sql_guard import (
    SQLValidationError,
    validate_sql,
)
from src.visualization import choose_chart


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Grupo Lar - Generative BI",
    page_icon="🏗️",
    layout="wide",
)


# Measures formatted as money, percentage or count in KPI cards.
MONEY_METRICS = {
    "valor_transferido",
    "monto_haber",
    "monto_total_neto",
    "valor_promedio_comprobante",
    "costo_unitario_promedio",
}
PERCENT_METRICS = {"porcentaje_revertido"}


def format_kpi(value, metric_name, symbol):
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return str(value)
    if metric_name in MONEY_METRICS:
        return f"{symbol} {number:,.2f}"
    if metric_name in PERCENT_METRICS:
        return f"{number:.2f} %"
    if float(number).is_integer():
        return f"{number:,.0f}"
    return f"{number:,.2f}"


# ============================================================
# LOAD CONFIGURATION
# ============================================================

try:

    settings = load_settings()

    semantic = load_json(
        "config/semantic_layer.json"
    )

except Exception as exc:

    st.error(
        f"Configuration error: {exc}"
    )

    st.stop()

currency_symbol = semantic.get(
    "business_context", {}
).get("currency_symbol", "")


# ============================================================
# AWS CLIENTS
# ============================================================

bedrock = BedrockClient(
    region=settings["aws_region"],
    model_id=settings["bedrock_model_id"],
)

athena = AthenaClient(
    region=settings["aws_region"],
    database=settings["athena_database"],
    output_s3=settings["athena_output_s3"],
    workgroup=settings.get(
        "athena_workgroup",
        "primary",
    ),
)


# ============================================================
# HEADER
# ============================================================

st.title(
    "🏗️ Grupo Lar — Generative BI"
)

st.caption(
    "Transferencias internas de recursos · "
    "Athena + Semantic Layer + Amazon Bedrock + Streamlit"
)

st.divider()


# ============================================================
# BUSINESS QUESTION
# ============================================================

question = st.text_input(
    "Pregunta de negocio",
    placeholder=(
        "Ej.: ¿Qué cuentas contables concentran el mayor monto total?"
    ),
)


col1, col2 = st.columns(
    [1, 4]
)

with col1:

    analyze = st.button(
        "🔎 Analizar",
        type="primary",
        width="stretch",
        disabled=not question,
    )


with col2:

    show_details = st.checkbox(
        "Mostrar detalles técnicos",
        value=False,
    )


# ============================================================
# ANALYSIS
# ============================================================

if analyze:

    try:

        # ----------------------------------------------------
        # 1. SEMANTIC RESOLUTION + NL-TO-SQL
        # ----------------------------------------------------

        with st.spinner(
            "Interpretando la pregunta..."
        ):

            generated = generate_sql(
                bedrock,
                question,
                semantic,
            )

        sql = generated["sql"]
        metric_used = generated.get("metric_used")
        metric_label = (
            semantic["measures"][metric_used]["label"]
            if metric_used in semantic.get("measures", {})
            else "Interpretación de Bedrock"
        )


        # ----------------------------------------------------
        # 2. QUESTION + INTERPRETATION (always visible)
        # ----------------------------------------------------

        st.markdown("#### Pregunta")
        st.write(question)

        st.markdown("#### Interpretación")
        st.info(
            f"{generated.get('interpretation', '')}  \n"
            f"Métrica aplicada: **{metric_label}**"
        )


        # ----------------------------------------------------
        # 3. SQL SAFETY GATE
        # ----------------------------------------------------

        try:

            validate_sql(
                sql,
                settings["allowed_view"],
            )

        except SQLValidationError as exc:

            st.error(
                f"SQL Guard bloqueó la consulta: {exc}"
            )

            st.code(sql, language="sql")

            st.stop()


        # ----------------------------------------------------
        # 4. EXECUTE ATHENA
        # ----------------------------------------------------

        with st.spinner(
            "Consultando Athena..."
        ):

            df, metadata = athena.run(
                sql
            )


        # ----------------------------------------------------
        # 5. GENERATE BUSINESS INSIGHT
        # ----------------------------------------------------

        with st.spinner(
            "Generando insight..."
        ):

            insight = generate_insight(
                bedrock,
                question,
                df,
                semantic_layer=semantic,
            )


        # ----------------------------------------------------
        # 6. BUSINESS INSIGHT
        # ----------------------------------------------------

        st.markdown("#### Insight")

        st.subheader(
            insight.get(
                "headline",
                "Business Insight",
            )
        )

        st.write(
            insight.get(
                "insight",
                ""
            )
        )

        caveat = insight.get(
            "caveat"
        )

        if caveat:

            st.caption(
                f"ℹ️ {caveat}"
            )


        # ----------------------------------------------------
        # 7. VISUALIZATION
        # ----------------------------------------------------

        st.markdown("#### Visualización")

        figure, chart_type = choose_chart(
            df
        )

        if figure is not None:

            st.plotly_chart(
                figure,
                width="stretch",
            )

        elif df.shape == (1, 1):

            st.metric(
                metric_label,
                format_kpi(
                    df.iloc[0, 0],
                    metric_used,
                    currency_symbol,
                ),
            )

        else:

            st.caption(
                f"Visualización seleccionada: {chart_type}"
            )


        # ----------------------------------------------------
        # 8. RESULT TABLE
        # ----------------------------------------------------

        st.markdown("#### Resultado (Athena)")

        st.dataframe(
            df,
            width="stretch",
            hide_index=True,
        )


        # ----------------------------------------------------
        # 9. TECHNICAL DETAILS
        # ----------------------------------------------------

        if show_details:

            st.divider()

            st.subheader(
                "🔧 Detalles técnicos"
            )

            col_a, col_b, col_c = st.columns(
                3
            )

            with col_a:

                st.metric(
                    "Métrica interpretada",
                    metric_used
                    or "LLM interpretation",
                )

            with col_b:

                execution_time = (
                    metadata.get(
                        "total_execution_ms"
                    )
                )

                st.metric(
                    "Athena execution",
                    (
                        f"{execution_time} ms"
                        if execution_time
                        else "N/A"
                    ),
                )

            with col_c:

                scanned = metadata.get(
                    "data_scanned_bytes"
                )

                if scanned is not None:

                    scanned_mb = (
                        scanned
                        / 1024
                        / 1024
                    )

                    st.metric(
                        "Data scanned",
                        f"{scanned_mb:.4f} MB",
                    )

                else:

                    st.metric(
                        "Data scanned",
                        "N/A",
                    )


            st.markdown(
                "### Semantic Rule Applied"
            )

            st.code(
                generated.get(
                    "semantic_rule_applied",
                    "No deterministic rule applied",
                )
            )


            st.markdown(
                "### Generated SQL"
            )

            st.code(
                sql,
                language="sql",
            )


            st.markdown(
                "### SQL Governance"
            )

            st.success(
                "✅ SQL Guard: PASSED"
            )


            st.markdown(
                "### Visualization Decision"
            )

            st.write(
                f"Selected visualization: **{chart_type}**"
            )


            st.markdown(
                "### Athena Metadata"
            )

            st.json(
                metadata
            )


    except Exception as exc:

        st.error(
            "Se produjo un error durante "
            "el análisis."
        )

        st.exception(
            exc
        )


# ============================================================
# EXAMPLE QUESTIONS
# ============================================================

st.divider()

st.subheader(
    "Preguntas de ejemplo"
)

st.markdown(
    """
**Preguntas de negocio del proyecto**
- ¿Qué sedes reciben la mayor cantidad de recursos?
- ¿Qué cuentas contables concentran el mayor monto total?
- ¿Cuáles son los recursos con mayor rotación entre obras?
- ¿Quiénes son los usuarios que registran más transacciones?
- ¿Cómo evolucionó el valor transferido por mes?

**KPI**
- ¿Cuántas transferencias se registraron?
- ¿Cuántos comprobantes de transferencia se emitieron?
- ¿Cuál fue el porcentaje revertido?
- ¿Cuál fue el valor promedio por comprobante?

**Ambigüedad**
- ¿Cuál fue la principal obra? → se mide por valor transferido
- ¿Qué recursos tuvieron más movimiento? → se mide por número de transferencias
"""
)
