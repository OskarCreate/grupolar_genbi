"""Pruebas del dashboard generativo: el plan del LLM se valida y el SQL siempre pasa el SQL Guard."""

import json
import unittest
from pathlib import Path

from src.dashboard_generator import GeneratedDashboard, validate_plan
from src.sql_guard import validate_sql

SEMANTIC = json.loads(Path("config/semantic_layer.json").read_text(encoding="utf-8"))


class _NoAthena:
    def run(self, sql):
        raise AssertionError("no debe ejecutarse en las pruebas")


RAW = {
    "title": "Prueba",
    "filters": {"mes": 8, "sede": "Sede inventada", "tipo_sede": "ALMACEN", "cuenta": "24111"},
    "filter_controls": ["mes", "cuenta", "proveedor"],
    "kpis": ["valor_transferido", "ventas", "cantidad_transferida"],
    "charts": [
        {"title": "Mensual", "type": "line", "measure": "valor_transferido", "dimension": "periodo_mes"},
        {"title": "Sedes", "type": "bar", "measure": "valor_transferido", "dimension": "sede_rol"},
        {"title": "Linea sin tiempo", "type": "line", "measure": "numero_transferencias", "dimension": "usuario"},
        {"title": "Heatmap sin serie", "type": "heatmap", "measure": "numero_transferencias", "dimension": "usuario"},
        {"title": "Treemap de porcentaje", "type": "treemap", "measure": "porcentaje_revertido", "dimension": "cuenta_contable"},
        {"title": "Medida falsa", "type": "bar", "measure": "ventas", "dimension": "usuario"},
        {"title": "Dimension falsa", "type": "bar", "measure": "valor_transferido", "dimension": "cliente"},
        {"title": "Top con serie", "type": "stacked_bar", "measure": "valor_transferido", "dimension": "recurso",
         "series": "familia_recurso", "top_n": 5, "only_obras": True},
        {"title": "Usuario x mes", "type": "heatmap", "measure": "numero_transferencias", "dimension": "usuario",
         "series": "periodo_mes"},
    ],
}


class TestDashboardGenerator(unittest.TestCase):
    def setUp(self):
        self.plan, self.notes = validate_plan(RAW, SEMANTIC)

    def test_filters_are_governed(self):
        f = self.plan["filters"]
        self.assertEqual(f["mes"], 8)
        self.assertIsNone(f["sede"])        # valor que no existe
        self.assertIsNone(f["tipo_sede"])   # ALMACEN como destino no tiene filas
        self.assertEqual(f["cuenta"], "24111")
        self.assertEqual(self.plan["filter_controls"], ["mes", "cuenta"])

    def test_invalid_measures_and_dimensions_are_dropped(self):
        self.assertEqual(self.plan["kpis"], ["valor_transferido", "cantidad_transferida"])
        titles = [c["title"] for c in self.plan["charts"]]
        self.assertNotIn("Medida falsa", titles)
        self.assertNotIn("Dimension falsa", titles)

    def test_chart_types_are_corrected(self):
        types = {c["title"]: c["type"] for c in self.plan["charts"]}
        self.assertEqual(types["Sedes"], "stacked_bar")
        self.assertEqual(types["Linea sin tiempo"], "hbar")
        self.assertEqual(types["Heatmap sin serie"], "hbar")
        self.assertEqual(types["Treemap de porcentaje"], "hbar")
        self.assertTrue(any("Cantidad transferida" in n for n in self.notes))

    def test_every_generated_sql_passes_the_guard(self):
        gen = GeneratedDashboard(_NoAthena(), SEMANTIC)
        view = SEMANTIC["allowed_view"]
        sqls = [gen.sql_kpis_plan(self.plan, self.plan["filters"])]
        sqls += [gen.sql_chart(c, self.plan["filters"]) for c in self.plan["charts"]]
        for sql in sqls:
            self.assertTrue(validate_sql(sql, view), sql)
            self.assertNotIn("select *", sql.lower())

    def test_measures_use_approved_formulas(self):
        gen = GeneratedDashboard(_NoAthena(), SEMANTIC)
        sql = gen.sql_kpis_plan(self.plan, {})
        self.assertIn(SEMANTIC["measures"]["valor_transferido"]["sql"], sql)
        mensual = gen.sql_chart(self.plan["charts"][0], {"mes": 8})
        self.assertNotIn("mes = 8", mensual)  # la evolución mensual no se recorta al mes elegido


if __name__ == "__main__":
    unittest.main()
