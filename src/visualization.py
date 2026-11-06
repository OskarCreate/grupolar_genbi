import re

import pandas as pd
import plotly.express as px


# Column-name tokens that identify a time axis (Spanish and English).
TIME_TOKENS = {
    "periodo", "fecha", "dia", "mes", "anio", "año", "trimestre", "semana",
    "date", "day", "month", "year", "quarter", "week",
}


# Column-name tokens that identify codes/identifiers. They may look
# numeric ("24111") but they are labels, never measures.
ID_TOKENS = {"codigo", "cod", "id", "mayor"}


def _tokens(column):
    return set(re.split(r"[^a-z0-9ñ]+", str(column).lower()))


def is_time_column(column):
    return bool(_tokens(column) & TIME_TOKENS)


def is_id_column(column):
    name = str(column).lower()
    return bool(_tokens(column) & ID_TOKENS) or name.startswith("num_")


def coerce_numeric(df):
    result = df.copy()
    for column in result.columns:
        if is_id_column(column):
            result[column] = result[column].astype(str)
            continue
        try:
            converted = pd.to_numeric(result[column])
            # Keep conversion only when it is meaningfully numeric.
            if converted.notna().sum() > 0:
                result[column] = converted
        except (TypeError, ValueError):
            pass
    return result


def _time_axis(df, time_cols):
    """Pick (or build) the x axis for a time series."""
    lowered = {c.lower(): c for c in time_cols}

    if "periodo_mes" in lowered:
        return df, lowered["periodo_mes"]

    # anio + mes numeric -> build a sortable YYYY-MM label
    if "anio" in lowered and "mes" in lowered:
        df = df.copy()
        df["periodo"] = (
            df[lowered["anio"]].astype(int).astype(str)
            + "-"
            + df[lowered["mes"]].astype(int).astype(str).str.zfill(2)
        )
        return df, "periodo"

    return df, time_cols[0]


def choose_chart(df):
    """
    Deterministic, intentionally simple BI visualization logic.
    Bedrock does NOT generate executable Python.
    """
    df = coerce_numeric(df)

    if df.empty:
        return None, "No data"

    if len(df.columns) < 2 or len(df) == 1:
        return None, "KPI/table"

    numeric = list(df.select_dtypes(include="number").columns)
    time_cols = [c for c in df.columns if is_time_column(c)]

    # The metric is the first numeric column that is not a time column
    # (anio and mes are numeric but they are axes, not measures).
    metrics = [c for c in numeric if c not in time_cols]

    if not metrics:
        return None, "Table"

    y = metrics[0]

    categories = [
        c for c in df.columns
        if c not in numeric and c not in time_cols
    ]

    # Time series -> line chart (one line per category, if any)
    if time_cols:
        plot_df, x = _time_axis(df, time_cols)
        color = categories[0] if categories else None
        plot_df = plot_df.sort_values([c for c in (color, x) if c])
        figure = px.line(plot_df, x=x, y=y, color=color, markers=True)
        return figure, "Line"

    # Dimension + metric -> bar chart (grouped if there is a second dimension)

    if categories:
        x = categories[0]
        color = categories[1] if len(categories) > 1 else None
        figure = px.bar(df, x=x, y=y, color=color, barmode="group")
        return figure, "Bar"

    return None, "Table"
