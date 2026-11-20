"""
Dashboard generativo (GenBI): prompt -> plan -> SQL gobernado -> resultados.

1. Bedrock lee el prompt y devuelve SOLO un plan en JSON: qué KPI, qué
   gráficos (medida x dimensión x tipo) y qué filtros. No escribe SQL.
2. validate_plan() revisa el plan contra la Semantic Layer: medidas y
   dimensiones que no existen se descartan, tipos de gráfico incompatibles se
   corrigen y se agregan las advertencias de las reglas de negocio.
3. El SQL de cada KPI y gráfico lo arma este módulo con las expresiones
   aprobadas de la capa semántica (siempre las mismas) y pasa por el SQL Guard
   antes de ir a Athena.

Así el LLM decide QUÉ mostrar, pero nunca CÓMO se calcula una métrica.
"""

import json
from concurrent.futures import ThreadPoolExecutor

from src.dashboard_data import DashboardData, _lit

PLANNER_TAG = "DASHBOARD_PLANNER"

CHART_TYPES = {
    "line": "evolución en el tiempo (dimensión de tiempo)",
    "bar": "comparar pocas categorías o meses (barras verticales)",
    "hbar": "ranking / top N de categorías con nombres largos (barras horizontales)",
    "stacked_bar": "comparar una categoría dividida en una segunda dimensión (series) o enviado vs recibido por sede (dimension = sede_rol)",
    "treemap": "participación de cada categoría sobre el total",
    "donut": "participación de pocas categorías (máximo 6)",
    "heatmap": "cruce de dos dimensiones, por ejemplo usuario x mes (requiere series)",
    "table": "detalle con varias categorías",
}

TIME_DIMENSIONS = {"periodo_mes", "nombre_mes", "trimestre", "fecha_transferencia", "anio"}
MONEY = {"valor_transferido", "monto_haber", "monto_total_neto", "valor_promedio_comprobante", "costo_unitario_promedio"}
PERCENT = {"porcentaje_revertido"}
FILTER_CONTROLS = ["anio", "mes", "sede", "tipo_sede", "cuenta"]
MAX_KPIS, MAX_CHARTS = 6, 8

# Dimensión virtual: cada sede con dos roles (ENVIADO como origen, RECIBIDO como destino).
VIRTUAL_SEDE_ROL = "sede_rol"


def measure_kind(name):
    return "money" if name in MONEY else ("pct" if name in PERCENT else "count")


# ==================================================================
# 1. Prompt para Bedrock (planificador)
# ==================================================================

def build_catalog(semantic):
    measures = "\n".join(
        f"- {name}: {m['label']}. Fórmula aprobada: {m['sql']}. Sinónimos: {', '.join(m.get('synonyms', [])[:5])}"
        for name, m in semantic["measures"].items()
    )
    dims = []
    for name, d in semantic["dimensions"].items():
        line = f"- {name}: {d.get('label', name)}"
        values = d.get("values", [])
        if values and len(values) <= 12:
            line += f". Valores: {', '.join(map(str, values))}"
        if d.get("synonyms"):
            line += f". Sinónimos: {', '.join(d['synonyms'][:5])}"
        dims.append(line)
    dims.append(f"- {VIRTUAL_SEDE_ROL}: Sede con su rol (ENVIADO como origen y RECIBIDO como destino). "
                "Usar para comparar lo que cada sede envía y recibe, con type stacked_bar.")
    charts = "\n".join(f"- {k}: {v}" for k, v in CHART_TYPES.items())
    rules = "\n".join(f"- {r}" for r in semantic.get("business_rules", []))
    ambiguities = "\n".join(
        f"- '{k}': usar {v.get('approved_default')} por defecto. {v.get('note', '')}"
        for k, v in semantic.get("ambiguities", {}).items()
    )
    return measures, "\n".join(dims), charts, rules, ambiguities


def planner_prompt(semantic):
    measures, dims, charts, rules, ambiguities = build_catalog(semantic)
    sedes = semantic["dimensions"]["sede_origen"].get("values", [])
    cuentas = semantic["dimensions"]["cuenta_contable"].get("values", [])
    ctx = semantic.get("business_context", {})
    return f"""{PLANNER_TAG}
You design executive dashboards for a governed Generative BI application.
Company: {ctx.get('company', 'Grupo Lar')}. Dataset: {semantic.get('dataset')}. Period: {ctx.get('period_covered')}.
Currency: {ctx.get('currency_symbol', 'S/')} ({ctx.get('currency', 'PEN')}).

You do NOT write SQL. You only choose, from the approved catalog, which KPIs and charts answer the user's request.
Use ONLY the exact names listed below. Never invent measures or dimensions.

APPROVED MEASURES (name: meaning):
{measures}

APPROVED DIMENSIONS (name: meaning):
{dims}

CHART TYPES:
{charts}

BUSINESS RULES:
{rules}

AMBIGUITIES (approved defaults):
{ambiguities}

FILTERS you can preset (null = no filter):
- mes: integer 1-12 of 2025, only if the user names a month.
- sede: one of {json.dumps(sedes, ensure_ascii=False)} (matches sending or receiving).
- tipo_sede: "OBRA" or "ALMACEN" (applies to the receiving site).
- cuenta: one of {json.dumps(cuentas)}.
filter_controls: which filter selectors the dashboard should show, from {json.dumps(FILTER_CONTROLS)}.

GUIDELINES:
- One KPI per measure the user asks for. If the user asks for none, choose 3 to 5 relevant ones. Maximum {MAX_KPIS}.
- One chart per analysis the user asks for, in the order requested. Maximum {MAX_CHARTS}.
- Monthly evolution: dimension periodo_mes with type line (or bar).
- Sent vs received by site: dimension {VIRTUAL_SEDE_ROL}, type stacked_bar.
- Rotation between construction sites (rotación entre obras): measure numero_transferencias, dimension recurso, type hbar, only_obras true, top_n 10.
- Accounts with largest amount: dimension cuenta_contable; if the user also asks for % revertido, add it as second_measure.
- User participation: dimension usuario with type donut or hbar; activity by month: heatmap with series periodo_mes.
- top_n: 10 for rankings, null when all categories should be shown.
- width: "full" for wide charts (heatmap, tables, rankings of 10), otherwise "half".
- If something in the request cannot be answered with this catalog, list it in not_supported (in Spanish) and build the rest.
- All titles, reasons and texts in Spanish.

Return ONLY this JSON (no markdown):
{{
  "title": "short dashboard title",
  "subtitle": "one sentence",
  "interpretation": "one sentence: what you understood",
  "filters": {{"mes": null, "sede": null, "tipo_sede": null, "cuenta": null}},
  "filter_controls": ["anio", "mes"],
  "kpis": ["measure_name"],
  "charts": [
    {{"title": "...", "type": "line", "measure": "measure_name", "second_measure": null,
      "dimension": "dimension_name", "series": null, "top_n": null, "only_obras": false,
      "width": "half", "reason": "why this chart type"}}
  ],
  "not_supported": []
}}

EXAMPLE
Request: "Necesito ver cómo se mueven los recursos hacia las obras en agosto: valor y comprobantes, qué familias pesan más y qué obras reciben más"
{{"title": "Abastecimiento de obras · agosto 2025", "subtitle": "Recursos enviados a obras durante agosto",
  "interpretation": "Valor y comprobantes de agosto, participación por familia de recurso y ranking de obras receptoras.",
  "filters": {{"mes": 8, "sede": null, "tipo_sede": "OBRA", "cuenta": null}},
  "filter_controls": ["mes", "sede"],
  "kpis": ["valor_transferido", "numero_comprobantes"],
  "charts": [
    {{"title": "Valor por familia de recurso", "type": "treemap", "measure": "valor_transferido", "second_measure": null,
      "dimension": "familia_recurso", "series": null, "top_n": null, "only_obras": false, "width": "half",
      "reason": "El treemap muestra la participación de cada familia."}},
    {{"title": "Obras que más reciben", "type": "hbar", "measure": "valor_transferido", "second_measure": null,
      "dimension": "sede_destino", "series": null, "top_n": 10, "only_obras": false, "width": "half",
      "reason": "Ranking ordenado de obras receptoras."}}
  ],
  "not_supported": []}}
"""


def plan_dashboard(bedrock, prompt, semantic):
    """Ask Bedrock for a dashboard plan (JSON). Returns the raw plan."""
    raw = bedrock.ask_json(
        system_prompt=planner_prompt(semantic),
        user_prompt=f"Request: {prompt.strip()}\nReturn only the JSON plan.",
        max_tokens=2600,
    )
    if not isinstance(raw, dict):
        raise ValueError("Bedrock no devolvió un plan en formato JSON.")
    return raw


# ==================================================================
# 2. Validación del plan contra la Semantic Layer
# ==================================================================

def _name(value):
    """LLMs sometimes return {"measure": "x"} or ["x"] instead of "x"."""
    if isinstance(value, dict):
        value = value.get("measure") or value.get("name") or value.get("dimension")
    if isinstance(value, list):
        value = value[0] if value else None
    return str(value).strip() if value not in (None, "", "null") else None


def _as_int(value, low, high):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if low <= number <= high else None


def validate_plan(raw, semantic):
    """Return (plan, notes). Fixes or removes anything that is not governed."""
    measures = semantic["measures"]
    dimensions = semantic["dimensions"]
    notes = []

    # ---- filters
    f_raw = raw.get("filters") if isinstance(raw.get("filters"), dict) else {}
    sedes = set(dimensions["sede_origen"].get("values", [])) | set(dimensions["sede_destino"].get("values", []))
    cuentas = set(map(str, dimensions["cuenta_contable"].get("values", [])))
    filters = {
        "mes": _as_int(f_raw.get("mes"), 1, 12),
        "sede": f_raw.get("sede") if f_raw.get("sede") in sedes else None,
        "tipo_sede": str(f_raw.get("tipo_sede")).upper() if str(f_raw.get("tipo_sede")).upper() in ("OBRA", "ALMACEN") else None,
        "cuenta": str(f_raw.get("cuenta")) if str(f_raw.get("cuenta")) in cuentas else None,
    }
    for key in ("sede", "cuenta"):
        if f_raw.get(key) and not filters[key]:
            notes.append(f"El filtro {key} = «{f_raw.get(key)}» no existe en la capa semántica y se ignoró.")
    if filters["tipo_sede"] == "ALMACEN":
        notes.append("Tipo de sede se aplica a la sede de destino y los almacenes no reciben transferencias: se quitó ese filtro.")
        filters["tipo_sede"] = None
    controls = [c for c in (_name(x) for x in (raw.get("filter_controls") or [])) if c in FILTER_CONTROLS]

    # ---- KPIs
    kpis = []
    for name in [_name(x) for x in (raw.get("kpis") or [])]:
        if name in measures and name not in kpis:
            kpis.append(name)
        elif name not in measures:
            notes.append(f"KPI «{name}» descartado: no es una medida aprobada.")
    if len(kpis) > MAX_KPIS:
        kpis = kpis[:MAX_KPIS]
    if not kpis:
        kpis = ["numero_transferencias", "valor_transferido", "monto_total_neto"]
        notes.append("No se identificaron KPI válidos; se muestran los KPI base.")
    if "cantidad_transferida" in kpis:
        notes.append("Cantidad transferida suma unidades de medida distintas (bolsas, m3, kg…): úsala como referencia.")

    # ---- charts
    charts = []
    for i, c in enumerate(raw.get("charts") or []):
        if len(charts) >= MAX_CHARTS:
            notes.append(f"Se mostraron solo los primeros {MAX_CHARTS} gráficos.")
            break
        if not isinstance(c, dict):
            continue
        title = str(c.get("title") or f"Gráfico {i + 1}")
        measure = _name(c.get("measure"))
        dimension = _name(c.get("dimension"))
        if measure not in measures:
            notes.append(f"«{title}» descartado: la medida «{measure}» no está aprobada.")
            continue
        if dimension != VIRTUAL_SEDE_ROL and dimension not in dimensions:
            notes.append(f"«{title}» descartado: la dimensión «{dimension}» no está aprobada.")
            continue
        series = _name(c.get("series"))
        series = series if (series in dimensions and series != dimension) else None
        second = _name(c.get("second_measure"))
        second = second if (second in measures and second != measure) else None
        chart_type = c.get("type") if c.get("type") in CHART_TYPES else "bar"
        is_time = dimension in TIME_DIMENSIONS

        if dimension == "fecha_transferencia" or dimension == "nombre_mes" or dimension == "anio":
            dimension, is_time = "periodo_mes", True
        if series in ("fecha_transferencia", "nombre_mes", "anio"):
            series = "periodo_mes"

        if dimension == VIRTUAL_SEDE_ROL:
            chart_type, series = "stacked_bar", None
        elif chart_type == "line" and not is_time and not (series in TIME_DIMENSIONS):
            chart_type = "hbar"
            notes.append(f"«{title}»: una línea necesita una dimensión de tiempo; se cambió a barras.")
        elif chart_type == "heatmap" and not series:
            chart_type = "line" if is_time else "hbar"
            notes.append(f"«{title}»: un mapa de calor necesita dos dimensiones; se cambió a {'línea' if is_time else 'barras'}.")
        elif chart_type == "stacked_bar" and not series:
            chart_type = "bar" if is_time else "hbar"
        elif chart_type in ("treemap", "donut") and is_time:
            chart_type = "bar"
            notes.append(f"«{title}»: la participación no aplica al tiempo; se cambió a barras.")
        elif chart_type in ("treemap", "donut") and measure in PERCENT:
            chart_type = "hbar"
            notes.append(f"«{title}»: un porcentaje no se puede sumar como participación; se cambió a barras.")

        if measure == "cantidad_transferida" and dimension not in ("recurso", "unidad_medida") and series not in ("recurso", "unidad_medida"):
            notes.append(f"«{title}»: la cantidad mezcla unidades distintas entre {dimensions.get(dimension, {}).get('label', 'sedes').lower()}; "
                         "compárala con cuidado o usa valor transferido.")
        if measure == "costo_unitario_promedio" and dimension != "recurso":
            notes.append(f"«{title}»: el costo unitario solo es comparable por recurso (regla de la capa semántica).")

        top_n = _as_int(c.get("top_n"), 1, 50)
        if is_time:
            top_n = None
        only_obras = bool(c.get("only_obras"))
        width = "full" if c.get("width") == "full" or chart_type in ("heatmap", "table") else "half"
        charts.append({
            "id": f"c{len(charts) + 1}", "title": title, "type": chart_type, "measure": measure,
            "second_measure": second, "dimension": dimension, "series": series, "top_n": top_n,
            "only_obras": only_obras, "width": width, "reason": str(c.get("reason") or ""),
        })

    if not charts:
        charts.append({"id": "c1", "title": "Evolución mensual", "type": "line", "measure": kpis[0], "second_measure": None,
                       "dimension": "periodo_mes", "series": None, "top_n": None, "only_obras": False, "width": "full",
                       "reason": "Gráfico base: el plan no tenía gráficos válidos."})
        notes.append("No se identificaron gráficos válidos; se agregó la evolución mensual del primer KPI.")

    plan = {
        "title": str(raw.get("title") or "Dashboard generado"),
        "subtitle": str(raw.get("subtitle") or ""),
        "interpretation": str(raw.get("interpretation") or ""),
        "filters": filters,
        "filter_controls": controls,
        "kpis": kpis,
        "charts": charts,
        "not_supported": [str(x) for x in (raw.get("not_supported") or [])][:5],
    }
    return plan, notes


# ==================================================================
# 3. SQL gobernado y ejecución
# ==================================================================

class GeneratedDashboard(DashboardData):
    """Builds the SQL of a validated plan with the approved measure expressions."""

    def col(self, dimension):
        return self.semantic["dimensions"][dimension]["column"]

    def sql_kpis_plan(self, plan, f):
        select = ",\n    ".join(f"{self.m(k)} AS {k}" for k in plan["kpis"])
        return f"SELECT\n    {select}\nFROM {self.view}\n{self.where(f)}"

    def sql_chart(self, chart, f):
        measure, dim, series = chart["measure"], chart["dimension"], chart["series"]
        measures = f"{self.m(measure)} AS valor"
        if chart["second_measure"]:
            measures += f",\n    {self.m(chart['second_measure'])} AS valor_2"
        extra = "tipo_sede_destino = 'OBRA'" if chart["only_obras"] else None
        time_axis = dim in TIME_DIMENSIONS or series in TIME_DIMENSIONS
        where = self.where(f, include_mes=not time_axis, extra=extra)

        if dim == VIRTUAL_SEDE_ROL:
            parts = []
            for column, tipo, rol in (("sede_origen", "tipo_sede_origen", "ENVIADO"), ("sede_destino", "tipo_sede_destino", "RECIBIDO")):
                parts.append(f"SELECT {column} AS dim, {tipo} AS tipo_sede, '{rol}' AS serie, {measures}\n"
                             f"FROM {self.view}\n{where}\nGROUP BY {column}, {tipo}")
            return "\nUNION ALL\n".join(parts)

        def dim_select(d, alias):
            if d == "periodo_mes":
                return [f"periodo_mes AS {alias}", "mes", "nombre_mes"], ["periodo_mes", "mes", "nombre_mes"]
            if d == "cuenta_contable":
                return [f"codigo_cuenta AS {alias}", "descripcion_cuenta"], ["codigo_cuenta", "descripcion_cuenta"]
            if d == "recurso":
                return [f"descripcion_recurso AS {alias}", "unidad_medida"], ["descripcion_recurso", "unidad_medida"]
            column = self.col(d)
            return [f"{column} AS {alias}"], [column]

        sel, grp = dim_select(dim, "dim")
        if series:
            s_sel, s_grp = dim_select(series, "serie")
            sel += [x for x in s_sel if x not in sel and x.split(" AS ")[0] not in grp]
            grp += [x for x in s_grp if x not in grp]

        sql = f"SELECT\n    {', '.join(sel)},\n    {measures}\nFROM {self.view}\n{where}"
        if series and chart["top_n"] and dim not in TIME_DIMENSIONS:
            column = grp[0]
            sub_where = self.where(f, include_mes=not time_axis, extra=extra)
            top = (f"{column} IN (SELECT {column} FROM {self.view} {sub_where} GROUP BY {column} "
                   f"ORDER BY {self.m(measure)} DESC LIMIT {int(chart['top_n'])})")
            sql = f"SELECT\n    {', '.join(sel)},\n    {measures}\nFROM {self.view}\n{self.where(f, include_mes=not time_axis, extra=(extra + ' AND ' if extra else '') + top)}"
        sql += f"\nGROUP BY {', '.join(grp)}"
        if dim == "periodo_mes" or (series == "periodo_mes" and dim in TIME_DIMENSIONS):
            sql += "\nORDER BY periodo_mes"
        elif dim in TIME_DIMENSIONS:
            sql += f"\nORDER BY {grp[0]}"
        elif series:
            sql += f"\nORDER BY {grp[0]}"
        else:
            sql += "\nORDER BY valor DESC"
            if chart["top_n"]:
                sql += f"\nLIMIT {int(chart['top_n'])}"
            else:
                sql += "\nLIMIT 50"
        return sql

    def run_plan(self, plan, filters):
        jobs = {"kpis": self.sql_kpis_plan(plan, filters)}
        for chart in plan["charts"]:
            jobs[chart["id"]] = self.sql_chart(chart, filters)
        with ThreadPoolExecutor(max_workers=min(len(jobs), 8)) as pool:
            futures = {name: pool.submit(self._run, sql) for name, sql in jobs.items()}
            results, errors = {}, {}
            for name, future in futures.items():
                try:
                    results[name] = future.result()
                except Exception as exc:  # one failing chart must not break the dashboard
                    errors[name] = str(exc)
        return results, errors, jobs
