"""
Datos del dashboard de Grupo Lar.

Todas las cifras salen de la GenBI View en Athena con SQL fijo (no generado
por el LLM). Las métricas se toman de la Semantic Layer aprobada, así el
dashboard y GenBI usan exactamente las mismas definiciones de negocio.
Cada consulta pasa por el SQL Guard antes de ejecutarse.

Filtros soportados (todos opcionales):
    mes        1-12 (año 2025)
    sede       nombre exacto; incluye envíos (origen) y recepciones (destino)
    tipo_sede  ALMACEN u OBRA; se aplica a la sede de destino (regla de la capa)
    cuenta     codigo_cuenta exacto
"""

import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from src.sql_guard import validate_sql


def _lit(value):
    """SQL string literal with quotes escaped."""
    return "'" + str(value).replace("'", "''") + "'"


class DashboardData:
    def __init__(self, athena_client, semantic_layer):
        self.athena = athena_client
        self.semantic = semantic_layer
        self.view = semantic_layer["allowed_view"]

    # --------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------

    def m(self, name):
        """SQL of an approved measure, e.g. m('valor_transferido') -> SUM(monto_debe)."""
        return self.semantic["measures"][name]["sql"]

    def _run(self, sql):
        validate_sql(sql, self.view)
        df, _ = self.athena.run(sql)
        for column in df.columns:
            converted = pd.to_numeric(df[column], errors="coerce")
            if len(df) and converted.notna().sum() == df[column].notna().sum():
                df[column] = converted
        return df

    @staticmethod
    def where(filters, include_mes=True, extra=None):
        f = filters or {}
        conditions = []
        if include_mes and f.get("mes"):
            conditions.append(f"anio = 2025 AND mes = {int(f['mes'])}")
        if f.get("sede"):
            sede = _lit(f["sede"])
            conditions.append(f"(sede_origen = {sede} OR sede_destino = {sede})")
        if f.get("tipo_sede"):
            conditions.append(f"tipo_sede_destino = {_lit(f['tipo_sede'])}")
        if f.get("cuenta"):
            conditions.append(f"codigo_cuenta = {_lit(f['cuenta'])}")
        if extra:
            conditions.append(extra)
        return ("WHERE " + " AND ".join(conditions)) if conditions else ""

    # --------------------------------------------------------------
    # Queries
    # --------------------------------------------------------------

    def sql_kpis(self, f):
        return f"""
SELECT
    {self.m('numero_transferencias')} AS numero_transferencias,
    {self.m('numero_comprobantes')} AS numero_comprobantes,
    {self.m('cantidad_transferida')} AS cantidad_transferida,
    {self.m('valor_transferido')} AS valor_transferido,
    {self.m('monto_haber')} AS monto_haber,
    {self.m('monto_total_neto')} AS monto_total_neto,
    {self.m('porcentaje_revertido')} AS porcentaje_revertido
FROM {self.view}
{self.where(f)}
""".strip()

    def sql_mensual(self, f):
        return f"""
SELECT
    periodo_mes,
    mes,
    nombre_mes,
    {self.m('numero_transferencias')} AS numero_transferencias,
    {self.m('numero_comprobantes')} AS numero_comprobantes,
    {self.m('valor_transferido')} AS valor_transferido,
    {self.m('monto_total_neto')} AS monto_total_neto
FROM {self.view}
{self.where(f, include_mes=False)}
GROUP BY periodo_mes, mes, nombre_mes
ORDER BY periodo_mes
""".strip()

    def sql_usuarios(self, f):
        return f"""
SELECT
    usuario,
    {self.m('numero_transferencias')} AS numero_transferencias,
    {self.m('valor_transferido')} AS valor_transferido
FROM {self.view}
{self.where(f)}
GROUP BY usuario
ORDER BY numero_transferencias DESC
""".strip()

    def sql_usuario_mes(self, f):
        return f"""
SELECT
    usuario,
    mes,
    {self.m('numero_transferencias')} AS numero_transferencias
FROM {self.view}
{self.where(f, include_mes=False)}
GROUP BY usuario, mes
ORDER BY usuario, mes
""".strip()

    def sql_sedes(self, f):
        where = self.where(f)
        return f"""
SELECT
    sede_origen AS sede,
    tipo_sede_origen AS tipo_sede,
    'ENVIADO' AS rol,
    {self.m('numero_transferencias')} AS numero_transferencias,
    {self.m('cantidad_transferida')} AS cantidad_transferida,
    {self.m('valor_transferido')} AS valor_transferido
FROM {self.view}
{where}
GROUP BY sede_origen, tipo_sede_origen
UNION ALL
SELECT
    sede_destino AS sede,
    tipo_sede_destino AS tipo_sede,
    'RECIBIDO' AS rol,
    {self.m('numero_transferencias')} AS numero_transferencias,
    {self.m('cantidad_transferida')} AS cantidad_transferida,
    {self.m('valor_transferido')} AS valor_transferido
FROM {self.view}
{where}
GROUP BY sede_destino, tipo_sede_destino
""".strip()

    def sql_cuentas(self, f):
        return f"""
SELECT
    codigo_cuenta,
    descripcion_cuenta,
    clase_contable,
    {self.m('valor_transferido')} AS valor_transferido,
    {self.m('monto_haber')} AS monto_haber,
    {self.m('monto_total_neto')} AS monto_total_neto,
    {self.m('porcentaje_revertido')} AS porcentaje_revertido
FROM {self.view}
{self.where(f)}
GROUP BY codigo_cuenta, descripcion_cuenta, clase_contable
ORDER BY monto_total_neto DESC
""".strip()

    def sql_recursos(self, f):
        return f"""
SELECT
    descripcion_recurso,
    familia_recurso,
    unidad_medida,
    {self.m('numero_transferencias')} AS numero_transferencias,
    {self.m('cantidad_transferida')} AS cantidad_transferida,
    {self.m('obras_destino')} AS obras_destino,
    {self.m('valor_transferido')} AS valor_transferido
FROM {self.view}
{self.where(f, extra="tipo_sede_destino = 'OBRA'")}
GROUP BY descripcion_recurso, familia_recurso, unidad_medida
ORDER BY numero_transferencias DESC, valor_transferido DESC
LIMIT 10
""".strip()

    # --------------------------------------------------------------
    # Load everything for one filter combination (queries in parallel)
    # --------------------------------------------------------------

    def load(self, filters=None):
        f = dict(filters or {})
        jobs = {
            "kpis": self.sql_kpis(f),
            "mensual": self.sql_mensual(f),
            "usuarios": self.sql_usuarios(f),
            "usuario_mes": self.sql_usuario_mes(f),
            "sedes": self.sql_sedes(f),
            "cuentas": self.sql_cuentas(f),
            "recursos": self.sql_recursos(f),
        }
        if f.get("mes") and int(f["mes"]) > 1:
            jobs["kpis_anterior"] = self.sql_kpis({**f, "mes": int(f["mes"]) - 1})

        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            futures = {name: pool.submit(self._run, sql) for name, sql in jobs.items()}
            data = {name: future.result() for name, future in futures.items()}

        data["sql"] = jobs
        data["loaded_at"] = time.time()
        return data
